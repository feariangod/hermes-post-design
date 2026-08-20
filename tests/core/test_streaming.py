"""
TDD tests for SSE (Server-Sent Events) streaming parser.

Tests the public interface:
    from hermes_post_design.chiyi_core.streaming import parse_sse

Returns CompletedArtifact. All failures use ValueError (client maps to protocol_error).
Tests pure iterator behavior without network I/O.
"""

import ast
from pathlib import Path

import pytest
from hermes_post_design.chiyi_core.models import CompletedArtifact


# ============================================================================
# Category 1: Partial events do not return, only completed with [DONE]
# ============================================================================

def test_partial_event_with_completed_and_done():
    """Partial image event + progress + heartbeat + completed b64 + [DONE] returns final artifact."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.partial_image\n",
        'data: {"partial_image_b64": "dGVtcA=="}\n',
        "\n",
        "event: progress\n",
        'data: {"percent": 50}\n',
        "\n",
        ": heartbeat\n",
        "\n",
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "b64_json": "RklOQUw="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)

    assert isinstance(result, CompletedArtifact)
    assert result.kind == "b64_json"
    assert result.value == "RklOQUw="  # "FINAL" in base64


def test_multiple_partial_events_ignored():
    """Multiple partial events are skipped, only completed matters."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.partial_image\n",
        'data: {"partial_image_b64": "cGFydDE="}\n',
        "\n",
        "event: image_generation.partial_image\n",
        'data: {"partial_image_b64": "cGFydDI="}\n',
        "\n",
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "b64_json": "Y29tcGxldGU="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "Y29tcGxldGU="


# ============================================================================
# Category 2: Completed-only without [DONE] is acceptable
# ============================================================================

def test_completed_only_with_empty_line_no_done():
    """Completed event properly terminated with empty line, then iterator EOF, no [DONE] - accept."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "b64_json": "ZmluYWw="}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "ZmluYWw="


def test_completed_event_header_with_payload_type_missing():
    """Event header 'completed' with payload missing 'type' field."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "ZGF0YQ=="}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "ZGF0YQ=="


def test_payload_type_completed_no_event_header():
    """Payload type indicates completed but no event header present."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        'data: {"type": "image_generation.completed", "b64_json": "cmVzdWx0"}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "cmVzdWx0"


# ============================================================================
# Category 3: URL completed with nested artifact structures
# ============================================================================

def test_url_completed_nested_structure():
    """Artifact in nested structure: event.data[0].url pattern."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "data": [{"url": "https://example.com/final.png"}]}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "url"
    assert result.value == "https://example.com/final.png"


def test_url_completed_direct_field():
    """URL artifact as direct field."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "url": "https://example.com/image.jpg"}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "url"
    assert result.value == "https://example.com/image.jpg"


def test_url_no_validation_or_download():
    """URL is accepted without validation or download attempt."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"url": "not-even-a-valid-url"}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "url"
    assert result.value == "not-even-a-valid-url"


# ============================================================================
# Category 4: String and UTF-8 bytes, CRLF handling, optional spaces
# ============================================================================

def test_string_lines_crlf_removed():
    """String lines with CRLF have CR properly removed."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\r\n",
        'data: {"b64_json": "dGVzdA=="}\r\n',
        "\r\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "dGVzdA=="


def test_utf8_bytes_lines():
    """UTF-8 encoded bytes as lines."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        b"event: image_generation.completed\n",
        b'data: {"b64_json": "Ynl0ZXM="}\n',
        b"\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "Ynl0ZXM="


def test_data_field_with_optional_space():
    """Data field accepts 'data:{...}' or 'data: {...}' with optional space."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines_no_space = [
        "event:image_generation.completed\n",
        'data:{"b64_json": "bm9zcGFjZQ=="}\n',
        "\n",
    ]
    result1 = parse_sse(lines_no_space, max_event_bytes=10000)
    assert result1.value == "bm9zcGFjZQ=="

    lines_with_space = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "c3BhY2U="}\n',
        "\n",
    ]
    result2 = parse_sse(lines_with_space, max_event_bytes=10000)
    assert result2.value == "c3BhY2U="


def test_event_field_and_data_field_allow_space_after_colon():
    """SSE fields allow one optional space after the colon."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "c3BhY2VkZXZlbnQ="}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "c3BhY2VkZXZlbnQ="


# ============================================================================
# Category 5: Multi-line data concatenation and ignored fields
# ============================================================================

