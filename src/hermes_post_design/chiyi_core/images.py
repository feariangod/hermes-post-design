"""Image inspection and normalization."""
import io
from typing import Literal

from PIL import Image, ImageOps

from hermes_post_design.chiyi_core.models import ImageInfo

MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000

# Supported formats
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}

# Format to normalized name mapping
FORMAT_TO_NAME: dict[str, Literal["png", "jpg", "webp", "gif"]] = {
    "PNG": "png",
    "JPEG": "jpg",
    "WEBP": "webp",
    "GIF": "gif",
}

# MIME type mapping
MIME_TO_FORMAT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}

FORMAT_TO_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _open_image_checked(data: bytes) -> Image.Image:
    """
    Open image with decompression bomb detection.

    Treats DecompressionBombWarning as error and maps both warning and error
    to ValueError with consistent message.

    Args:
        data: Raw image bytes

    Returns:
        Opened PIL Image object

    Raises:
        ValueError: If decompression bomb detected or image cannot be opened
    """
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            return Image.open(io.BytesIO(data))
        except Image.DecompressionBombWarning as e:
            raise ValueError(f"Image too large: decompression bomb detected - {e}") from e
        except Image.DecompressionBombError as e:
            raise ValueError(f"Image too large: decompression bomb detected - {e}") from e


def inspect_image(data: bytes, *, declared_mime: str | None = None) -> ImageInfo:
    """
    Inspect image data and return metadata.

    Args:
        data: Raw image bytes
        declared_mime: Optional declared MIME type to validate

    Returns:
        ImageInfo with format, dimensions, MIME type, and frame count

    Raises:
        ValueError: If data is invalid, unsupported format, too large,
                   or declared_mime doesn't match actual format
    """
    # Validate input type
    if not isinstance(data, bytes):
        raise ValueError("Image data must be bytes")

    # Check size limit first
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(
            f"Image data exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB"
        )

    if len(data) == 0:
        raise ValueError("Image data is empty")

    # Validate declared MIME if provided
    normalized_declared_format = None
    if declared_mime is not None:
        # Normalize: strip parameters and lowercase
        mime_clean = declared_mime.split(";")[0].strip().lower()

        # Check it's an image MIME
        if not mime_clean.startswith("image/"):
            raise ValueError(f"Declared MIME type '{declared_mime}' is not an image type")

        # Check it's supported
        if mime_clean not in MIME_TO_FORMAT:
            raise ValueError(f"Unsupported MIME type: {mime_clean}")

        normalized_declared_format = MIME_TO_FORMAT[mime_clean]

    # Open and inspect image
    try:
        img = _open_image_checked(data)
    except ValueError:
        # Re-raise our ValueError
        raise
    except Exception as e:
        # Convert all other Pillow/IO errors to ValueError
        raise ValueError(f"Cannot identify image: invalid or corrupted data") from e

    try:
        # Check format is supported
        if img.format not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {img.format}")

        # Get normalized format name
        format_name = FORMAT_TO_NAME[img.format]

        # Verify declared MIME matches actual format
        if normalized_declared_format is not None and normalized_declared_format != format_name:
            raise ValueError(
                f"MIME type mismatch: declared {declared_mime} but actual format is {format_name}"
            )

        # Get dimensions
        width, height = img.size

        # Check pixel count
        if width * height > MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Image exceeds maximum pixels: {width}x{height} = {width * height} > {MAX_IMAGE_PIXELS}"
            )

        # Get frame count
        try:
            n_frames = getattr(img, "n_frames", 1)
        except Exception:
            n_frames = 1

        # Reject multi-frame/animated images
        if n_frames > 1:
            raise ValueError(f"Animated or multiple frame image not supported: {format_name} with {n_frames} frames")

        # Verify image integrity using a separate image instance
        # This is a defensive integrity check that can catch corruption not detectable
        # from header-only inspection (e.g., truncated data, invalid chunks).
        # verify() is destructive and affects the main image, so open a new instance.
        try:
            verify_img = _open_image_checked(data)
            try:
                verify_img.verify()
            finally:
                verify_img.close()
        except ValueError:
            # Re-raise ValueError (including decompression bombs)
            raise
        except Exception as e:
            raise ValueError("Image verification failed: corrupted data") from e

        # Return ImageInfo
        return ImageInfo(
            format=format_name,
            mime_type=FORMAT_TO_MIME[format_name],
            width=width,
            height=height,
            frames=n_frames,
        )

    finally:
        img.close()


