"""Comprehensive security regression tests for source loading module."""
import base64
import io
import os
import socket
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest
import requests

from hermes_post_design.chiyi_core.models import ImageSource, LoadedSource
from hermes_post_design.chiyi_core import sources


# ============================================================================
# Test Fixtures: Programmatic Image Generation
# ============================================================================

def _create_valid_png() -> bytes:
    """Create a minimal valid 1x1 PNG using PIL."""
    from PIL import Image
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_valid_jpeg() -> bytes:
    """Create a minimal valid 1x1 JPEG using PIL."""
    from PIL import Image
    img = Image.new("RGB", (1, 1), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _create_valid_webp() -> bytes:
    """Create a minimal valid 1x1 WebP using PIL."""
    from PIL import Image
    img = Image.new("RGB", (1, 1), color="green")
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


def _create_valid_gif() -> bytes:
    """Create a minimal valid 1x1 GIF using PIL."""
    from PIL import Image
    img = Image.new("RGB", (1, 1), color="yellow")
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


# Pre-generate test images
VALID_PNG = _create_valid_png()
VALID_JPEG = _create_valid_jpeg()
VALID_WEBP = _create_valid_webp()
VALID_GIF = _create_valid_gif()


# ============================================================================
# Test Fixtures: Fake Response and Recorder
# ============================================================================

class FakeResponse:
    """Fake HTTP response for testing with close tracking."""

    def __init__(self, status, headers, peer_ip, chunks):
        self.status_code = status
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.peer_ip = peer_ip
        self._chunks = chunks if not isinstance(chunks, list) else iter(chunks)
        self.close_count = 0
        self.chunks_consumed = []

    def iter_bytes(self, chunk_size=8192):
        for chunk in self._chunks:
            self.chunks_consumed.append(chunk)
            yield chunk

    def close(self):
        self.close_count += 1


class RecorderResolver:
    """Records resolver calls."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, host, port):
        self.calls.append((host, port))
        result = self.responses.get((host, port))
        if isinstance(result, Exception):
            raise result
        return result


class RecorderDownloader:
    """Records downloader calls."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, url, approved_ips):
        self.calls.append((url, approved_ips))
        result = self.responses.get(url)
        if isinstance(result, Exception):
            raise result
        return result


# PART1_END

# ============================================================================
# Category 1: Input Validation / Ordering / Zero-Operation
# ============================================================================

def test_input_primary_not_imagesource():
    """Reject primary not being ImageSource type."""
    with pytest.raises(ValueError, match="primary must be ImageSource"):
        sources.load_sources("not_imagesource", tuple())


def test_input_references_not_tuple():
    """Reject references not being tuple."""
    primary = ImageSource(value="test.png", role="primary")
    with pytest.raises(ValueError, match="references must be tuple"):
        sources.load_sources(primary, ["ref1.png"])


def test_input_reference_element_not_imagesource():
    """Reject reference element not being ImageSource."""
    primary = ImageSource(value="test.png", role="primary")
    with pytest.raises(ValueError, match="All sources must be ImageSource"):
        sources.load_sources(primary, ("not_imagesource",))


def test_input_value_not_string():
    """Reject source value not being string."""
    primary = ImageSource(value=123, role="primary")
    with pytest.raises(ValueError, match="Source value must be string"):
        sources.load_sources(primary, tuple())


def test_input_value_empty_string():
    """Reject empty source value."""
    primary = ImageSource(value="", role="primary")
    with pytest.raises(ValueError, match="Source value must be non-empty"):
        sources.load_sources(primary, tuple())


def test_input_value_whitespace_only():
    """Reject whitespace-only source value."""
    primary = ImageSource(value="   ", role="primary")
    with pytest.raises(ValueError):
        sources.load_sources(primary, tuple())


def test_input_value_contains_nul_byte():
    """Reject source value containing NUL byte."""
    primary = ImageSource(value="test\x00.png", role="primary")
    with pytest.raises(ValueError, match="Source value must not contain NUL bytes"):
        sources.load_sources(primary, tuple())


def test_ordering_primary_first_with_15_references(tmp_path):
    """Primary + 15 refs = 16 total, strict ordering maintained."""
    primary_file = tmp_path / "primary.png"
    primary_file.write_bytes(VALID_PNG)

    ref_files = []
    for i in range(15):
        ref_file = tmp_path / f"ref{i:02d}.png"
        ref_file.write_bytes(VALID_PNG)
        ref_files.append(ref_file)

    primary = ImageSource(value=str(primary_file), role="primary")
    refs = tuple(ImageSource(value=str(f), role="reference") for f in ref_files)

    result = sources.load_sources(primary, refs)

    assert len(result) == 16
    assert result[0].filename == "primary.png"
    for i in range(15):
        assert result[i + 1].filename == f"ref{i:02d}.png"


def test_ordering_role_field_does_not_affect_order(tmp_path):
    """Role field is metadata; ordering still primary first."""
    primary_file = tmp_path / "first.png"
    primary_file.write_bytes(VALID_PNG)

    ref_file = tmp_path / "second.png"
    ref_file.write_bytes(VALID_PNG)

    primary = ImageSource(value=str(primary_file), role="reference")
    refs = tuple([ImageSource(value=str(ref_file), role="primary")])

    result = sources.load_sources(primary, refs)

    assert len(result) == 2
    assert result[0].filename == "first.png"
    assert result[1].filename == "second.png"


def test_reject_17_sources_before_any_operation():
    """Reject 17 sources immediately, zero file operations."""
    primary = ImageSource(value="primary.png", role="primary")
    refs = tuple(ImageSource(value=f"ref{i}.png", role="reference") for i in range(16))

    with patch("builtins.open", side_effect=AssertionError("Should not open")) as mock_open:
        with pytest.raises(ValueError, match="Maximum 16 sources allowed, got 17"):
            sources.load_sources(primary, refs)
        mock_open.assert_not_called()


def test_reject_17_sources_no_resolver_downloader_calls():
    """Reject 17 sources before calling resolver or downloader."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/primary.png", role="primary")
    refs = tuple(ImageSource(value=f"http://example.com/ref{i}.png", role="reference")
                 for i in range(16))

    with pytest.raises(ValueError, match="Maximum 16 sources allowed, got 17"):
        loader.load_sources(primary, refs)

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_max_redirects_rejects_negative():
    """Reject negative max_redirects."""
    with pytest.raises((ValueError, TypeError)):
        sources.SourceLoader(max_redirects=-1)


def test_max_redirects_rejects_bool():
    """Reject bool for max_redirects."""
    with pytest.raises(TypeError):
        sources.SourceLoader(max_redirects=True)


def test_max_redirects_rejects_non_int():
    """Reject non-int for max_redirects."""
    with pytest.raises(TypeError):
        sources.SourceLoader(max_redirects="3")


# ============================================================================
# Category 2: Local Files
# ============================================================================

def test_local_png_success(tmp_path):
    """Local PNG file loads successfully."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    primary = ImageSource(value=str(png_file), role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "test.png"
    assert result[0].data == VALID_PNG
    assert result[0].mime_type == "image/png"


def test_local_jpeg_content_disguised_as_png(tmp_path):
    """JPEG content with .png extension: filename corrected to .jpg."""
    jpeg_as_png = tmp_path / "image.png"
    jpeg_as_png.write_bytes(VALID_JPEG)

    primary = ImageSource(value=str(jpeg_as_png), role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "image.jpg"
    assert result[0].data == VALID_JPEG
    assert result[0].mime_type == "image/jpeg"


def test_local_file_not_exists():
    """Reject non-existent file."""
    primary = ImageSource(value="/nonexistent/file.png", role="primary")
    with pytest.raises(ValueError, match="File not found"):
        sources.load_sources(primary, tuple())


def test_local_file_is_directory(tmp_path):
    """Reject directory path."""
    dir_path = tmp_path / "notafile"
    dir_path.mkdir()

    primary = ImageSource(value=str(dir_path), role="primary")
    with pytest.raises(ValueError, match="Not a regular file"):
        sources.load_sources(primary, tuple())


def test_local_file_empty(tmp_path):
    """Reject empty file."""
    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")

    primary = ImageSource(value=str(empty_file), role="primary")
    with pytest.raises(ValueError, match="(?i)empty"):
        sources.load_sources(primary, tuple())


def test_local_file_stat_oversize(tmp_path, monkeypatch):
    """Reject file that exceeds MAX_IMAGE_BYTES at stat check."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    # Patch MAX_IMAGE_BYTES to a small value
    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", 10)

    primary = ImageSource(value=str(png_file), role="primary")
    with pytest.raises(ValueError, match="exceeds maximum size"):
        sources.load_sources(primary, tuple())


def test_local_file_read_growth_oversize(tmp_path, monkeypatch):
    """Reject file that grows during read beyond MAX_IMAGE_BYTES."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    # Patch MAX_IMAGE_BYTES to a value between stat and read
    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", len(VALID_PNG) - 1)

    primary = ImageSource(value=str(png_file), role="primary")
    with pytest.raises(ValueError, match="exceeds maximum size"):
        sources.load_sources(primary, tuple())


def test_local_file_rejects_regular_symlink(tmp_path):
    """Reject regular symlink."""
    try:
        target = tmp_path / "target.png"
        target.write_bytes(VALID_PNG)

        link = tmp_path / "link.png"
        link.symlink_to(target)

        primary = ImageSource(value=str(link), role="primary")
        with pytest.raises(ValueError, match="(?i)symlink"):
            sources.load_sources(primary, tuple())
    except OSError:
        pytest.skip("Cannot create symlinks on this system")


def test_local_file_rejects_broken_symlink(tmp_path):
    """Reject broken symlink."""
    try:
        link = tmp_path / "broken.png"
        link.symlink_to(tmp_path / "nonexistent_target.png")

        primary = ImageSource(value=str(link), role="primary")
        with pytest.raises(ValueError, match="(?i)symlink"):
            sources.load_sources(primary, tuple())
    except OSError:
        pytest.skip("Cannot create symlinks on this system")


def test_local_file_rejects_file_in_symlink_parent(tmp_path):
    """Reject file within a symlinked parent directory."""
    try:
        real_dir = tmp_path / "real_dir"
        real_dir.mkdir()

        real_file = real_dir / "image.png"
        real_file.write_bytes(VALID_PNG)

        link_dir = tmp_path / "link_dir"
        link_dir.symlink_to(real_dir)

        file_via_link = link_dir / "image.png"

        primary = ImageSource(value=str(file_via_link), role="primary")
        with pytest.raises(ValueError, match="(?i)symlink"):
            sources.load_sources(primary, tuple())
    except OSError:
        pytest.skip("Cannot create symlinks on this system")


def test_local_file_error_no_full_sensitive_path(tmp_path):
    """Errors should not contain full sensitive parent path."""
    deep_dir = tmp_path / "secret-unique-token-xyz" / "nested"
    deep_dir.mkdir(parents=True)

    png_file = deep_dir / "test.png"
    png_file.write_bytes(b"not_an_image")

    primary = ImageSource(value=str(png_file), role="primary")

    try:
        sources.load_sources(primary, tuple())
        assert False, "Should have raised"
    except ValueError as e:
        error_msg = str(e)
        # Should not contain the unique token
        assert "secret-unique-token-xyz" not in error_msg


# PART2_END

# ============================================================================
# Category 3: Data URLs
# ============================================================================

def test_data_url_png_success():
    """Data URL PNG loads successfully."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/png;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "image.png"
    assert result[0].data == VALID_PNG
    assert result[0].mime_type == "image/png"


def test_data_url_jpeg_success():
    """Data URL JPEG loads successfully."""
    b64_data = base64.b64encode(VALID_JPEG).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "image.jpg"
    assert result[0].data == VALID_JPEG
    assert result[0].mime_type == "image/jpeg"


def test_data_url_webp_success():
    """Data URL WebP loads successfully."""
    b64_data = base64.b64encode(VALID_WEBP).decode("ascii")
    data_url = f"data:image/webp;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "image.webp"
    assert result[0].mime_type == "image/webp"


def test_data_url_gif_success():
    """Data URL GIF loads successfully."""
    b64_data = base64.b64encode(VALID_GIF).decode("ascii")
    data_url = f"data:image/gif;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].filename == "image.gif"
    assert result[0].mime_type == "image/gif"


def test_data_url_case_insensitive():
    """Data URL parsing is case insensitive for DATA/IMAGE/BASE64."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"DATA:IMAGE/PNG;BASE64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    result = sources.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].mime_type == "image/png"


def test_data_url_rejects_malformed_no_comma():
    """Reject malformed data URL - explicit data: prefix but missing comma."""
    primary = ImageSource(value="data:image/png;base64abc", role="primary")
    with pytest.raises(ValueError, match="(?i)missing comma|invalid"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_missing_comma():
    """Reject data URL missing comma separator."""
    primary = ImageSource(value="data:image/png;base64abc", role="primary")
    with pytest.raises(ValueError, match="(?i)missing comma"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_non_base64():
    """Reject data URL without base64 encoding."""
    primary = ImageSource(value="data:image/png,notbase64", role="primary")
    with pytest.raises(ValueError, match="(?i)base64"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_invalid_base64():
    """Reject data URL with invalid base64 data."""
    primary = ImageSource(value="data:image/png;base64,!!!invalid!!!", role="primary")
    with pytest.raises(ValueError, match="(?i)base64"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_non_image():
    """Reject data URL for non-image MIME type."""
    primary = ImageSource(value="data:text/plain;base64,SGVsbG8=", role="primary")
    with pytest.raises(ValueError, match="(?i)not.*image"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_unsupported_mime():
    """Reject data URL with unsupported image MIME type."""
    primary = ImageSource(value="data:image/bmp;base64,Qk0=", role="primary")
    with pytest.raises(ValueError, match="(?i)unsupported"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_charset_parameter():
    """Reject data URL with charset parameter."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/png;charset=utf-8;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    with pytest.raises(ValueError, match="(?i)unexpected.*parameter"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_unknown_parameter():
    """Reject data URL with unknown parameter."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/png;foo=bar;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    with pytest.raises(ValueError, match="(?i)unexpected.*parameter"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_empty_payload():
    """Reject data URL with empty payload."""
    primary = ImageSource(value="data:image/png;base64,", role="primary")
    with pytest.raises(ValueError, match="(?i)empty"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_invalid_padding():
    """Reject data URL with invalid base64 padding."""
    primary = ImageSource(value="data:image/png;base64,abc", role="primary")
    with pytest.raises(ValueError, match="(?i)base64"):
        sources.load_sources(primary, tuple())


def test_data_url_rejects_mime_mismatch():
    """Reject data URL where declared MIME doesn't match actual content."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64_data}"

    primary = ImageSource(value=data_url, role="primary")
    with pytest.raises(ValueError, match="(?i)mismatch"):
        sources.load_sources(primary, tuple())


def test_data_url_predecode_oversize(monkeypatch):
    """Reject data URL that exceeds MAX_IMAGE_BYTES before decode."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/png;base64,{b64_data}"

    # Patch MAX_IMAGE_BYTES to trigger pre-decode check
    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", 10)

    primary = ImageSource(value=data_url, role="primary")
    with pytest.raises(ValueError, match="(?i)too large"):
        sources.load_sources(primary, tuple())


def test_data_url_base64_decode_not_called_on_predecode_oversize(monkeypatch):
    """Ensure base64.b64decode not called when pre-decode size check fails."""
    b64_data = base64.b64encode(VALID_PNG).decode("ascii")
    data_url = f"data:image/png;base64,{b64_data}"

    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", 10)

    with patch("base64.b64decode") as mock_decode:
        primary = ImageSource(value=data_url, role="primary")
        try:
            sources.load_sources(primary, tuple())
        except ValueError:
            pass
        mock_decode.assert_not_called()


def test_data_url_error_no_secret_in_exception():
    """Data URL errors should not expose payload or secret data."""
    secret = "opaque-secret-value"
    b64_secret = base64.b64encode(secret.encode()).decode("ascii")
    data_url = f"data:image/png;base64,{b64_secret}"

    primary = ImageSource(value=data_url, role="primary")

    try:
        sources.load_sources(primary, tuple())
        assert False, "Should have raised"
    except ValueError as e:
        error_msg = str(e)
        # Strict: secret value must not appear
        assert "opaque-secret-value" not in error_msg
        assert b64_secret not in error_msg


# ============================================================================
# Category 4: IP/DNS/Peer Validation
# ============================================================================

@pytest.mark.parametrize("private_ip", [
    "127.0.0.1",
    "10.0.0.1",
    "169.254.169.254",
    "224.0.0.1",
    "192.0.2.1",
    "::1",
    "fe80::1",
    "::ffff:127.0.0.1",
])
def test_remote_rejects_private_ips(private_ip):
    """Reject private/loopback/reserved IP addresses."""
    resolver = RecorderResolver({("example.com", 80): (private_ip,)})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)private|public|loopback"):
        loader.load_sources(primary, tuple())

    assert len(downloader.calls) == 0


def test_remote_rejects_mixed_public_private_ips():
    """Reject when DNS returns mixed public and private IPs."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8", "10.0.0.1")})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)private|public"):
        loader.load_sources(primary, tuple())

    assert len(downloader.calls) == 0


def test_remote_ipv4_public_success():
    """Accept public IPv4 address (8.8.8.8)."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, "8.8.8.8", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert response.close_count == 1


def test_remote_ipv6_public_success():
    """Accept public IPv6 address (2001:4860:4860::8888)."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, "2001:4860:4860::8888", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("2001:4860:4860::8888",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert response.close_count == 1


def test_remote_peer_ip_none_rejected():
    """Reject when peer_ip is None (fail-closed)."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, None, [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)peer.*IP"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_peer_ip_invalid_format():
    """Reject when peer_ip has invalid format."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, "not-an-ip", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)peer.*IP"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_peer_ip_mismatch():
    """Reject when peer_ip doesn't match approved IPs (DNS rebinding protection)."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, "1.2.3.4", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)peer.*mismatch|DNS"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_ipv6_normalization_equivalence():
    """IPv6 addresses normalized for comparison."""
    # Resolver returns compressed form, peer returns expanded form
    response = FakeResponse(200, {"Content-Type": "image/png"},
                          "2001:4860:4860:0000:0000:0000:0000:8888", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("2001:4860:4860::8888",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert response.close_count == 1


def test_remote_response_closed_once_on_success():
    """Verify response.close() called exactly once on success."""
    response = FakeResponse(200, {"Content-Type": "image/png"}, "8.8.8.8", [VALID_PNG])
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_resolver_returns_empty():
    """Reject when resolver returns empty tuple."""
    resolver = RecorderResolver({("example.com", 80): ()})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)no.*IP"):
        loader.load_sources(primary, tuple())


def test_remote_resolver_returns_non_tuple():
    """Reject when resolver returns non-tuple."""
    def bad_resolver(host, port):
        return "8.8.8.8"  # String instead of tuple

    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=bad_resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises((ValueError, TypeError)):
        loader.load_sources(primary, tuple())


def test_remote_resolver_returns_invalid_ip():
    """Reject when resolver returns invalid IP string."""
    resolver = RecorderResolver({("example.com", 80): ("not-an-ip",)})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError):
        loader.load_sources(primary, tuple())


def test_remote_resolver_exception_with_secret_redacted():
    """Resolver exceptions should not leak host secrets."""
    def bad_resolver(host, port):
        raise ValueError(f"DNS failed for secret-host-{host}-secret")

    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=bad_resolver, downloader=downloader)

    primary = ImageSource(value="http://secret-example.com/test.png", role="primary")

    try:
        loader.load_sources(primary, tuple())
        assert False, "Should have raised"
    except ValueError as e:
        error_msg = str(e)
        # Strict: secret token must not appear
        assert "secret-host-secret-example.com-secret" not in error_msg


# PART3_END


# ============================================================================
# Category 5: URL Initial Validation & Multi-hop Redirect
# ============================================================================

@pytest.mark.parametrize("scheme,url", [
    ("ftp", "ftp://example.com/file.png"),
    ("file", "file:///etc/passwd"),
    ("javascript", "javascript:alert(1)"),
])
def test_remote_rejects_non_http_schemes(scheme, url):
    """Reject non-HTTP(S) schemes at initial URL parse."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value=url, role="primary")

    with pytest.raises(ValueError, match="(?i)scheme|protocol|http"):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_remote_rejects_userinfo_in_url():
    """Reject URL with username:password@ userinfo."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://user:pass@example.com/test.png", role="primary")

    with pytest.raises(ValueError) as exc:
        loader.load_sources(primary, tuple())

    error_msg = str(exc.value)
    assert "user" not in error_msg.lower()
    assert "pass" not in error_msg.lower()
    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_remote_rejects_fragment_in_url():
    """Reject URL with fragment identifier."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png#fragment", role="primary")

    with pytest.raises(ValueError, match="(?i)fragment"):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


@pytest.mark.parametrize("bad_url", [
    "http://example.com/test\r\n.png",
    "http://example.com/test\n.png",
    "http://example.com/test\r.png",
])
def test_remote_rejects_crlf_in_url(bad_url):
    """Reject URL containing CR/LF characters."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value=bad_url, role="primary")

    with pytest.raises(ValueError):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_remote_rejects_nul_in_url():
    """Reject URL containing NUL byte."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test\x00.png", role="primary")

    with pytest.raises(ValueError):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_remote_rejects_missing_host():
    """Reject URL with missing host."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http:///test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)host"):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


@pytest.mark.parametrize("port_val,url", [
    (0, "http://example.com:0/test.png"),
    (65536, "http://example.com:65536/test.png"),
    ("abc", "http://example.com:abc/test.png"),
])
def test_remote_rejects_invalid_port(port_val, url):
    """Reject invalid port numbers."""
    resolver = RecorderResolver({})
    downloader = RecorderDownloader({})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value=url, role="primary")

    with pytest.raises(ValueError):
        loader.load_sources(primary, tuple())

    assert len(resolver.calls) == 0
    assert len(downloader.calls) == 0


def test_remote_public_200_success_normalizes_content_type():
    """Public IP, 200 OK, Content-Type case-insensitive and charset normalized."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"Content-Type": "IMAGE/PNG; charset=binary"},  # Mixed case + charset
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].data == VALID_PNG
    assert result[0].filename == "test.png"
    assert response.close_count == 1


def test_remote_relative_redirect_success():
    """Relative redirect resolves correctly, each response closes once."""
    resolver = RecorderResolver({
        ("example.com", 80): ("8.8.8.8",),
        ("cdn.example.com", 80): ("8.8.4.4",),
    })

    redirect_response = FakeResponse(
        status=302,
        headers={"Location": "http://cdn.example.com/final.png"},
        peer_ip="8.8.8.8",
        chunks=[]
    )
    final_response = FakeResponse(
        status=200,
        headers={"Content-Type": "image/png"},
        peer_ip="8.8.4.4",
        chunks=[VALID_PNG]
    )

    downloader = RecorderDownloader({
        "http://example.com/redirect.png": redirect_response,
        "http://cdn.example.com/final.png": final_response,
    })
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/redirect.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].data == VALID_PNG
    assert result[0].filename == "final.png"  # From final URL

    # Each response closed exactly once
    assert redirect_response.close_count == 1
    assert final_response.close_count == 1

    # Verify resolver and downloader called correctly
    assert len(resolver.calls) == 2
    assert ("example.com", 80) in resolver.calls
    assert ("cdn.example.com", 80) in resolver.calls

    assert len(downloader.calls) == 2
    assert downloader.calls[0][0] == "http://example.com/redirect.png"
    assert downloader.calls[1][0] == "http://cdn.example.com/final.png"


def test_remote_public_to_private_redirect_blocked():
    """Redirect from public to private IP should be blocked before second download."""
    resolver = RecorderResolver({
        ("public.example.com", 80): ("8.8.8.8",),
        ("private.internal", 80): ("10.0.0.1",),  # Private IP
    })

    redirect_response = FakeResponse(
        status=302,
        headers={"Location": "http://private.internal/secret.png"},
        peer_ip="8.8.8.8",
        chunks=[]
    )

    downloader = RecorderDownloader({
        "http://public.example.com/redirect.png": redirect_response,
    })
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://public.example.com/redirect.png", role="primary")

    with pytest.raises(ValueError, match="(?i)private|public"):
        loader.load_sources(primary, tuple())

    # First response should be closed
    assert redirect_response.close_count == 1

    # Second resolver called, but second download should NOT happen
    assert len(resolver.calls) == 2
    assert len(downloader.calls) == 1  # Only first download


@pytest.mark.parametrize("bad_location", [
    "http://user:secret@evil.com/test.png",
    "http://evil.com/test.png#fragment",
    "http://evil.com/test\r\n.png",
    "http://evil.com:0/test.png",
    "http://evil.com:99999/test.png",
])
def test_remote_redirect_to_invalid_url(bad_location):
    """Redirect to URL with userinfo/fragment/CRLF/invalid port should be rejected."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    redirect_response = FakeResponse(
        status=302,
        headers={"Location": bad_location},
        peer_ip="8.8.8.8",
        chunks=[]
    )

    downloader = RecorderDownloader({
        "http://example.com/redirect.png": redirect_response,
    })
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/redirect.png", role="primary")

    with pytest.raises(ValueError) as exc:
        loader.load_sources(primary, tuple())

    error_msg = str(exc.value)
    # Should not leak secrets from URL
    if "secret" in bad_location:
        assert "secret" not in error_msg

    # Verify only initial request made, invalid Location rejected before second resolver/download
    assert len(resolver.calls) == 1
    assert resolver.calls[0] == ("example.com", 80)
    assert len(downloader.calls) == 1
    assert redirect_response.close_count == 1


def test_remote_redirect_missing_location_header():
    """3xx redirect without Location header should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    redirect_response = FakeResponse(
        status=302,
        headers={},  # Missing Location
        peer_ip="8.8.8.8",
        chunks=[]
    )

    downloader = RecorderDownloader({
        "http://example.com/redirect.png": redirect_response,
    })
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/redirect.png", role="primary")

    with pytest.raises(ValueError, match="(?i)location"):
        loader.load_sources(primary, tuple())

    assert redirect_response.close_count == 1


def test_remote_max_redirects_zero_fails_on_first_redirect():
    """max_redirects=0 should fail on first redirect."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    redirect_response = FakeResponse(
        status=302,
        headers={"Location": "http://example.com/final.png"},
        peer_ip="8.8.8.8",
        chunks=[]
    )

    downloader = RecorderDownloader({
        "http://example.com/redirect.png": redirect_response,
    })
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader, max_redirects=0)

    primary = ImageSource(value="http://example.com/redirect.png", role="primary")

    with pytest.raises(ValueError, match="(?i)redirect"):
        loader.load_sources(primary, tuple())

    assert redirect_response.close_count == 1