def test_multiline_data_concatenation():
    """Multiple 'data:' lines concatenate to form valid JSON."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed",\n',
        'data: "b64_json": "bXVsdGlsaW5l"}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "bXVsdGlsaW5l"


def test_empty_event_id_retry_fields_ignored():
    """Empty event, id, retry, and unknown fields do not affect parsing."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event:\n",
        "id: 12345\n",
        "retry: 3000\n",
        "unknown: field\n",
        "event: image_generation.completed\n",
        'data: {"b64_json": "aWdub3JlZA=="}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "aWdub3JlZA=="


# ============================================================================
# Category 6: partial-only, empty stream, [DONE] before completed
# ============================================================================

def test_partial_only_with_done_error():
    """Partial events only followed by [DONE] raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.partial_image\n",
        'data: {"partial_image_b64": "cGFydGlhbA=="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError, match="completed"):
        parse_sse(lines, max_event_bytes=10000)


def test_empty_stream_error():
    """Empty stream raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = []

    with pytest.raises(ValueError, match="completed|end"):
        parse_sse(lines, max_event_bytes=10000)


def test_done_before_completed_error():
    """[DONE] appearing before any completed event raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: progress\n",
        'data: {"percent": 10}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError, match="completed"):
        parse_sse(lines, max_event_bytes=10000)


# ============================================================================
# Category 7: Malformed JSON and invalid input types
# ============================================================================

def test_malformed_json_error():
    """Malformed JSON in data field raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": invalid}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_invalid_utf8_bytes_error():
    """Invalid UTF-8 bytes raise ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        b"event: image_generation.completed\n",
        b'data: \xff\xfe invalid utf8\n',
        b"\n",
    ]

    with pytest.raises((ValueError, UnicodeDecodeError)):
        parse_sse(lines, max_event_bytes=10000)


def test_non_string_non_bytes_line_error():
    """Non-string, non-bytes line raises TypeError or ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        123,
        'data: {"b64_json": "ZGF0YQ=="}\n',
        "\n",
    ]

    with pytest.raises((TypeError, ValueError)):
        parse_sse(lines, max_event_bytes=10000)


def test_lines_as_string_itself_error():
    """Passing a single string instead of iterable of lines raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    # String itself is iterable of characters, should be rejected
    with pytest.raises((TypeError, ValueError)):
        parse_sse('data: {"b64_json": "test"}\n\n', max_event_bytes=10000)


def test_lines_as_bytes_itself_error():
    """Passing single bytes object instead of iterable of lines raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    with pytest.raises((TypeError, ValueError)):
        parse_sse(b'data: {"b64_json": "test"}\n\n', max_event_bytes=10000)


def test_non_iterable_lines_error():
    """Non-iterable lines argument raises TypeError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    with pytest.raises(TypeError):
        parse_sse(None, max_event_bytes=10000)


# ============================================================================
# Category 8: Error events and bounded error messages
# ============================================================================

def test_event_error_raises_valueerror():
    """Event type 'error' raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: error\n",
        'data: {"message": "Something went wrong"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_type_failed_suffix_error():
    """Payload type ending with '.failed' raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.failed\n",
        'data: {"type": "image_generation.failed", "error": "generation error"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_payload_with_nonempty_error_field():
    """Payload containing non-empty 'error' field raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        'data: {"error": "API rate limit exceeded", "details": "retry after 60s"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_error_message_bounded_no_secrets():
    """Error messages are bounded and don't echo secrets/base64/URL query params."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: error\n",
        'data: {"error": "Failed", "secret_key": "sk_live_1234567890abcdef", "image_b64": "' + 'A' * 10000 + '", "url": "https://api.example.com?token=secret123"}\n',
        "\n",
    ]

    with pytest.raises(ValueError) as exc_info:
        parse_sse(lines, max_event_bytes=50000)

    error_msg = str(exc_info.value)
    # Error message should be bounded (e.g., <= 300 chars)
    assert len(error_msg) <= 300
    # Should not echo the secret key, long base64, or URL query params
    assert "sk_live_1234567890abcdef" not in error_msg
    assert "secret123" not in error_msg


def test_generic_stream_error_message():
    """Generic stream error can be tested with simple assertion."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: error\n",
        'data: {"error": "unknown failure"}\n',
        "\n",
    ]

    # Just assert it raises ValueError, message content is implementation detail
    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


# ============================================================================
# Category 9: Completed event validation errors
# ============================================================================