def normalize_image(data: bytes, *, target_width: int, target_height: int) -> tuple[bytes, bool]:
    """
    Normalize image to target dimensions.

    If source dimensions match target and no EXIF orientation correction needed,
    returns original bytes with normalized=False. Otherwise, performs center crop
    with LANCZOS resampling and returns new bytes with normalized=True.

    Args:
        data: Raw image bytes
        target_width: Target width in pixels (must be > 0)
        target_height: Target height in pixels (must be > 0)

    Returns:
        Tuple of (normalized_bytes, normalized_flag)

    Raises:
        ValueError: If target dimensions invalid or output too large
    """
    # Validate target dimensions
    if target_width <= 0:
        raise ValueError(f"Invalid target width: {target_width} (must be positive)")
    if target_height <= 0:
        raise ValueError(f"Invalid target height: {target_height} (must be positive)")

    # Check target pixel count
    target_pixels = target_width * target_height
    if target_pixels > MAX_IMAGE_PIXELS:
        raise ValueError(
            f"Target dimensions exceed maximum pixels: {target_width}x{target_height} = {target_pixels} > {MAX_IMAGE_PIXELS}"
        )

    # Inspect source image
    source_info = inspect_image(data)

    # Open image for processing
    img = Image.open(io.BytesIO(data))
    img_transposed = None
    img_fitted = None

    try:
        # Check EXIF orientation before any transformation
        orientation = None
        try:
            orientation = img.getexif().get(0x0112)
        except Exception:
            # If EXIF reading fails, treat as no orientation
            pass

        # Determine if orientation correction is needed
        # Only orientation None or 1 means no correction needed
        needs_orientation = orientation not in (None, 1)

        # Apply EXIF orientation correction
        img_transposed = ImageOps.exif_transpose(img)

        if img_transposed is not None:
            # Check if dimensions match target after transpose
            if img_transposed.size == (target_width, target_height) and not needs_orientation:
                # No normalization needed - close resources and return original
                img_transposed.close()
                return data, False

            # Use transposed image for further processing
            # Close original and work with transposed
            img.close()
            img = img_transposed
            img_transposed = None  # Prevent double-close
        else:
            # No transposition occurred
            if img.size == (target_width, target_height) and not needs_orientation:
                # No normalization needed
                return data, False

        # Perform center crop and resize
        img_fitted = ImageOps.fit(
            img,
            (target_width, target_height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

        # Convert JPEG to RGB if needed (remove alpha)
        if source_info.format == "jpg" and img_fitted.mode not in ("RGB", "L"):
            converted = img_fitted.convert("RGB")
            # Close the original fitted image to prevent resource leak
            img_fitted.close()
            img_fitted = converted

        # Encode based on original format
        output_buf = io.BytesIO()

        if source_info.format == "png":
            img_fitted.save(output_buf, format="PNG", optimize=True)
        elif source_info.format == "jpg":
            img_fitted.save(output_buf, format="JPEG", quality=95, optimize=True)
        elif source_info.format == "webp":
            img_fitted.save(output_buf, format="WEBP", quality=95)
        elif source_info.format == "gif":
            img_fitted.save(output_buf, format="GIF")
        else:
            raise ValueError(f"Unsupported format for normalization: {source_info.format}")

        output_data = output_buf.getvalue()

        # Check output size
        if len(output_data) > MAX_IMAGE_BYTES:
            raise ValueError(
                f"Normalized image exceeds maximum size of {MAX_IMAGE_BYTES / (1024 * 1024):.0f}MB"
            )

        # Verify output
        result_info = inspect_image(output_data)
        if result_info.width != target_width or result_info.height != target_height:
            raise ValueError(
                f"Normalization failed: expected {target_width}x{target_height}, "
                f"got {result_info.width}x{result_info.height}"
            )

        return output_data, True

    finally:
        # Clean up all image resources
        if img is not None:
            try:
                img.close()
            except Exception:
                pass
        if img_transposed is not None:
            try:
                img_transposed.close()
            except Exception:
                pass
        if img_fitted is not None:
            try:
                img_fitted.close()
            except Exception:
                pass