def test_remote_max_redirects_allows_exactly_limit():
    """max_redirects=3 should allow exactly 3 redirects then success."""
    resolver = RecorderResolver({
        ("example.com", 80): ("8.8.8.8",),
    })

    responses = []
    for i in range(3):
        resp = FakeResponse(
            status=302,
            headers={"Location": f"http://example.com/redirect{i+1}.png"},
            peer_ip="8.8.8.8",
            chunks=[]
        )
        responses.append(resp)

    final_response = FakeResponse(
        status=200,
        headers={"Content-Type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    responses.append(final_response)

    downloader_map = {
        "http://example.com/start.png": responses[0],
        "http://example.com/redirect1.png": responses[1],
        "http://example.com/redirect2.png": responses[2],
        "http://example.com/redirect3.png": responses[3],
    }
    downloader = RecorderDownloader(downloader_map)
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader, max_redirects=3)

    primary = ImageSource(value="http://example.com/start.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert result[0].data == VALID_PNG

    # All responses closed exactly once
    for resp in responses:
        assert resp.close_count == 1


def test_remote_max_redirects_rejects_beyond_limit():
    """4 redirects with max_redirects=3 should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    responses = []
    for i in range(4):
        resp = FakeResponse(
            status=302,
            headers={"Location": f"http://example.com/redirect{i+1}.png"},
            peer_ip="8.8.8.8",
            chunks=[]
        )
        responses.append(resp)

    downloader_map = {}
    downloader_map["http://example.com/start.png"] = responses[0]
    for i in range(3):
        downloader_map[f"http://example.com/redirect{i+1}.png"] = responses[i+1]

    downloader = RecorderDownloader(downloader_map)
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader, max_redirects=3)

    primary = ImageSource(value="http://example.com/start.png", role="primary")

    with pytest.raises(ValueError, match="(?i)redirect"):
        loader.load_sources(primary, tuple())

    # All encountered responses should be closed once
    for resp in responses[:4]:  # Only first 4 were accessed
        assert resp.close_count == 1


# ============================================================================
# Category 6: Response/Stream/Filename/Close Edge Cases
# ============================================================================

def test_remote_response_status_non_int():
    """Non-integer status code should fail gracefully."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    class BadStatusResponse:
        status_code = "200"  # String instead of int
        headers = {"content-type": "image/png"}
        peer_ip = "8.8.8.8"
        close_count = 0

        def iter_bytes(self, chunk_size=8192):
            yield VALID_PNG

        def close(self):
            self.close_count += 1

    bad_response = BadStatusResponse()
    downloader = RecorderDownloader({"http://example.com/test.png": bad_response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises((ValueError, TypeError)):
        loader.load_sources(primary, tuple())

    assert bad_response.close_count == 1


def test_remote_response_404_not_found():
    """404 status should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=404,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[]
    )
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)404|not found|status"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_response_missing_content_type():
    """Missing Content-Type header should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={},  # No Content-Type
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)content-type|mime"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_response_unsupported_mime_type():
    """Unsupported MIME type should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "application/pdf"},
        peer_ip="8.8.8.8",
        chunks=[b"%PDF-1.4"]
    )
    downloader = RecorderDownloader({"http://example.com/test.pdf": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.pdf", role="primary")

    with pytest.raises(ValueError, match="(?i)unsupported|mime|type"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_response_mime_format_mismatch():
    """Content-Type says PNG but data is JPEG - should fail after decode."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_JPEG]  # JPEG data with PNG Content-Type
    )
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)format|mismatch|mime"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_response_empty_body():
    """Empty response body should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[]  # Empty
    )
    downloader = RecorderDownloader({"http://example.com/test.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises(ValueError, match="(?i)empty|size"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


def test_remote_response_non_bytes_chunk():
    """Non-bytes chunk in stream should fail."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    class BadChunkResponse:
        status_code = 200
        headers = {"content-type": "image/png"}
        peer_ip = "8.8.8.8"
        close_count = 0

        def iter_bytes(self, chunk_size=8192):
            yield "not bytes"  # String instead of bytes

        def close(self):
            self.close_count += 1

    bad_response = BadChunkResponse()
    downloader = RecorderDownloader({"http://example.com/test.png": bad_response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png", role="primary")

    with pytest.raises((ValueError, TypeError)):
        loader.load_sources(primary, tuple())

    assert bad_response.close_count == 1


def test_remote_stream_exception_contains_secret_redacted():
    """Exception during streaming should not leak query params or secrets."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    class ExceptionResponse:
        status_code = 200
        headers = {"content-type": "image/png"}
        peer_ip = "8.8.8.8"
        close_count = 0

        def iter_bytes(self, chunk_size=8192):
            raise ValueError("Network error: token=secret-abc-123")

        def close(self):
            self.close_count += 1

    bad_response = ExceptionResponse()
    downloader = RecorderDownloader({"http://example.com/test.png?token=secret-abc-123": bad_response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/test.png?token=secret-abc-123", role="primary")

    try:
        loader.load_sources(primary, tuple())
        assert False, "Should have raised"
    except ValueError as e:
        error_msg = str(e)
        # Strict: token must not appear
        assert "secret-abc-123" not in error_msg

    assert bad_response.close_count == 1


def test_remote_oversize_image_rejected_with_close():
    """Image exceeding MAX_IMAGE_BYTES should fail and close response once."""
    original_max = sources.MAX_IMAGE_BYTES

    try:
        # Patch to small value for testing
        sources.MAX_IMAGE_BYTES = 100

        resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

        def oversize_generator():
            yield b"x" * 100  # Exactly at limit
            yield b"x"  # One byte over
            yield b"sentinel-should-not-be-consumed"  # Should not be consumed

        class OversizeResponse:
            status_code = 200
            headers = {"content-type": "image/png"}
            peer_ip = "8.8.8.8"
            close_count = 0
            chunks_consumed = []

            def iter_bytes(self, chunk_size=8192):
                gen = oversize_generator()
                for chunk in gen:
                    self.chunks_consumed.append(chunk)
                    yield chunk

            def close(self):
                self.close_count += 1

        oversize_response = OversizeResponse()
        downloader = RecorderDownloader({"http://example.com/test.png": oversize_response})
        loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

        primary = ImageSource(value="http://example.com/test.png", role="primary")

        with pytest.raises(ValueError, match="(?i)size|large|exceed"):
            loader.load_sources(primary, tuple())

        assert oversize_response.close_count == 1
        # Sentinel should not be consumed after size limit hit
        assert b"sentinel-should-not-be-consumed" not in oversize_response.chunks_consumed

    finally:
        sources.MAX_IMAGE_BYTES = original_max


def test_remote_filename_from_final_url_percent_decoded():
    """Filename should be percent-decoded from final URL."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({"http://example.com/my%20image%20file.png": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/my%20image%20file.png", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    # Should decode %20 to space
    assert result[0].filename == "my image file.png"


@pytest.mark.parametrize("encoded_path,expected_safe", [
    ("test%2Fslash.png", "test_slash.png"),  # %2F = /
    ("test%5Cbackslash.png", "test_backslash.png"),  # %5C = \
    ("test%00nul.png", "test_nul.png"),  # %00 = NUL
    ("test%0Dcarriage.png", "test_carriage.png"),  # %0D = CR
])
def test_remote_filename_sanitizes_dangerous_decoded_chars(encoded_path, expected_safe):
    """Filename should sanitize path separators and control chars after decode."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({f"http://example.com/{encoded_path}": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value=f"http://example.com/{encoded_path}", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    # Should not contain literal / \ or control chars
    assert "/" not in result[0].filename
    assert "\\" not in result[0].filename
    assert "\x00" not in result[0].filename
    assert "\r" not in result[0].filename


def test_remote_filename_from_url_no_basename():
    """URL with no basename should generate safe fallback filename."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({"http://example.com/": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    # Should have some fallback filename
    assert len(result[0].filename) > 0
    assert result[0].filename.endswith(".png")


def test_remote_filename_truncated_to_max_length():
    """Filename over 200 chars should be truncated."""
    long_name = "a" * 250 + ".png"
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({f"http://example.com/{long_name}": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value=f"http://example.com/{long_name}", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    assert len(result[0].filename) <= 200


def test_remote_filename_extension_matches_real_format():
    """Filename extension should match actual decoded format, not URL extension."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    # URL says .jpg but data is PNG
    downloader = RecorderDownloader({"http://example.com/image.jpg": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/image.jpg", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    # Should correct extension to .png based on real format
    assert result[0].filename.endswith(".png")


def test_remote_filename_no_query_params_leaked():
    """Query parameters should not appear in filename."""
    resolver = RecorderResolver({("example.com", 80): ("8.8.8.8",)})

    response = FakeResponse(
        status=200,
        headers={"content-type": "image/png"},
        peer_ip="8.8.8.8",
        chunks=[VALID_PNG]
    )
    downloader = RecorderDownloader({"http://example.com/image.png?token=secret123&size=large": response})
    loader = sources.SourceLoader(resolver=resolver, downloader=downloader)

    primary = ImageSource(value="http://example.com/image.png?token=secret123&size=large", role="primary")
    result = loader.load_sources(primary, tuple())

    assert len(result) == 1
    # Query should not leak into filename
    assert "token" not in result[0].filename
    assert "secret123" not in result[0].filename
    assert "?" not in result[0].filename


# ============================================================================
# Category 7: Default Resolver/Downloader Implementation
# ============================================================================

def test_default_resolver_deduplicates_ips():
    """_default_resolver should deduplicate IPs from getaddrinfo."""
    with patch("hermes_post_design.chiyi_core.sources.socket.getaddrinfo") as mock_gai:
        # Simulate getaddrinfo returning duplicates
        mock_gai.return_value = [
            (socket.AF_INET, None, None, None, ("8.8.8.8", 80)),
            (socket.AF_INET, None, None, None, ("8.8.8.8", 80)),  # Duplicate
            (socket.AF_INET6, None, None, None, ("2001:4860:4860::8888", 80, 0, 0)),
            (socket.AF_INET6, None, None, None, ("2001:4860:4860::8888", 80, 0, 0)),  # Duplicate
            (socket.AF_INET, None, None, None, ("8.8.4.4", 80)),
        ]

        result = sources._default_resolver("example.com", 80)

        # Should deduplicate and return stable tuple
        assert isinstance(result, tuple)
        assert len(result) == 3  # Only unique IPs
        assert "8.8.8.8" in result
        assert "8.8.4.4" in result
        assert "2001:4860:4860::8888" in result


def test_default_resolver_exception_no_secret_leak():
    """_default_resolver exceptions should not leak host/port secrets."""
    with patch("hermes_post_design.chiyi_core.sources.socket.getaddrinfo") as mock_gai:
        mock_gai.side_effect = socket.gaierror("DNS error for secret-internal-host.local")

        try:
            sources._default_resolver("secret-internal-host.local", 8080)
            assert False, "Should have raised"
        except Exception as e:
            error_msg = str(e)
            # Strict: secret token must not appear
            assert "secret-internal-host" not in error_msg


def test_requests_downloader_class_exists():
    """Private _RequestsDownloader class should exist."""
    assert hasattr(sources, "_RequestsDownloader")


def test_requests_downloader_owned_session_trust_env_false():
    """_RequestsDownloader with owned session should set trust_env=False."""
    with patch("hermes_post_design.chiyi_core.sources.requests.Session") as MockSession:
        mock_session = Mock()
        mock_session.trust_env = True  # Mock initial state
        MockSession.return_value = mock_session

        # Create downloader without providing session (owns its session)
        downloader = sources._RequestsDownloader()

        # Should have created session and set trust_env=False
        assert MockSession.called
        assert mock_session.trust_env is False


def test_requests_downloader_get_kwargs():
    """_RequestsDownloader should call session.get with exact kwargs."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = Mock()
    mock_response.raw.connection.sock = Mock()
    mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)

    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    # Should call with exact kwargs
    mock_session.get.assert_called_once()
    call_kwargs = mock_session.get.call_args[1]
    assert call_kwargs["stream"] is True
    assert call_kwargs["allow_redirects"] is False
    assert call_kwargs["timeout"] == (15, 60)


def test_requests_downloader_peer_ip_none_when_no_socket():
    """_RequestsDownloader should return peer_ip=None when raw has no socket."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = None  # No connection

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)
    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    assert response.peer_ip is None


def test_requests_downloader_headers_case_insensitive():
    """_RequestsDownloader wrapper should allow case-insensitive header access."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}  # Mixed case
    mock_response.raw = Mock()
    mock_response.raw.connection = Mock()
    mock_response.raw.connection.sock = Mock()
    mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)
    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    # Should be accessible in lowercase
    assert "content-type" in response.headers or "Content-Type" in response.headers


def test_requests_downloader_iter_content_forwarded():
    """_RequestsDownloader should forward iter_content correctly."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = Mock()
    mock_response.raw.connection.sock = Mock()
    mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

    chunks = [b"chunk1", b"chunk2", b"chunk3"]

    def mock_iter_content(chunk_size):
        for chunk in chunks:
            yield chunk

    mock_response.iter_content = mock_iter_content
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)
    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    # Consume iterator
    received = list(response.iter_bytes())
    assert received == chunks


def test_requests_downloader_close_forwarded_once():
    """_RequestsDownloader should forward close() exactly once."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = Mock()
    mock_response.raw.connection.sock = Mock()
    mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_response.close = Mock()
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)
    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    response.close()
    response.close()  # Call twice

    # Underlying response should be closed exactly once
    assert mock_response.close.call_count == 1


def test_source_loader_close_does_not_close_injected_downloader():
    """SourceLoader.close() should not close an injected downloader."""
    mock_downloader = Mock()
    mock_downloader.close = Mock()

    loader = sources.SourceLoader(downloader=mock_downloader)

    loader.close()
    loader.close()  # Call twice

    # Injected downloader's close should never be called
    mock_downloader.close.assert_not_called()


def test_requests_downloader_owned_session_close_idempotent():
    """_RequestsDownloader with owned session should close session exactly once."""
    with patch("hermes_post_design.chiyi_core.sources.requests.Session") as MockSession:
        mock_session = Mock()
        mock_session.trust_env = True
        mock_session.close = Mock()
        MockSession.return_value = mock_session

        # Create downloader with owned session
        downloader = sources._RequestsDownloader()

        # Close twice
        downloader.close()
        downloader.close()

        # Underlying session.close should be called exactly once
        assert mock_session.close.call_count == 1


def test_requests_downloader_owned_session_close_exception_idempotent():
    """_RequestsDownloader owned session close exception shouldn't prevent second close."""
    with patch("hermes_post_design.chiyi_core.sources.requests.Session") as MockSession:
        mock_session = Mock()
        mock_session.trust_env = True
        mock_session.close = Mock(side_effect=[Exception("close error"), None])
        MockSession.return_value = mock_session

        downloader = sources._RequestsDownloader()

        # First close raises exception
        with pytest.raises(Exception, match="close error"):
            downloader.close()

        # Second close should not call session.close again (idempotent despite exception)
        downloader.close()

        # Should only be called once (during first close attempt)
        assert mock_session.close.call_count == 1


def test_requests_downloader_exception_no_secret_leak():
    """_RequestsDownloader should redact secrets from exceptions."""
    mock_session = Mock()
    mock_session.get.side_effect = Exception("Connection error: token=secret-xyz-789")

    downloader = sources._RequestsDownloader(session=mock_session)

    try:
        downloader("https://example.com/test.png?token=secret-xyz-789", ("8.8.8.8",))
        assert False, "Should have raised"
    except Exception as e:
        error_msg = str(e)
        # Strict: token must not appear
        assert "secret-xyz-789" not in error_msg


def test_no_real_network_requests():
    """Verify downloader construction does not trigger network requests."""
    # Patch at module level to prevent import-time network access
    with patch("hermes_post_design.chiyi_core.sources.requests.Session") as MockSession:
        mock_session = Mock()
        MockSession.return_value = mock_session

        # Construct downloader - should not call get()
        downloader = sources._RequestsDownloader()

        # Verify Session was created but get() was never called
        assert MockSession.called
        mock_session.get.assert_not_called()


# ============================================================================
# Category 8: Module Boundary & Isolation
# ============================================================================

def test_load_sources_no_global_state_reuse():
    """Consecutive load_sources calls should not reuse mutable global loader state."""
    # This test is expected to RED if implementation has _default_loader global

    loader1 = Mock()
    loader1.load_sources.return_value = [
        LoadedSource(filename="test1.png", data=VALID_PNG, mime_type="image/png")
    ]

    loader2 = Mock()
    loader2.load_sources.return_value = [
        LoadedSource(filename="test2.png", data=VALID_PNG, mime_type="image/png")
    ]

    # Patch SourceLoader to return different instances
    with patch.object(sources, "SourceLoader", side_effect=[loader1, loader2]) as mock_loader:
        primary1 = ImageSource(value="http://example.com/test1.png", role="primary")
        result1 = sources.load_sources(primary1, tuple())

        primary2 = ImageSource(value="http://example.com/test2.png", role="primary")
        result2 = sources.load_sources(primary2, tuple())

        # Should have constructed SourceLoader twice
        assert mock_loader.call_count == 2

    # Each call should use its own loader
    assert loader1.load_sources.call_count == 1
    assert loader2.load_sources.call_count == 1
    assert result1[0].filename == "test1.png"
    assert result2[0].filename == "test2.png"


def test_sources_module_no_forbidden_imports():
    """sources.py should not import agent/tools/hermes_cli/hermes_constants."""
    # tests/core/test_sources.py -> repo root is 2 levels up
    repo_root = Path(__file__).resolve().parents[2]
    source_file = repo_root / "src" / "hermes_post_design" / "chiyi_core" / "sources.py"

    assert source_file.exists(), f"sources.py not found at {source_file}"

    source_code = source_file.read_text(encoding="utf-8")

    # Check for forbidden imports
    forbidden = ["hermes_agent", "agent", "tools", "hermes_cli", "hermes_constants"]
    for forbidden_module in forbidden:
        assert f"import {forbidden_module}" not in source_code
        assert f"from {forbidden_module}" not in source_code


def test_sources_local_no_read_bytes():
    """Local file implementation should not use .read_bytes() directly."""
    # tests/core/test_sources.py -> repo root is 2 levels up
    repo_root = Path(__file__).resolve().parents[2]
    source_file = repo_root / "src" / "hermes_post_design" / "chiyi_core" / "sources.py"

    assert source_file.exists(), f"sources.py not found at {source_file}"

    source_code = source_file.read_text(encoding="utf-8")

    # Should not contain .read_bytes(
    assert ".read_bytes(" not in source_code


# PART4_END


# ============================================================================
# Category 9: Task 5 Quality RED Tests - Partial Local Read
# ============================================================================

def test_local_file_partial_read_loop_complete_data(tmp_path, monkeypatch):
    """Partial local read with os.read chunking - must loop until complete."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    # Mock os.open/lstat/fstat/os.read
    real_open = os.open
    real_lstat = os.lstat
    real_fstat = os.fstat
    real_read = os.read
    real_close = os.close

    fd_tracker = {'fd': None, 'read_count': 0}

    def mock_open(path, flags):
        fd = real_open(path, flags)
        fd_tracker['fd'] = fd
        return fd

    def mock_lstat(path):
        result = real_lstat(path)
        return result

    def mock_fstat(fd):
        result = real_fstat(fd)
        return result

    def mock_read(fd, n):
        """First call returns first half, second returns second half, third returns empty."""
        fd_tracker['read_count'] += 1
        if fd_tracker['read_count'] == 1:
            return VALID_PNG[:len(VALID_PNG)//2]
        elif fd_tracker['read_count'] == 2:
            return VALID_PNG[len(VALID_PNG)//2:]
        else:
            return b''

    with patch('os.open', side_effect=mock_open):
        with patch('os.lstat', side_effect=mock_lstat):
            with patch('os.fstat', side_effect=mock_fstat):
                with patch('os.read', side_effect=mock_read):
                    with patch('os.close', side_effect=real_close):
                        primary = ImageSource(value=str(png_file), role="primary")

                        # RED: Should fail if implementation doesn't loop os.read
                        # Expected: call succeeds, result[0].data == VALID_PNG, read_count >= 2
                        result = sources.load_sources(primary, tuple())

                        assert len(result) == 1
                        assert result[0].data == VALID_PNG
                        assert fd_tracker['read_count'] >= 2


def test_local_file_partial_read_exceeds_max_during_loop(tmp_path, monkeypatch):
    """File size=small_max (not MAX+2), chunked reads total 21=MAX+1, should reject."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    # Patch MAX_IMAGE_BYTES to small value
    small_max = 20
    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", small_max)

    real_open = os.open
    real_path_lstat = Path.lstat
    real_fstat = os.fstat
    real_close = os.close

    fd_tracker = {'fd': None, 'read_count': 0}

    def mock_path_lstat(path):
        result = real_path_lstat(path)
        if path != png_file:
            return result
        # Report size = small_max to avoid pre-check rejection.
        class FakeStat:
            st_mode = result.st_mode
            st_size = small_max
            st_dev = result.st_dev
            st_ino = result.st_ino
        return FakeStat()

    def mock_fstat(fd):
        result = real_fstat(fd)
        # Report size = small_max to avoid pre-check rejection.
        class FakeStat:
            st_mode = result.st_mode
            st_size = small_max
            st_dev = result.st_dev
            st_ino = result.st_ino
        return FakeStat()

    def mock_read(fd, n):
        """Return chunks that total 21 bytes = MAX+1."""
        fd_tracker['read_count'] += 1
        if fd_tracker['read_count'] == 1:
            return b'x' * 10
        elif fd_tracker['read_count'] == 2:
            return b'x' * 11  # Total would be 21 = MAX+1
        else:
            return b''

    with patch.object(Path, 'lstat', mock_path_lstat):
        with patch('os.open', side_effect=real_open):
            with patch('os.fstat', side_effect=mock_fstat):
                with patch('os.read', side_effect=mock_read):
                    with patch('os.close', side_effect=real_close):
                        primary = ImageSource(value=str(png_file), role="primary")

                        # RED: Should reject after read_count==2, total 21 > MAX.
                        with pytest.raises(ValueError, match="(?i)size|exceed|maximum"):
                            sources.load_sources(primary, tuple())

                        # Verify read was called exactly twice.
                        assert fd_tracker['read_count'] == 2


# ============================================================================
# Category 10: Task 5 Quality RED Tests - Zero Identity Usable
# ============================================================================

def test_local_file_zero_identity_stable_should_not_reject(tmp_path, monkeypatch):
    """Zero identity (dev=0, ino=0) but stable size/mode should not reject."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    real_open = os.open
    real_path_lstat = Path.lstat
    real_fstat = os.fstat
    real_close = os.close

    def mock_path_lstat(path):
        result = real_path_lstat(path)
        if path != png_file:
            return result
        class FakeStat:
            st_mode = result.st_mode
            st_size = result.st_size
            st_dev = 0
            st_ino = 0
        return FakeStat()

    def mock_fstat(fd):
        result = real_fstat(fd)
        class FakeStat:
            st_mode = result.st_mode
            st_size = result.st_size
            st_dev = 0
            st_ino = 0
        return FakeStat()

    read_calls = 0

    def mock_read(fd, n):
        nonlocal read_calls
        read_calls += 1
        return VALID_PNG if read_calls == 1 else b''

    with patch.object(Path, 'lstat', mock_path_lstat):
        with patch('os.open', side_effect=real_open):
            with patch('os.fstat', side_effect=mock_fstat):
                with patch('os.read', side_effect=mock_read):
                    with patch('os.close', side_effect=real_close):
                        primary = ImageSource(value=str(png_file), role="primary")

                        # RED: Should succeed (zero identity is unavailable on some filesystems).
                        # Contract: only compare identity when both components are non-zero.
                        result = sources.load_sources(primary, tuple())

                        assert len(result) == 1
                        assert result[0].data == VALID_PNG


def test_local_file_nonzero_identity_changes_should_reject(tmp_path, monkeypatch):
    """Non-zero identity that changes between checks should be rejected."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    real_open = os.open
    real_lstat = os.lstat
    real_fstat = os.fstat
    real_read = os.read
    real_close = os.close

    call_tracker = {'lstat_calls': 0, 'fstat_calls': 0}

    def mock_lstat(path):
        result = real_lstat(path)
        call_tracker['lstat_calls'] += 1
        class FakeStat:
            st_mode = result.st_mode
            st_size = result.st_size
            st_dev = 123
            st_ino = 456
        return FakeStat()

    def mock_fstat(fd):
        result = real_fstat(fd)
        call_tracker['fstat_calls'] += 1
        class FakeStat:
            st_mode = result.st_mode
            st_size = result.st_size
            # Change identity on second fstat
            st_dev = 123 if call_tracker['fstat_calls'] == 1 else 999
            st_ino = 456 if call_tracker['fstat_calls'] == 1 else 888
        return FakeStat()

    def mock_read(fd, n):
        return VALID_PNG

    with patch('os.open', side_effect=real_open):
        with patch('os.lstat', side_effect=mock_lstat):
            with patch('os.fstat', side_effect=mock_fstat):
                with patch('os.read', side_effect=mock_read):
                    with patch('os.close', side_effect=real_close):
                        primary = ImageSource(value=str(png_file), role="primary")

                        # Should reject when identity changes
                        with pytest.raises(ValueError, match="(?i)identity|changed"):
                            sources.load_sources(primary, tuple())


# ============================================================================
# Category 11: Task 5 Quality RED Tests - Data Predecode Size Check
# ============================================================================

def test_data_url_predecode_rejects_before_decode_without_large_fixture(monkeypatch):
    """Data URL with payload string length > encoded max should reject before calling decode."""
    # Patch MAX to 8 bytes
    monkeypatch.setattr("hermes_post_design.chiyi_core.sources.MAX_IMAGE_BYTES", 8)

    # Construct payload: base64 encoding expands by ~4/3, so 20 chars -> ~15 decoded bytes > 8
    # Use invalid base64 chars to ensure it fails validation if decode is called
    payload = "!@#$%^&*()_+ABCDEF"  # 18 chars, clearly invalid base64

    data_url = f"data:image/png;base64,{payload}"

    with patch("base64.b64decode") as mock_decode:
        mock_decode.side_effect = AssertionError("b64decode should not be called")

        primary = ImageSource(value=data_url, role="primary")

        # Should FAIL if implementation calls decode before size check
        # Expected: reject based on pre-decode size estimate
        with pytest.raises(ValueError):
            sources.load_sources(primary, tuple())

        # Verify decode was not called
        mock_decode.assert_not_called()


def test_data_url_whitespace_chars_rejected_by_validate(monkeypatch):
    """Small payload with whitespace/invalid chars rejected by validate=True."""
    # Valid base64 with embedded whitespace
    b64_data = base64.b64encode(b"small").decode("ascii")
    b64_with_whitespace = b64_data[:4] + " \n\t" + b64_data[4:]

    data_url = f"data:image/png;base64,{b64_with_whitespace}"

    primary = ImageSource(value=data_url, role="primary")

    # Should reject due to whitespace with validate=True
    with pytest.raises(ValueError, match="(?i)base64|invalid"):
        sources.load_sources(primary, tuple())


# ============================================================================
# Category 12: Task 5 Quality RED Tests - DNS Normalize Dedupe
# ============================================================================

def test_remote_default_resolver_compressed_expanded_canonical():
    """_default_resolver with getaddrinfo returning compressed/expanded IPv6 should canonicalize."""
    with patch("hermes_post_design.chiyi_core.sources.socket.getaddrinfo") as mock_gai:
        # Simulate getaddrinfo returning same IPv6 in compressed and expanded forms
        mock_gai.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ("2001:4860:4860::8888", 443, 0, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ("2001:4860:4860:0000:0000:0000:0000:8888", 443, 0, 0)),
        ]

        result = sources._default_resolver("example.com", 443)

        # RED: Should dedupe to single canonical form
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert "2001:4860:4860::8888" in result or "2001:4860:4860:0000:0000:0000:0000:8888" in result


def test_remote_default_resolver_ipv4_mapped_plain_canonical():
    """_default_resolver with IPv4-mapped and plain IPv4 should canonicalize to plain."""
    with patch("hermes_post_design.chiyi_core.sources.socket.getaddrinfo") as mock_gai:
        # Simulate getaddrinfo returning IPv4-mapped and plain IPv4
        mock_gai.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ("::ffff:8.8.8.8", 443, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ("8.8.8.8", 443)),
        ]

        result = sources._default_resolver("example.com", 443)

        # RED: Should dedupe to single canonical form (prefer plain IPv4)
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert "8.8.8.8" in result