def test_completed_event_no_artifact_error():
    """Completed event with no artifact field raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"type": "image_generation.completed", "status": "done"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_empty_artifact_value_error():
    """Empty artifact value raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": ""}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_whitespace_only_artifact_error():
    """Whitespace-only artifact value raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "   "}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_both_b64_and_url_error():
    """Having both b64_json and url artifacts raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "ZGF0YQ==", "url": "https://example.com/image.png"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_nested_multiple_artifacts_error():
    """Nested structure with multiple artifacts raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"data": [{"url": "https://example.com/1.png"}, {"url": "https://example.com/2.png"}]}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_same_kind_two_artifacts_error():
    """Two artifacts of the same kind raise ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"url": "https://example.com/1.png", "data": {"url": "https://example.com/2.png"}}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_multiple_completed_events_error():
    """Multiple completed events raise ValueError, even if identical."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "Zmlyc3Q="}\n',
        "\n",
        "event: image_generation.completed\n",
        'data: {"b64_json": "Zmlyc3Q="}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


# ============================================================================
# Category 10: max_event_bytes enforcement
# ============================================================================

def test_max_event_bytes_exact_boundary_pass():
    """Event exactly at max_event_bytes boundary passes."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    # Calculate exact byte size
    event_line = "event: image_generation.completed\n"
    data_line = 'data: {"b64_json": "dGVzdA=="}\n'
    empty_line = "\n"

    total_bytes = len(event_line.encode('utf-8')) + len(data_line.encode('utf-8')) + len(empty_line.encode('utf-8'))

    lines = [event_line, data_line, empty_line]

    result = parse_sse(lines, max_event_bytes=total_bytes)
    assert result.kind == "b64_json"


def test_max_event_bytes_exceeds_by_one_error():
    """Event exceeding max_event_bytes by 1 raises ValueError before completing."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    event_line = "event: image_generation.completed\n"
    data_line = 'data: {"b64_json": "dGVzdA=="}\n'
    empty_line = "\n"

    total_bytes = len(event_line.encode('utf-8')) + len(data_line.encode('utf-8')) + len(empty_line.encode('utf-8'))

    lines = [event_line, data_line, empty_line]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=total_bytes - 1)


def test_max_event_bytes_stops_consuming_iterator():
    """When max_event_bytes exceeded, iterator consumption stops."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    class ObservableIterator:
        def __init__(self):
            self.consumed_count = 0

        def __iter__(self):
            return self

        def __next__(self):
            self.consumed_count += 1
            if self.consumed_count == 1:
                # First event: large enough to exceed limit
                return 'data: {"type": "x", "payload": "' + 'X' * 1000 + '"}\n'
            elif self.consumed_count == 2:
                return "\n"
            else:
                # If this is consumed, it means parser didn't stop
                raise AssertionError("Iterator consumed beyond max_event_bytes violation")

    observable = ObservableIterator()

    with pytest.raises(ValueError):
        parse_sse(observable, max_event_bytes=100)

    # Should have stopped early, not consumed the assertion-raising item
    assert observable.consumed_count <= 2


def test_max_event_bytes_invalid_values():
    """max_event_bytes with invalid values raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = ['data: {"b64_json": "dGVzdA=="}\n', "\n"]

    # max_event_bytes <= 0
    with pytest.raises((ValueError, TypeError)):
        parse_sse(lines, max_event_bytes=0)

    with pytest.raises((ValueError, TypeError)):
        parse_sse(lines, max_event_bytes=-1)

    # max_event_bytes as bool
    with pytest.raises(TypeError):
        parse_sse(lines, max_event_bytes=True)

    # max_event_bytes as non-int
    with pytest.raises(TypeError):
        parse_sse(lines, max_event_bytes="1000")


def test_max_event_bytes_keyword_only():
    """max_event_bytes must be keyword-only argument."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = ['data: {"b64_json": "dGVzdA=="}\n', "\n"]

    # Positional argument should raise TypeError
    with pytest.raises(TypeError):
        parse_sse(lines, 10000)  # Trying to pass max_event_bytes positionally


# ============================================================================
# Category 11: Unexpected EOF scenarios
# ============================================================================

