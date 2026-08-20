"""Size resolution and validation for gpt-image-2 canvas constraints."""
import re

from .models import SizePlan

# Size constants
DEFAULT_SIZE = "1024x1024"
MIN_OUTPUT_SHORT_EDGE = 1024
MIN_CUSTOM_SHORT_EDGE = 256
MAX_CUSTOM_DIMENSION = 3840
MIN_UPSTREAM_PIXELS = 655_360
MAX_UPSTREAM_PIXELS = 8_294_400
SIZE_MULTIPLE = 16

# Maximum aspect ratio (either direction)
_MAX_ASPECT_RATIO = 3.0

# Size pattern: WIDTHxHEIGHT (case insensitive)
_SIZE_PATTERN = re.compile(r"^(\d+)x(\d+)$", re.IGNORECASE)


def resolve_size(size: str) -> SizePlan:
    """Resolve requested size to upstream canvas and target dimensions.

    Args:
        size: Size string in "WIDTHxHEIGHT" format (e.g., "1080x1920")

    Returns:
        SizePlan with requested size, upstream canvas size, and target dimensions

    Raises:
        ValueError: If size format is invalid or violates dimension/pixel/ratio constraints
    """
    # Validate type and format
    if not isinstance(size, str):
        raise ValueError("size must use WIDTHxHEIGHT, for example 1080x1920")

    size = size.strip()
    match = _SIZE_PATTERN.match(size)
    if not match:
        raise ValueError("size must use WIDTHxHEIGHT, for example 1080x1920")

    width = int(match.group(1))
    height = int(match.group(2))

    # Zero dimensions are format errors, not constraint violations
    if width == 0 or height == 0:
        raise ValueError("size must use WIDTHxHEIGHT, for example 1080x1920")

    # Validate basic dimension constraints
    short_edge = min(width, height)
    long_edge = max(width, height)

    if short_edge < MIN_CUSTOM_SHORT_EDGE:
        raise ValueError(
            f"Short edge must be at least {MIN_CUSTOM_SHORT_EDGE}, got {short_edge}"
        )

    if long_edge > MAX_CUSTOM_DIMENSION:
        raise ValueError(
            f"Long edge must not exceed {MAX_CUSTOM_DIMENSION}, got {long_edge}"
        )

    # Validate requested pixels
    requested_pixels = width * height
    if requested_pixels > MAX_UPSTREAM_PIXELS:
        raise ValueError(
            f"Requested size {width}x{height} pixels exceed 8,294,400 limit"
        )

    # Validate aspect ratio (use integer comparison to avoid float precision issues)
    if long_edge > short_edge * 3:
        raise ValueError(
            f"Aspect ratio must not exceed 3:1, got {long_edge}:{short_edge}"
        )

    # Calculate upstream canvas dimensions using pure integer arithmetic
    if short_edge >= MIN_OUTPUT_SHORT_EDGE:
        # No scaling needed, just round up to SIZE_MULTIPLE
        # Formula: ((edge + SIZE_MULTIPLE - 1) // SIZE_MULTIPLE) * SIZE_MULTIPLE
        upstream_width = ((width + SIZE_MULTIPLE - 1) // SIZE_MULTIPLE) * SIZE_MULTIPLE
        upstream_height = ((height + SIZE_MULTIPLE - 1) // SIZE_MULTIPLE) * SIZE_MULTIPLE
    else:
        # Scale up so short edge reaches MIN_OUTPUT_SHORT_EDGE
        # Formula: ceil(edge * MIN_OUTPUT_SHORT_EDGE / short_edge / SIZE_MULTIPLE) * SIZE_MULTIPLE
        # Implemented as: ((edge * MIN_OUTPUT_SHORT_EDGE + denominator - 1) // denominator) * SIZE_MULTIPLE
        denominator = short_edge * SIZE_MULTIPLE
        upstream_width = ((width * MIN_OUTPUT_SHORT_EDGE + denominator - 1) // denominator) * SIZE_MULTIPLE
        upstream_height = ((height * MIN_OUTPUT_SHORT_EDGE + denominator - 1) // denominator) * SIZE_MULTIPLE

    # Validate upstream canvas constraints
    upstream_pixels = upstream_width * upstream_height
    upstream_max_dim = max(upstream_width, upstream_height)

    if upstream_max_dim > MAX_CUSTOM_DIMENSION:
        raise ValueError(
            f"Requested size {width}x{height} cannot map to valid gpt-image-2 canvas: "
            f"upstream dimension {upstream_max_dim} exceeds {MAX_CUSTOM_DIMENSION}"
        )

    if upstream_pixels < MIN_UPSTREAM_PIXELS or upstream_pixels > MAX_UPSTREAM_PIXELS:
        raise ValueError(
            f"Requested size {width}x{height} cannot map to valid gpt-image-2 canvas: "
            f"upstream pixels {upstream_pixels} outside valid range "
            f"[{MIN_UPSTREAM_PIXELS}, {MAX_UPSTREAM_PIXELS}]"
        )

    # Normalize requested format to lowercase 'x'
    requested_normalized = f"{width}x{height}"
    upstream_size = f"{upstream_width}x{upstream_height}"

    return SizePlan(
        requested=requested_normalized,
        upstream=upstream_size,
        target_width=width,
        target_height=height,
    )