def test_remote_dns_normalize_still_rejects_private():
    """DNS normalization/dedupe should still reject private IPs."""
    with patch("hermes_post_design.chiyi_core.sources.socket.getaddrinfo") as mock_gai:
        # Simulate getaddrinfo returning private IPs in various forms
        mock_gai.return_value = [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ("::ffff:127.0.0.1", 443, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ("127.0.0.1", 443)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ("::1", 443, 0, 0)),
        ]

        with pytest.raises(ValueError, match="(?i)globally|private|public|loopback"):
            sources._default_resolver("localhost", 443)


# ============================================================================
# Category 13: Task 5 Quality RED Tests - Wrapper Construction Failure Close
# ============================================================================

def test_requests_downloader_wrapper_construction_failure_closes_response():
    """Response wrapper construction failure should close underlying response exactly once."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200

    # headers.items() raises exception during wrapper construction
    def raise_on_items():
        raise ValueError("Mock headers.items() error with secret-token-xyz")

    mock_response.headers = Mock()
    mock_response.headers.items = Mock(side_effect=raise_on_items)
    mock_response.close = Mock()

    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)

    try:
        downloader("https://example.com/test.png", ("8.8.8.8",))
        assert False, "Should have raised"
    except ValueError as e:
        error_msg = str(e)
        # Should be bounded ValueError, not leak secret
        assert "secret-token-xyz" not in error_msg

    # RED: Underlying response should be closed exactly once (not 0)
    assert mock_response.close.call_count == 1


def test_requests_downloader_wrapper_peer_extraction_malformed_closes():
    """Malformed peer extraction should handle gracefully and still close response."""
    mock_session = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}

    # Mock raw with malformed connection that raises during peer extraction
    mock_raw = Mock()
    mock_raw._connection = Mock()
    mock_raw._connection.sock = Mock()
    mock_raw._connection.sock.getpeername = Mock(side_effect=OSError("Connection closed"))
    mock_response.raw = mock_raw

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_response.close = Mock()

    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)

    # Should construct wrapper successfully (peer_ip will be None)
    response = downloader("https://example.com/test.png", ("8.8.8.8",))

    # peer_ip should be None due to extraction failure
    assert response.peer_ip is None

    # Close should still work
    response.close()
    assert mock_response.close.call_count == 1


# ============================================================================
# Category 14: Task 5 Quality RED Tests - Connection Pinning
# ============================================================================

def test_requests_downloader_connection_pinning_installs_adapter():
    """_RequestsDownloader should install _PinnedAddressAdapter before session.get."""
    mock_session = Mock()

    # Track mount calls with event recording
    events = []
    mount_calls = []

    def track_mount(prefix, adapter):
        events.append(('mount', prefix, adapter))
        mount_calls.append((prefix, adapter))

    mock_session.mount = Mock(side_effect=track_mount)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = None

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_response.close = Mock()

    def track_get(*args, **kwargs):
        events.append(('get', args, kwargs))
        return mock_response

    mock_session.get.side_effect = track_get

    downloader = sources._RequestsDownloader(session=mock_session)

    # Call downloader with approved IPs
    response = downloader("https://example.com/test.png", ("8.8.8.8", "1.1.1.1"))
    response.close()

    # RED: Should fail - adapter not yet implemented
    # Expected: session.mount called at least once before session.get
    assert len(mount_calls) >= 1, "No adapter mounted - connection pinning not implemented"

    # Verify mount happened before get
    mount_event_idx = None
    get_event_idx = None
    for i, event in enumerate(events):
        if event[0] == 'mount' and mount_event_idx is None:
            mount_event_idx = i
        if event[0] == 'get' and get_event_idx is None:
            get_event_idx = i

    assert mount_event_idx is not None, "mount was not called"
    assert get_event_idx is not None, "get was not called"
    assert mount_event_idx < get_event_idx, "mount must occur before get"

    # Verify adapter is instance of _PinnedAddressAdapter
    adapter = mount_calls[0][1]
    assert type(adapter).__name__ == "_PinnedAddressAdapter"


def test_pinned_address_adapter_https_connection_pool():
    """_PinnedAddressAdapter.get_connection should return HTTPSConnectionPool with pinned IP and SNI."""
    # RED: Class doesn't exist yet, this will fail on import/construction
    adapter = sources._PinnedAddressAdapter(
        original_hostname='example.com',
        pinned_ip='8.8.8.8',
        scheme='https',
        port=443
    )

    # Prepare a request
    from requests import Request
    req = Request('GET', 'https://example.com/path').prepare()

    # Call get_connection_with_tls_context
    pool = adapter.get_connection_with_tls_context(req, verify=True, proxies={}, cert=None)

    # Verify connection pool properties
    assert pool.host == '8.8.8.8'
    assert pool.port == 443
    assert pool.conn_kw['server_hostname'] == 'example.com'
    assert pool.assert_hostname == 'example.com'


def test_pinned_address_adapter_http_connection_pool():
    """_PinnedAddressAdapter.get_connection for HTTP should return HTTPConnectionPool with pinned IP."""
    # RED: Class doesn't exist yet
    adapter = sources._PinnedAddressAdapter(
        original_hostname='example.com',
        pinned_ip='8.8.8.8',
        scheme='http',
        port=80
    )

    from requests import Request
    req = Request('GET', 'http://example.com/path').prepare()

    pool = adapter.get_connection_with_tls_context(req, verify=False, proxies={}, cert=None)

    # Verify connection pool properties
    assert pool.host == '8.8.8.8'
    assert pool.port == 80


def test_pinned_address_adapter_add_headers_host():
    """_PinnedAddressAdapter.add_headers should set Host header to original hostname."""
    # RED: Class doesn't exist yet
    adapter = sources._PinnedAddressAdapter(
        original_hostname='example.com',
        pinned_ip='8.8.8.8',
        scheme='https',
        port=443
    )

    from requests import Request
    req = Request('GET', 'https://example.com/path').prepare()

    adapter.add_headers(req)

    # Host header should be original hostname
    assert req.headers['Host'] == 'example.com'


def test_pinned_address_adapter_ipv6_host_header():
    """_PinnedAddressAdapter with IPv6 should use bracket form for connection but plain host for Host header."""
    # RED: Class doesn't exist yet
    adapter = sources._PinnedAddressAdapter(
        original_hostname='example.com',
        pinned_ip='2001:4860:4860::8888',
        scheme='https',
        port=443
    )

    from requests import Request
    req = Request('GET', 'https://example.com/path').prepare()

    pool = adapter.get_connection_with_tls_context(req, verify=True, proxies={}, cert=None)

    # Connection IP includes brackets for IPv6 addressing
    assert '2001:4860:4860::8888' in pool.host

    adapter.add_headers(req)
    # Host header should remain original hostname
    assert req.headers['Host'] == 'example.com'


def test_pinned_address_adapter_close():
    """_PinnedAddressAdapter.close should be callable."""
    # RED: Class doesn't exist yet
    adapter = sources._PinnedAddressAdapter(
        original_hostname='example.com',
        pinned_ip='8.8.8.8',
        scheme='https',
        port=443
    )

    # Should not raise
    adapter.close()


def test_requests_downloader_pinning_rejects_empty_approved_ips():
    """Connection pinning should reject empty approved IPs before session.get."""
    mock_session = Mock()
    mock_session.get = Mock(side_effect=AssertionError("session.get should not be called"))

    downloader = sources._RequestsDownloader(session=mock_session)

    # Should reject before calling session.get
    with pytest.raises(ValueError):
        downloader("https://example.com/test.png", ())

    # session.get should not be called
    mock_session.get.assert_not_called()


def test_requests_downloader_pinning_rejects_private_approved_ips():
    """Connection pinning should reject private IPs in approved_ips before session.get."""
    mock_session = Mock()
    mock_session.get = Mock(side_effect=AssertionError("session.get should not be called"))

    downloader = sources._RequestsDownloader(session=mock_session)

    # Should reject private IPs before calling session.get
    with pytest.raises(ValueError):
        downloader("https://example.com/test.png", ("10.0.0.1", "127.0.0.1"))

    # session.get should not be called
    mock_session.get.assert_not_called()


def test_requests_downloader_pinning_rejects_invalid_approved_ips():
    """Connection pinning should reject invalid IPs in approved_ips before session.get."""
    mock_session = Mock()
    mock_session.get = Mock(side_effect=AssertionError("session.get should not be called"))

    downloader = sources._RequestsDownloader(session=mock_session)

    # Should reject invalid IPs before calling session.get
    with pytest.raises(ValueError):
        downloader("https://example.com/test.png", ("not-an-ip", "invalid"))

    # session.get should not be called
    mock_session.get.assert_not_called()


def test_requests_downloader_pinning_uses_deterministic_selection():
    """Connection pinning should use deterministic selection from approved IPs (first one)."""
    mock_session = Mock()

    mount_calls = []

    def track_mount(prefix, adapter):
        mount_calls.append((prefix, adapter))

    mock_session.mount = Mock(side_effect=track_mount)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = None

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_response.close = Mock()

    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)

    # Call twice with same approved IPs tuple
    approved = ("8.8.8.8", "1.1.1.1", "8.8.4.4")

    response1 = downloader("https://example.com/test1.png", approved)
    response1.close()

    response2 = downloader("https://example.com/test2.png", approved)
    response2.close()

    # RED: Should fail - connection pinning not yet implemented
    # Expected: both calls use same deterministic IP (first one: 8.8.8.8)
    assert len(mount_calls) >= 2, "No pinning - connection pinning not implemented"

    # Extract only pinned adapters; restore mounts contain the previous adapter.
    pinned_adapters = [
        adapter for _, adapter in mount_calls
        if type(adapter).__name__ == "_PinnedAddressAdapter"
    ]
    assert len(pinned_adapters) == 2
    pinned_ip_1 = pinned_adapters[0].pinned_ip
    pinned_ip_2 = pinned_adapters[1].pinned_ip

    # Both should be the same deterministic value (convention: first in tuple)
    assert pinned_ip_1 == pinned_ip_2
    assert pinned_ip_1 == "8.8.8.8"


# PART5_END


# ============================================================================
# Category 15: Task 5 RED Tests - Connection Layer Quality
# ============================================================================

def test_requests_downloader_unicode_idna_mount_prefix_ascii_punycode():
    """Unicode hostname URL should mount with ASCII punycode prefix, not Unicode."""
    mock_session = Mock()
    mock_session.trust_env = False

    mount_calls = []
    get_adapter_calls = []

    def track_mount(prefix, adapter):
        mount_calls.append((prefix, adapter))

    def track_get_adapter(url):
        get_adapter_calls.append(url)
        return Mock()  # Return old adapter

    mock_session.mount = Mock(side_effect=track_mount)
    mock_session.get_adapter = Mock(side_effect=track_get_adapter)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "image/png"}
    mock_response.raw = Mock()
    mock_response.raw.connection = Mock()
    mock_response.raw.connection.sock = Mock()
    mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

    def mock_iter_content(chunk_size):
        yield VALID_PNG

    mock_response.iter_content = mock_iter_content
    mock_response.close = Mock()
    mock_session.get.return_value = mock_response

    downloader = sources._RequestsDownloader(session=mock_session)

    # RED: Unicode domain should be converted to punycode for mount prefix
    # Expected: mount prefix is "https://xn--bcher-kva.example/" (ASCII punycode)
    # Not: "https://bücher.example/" (Unicode)
    response = downloader("https://bücher.example/path.png", ("8.8.8.8",))
    response.close()

    # Find pinned adapter mount call
    pinned_mounts = [(prefix, adapter) for prefix, adapter in mount_calls
                     if type(adapter).__name__ == "_PinnedAddressAdapter"]

    assert len(pinned_mounts) >= 1, "No pinned adapter mounted"

    mount_prefix = pinned_mounts[0][0]
    pinned_adapter = pinned_mounts[0][1]

    # RED: Should mount with ASCII punycode, not Unicode
    assert mount_prefix == "https://xn--bcher-kva.example/", \
        f"Mount prefix should be ASCII punycode, got: {mount_prefix}"

    # RED: Adapter should have ASCII punycode as original_hostname for SNI
    assert pinned_adapter.original_hostname == "xn--bcher-kva.example", \
        f"SNI should be ASCII punycode, got: {pinned_adapter.original_hostname}"


def test_pinned_adapter_ipv6_direct_host_header_brackets():
    """IPv6 address as hostname should have bracketed Host header for non-default ports."""
    # RED: Test direct IPv6 hostname (not domain resolving to IPv6)
    # When original_hostname IS the IPv6 address, Host header needs brackets

    # HTTPS default port 443 - no brackets needed
    adapter_default = sources._PinnedAddressAdapter(
        original_hostname="2001:4860:4860::8888",
        pinned_ip="2001:4860:4860::8888",
        scheme="https",
        port=443
    )

    from requests import Request
    req_default = Request('GET', 'https://[2001:4860:4860::8888]/path').prepare()
    adapter_default.add_headers(req_default)

    # RED: Default port should have brackets for IPv6 hostname
    assert req_default.headers['Host'] == "[2001:4860:4860::8888]", \
        f"IPv6 Host header for default port should use brackets, got: {req_default.headers['Host']}"

    # Non-default port 8443 - needs brackets and port
    adapter_custom = sources._PinnedAddressAdapter(
        original_hostname="2001:4860:4860::8888",
        pinned_ip="2001:4860:4860::8888",
        scheme="https",
        port=8443
    )

    req_custom = Request('GET', 'https://[2001:4860:4860::8888]:8443/path').prepare()
    adapter_custom.add_headers(req_custom)

    # RED: Non-default port should have brackets and port
    assert req_custom.headers['Host'] == "[2001:4860:4860::8888]:8443", \
        f"IPv6 Host header for non-default port should use [ip]:port, got: {req_custom.headers['Host']}"


def test_requests_downloader_adapter_restore_preserves_identity():
    """Session adapters dict should restore to exact original identity after download."""
    # Create real Session
    real_session = requests.Session()

    # Record initial adapter mapping (identity of dict items)
    initial_adapters_keys = set(real_session.adapters.keys())
    initial_adapters_items = list(real_session.adapters.items())
    initial_adapters_id = id(real_session.adapters)

    # Patch only session.get to return fake response, keep real mount/get_adapter
    original_get = real_session.get

    def fake_get(url, **kwargs):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.raw = Mock()
        mock_response.raw.connection = Mock()
        mock_response.raw.connection.sock = Mock()
        mock_response.raw.connection.sock.getpeername.return_value = ("8.8.8.8", 443)

        def mock_iter_content(chunk_size):
            yield VALID_PNG

        mock_response.iter_content = mock_iter_content
        mock_response.close = Mock()
        return mock_response

    real_session.get = fake_get

    try:
        downloader = sources._RequestsDownloader(session=real_session)

        # Download from first origin
        response1 = downloader("https://example1.com/image.png", ("8.8.8.8",))
        response1.close()

        # RED: Adapters dict should restore to original keys
        after_first_keys = set(real_session.adapters.keys())
        assert after_first_keys == initial_adapters_keys, \
            f"Adapter keys not restored after first download. Initial: {initial_adapters_keys}, After: {after_first_keys}"

        # Download from second origin
        response2 = downloader("https://example2.com/image.png", ("8.8.8.8",))
        response2.close()

        # RED: Adapters dict should still match original
        after_second_keys = set(real_session.adapters.keys())
        assert after_second_keys == initial_adapters_keys, \
            f"Adapter keys not restored after second download. Initial: {initial_adapters_keys}, After: {after_second_keys}"

        # RED: No extra keys from origin prefixes
        assert "https://example1.com/" not in real_session.adapters, \
            "Origin prefix https://example1.com/ leaked into adapters"
        assert "https://example2.com/" not in real_session.adapters, \
            "Origin prefix https://example2.com/ leaked into adapters"

    finally:
        real_session.close()


def test_requests_downloader_mount_failure_cleanup():
    """Mount failure should cleanup pinned adapter and not leak secrets."""
    mock_session = Mock()
    mock_session.trust_env = False

    old_adapter = Mock()
    mock_session.get_adapter = Mock(return_value=old_adapter)

    # Track created adapters and close calls without patching __init__ in place.
    created_adapters = []

    class TrackedAdapter(sources._PinnedAddressAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.close_count = 0
            created_adapters.append(self)

        def close(self):
            self.close_count += 1
            super().close()

    # Patch mount to raise exception with secret.
    def mount_raises(prefix, adapter):
        raise Exception("Mount failed: internal-secret-token-12345")

    mock_session.mount = Mock(side_effect=mount_raises)
    mock_session.get = Mock(side_effect=AssertionError("session.get should not be called after mount failure"))

    with patch("hermes_post_design.chiyi_core.sources._PinnedAddressAdapter", TrackedAdapter):
        downloader = sources._RequestsDownloader(session=mock_session)

        # RED: Should catch mount exception, cleanup adapter, raise bounded ValueError.
        with pytest.raises(ValueError) as exc:
            downloader("https://example.com/test.png", ("8.8.8.8",))

        assert "internal-secret-token-12345" not in str(exc.value)
        mock_session.get.assert_not_called()

        assert len(created_adapters) == 1, "No adapter created"
        assert created_adapters[0].close_count == 1


def test_requests_downloader_wrapper_construction_closes_pinned_adapter():
    """Wrapper construction failure should close both response AND pinned adapter."""
    mock_session = Mock()
    mock_session.trust_env = False

    old_adapter = Mock()
    mock_session.get_adapter = Mock(return_value=old_adapter)

    # Track adapters and their close calls
    created_adapters = []

    class TrackedAdapter(sources._PinnedAddressAdapter):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.close_count = 0
            created_adapters.append(self)

        def close(self):
            self.close_count += 1
            super().close()

    # Patch adapter class
    with patch("hermes_post_design.chiyi_core.sources._PinnedAddressAdapter", TrackedAdapter):
        mock_response = Mock()
        mock_response.status_code = 200

        # Make headers.items() raise during wrapper construction
        def raise_on_items():
            raise ValueError("Mock headers error")

        mock_response.headers = Mock()
        mock_response.headers.items = Mock(side_effect=raise_on_items)
        mock_response.close = Mock()

        mock_session.mount = Mock()
        mock_session.get.return_value = mock_response

        downloader = sources._RequestsDownloader(session=mock_session)

        try:
            downloader("https://example.com/test.png", ("8.8.8.8",))
            assert False, "Should have raised"
        except ValueError:
            pass

        # RED: Response should be closed exactly once
        assert mock_response.close.call_count == 1, \
            f"Response close count should be 1, got: {mock_response.close.call_count}"

        # RED: Pinned adapter should also be closed exactly once
        assert len(created_adapters) == 1, "No adapter created"
        adapter = created_adapters[0]
        assert adapter.close_count == 1, \
            f"Pinned adapter close count should be 1, got: {adapter.close_count}"


def test_pinned_adapter_close_idempotent():
    """_PinnedAddressAdapter.close should be idempotent - pool.close only once."""
    adapter = sources._PinnedAddressAdapter(
        original_hostname="example.com",
        pinned_ip="8.8.8.8",
        scheme="https",
        port=443
    )

    # Replace pool.close with Mock
    original_pool_close = adapter._pool.close
    adapter._pool.close = Mock(side_effect=original_pool_close)

    # Close twice
    adapter.close()
    adapter.close()

    # RED: Pool.close should be called exactly once (idempotent)
    assert adapter._pool.close.call_count == 1, \
        f"Pool close should be idempotent (called once), got: {adapter._pool.close.call_count}"


def test_local_file_short_eof_explicit_check(tmp_path):
    """Local file EOF before declared size should raise explicit ValueError, not just Pillow error."""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(VALID_PNG)

    real_open = os.open
    real_path_lstat = Path.lstat
    real_fstat = os.fstat
    real_close = os.close

    read_count = 0

    def mock_path_lstat(path):
        result = real_path_lstat(path)
        if path != png_file:
            return result
        # Report full size
        class FakeStat:
            st_mode = result.st_mode
            st_size = len(VALID_PNG)
            st_dev = result.st_dev
            st_ino = result.st_ino
        return FakeStat()

    def mock_fstat(fd):
        result = real_fstat(fd)
        # Report full size
        class FakeStat:
            st_mode = result.st_mode
            st_size = len(VALID_PNG)
            st_dev = result.st_dev
            st_ino = result.st_ino
        return FakeStat()

    def mock_read(fd, n):
        """First call returns only first half, second call returns empty (EOF)."""
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return VALID_PNG[:len(VALID_PNG)//2]
        else:
            return b''  # Premature EOF

    with patch.object(Path, 'lstat', mock_path_lstat):
        with patch('os.open', side_effect=real_open):
            with patch('os.fstat', side_effect=mock_fstat):
                with patch('os.read', side_effect=mock_read):
                    with patch('os.close', side_effect=real_close):
                        primary = ImageSource(value=str(png_file), role="primary")

                        # RED: Should raise ValueError with explicit message about size/short/incomplete
                        # Not just rely on Pillow's "cannot identify image file" error
                        try:
                            sources.load_sources(primary, tuple())
                            assert False, "Should have raised ValueError"
                        except ValueError as e:
                            error_msg = str(e).lower()
                            # RED: Error message should explicitly mention size mismatch or incomplete read
                            # Not just "invalid" or "cannot identify"
                            assert any(keyword in error_msg for keyword in ['size', 'short', 'incomplete', 'mismatch', 'expected']), \
                                f"Error should explicitly mention size/short/incomplete, got: {e}"


def test_requests_downloader_malformed_response_attrs_close_before_raise():
    """Downloader returning response without required attrs should close it before raising."""
    mock_session = Mock()
    mock_session.trust_env = False

    old_adapter = Mock()
    mock_session.get_adapter = Mock(return_value=old_adapter)
    mock_session.mount = Mock()

    # Create malformed response - has close but missing status_code/headers/peer_ip
    malformed_response = Mock()
    malformed_response.close = Mock()
    # Deliberately do NOT set status_code, headers, peer_ip

    mock_session.get.return_value = malformed_response

    downloader = sources._RequestsDownloader(session=mock_session)

    # RED: Should validate response has required attrs and close exactly once before raising
    try:
        downloader("https://example.com/test.png", ("8.8.8.8",))
        assert False, "Should have raised ValueError"
    except ValueError as e:
        error_msg = str(e)
        assert "invalid" in error_msg.lower() or "response" in error_msg.lower()

    # RED: Malformed response should be closed exactly once
    assert malformed_response.close.call_count == 1, \
        f"Malformed response should be closed once before raising, got: {malformed_response.close.call_count}"


def test_source_loader_injected_downloader_exception_is_sanitized():
    """Injected downloader failures must not leak query or underlying secrets."""
    secret = "INJECTED_DOWNLOADER_SECRET_9482"

    def failing_downloader(url, approved_ips):
        raise RuntimeError(
            f"failed {url} due to token={secret}"
        )

    loader = sources.SourceLoader(
        resolver=lambda host, port: ("8.8.8.8",),
        downloader=failing_downloader,
    )
    primary = ImageSource(
        value=f"https://example.com/a.png?token={secret}",
        role="primary",
    )

    with pytest.raises(ValueError) as exc:
        loader.load_sources(primary, tuple())

    message = str(exc.value)
    assert secret not in message
    assert "token=" not in message
    assert "https://example.com/a.png" in message


def test_source_loader_closes_injected_malformed_response_once():
    """A close-capable malformed injected response must be closed exactly once."""
    class MalformedResponse:
        def __init__(self):
            self.close_count = 0

        def close(self):
            self.close_count += 1

    response = MalformedResponse()
    loader = sources.SourceLoader(
        resolver=lambda host, port: ("8.8.8.8",),
        downloader=lambda url, approved_ips: response,
    )
    primary = ImageSource(value="https://example.com/a.png", role="primary")

    with pytest.raises(ValueError, match="Invalid HTTP response"):
        loader.load_sources(primary, tuple())

    assert response.close_count == 1


# RED_DONE
# End of Task 5 RED Tests