def test_pending_event_without_empty_line_eof_error():
    """Pending event/data without empty line termination, even valid JSON, raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "dGVzdA=="}\n',
        # Missing empty line, then EOF
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_event_header_only_eof_error():
    """Event header only followed by EOF raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        # EOF - no data, no empty line
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_completed_with_empty_line_then_eof_accepted():
    """Completed event with empty line termination, then EOF is accepted."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "dmFsaWQ="}\n',
        "\n",
        # EOF here is fine
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "dmFsaWQ="


# ============================================================================
# Category 12: [DONE] handling
# ============================================================================

def test_content_after_done_error():
    """Any event/data content after [DONE] raises ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "Y29tcGxldGU="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
        "event: extra\n",
        'data: {"extra": "data"}\n',
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_empty_lines_after_done_accepted():
    """Empty lines after [DONE] are accepted."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "ZG9uZQ=="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
        "\n",
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "ZG9uZQ=="


def test_comments_after_done_accepted():
    """Comment lines after [DONE] are accepted."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        'data: {"b64_json": "ZmluaXNo"}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
        ": This is a comment\n",
        ": Another comment\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "ZmluaXNo"


# ============================================================================
# Category 13: BOM handling
# ============================================================================

def test_bom_first_line_optional_removal():
    """UTF-8 BOM on first line is optionally removed."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "\ufeffevent: image_generation.completed\n",
        'data: {"b64_json": "Ym9t"}\n',
        "\n",
    ]

    result = parse_sse(lines, max_event_bytes=10000)
    assert result.kind == "b64_json"
    assert result.value == "Ym9t"


def test_bom_middle_line_error():
    """BOM in middle of stream raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed\n",
        "﻿data: {\"b64_json\": \"bWlkZGxl\"}\n",
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_malformed_bom_error():
    """Malformed BOM-like sequence raises error."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "﻿﻿data: {\"b64_json\": \"YmFk\"}\n",
        "\n",
    ]

    # Double BOM or other malformed patterns should error
    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


# ============================================================================
# Category 14: Artifact source validation and recursion limits
# ============================================================================

def test_artifact_from_partial_event_rejected():
    """Artifact fields in partial events are not accepted as final artifact."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.partial_image\n",
        'data: {"b64_json": "cGFydGlhbA=="}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_artifact_from_progress_event_rejected():
    """Artifact fields in progress events are rejected."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: progress\n",
        'data: {"b64_json": "cHJvZ3Jlc3M=", "percent": 75}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_artifact_from_unknown_event_rejected():
    """Artifact fields in unknown event types are rejected."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: unknown.type\n",
        'data: {"url": "https://example.com/unknown.png"}\n',
        "\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=10000)


def test_deep_nested_artifact_recursion_limit():
    """Deeply nested artifact structure (>64 levels) raises ValueError, not RecursionError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    # Build a >64 level deep nested structure
    nested = {"url": "https://example.com/deep.png"}
    for _ in range(70):
        nested = {"data": [nested]}

    import json
    data_json = json.dumps(nested)

    lines = [
        "event: image_generation.completed\n",
        f"data: {data_json}\n",
        "\n",
    ]

    with pytest.raises(ValueError):
        parse_sse(lines, max_event_bytes=100000)


# ============================================================================
# Category 15: Public interface signature and module isolation
# ============================================================================

def test_payload_error_without_type_still_aborts_before_later_completed():
    """A truthy payload error is authoritative even without event/type metadata."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    secret = "STREAM_ERROR_SECRET_9147"
    lines = [
        f'data: {{"error": "{secret}"}}\n',
        "\n",
        "event: completed\n",
        'data: {"b64_json": "T0s="}\n',
        "\n",
    ]

    with pytest.raises(ValueError) as exc:
        parse_sse(lines, max_event_bytes=10000)
    assert secret not in str(exc.value)


def test_event_error_cannot_be_overridden_by_completed_payload_type():
    """The event:error field cannot be downgraded by payload type metadata."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: error\n",
        'data: {"type": "completed", "b64_json": "T0s="}\n',
        "\n",
    ]

    with pytest.raises(ValueError, match="error"):
        parse_sse(lines, max_event_bytes=10000)


def test_done_marker_requires_blank_line_commit():
    """A [DONE] data field followed directly by EOF is an incomplete event."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: completed\n",
        'data: {"b64_json": "T0s="}\n',
        "\n",
        "data: [DONE]\n",
    ]

    with pytest.raises(ValueError, match="EOF|pending|incomplete"):
        parse_sse(lines, max_event_bytes=10000)


