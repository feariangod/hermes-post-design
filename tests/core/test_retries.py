"""Trusted RED tests for the only allowed paid-request retry: HTTP 429."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

import base64

from hermes_post_design.chiyi_core.models import GenerateRequest, ImageArtifact

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
        close_error=None,
    ):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}
        self._json_data = json_data
        self._close_error = close_error
        self.close_count = 0

    def json(self):
        return self._json_data

    def close(self):
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


def import_client():
    from hermes_post_design.chiyi_core import client

    return client


def request(tmp_path: Path) -> GenerateRequest:
    return GenerateRequest(prompt="retry test", output_dir=tmp_path, size="1024x1024")


def artifact(tmp_path: Path) -> ImageArtifact:
    return ImageArtifact(
        path=tmp_path / "retry.png",
        format="png",
        width=1024,
        height=1024,
        sha256="b" * 64,
        normalized=False,
    )


def client_for(session, retries=1):
    module = import_client()
    return module.ChiyiClient(
        api_key=API_KEY,
        session=session,
        timeout_seconds=300,
        max_retries=retries,
    )


def success_response():
    return FakeResponse(json_data={"data": [{"b64_json": PNG_B64}]})


def test_429_then_success_posts_twice_and_closes_first_before_second(tmp_path):
    first = FakeResponse(429, headers={"Retry-After": "0"}, json_data={})
    second = success_response()
    session = Mock()

    def post(*args, **kwargs):
        if session.post.call_count == 1:
            return first
        assert first.close_count == 1
        return second

    session.post.side_effect = post
    module = import_client()
    with patch.object(module.time, "sleep") as sleep:
        with patch.object(module, "save_artifact", return_value=artifact(tmp_path)):
            result = client_for(session).generate(request(tmp_path))
    assert result.success
    assert session.post.call_count == 2
    assert first.close_count == 1 and second.close_count == 1
    assert sleep.call_count <= 1
    assert session.post.call_args_list[0].args == session.post.call_args_list[1].args
    assert session.post.call_args_list[0].kwargs == session.post.call_args_list[1].kwargs


def test_429_then_429_stops_after_one_retry_and_is_retryable(tmp_path):
    first = FakeResponse(429, headers={"Retry-After": "1"}, json_data={})
    second = FakeResponse(429, headers={"Retry-After": "1"}, json_data={})
    session = Mock()
    session.post.side_effect = [first, second]
    module = import_client()
    with patch.object(module.time, "sleep"):
        result = client_for(session).generate(request(tmp_path))
    assert not result.success
    assert result.error.type == "rate_limited"
    assert result.error.retryable is True
    assert session.post.call_count == 2
    assert first.close_count == 1 and second.close_count == 1


def test_max_retries_zero_does_not_retry_429(tmp_path):
    response = FakeResponse(429, headers={"Retry-After": "1"}, json_data={})
    session = Mock()
    session.post.return_value = response
    module = import_client()
    with patch.object(module.time, "sleep") as sleep:
        result = client_for(session, retries=0).generate(request(tmp_path))
    assert result.error.type == "rate_limited"
    assert result.error.retryable is True
    assert session.post.call_count == 1
    sleep.assert_not_called()
    assert response.close_count == 1


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"Retry-After": "2.5"}, 2.5),
        ({"retry-after": "-4"}, 0.0),
        ({"RETRY-AFTER": "999"}, 5.0),
        ({"Retry-After": "invalid"}, 1.0),
        ({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}, 1.0),
        ({"Retry-After": "NaN"}, 1.0),
        ({"Retry-After": "Infinity"}, 1.0),
        ({}, 1.0),
    ],
)
def test_retry_after_is_case_insensitive_and_clamped(tmp_path, headers, expected):
    session = Mock()
    session.post.side_effect = [FakeResponse(429, headers=headers), success_response()]
    module = import_client()
    with patch.object(module.time, "sleep") as sleep:
        with patch.object(module, "save_artifact", return_value=artifact(tmp_path)):
            result = client_for(session).generate(request(tmp_path))
    assert result.success
    sleep.assert_called_once_with(expected)


@pytest.mark.parametrize("status", [400, 401, 403, 422, 500, 599])
def test_non_429_status_never_retries(tmp_path, status):
    response = FakeResponse(status, json_data={})
    session = Mock()
    session.post.return_value = response
    result = client_for(session).generate(request(tmp_path))
    assert not result.success
    assert session.post.call_count == 1
    assert response.close_count == 1


@pytest.mark.parametrize(
    "failure",
    [
        requests.Timeout("timeout"),
        requests.ConnectionError("connection"),
        RuntimeError("unexpected"),
    ],
)
def test_post_exceptions_never_retry(tmp_path, failure):
    session = Mock()
    session.post.side_effect = failure
    result = client_for(session).generate(request(tmp_path))
    assert result.error.type == "network_error"
    assert session.post.call_count == 1


def test_malformed_success_never_retries(tmp_path):
    response = FakeResponse(200, json_data={"data": []})
    session = Mock()
    session.post.return_value = response
    result = client_for(session).generate(request(tmp_path))
    assert result.error.type == "protocol_error"
    assert session.post.call_count == 1


def test_artifact_save_failure_never_retries(tmp_path):
    session = Mock()
    session.post.return_value = success_response()
    module = import_client()
    with patch.object(module, "save_artifact", side_effect=OSError("disk")):
        result = client_for(session).generate(request(tmp_path))
    assert result.error.type == "artifact_error"
    assert session.post.call_count == 1


def test_close_failure_on_first_429_does_not_prevent_retry(tmp_path):
    first = FakeResponse(
        429,
        headers={"Retry-After": "0"},
        close_error=RuntimeError("close"),
    )
    session = Mock()
    session.post.side_effect = [first, success_response()]
    module = import_client()
    with patch.object(module.time, "sleep"):
        with patch.object(module, "save_artifact", return_value=artifact(tmp_path)):
            result = client_for(session).generate(request(tmp_path))
    assert result.success
    assert session.post.call_count == 2
    assert first.close_count == 1
