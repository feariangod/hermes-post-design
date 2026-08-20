"""SSE (Server-Sent Events) streaming parser for Chiyi image generation.

Public interface:
    parse_sse(lines, *, max_event_bytes: int) -> CompletedArtifact

Parses SSE stream and returns the completed artifact. All failures raise ValueError.
"""
import json
from collections.abc import Iterable

from hermes_post_design.chiyi_core.models import CompletedArtifact


def parse_sse(lines: object, *, max_event_bytes: int) -> CompletedArtifact:
    """Parse SSE stream and return completed artifact.

    Args:
        lines: Iterable of str or bytes lines (each line should include terminator)
        max_event_bytes: Maximum bytes per event (must be positive int, not bool)

    Returns:
        CompletedArtifact with kind ('b64_json' or 'url') and value

    Raises:
        TypeError: Invalid argument types
        ValueError: Stream errors, malformed data, or protocol violations
    """
    # Validate max_event_bytes
    if isinstance(max_event_bytes, bool):
        raise TypeError("max_event_bytes must be int, not bool")
    if not isinstance(max_event_bytes, int):
        raise TypeError(f"max_event_bytes must be int, not {type(max_event_bytes).__name__}")
    if max_event_bytes <= 0:
        raise ValueError("max_event_bytes must be positive")

    # Validate lines is iterable but not str/bytes/None
    if lines is None:
        raise TypeError("lines must be iterable")
    if isinstance(lines, (str, bytes)):
        raise ValueError("lines must be iterable of lines, not a single str/bytes")
    if not isinstance(lines, Iterable):
        raise TypeError("lines must be iterable")

    # State machine
    event_type = None  # Current event type (from 'event:' field)
    data_lines = []  # Accumulated data lines for current event
    current_event_bytes = 0  # Byte count for current event
    completed_artifact = None  # The one completed artifact we find
    done_seen = False  # Whether [DONE] was encountered
    first_line = True  # Track first line for BOM handling
    pending = False  # Track if we have uncommitted event/data fields

    try:
        iterator = iter(lines)
    except TypeError:
        raise TypeError("lines must be iterable")

    # Explicit iteration to sanitize iterator exceptions
    while True:
        try:
            line = next(iterator)
        except StopIteration:
            break
        except Exception:
            raise ValueError("SSE stream iteration failed") from None
        # Validate line type
        if not isinstance(line, (str, bytes)):
            raise ValueError(f"Each line must be str or bytes, got {type(line).__name__}")

        # Convert bytes to str
        if isinstance(line, bytes):
            try:
                line = line.decode('utf-8', errors='strict')
            except UnicodeDecodeError as e:
                raise ValueError(f"Invalid UTF-8 in line: {e}")

        # Store raw decoded text before any processing for byte calculation
        raw_decoded = line

        # Handle BOM on first line only
        if first_line:
            if line.startswith('﻿'):
                # Check for double BOM or malformed BOM
                if line.startswith('﻿﻿'):
                    raise ValueError("Malformed BOM sequence")
                line = line[1:]  # Remove single BOM for parsing
            first_line = False
        else:
            # BOM in middle of stream is error
            if '﻿' in line:
                raise ValueError("BOM not allowed after first line")

        # Calculate original line bytes BEFORE removing terminators
        # Use the raw_decoded text (includes BOM if present)
        raw_line_bytes = len(raw_decoded.encode('utf-8'))

        # Remove line terminator: \n and optional preceding \r
        if line.endswith('\n'):
            line = line[:-1]
            if line.endswith('\r'):
                line = line[:-1]

        # Accumulate byte count for current event
        current_event_bytes += raw_line_bytes
        if current_event_bytes > max_event_bytes:
            raise ValueError(f"Event exceeds max_event_bytes limit ({max_event_bytes})")

        # Empty line: dispatch event boundary
        if line == '':
            if pending:
                # Consume the pending event
                action, new_artifact = _consume_event(event_type, data_lines, completed_artifact)

                if action == 'completed':
                    completed_artifact = new_artifact
                elif action == 'error':
                    raise ValueError("SSE stream reported an error")
                elif action == 'done':
                    done_seen = True
                # action == 'ignore' or None: just continue

            # Reset event state (always reset, even if no pending event)
            event_type = None
            data_lines = []
            current_event_bytes = 0
            pending = False
            continue

        # After [DONE], only allow comments and empty lines
        if done_seen:
            if line.startswith(':'):
                continue  # Comment allowed
            # Any other content after [DONE] is error
            raise ValueError("Content after [DONE] not allowed")

        # Comment line: counted toward bytes but doesn't set pending
        if line.startswith(':'):
            continue

        # Parse field
        if ':' not in line:
            # Line without colon is malformed
            raise ValueError("SSE line missing colon")

        field_name, _, field_value = line.partition(':')

        # Check for leading whitespace in field name (not allowed)
        if field_name != field_name.lstrip():
            raise ValueError("Field name cannot have leading whitespace")

        # Remove optional single leading space from value
        if field_value.startswith(' '):
            field_value = field_value[1:]

        # Process known fields
        if field_name == 'event':
            event_type = field_value
            pending = True
        elif field_name == 'data':
            data_lines.append(field_value)
            pending = True
        elif field_name in ('id', 'retry'):
            # These fields are ignored but mark event as pending
            pending = True
        else:
            # Unknown field - ignored but marks event as pending
            pending = True

    # EOF reached - check final state
    if pending:
        # Uncommitted event at EOF
        raise ValueError("Unexpected EOF with pending event fields")

    if completed_artifact is None:
        raise ValueError("No completed event found in stream")

    return completed_artifact