def test_comment_only_events_reset_byte_budget_at_blank_line():
    """Independent comment events must not accumulate one shared byte budget."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = []
    for _ in range(5):
        lines.extend([":" + "x" * 20 + "\n", "\n"])
    lines.extend([
        "event: completed\n",
        'data: {"b64_json": "T0s="}\n',
        "\n",
    ])

    result = parse_sse(lines, max_event_bytes=50)
    assert result == CompletedArtifact(kind="b64_json", value="T0s=")


def test_first_line_bom_raw_bytes_count_toward_event_limit():
    """Removing a BOM for parsing must not remove its three bytes from accounting."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "\ufeffevent: completed\n",
        'data: {"b64_json":"T0s="}\n',
        "\n",
    ]
    raw_size = sum(len(line.encode("utf-8")) for line in lines)

    with pytest.raises(ValueError, match="max_event_bytes|exceeds"):
        parse_sse(lines, max_event_bytes=raw_size - 1)
    assert parse_sse(lines, max_event_bytes=raw_size).value == "T0s="


def test_extremely_deep_json_is_bounded_value_error_not_recursionerror():
    """json decoder recursion limits must map to a stable protocol ValueError."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    depth = 1100
    payload = '{"data":' * depth + '{"url":"x"}' + '}' * depth
    lines = ["event: completed\n", f"data: {payload}\n", "\n"]

    with pytest.raises(ValueError) as exc:
        parse_sse(lines, max_event_bytes=len(payload.encode("utf-8")) + 1000)
    assert not isinstance(exc.value, RecursionError)
    assert len(str(exc.value)) <= 300


def test_requests_iter_lines_without_terminators_is_supported():
    """Requests-style iter_lines output omits line terminators but keeps blank separators."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.completed",
        'data: {"b64_json":"T0s="}',
        "",
        "data: [DONE]",
        "",
    ]

    assert parse_sse(lines, max_event_bytes=1000).value == "T0s="


def test_completed_or_done_header_without_data_fails_before_later_success():
    """A committed completed/done header without data is not an ignorable event."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    for name in ("completed", "done", "image_generation.completed"):
        lines = [
            f"event: {name}\n",
            "\n",
            "event: completed\n",
            'data: {"b64_json":"T0s="}\n',
            "\n",
        ]
        with pytest.raises(ValueError, match="artifact"):
            parse_sse(lines, max_event_bytes=1000)


def test_failed_header_without_data_cannot_be_hidden_by_later_completed():
    """A failed event is authoritative even when it has no data payload."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: image_generation.failed\n",
        "\n",
        "event: completed\n",
        'data: {"b64_json":"T0s="}\n',
        "\n",
    ]

    with pytest.raises(ValueError, match="error"):
        parse_sse(lines, max_event_bytes=1000)


def test_error_event_cannot_be_reclassified_as_done_sentinel():
    """An event:error header takes precedence over a [DONE] data marker."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    lines = [
        "event: completed\n",
        'data: {"b64_json":"T0s="}\n',
        "\n",
        "event: error\n",
        "data: [DONE]\n",
        "\n",
    ]

    with pytest.raises(ValueError, match="error"):
        parse_sse(lines, max_event_bytes=1000)


def test_iterator_failure_is_sanitized_and_bounded():
    """A streaming iterator failure must not expose provider exception details."""
    from hermes_post_design.chiyi_core.streaming import parse_sse

    secret = "ITERATOR_STREAM_SECRET_7319"

    def broken_lines():
        yield "event: progress\n"
        raise RuntimeError(f"socket failed token={secret}")

    with pytest.raises(ValueError) as exc:
        parse_sse(broken_lines(), max_event_bytes=1000)
    assert secret not in str(exc.value)
    assert len(str(exc.value)) <= 300


def test_public_signature_max_event_bytes_keyword_only():
    """Verify parse_sse(lines, *, max_event_bytes: int) signature."""
    from hermes_post_design.chiyi_core.streaming import parse_sse
    import inspect

    sig = inspect.signature(parse_sse)
    params = list(sig.parameters.values())

    # First parameter: lines
    assert params[0].name == "lines"
    assert params[0].kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY)

    # Second parameter: max_event_bytes, keyword-only
    assert params[1].name == "max_event_bytes"
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY


def test_streaming_module_no_external_dependencies():
    """Streaming module imports only stdlib plus local models."""
    module_path = (
        Path(__file__).parents[2]
        / "src"
        / "hermes_post_design"
        / "chiyi_core"
        / "streaming.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    forbidden = ("requests", "urllib3", "httpx", "PIL", "agent", "tools", "hermes_cli")
    assert not any(
        name == prefix or name.startswith(prefix + ".")
        for name in imported
        for prefix in forbidden
    )
