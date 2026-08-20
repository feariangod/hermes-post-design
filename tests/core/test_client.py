"""Trusted RED tests for the platform-neutral Chiyi HTTP client."""
from __future__ import annotations

import ast
import base64
import io
import inspect
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from hermes_post_design.chiyi_core.models import (
    CoreResult,
    EditRequest,
    GenerateRequest,
    ImageArtifact,
    ImageSource,
    LoadedSource,
)

API_KEY = "client-test-key"
PNG_B64 = base64.b64encode(
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x00\x05\x01\x00\x01\x7f\xe3\x10\x00\x00\x00\x00IEND\xaeB`\x82"
).decode("ascii")


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        *,
        headers=None,
        json_data=None,
        json_error=None,
        lines=(),
        iter_error=None,
        close_error=None,
    ):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}
        self._json_data = json_data
        self._json_error = json_error
        self._lines = tuple(lines)
        self._iter_error = iter_error
        self._close_error = close_error
        self.close_count = 0

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_data

    def iter_lines(self, **kwargs):
        if self._iter_error is not None:
            raise self._iter_error
        yield from self._lines

    def close(self):
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


def import_client():
    from hermes_post_design.chiyi_core import client

    return client


def make_client(session=None, **kwargs):
    module = import_client()
    return module.ChiyiClient(
        api_key=kwargs.pop("api_key", API_KEY),
        session=session if session is not None else Mock(),
        **kwargs,
    )


def make_artifact(tmp_path: Path) -> ImageArtifact:
    return ImageArtifact(
        path=tmp_path / "result.png",
        format="png",
        width=1024,
        height=1024,
        sha256="a" * 64,
        normalized=False,
    )


def generate_request(tmp_path: Path, **kwargs) -> GenerateRequest:
    values = {"prompt": "  a test image  ", "output_dir": tmp_path, "size": "1024x1024"}
    values.update(kwargs)
    return GenerateRequest(**values)


def edit_request(tmp_path: Path, **kwargs) -> EditRequest:
    values = {
        "prompt": "  edit this image  ",
        "output_dir": tmp_path,
        "primary_image": ImageSource("primary.png", role="primary"),
        "reference_images": (),
        "size": "1024x1024",
    }
    values.update(kwargs)
    return EditRequest(**values)


def loaded_sources(*names):
    return tuple(
        LoadedSource(name, b"source-" + name.encode(), "image/png") for name in names
    )


# Constructor and module boundary

def test_constructor_requires_api_key_and_session():
    from hermes_post_design.chiyi_core.client import ChiyiClient

    with pytest.raises(TypeError):
        ChiyiClient(session=Mock())
    with pytest.raises(TypeError):
        ChiyiClient(api_key=API_KEY)


def test_constructor_rejects_invalid_values_without_echoing_key():
    from hermes_post_design.chiyi_core.client import ChiyiClient

    for value in (None, 1, b"key"):
        with pytest.raises(TypeError):
            ChiyiClient(api_key=value, session=Mock())
    for value in ("", "  \t"):
        with pytest.raises(ValueError) as exc:
            ChiyiClient(api_key=value, session=Mock())
        assert len(str(exc.value)) <= 120
        if value:
            assert value not in str(exc.value)
    for value in (True, False, "300", 0, -1):
        with pytest.raises((TypeError, ValueError)):
            ChiyiClient(api_key=API_KEY, session=Mock(), timeout_seconds=value)
    for value in (True, False, "1", -1, 2):
        with pytest.raises((TypeError, ValueError)):
            ChiyiClient(api_key=API_KEY, session=Mock(), max_retries=value)


def test_constructor_signature_is_fixed_and_does_not_close_session():
    from hermes_post_design.chiyi_core.client import ChiyiClient

    signature = inspect.signature(ChiyiClient.__init__)
    assert list(signature.parameters) == [
        "self",
        "api_key",
        "session",
        "timeout_seconds",
        "max_retries",
    ]
    assert signature.parameters["timeout_seconds"].default == 300
    assert signature.parameters["max_retries"].default == 1
    assert not hasattr(ChiyiClient, "close")
    session = Mock()
    ChiyiClient(api_key=API_KEY, session=session)
    session.close.assert_not_called()


def test_client_module_has_no_hermes_or_environment_imports():
    path = Path("src/hermes_post_design/chiyi_core/client.py")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden = {"os", "dotenv", "hermes", "hermes_agent"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] not in forbidden for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in forbidden


# Preflight and fixed generation request

def test_generate_rejects_non_directory_output_path_before_post(tmp_path):
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("x", encoding="utf-8")
    session = Mock()
    result = make_client(session).generate(generate_request(tmp_path, output_dir=output_file))
    assert not result.success
    assert result.error.type == "invalid_argument"
    session.post.assert_not_called()


def test_generate_requires_request_and_does_not_post_on_preflight_failure(tmp_path):
    session = Mock()
    client = make_client(session)
    with pytest.raises(TypeError):
        client.generate({"prompt": "x"})
    for request in (
        generate_request(tmp_path, prompt="   "),
        generate_request(tmp_path, size="invalid"),
        generate_request(tmp_path, output_dir="not-a-path"),
    ):
        result = client.generate(request)
        assert isinstance(result, CoreResult)
        assert not result.success
        assert result.error.type == "invalid_argument"
        assert result.error.request_id == request.request_id
    assert session.post.call_count == 0


def test_generate_posts_exact_fixed_json_and_timeout(tmp_path):
    session = Mock()
    response = FakeResponse(json_data={"data": [{"b64_json": PNG_B64}]})
    session.post.return_value = response
    client = make_client(session, timeout_seconds=90, max_retries=0)
    module = import_client()
    with patch.object(module, "save_artifact", return_value=make_artifact(tmp_path)):
        result = client.generate(generate_request(tmp_path, request_id="req-1"))
    args, kwargs = session.post.call_args
    assert args == ("https://api.chiyi.cc/v1/images/generations",)
    assert kwargs["headers"] == {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json",
    }
    assert kwargs["json"] == {
        "model": "gpt-image-2",
        "prompt": "a test image",
        "size": "1024x1024",
        "quality": "high",
        "n": 1,
        "response_format": "b64_json",
    }
    assert kwargs["timeout"] == (15, 90.0)
    assert kwargs["allow_redirects"] is False
    assert "files" not in kwargs and "data" not in kwargs and "stream" not in kwargs
    assert result.success and result.artifact.width == 1024
    assert result.provider == "chiyi" and result.model == "gpt-image-2"
    assert result.quality == "high" and result.upstream_size == "1024x1024"
    assert response.close_count == 1


# Edit preflight and multipart

def test_edit_validates_before_loading_and_before_posting(tmp_path):
    session = Mock()
    client = make_client(session)
    module = import_client()
    with patch.object(module, "load_sources") as load:
        for request in (
            edit_request(tmp_path, prompt=""),
            edit_request(tmp_path, size="bad"),
            edit_request(tmp_path, output_dir="bad"),
            edit_request(
                tmp_path,
                reference_images=tuple(ImageSource(f"r{i}.png") for i in range(16)),
            ),
        ):
            result = client.edit(request)
            assert not result.success
            assert result.error.type == "invalid_argument"
        load.assert_not_called()
    session.post.assert_not_called()


def test_edit_loader_must_return_exact_requested_count_before_post(tmp_path):
    session = Mock()
    client = make_client(session)
    module = import_client()
    request = edit_request(
        tmp_path,
        reference_images=(ImageSource("reference.png"),),
    )
    with patch.object(module, "load_sources", return_value=loaded_sources("primary.png")):
        result = client.edit(request)
    assert not result.success
    assert result.error.type == "invalid_image"
    session.post.assert_not_called()


def test_edit_loads_primary_first_and_posts_exact_multipart(tmp_path):
    session = Mock()
    response = FakeResponse(json_data={"data": [{"b64_json": PNG_B64}]})
    session.post.return_value = response
    client = make_client(session, timeout_seconds=60, max_retries=0)
    module = import_client()
    sources = loaded_sources("primary.png", "reference.jpg")
    request = edit_request(
        tmp_path,
        reference_images=(ImageSource("reference.jpg"),),
    )
    with patch.object(module, "load_sources", return_value=sources) as load:
        with patch.object(module, "save_artifact", return_value=make_artifact(tmp_path)):
            result = client.edit(request)
    load.assert_called_once_with(request.primary_image, request.reference_images)
    args, kwargs = session.post.call_args
    assert args == ("https://api.chiyi.cc/v1/images/edits",)
    assert kwargs["headers"]["Authorization"] == f"Bearer {API_KEY}"
    assert kwargs["headers"]["Accept"] == "text/event-stream, application/json"
    assert kwargs["data"] == {
        "model": "gpt-image-2",
        "prompt": "edit this image",
        "size": "1024x1024",
        "quality": "high",
        "n": "1",
        "response_format": "b64_json",
        "stream": "true",
        "partial_images": "1",
    }
    assert kwargs["files"] == [
        ("image", ("primary.png", sources[0].data, "image/png")),
        ("image", ("reference.jpg", sources[1].data, "image/png")),
    ]
    assert kwargs["stream"] is True
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == (15, 60.0)
    assert "json" not in kwargs
    assert result.success and result.modality == "image"
    assert response.close_count == 1


def test_edit_source_errors_are_safe_and_do_not_post(tmp_path):
    session = Mock()
    client = make_client(session)
    module = import_client()
    secret = "C:/Users/secret/private.png?token=secret-value"
    request = edit_request(tmp_path, primary_image=ImageSource(secret, role="primary"))
    with patch.object(module, "load_sources", side_effect=RuntimeError(secret)):
        result = client.edit(request)
    assert not result.success
    assert result.error.type == "invalid_image"
    assert secret not in result.error.message
    assert "secret-value" not in result.error.message
    session.post.assert_not_called()


# Response cardinality, SSE, artifact handling, and lifecycle

@pytest.mark.parametrize(
    "body",
    [None, [], {}, {"data": []}, {"data": [{"b64_json": "x"}, {"b64_json": "y"}]},
     {"data": [{}]}, {"data": [{"b64_json": "", "url": "https://x"}]},
     {"data": [{"b64_json": 1}]}, {"data": [{"b64_json": "x", "url": "https://x"}]}],
)
def test_generate_invalid_json_success_shapes_are_protocol_errors(tmp_path, body):
    session = Mock()
    response = FakeResponse(json_data=body)
    session.post.return_value = response
    client = make_client(session, max_retries=0)
    result = client.generate(generate_request(tmp_path))
    assert not result.success
    assert result.error.type == "protocol_error"
    assert response.close_count == 1


def test_edit_sse_uses_stream_parser_and_passes_bytes_lines(tmp_path):
    session = Mock()
    response = FakeResponse(
        headers={"content-type": "Text/Event-Stream; charset=utf-8"},
        lines=[b"event: completed", b'data: {"b64_json":"x"}', b""],
    )
    session.post.return_value = response
    client = make_client(session, max_retries=0)
    module = import_client()
    sources = loaded_sources("primary.png")
    with patch.object(module, "load_sources", return_value=sources):
        with patch.object(module, "parse_sse", return_value=module.CompletedArtifact("b64_json", PNG_B64)) as parse:
            with patch.object(module, "save_artifact", return_value=make_artifact(tmp_path)):
                result = client.edit(edit_request(tmp_path))
    parse.assert_called_once()
    assert not isinstance(parse.call_args.args[0], list)
    assert result.success
    assert response.close_count == 1


def test_sse_parser_failure_is_protocol_error_and_not_retried(tmp_path):
    session = Mock()
    response = FakeResponse(headers={"content-type": "text/event-stream"}, lines=[])
    session.post.return_value = response
    client = make_client(session, max_retries=1)
    module = import_client()
    with patch.object(module, "load_sources", return_value=loaded_sources("primary.png")):
        with patch.object(module, "parse_sse", side_effect=ValueError("secret b64 payload")):
            result = client.edit(edit_request(tmp_path))
    assert not result.success and result.error.type == "protocol_error"
    assert "secret" not in result.error.message
    assert session.post.call_count == 1
    assert response.close_count == 1


def test_url_artifact_uses_secure_loader_not_session_get(tmp_path):
    session = Mock()
    session.post.return_value = FakeResponse(json_data={"data": [{"url": "https://example.com/a.png?token=secret"}]})
    client = make_client(session, max_retries=0)
    module = import_client()
    request = generate_request(tmp_path)
    with patch.object(module, "load_sources", return_value=loaded_sources("a.png")) as load:
        with patch.object(module, "save_artifact", return_value=make_artifact(tmp_path)):
            result = client.generate(request)
    load.assert_called_once()
    source, refs = load.call_args.args
    assert source == ImageSource("https://example.com/a.png?token=secret", role="primary")
    assert refs == ()
    session.get.assert_not_called()
    assert result.success


def test_invalid_base64_is_invalid_image_and_not_echoed(tmp_path):
    session = Mock()
    payload = "THIS_IS_NOT_BASE64_SECRET"
    session.post.return_value = FakeResponse(json_data={"data": [{"b64_json": payload}]})
    result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
    assert not result.success and result.error.type == "invalid_image"
    assert payload not in result.error.message


def test_save_errors_are_mapped_without_retry(tmp_path):
    session = Mock()
    session.post.return_value = FakeResponse(json_data={"data": [{"b64_json": PNG_B64}]})
    client = make_client(session, max_retries=1)
    module = import_client()
    for exc, error_type in (
        (ValueError("resolution insufficient"), "resolution_mismatch"),
        (ValueError("corrupt"), "invalid_image"),
        (OSError("disk"), "artifact_error"),
    ):
        session.post.reset_mock()
        session.post.return_value = FakeResponse(json_data={"data": [{"b64_json": PNG_B64}]})
        with patch.object(module, "save_artifact", side_effect=exc):
            result = client.generate(generate_request(tmp_path))
        assert not result.success and result.error.type == error_type
        assert session.post.call_count == 1


# HTTP status and exception hygiene

@pytest.mark.parametrize(
    "status,error_type",
    [(400, "invalid_argument"), (401, "auth_error"), (403, "auth_error"),
     (404, "invalid_argument"), (422, "invalid_argument"), (429, "rate_limited"),
     (500, "server_error"), (599, "server_error")],
)
def test_http_status_mapping(tmp_path, status, error_type):
    session = Mock()
    response = FakeResponse(status, json_data={"message": "generic upstream failure"})
    session.post.return_value = response
    result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
    assert not result.success and result.error.type == error_type
    assert len(result.error.message) <= 300
    assert API_KEY not in result.error.message
    assert "balance" not in result.error.message.lower()
    assert response.close_count == 1


def test_quota_markers_override_generic_4xx_and_5xx_but_not_auth(tmp_path):
    for status, expected in ((400, "quota_error"), (500, "quota_error"), (401, "auth_error")):
        session = Mock()
        response = FakeResponse(status, json_data={"message": "balance quota credit exhausted"})
        session.post.return_value = response
        result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
        assert not result.success and result.error.type == expected
        assert "balance" not in result.error.message.lower()
        assert "quota" not in result.error.message.lower()
        assert response.close_count == 1


def test_network_and_unexpected_post_errors_are_safe_and_not_retried(tmp_path):
    import requests

    for exc in (requests.Timeout("key-secret"), requests.ConnectionError("token-secret"), RuntimeError("raw-secret")):
        session = Mock()
        session.post.side_effect = exc
        result = make_client(session, max_retries=1).generate(generate_request(tmp_path))
        assert not result.success and result.error.type == "network_error"
        assert not result.error.retryable
        assert "secret" not in result.error.message
        assert session.post.call_count == 1


def test_non_2xx_body_objects_cannot_escape_via_string_conversion(tmp_path):
    class EvilBody:
        def __str__(self):
            raise RuntimeError("BODY_SECRET")

    session = Mock()
    response = FakeResponse(400, json_data=EvilBody())
    session.post.return_value = response
    result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
    assert not result.success
    assert result.error.type == "invalid_argument"
    assert "SECRET" not in result.error.message


def test_malicious_response_attribute_getters_are_sanitized(tmp_path):
    class BadResponse:
        @property
        def status_code(self):
            raise RuntimeError("STATUS_GETTER_SECRET")

        @property
        def close(self):
            raise RuntimeError("CLOSE_GETTER_SECRET")

    session = Mock()
    session.post.return_value = BadResponse()
    result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
    assert not result.success
    assert result.error.type == "protocol_error"
    assert "SECRET" not in result.error.message


def test_malformed_response_none_status_and_json_exception_are_protocol_errors(tmp_path):
    session = Mock()
    client = make_client(session, max_retries=0)
    for response in (
        None,
        FakeResponse(status_code=True, json_data={"data": []}),
        FakeResponse(status_code="200", json_data={"data": []}),
        FakeResponse(status_code=200, json_error=ValueError("raw body secret")),
    ):
        session.post.reset_mock()
        session.post.return_value = response
        result = client.generate(generate_request(tmp_path))
        assert not result.success and result.error.type == "protocol_error"
        if response is not None:
            assert response.close_count == 1


def test_response_close_exception_does_not_mask_success_or_error(tmp_path):
    session = Mock()
    response = FakeResponse(
        json_data={"data": [{"b64_json": PNG_B64}]},
        close_error=RuntimeError("close secret"),
    )
    session.post.return_value = response
    module = import_client()
    with patch.object(module, "save_artifact", return_value=make_artifact(tmp_path)):
        result = make_client(session, max_retries=0).generate(generate_request(tmp_path))
    assert result.success
    assert response.close_count == 1


def test_no_stdout_or_stderr_on_result(tmp_path, capsys):
    session = Mock()
    session.post.return_value = FakeResponse(status_code=401, json_data={"error": "secret"})
    make_client(session, max_retries=0).generate(generate_request(tmp_path))
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