def _consume_event(event_type, data_lines, completed_artifact):
    """Process a pending event and return action and optional artifact.

    Returns:
        (action, artifact) where action is 'completed', 'error', 'done', 'ignore', or None
        artifact is CompletedArtifact for 'completed' action, None otherwise

    Raises:
        ValueError: For malformed data, errors, or protocol violations
    """
    # No data lines - check event type
    if not data_lines:
        # Normalize event first
        norm_event = event_type.lower().strip() if event_type else None

        # Check for error/failed events
        if norm_event and (norm_event == 'error' or norm_event.endswith('.failed')):
            raise ValueError("SSE stream reported an error")

        # Check for completed/done events without data
        if norm_event and (norm_event.endswith('.completed') or norm_event in {'completed', 'done'}):
            raise ValueError("Completed event missing artifact")

        return ('ignore', None)

    # Join and trim data
    data_text = '\n'.join(data_lines)
    trimmed = data_text.strip()

    # Normalize event header before [DONE] classification: an error/failed
    # event header is authoritative and cannot be reclassified as a [DONE] sentinel.
    norm_event_pre = event_type.lower().strip() if event_type else None
    if norm_event_pre and (norm_event_pre == 'error' or norm_event_pre.endswith('.failed')):
        raise ValueError("SSE stream reported an error")

    # Check for [DONE] marker
    if trimmed == '[DONE]':
        if completed_artifact is None:
            raise ValueError("No completed artifact before [DONE]")
        return ('done', None)

    # Parse JSON data - catch all JSON-related errors and recursion
    try:
        data = json.loads(data_text)
    except json.JSONDecodeError:
        raise ValueError("Malformed SSE event data") from None
    except RecursionError:
        raise ValueError("Malformed SSE event data") from None
    except MemoryError:
        raise ValueError("Malformed SSE event data") from None
    except (UnicodeDecodeError, UnicodeError):
        raise ValueError("Malformed SSE event data") from None

    # Classify event: normalize event header and payload type
    norm_event = event_type.lower().strip() if event_type else None

    payload_type = None
    payload_error = None
    payload_kind = None
    has_partial_marker = False

    if isinstance(data, dict):
        pt = data.get('type')
        if isinstance(pt, str):
            payload_type = pt.lower().strip()

        # Check error field - any truthy value (not just string)
        pe = data.get('error')
        if pe:  # Truthy check
            payload_error = True

        # Check for partial markers
        if 'partial_image_b64' in data:
            has_partial_marker = True

        # Additional kind detection from payload
        for keyword in ('partial', 'progress', 'heartbeat'):
            if keyword in str(data.get('kind', '')).lower():
                payload_kind = keyword
                break

    # Priority 1: Error detection (highest priority)
    is_error = False
    if norm_event == 'error' or (norm_event and norm_event.endswith('.failed')):
        is_error = True
    if payload_type and (payload_type == 'error' or payload_type.endswith('.failed')):
        is_error = True
    if payload_error:
        is_error = True

    if is_error:
        raise ValueError("SSE stream reported an error")

    # Priority 2: Ignore partial/progress/heartbeat events
    # (prevent partial events masquerading as completed)
    is_ignorable = False
    if norm_event:
        for keyword in ('partial', 'progress', 'heartbeat'):
            if keyword in norm_event:
                is_ignorable = True
                break
    if payload_type:
        for keyword in ('partial', 'progress', 'heartbeat'):
            if keyword in payload_type:
                is_ignorable = True
                break
    if payload_kind or has_partial_marker:
        is_ignorable = True

    if is_ignorable:
        return ('ignore', None)

    # Priority 3: Completed event detection
    is_completed = False
    if norm_event and (norm_event.endswith('.completed') or norm_event in ('completed', 'done')):
        is_completed = True
    if payload_type and (payload_type.endswith('.completed') or payload_type in ('completed', 'done')):
        is_completed = True

    if not is_completed:
        # Unknown event with artifact - still ignore
        return ('ignore', None)

    # Extract artifact from completed event
    if completed_artifact is not None:
        raise ValueError("Multiple completed events")

    artifact = _extract_artifact_from_payload(data)
    return ('completed', artifact)


def _extract_artifact_from_payload(payload):
    """Extract artifact from completed event payload using explicit stack traversal.

    Args:
        payload: Parsed JSON payload (dict, list, or other)

    Returns:
        CompletedArtifact

    Raises:
        ValueError: If no artifact, multiple artifacts, or traversal limits exceeded
    """
    artifacts = []

    # Use explicit stack to avoid recursion
    stack = [(payload, 0)]  # (node, depth)
    visited_count = 0

    while stack:
        node, depth = stack.pop()

        # Depth limit
        if depth > 64:
            raise ValueError("Artifact nesting depth exceeds limit")

        # Node count limit
        visited_count += 1
        if visited_count > 10000:
            raise ValueError("Artifact tree too large")

        if isinstance(node, dict):
            # Check for artifact fields at this level
            for field_name in ('b64_json', 'url'):
                if field_name in node:
                    value = node[field_name]
                    if isinstance(value, str):
                        trimmed = value.strip()
                        if trimmed:  # Non-empty after trim
                            artifacts.append((field_name, trimmed))

            # Add child nodes to stack (in reverse to maintain order)
            for value in reversed(list(node.values())):
                if isinstance(value, (dict, list)):
                    stack.append((value, depth + 1))

        elif isinstance(node, list):
            # Add list items to stack (in reverse to maintain order)
            for item in reversed(node):
                if isinstance(item, (dict, list)):
                    stack.append((item, depth + 1))

    # Validate artifacts
    if not artifacts:
        raise ValueError("Completed event missing artifact")

    if len(artifacts) > 1:
        # Check if multiple kinds
        kinds = {kind for kind, _ in artifacts}
        if len(kinds) > 1:
            raise ValueError("Completed event has multiple artifact kinds")
        # Same kind multiple times is also error
        raise ValueError("Completed event has duplicate artifacts")

    kind, value = artifacts[0]
    return CompletedArtifact(kind=kind, value=value)
