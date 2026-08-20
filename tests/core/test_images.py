"""Tests for image inspection and normalization."""
import io
from unittest.mock import patch

import pytest
from PIL import Image, ImageOps

from hermes_post_design.chiyi_core.images import (
    MAX_IMAGE_BYTES,
    MAX_IMAGE_PIXELS,
    inspect_image,
    normalize_image,
)


def generate_png(width: int, height: int, color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    """Generate a PNG image programmatically."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_jpeg(width: int, height: int, color: tuple[int, int, int] = (0, 255, 0)) -> bytes:
    """Generate a JPEG image programmatically."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def generate_webp(width: int, height: int, color: tuple[int, int, int] = (0, 0, 255)) -> bytes:
    """Generate a WebP image programmatically."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=95)
    return buf.getvalue()


def generate_gif(width: int, height: int, color: tuple[int, int, int] = (255, 255, 0)) -> bytes:
    """Generate a single-frame GIF image programmatically."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    return buf.getvalue()


def generate_cmyk_jpeg(width: int, height: int) -> bytes:
    """Generate a CMYK JPEG image programmatically."""
    img = Image.new("CMYK", (width, height), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def generate_animated_webp(width: int, height: int, frames: int = 2) -> bytes:
    """Generate an animated WebP with multiple frames."""
    frame_list = []
    for i in range(frames):
        img = Image.new("RGB", (width, height), (i * 100, i * 50, i * 25))
        frame_list.append(img)

    buf = io.BytesIO()
    frame_list[0].save(
        buf,
        format="WEBP",
        save_all=True,
        append_images=frame_list[1:],
        duration=100,
        loop=0
    )
    return buf.getvalue()


def generate_apng(width: int, height: int, frames: int = 2) -> bytes:
    """Generate an animated PNG (APNG) with multiple frames."""
    frame_list = []
    for i in range(frames):
        img = Image.new("RGB", (width, height), (i * 100, i * 50, i * 25))
        frame_list.append(img)

    buf = io.BytesIO()
    try:
        frame_list[0].save(
            buf,
            format="PNG",
            save_all=True,
            append_images=frame_list[1:],
            duration=100,
            loop=0
        )
        return buf.getvalue()
    except Exception:
        # If APNG not supported, raise to allow test skip
        raise RuntimeError("APNG not supported by current Pillow version")


def generate_multi_frame_gif(width: int, height: int) -> bytes:
    """Generate a multi-frame animated GIF."""
    frames = []
    for i in range(3):
        img = Image.new("RGB", (width, height), (i * 80, i * 80, i * 80))
        frames.append(img)
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    return buf.getvalue()


def generate_jpeg_with_exif_orientation(width: int, height: int, orientation: int) -> bytes:
    """Generate a JPEG with EXIF orientation tag and four-quadrant colors.

    TL=red, TR=green, BL=blue, BR=yellow in original orientation.
    Uses large enough blocks to avoid JPEG compression artifacts at sampling points.
    """
    img = Image.new("RGB", (width, height))
    pixels = img.load()

    # Create four quadrants with distinct colors
    # Use 20% margins to avoid JPEG subsampling artifacts at edges
    margin_x = width // 10
    margin_y = height // 10

    for y in range(height):
        for x in range(width):
            # Determine quadrant
            is_left = x < width // 2
            is_top = y < height // 2

            if is_top and is_left:
                # Top-left: Red
                pixels[x, y] = (255, 0, 0)
            elif is_top and not is_left:
                # Top-right: Green
                pixels[x, y] = (0, 255, 0)
            elif not is_top and is_left:
                # Bottom-left: Blue
                pixels[x, y] = (0, 0, 255)
            else:
                # Bottom-right: Yellow
                pixels[x, y] = (255, 255, 0)

    buf = io.BytesIO()
    # Save with EXIF orientation
    exif_data = img.getexif()
    exif_data[0x0112] = orientation  # Orientation tag
    img.save(buf, format="JPEG", quality=95, exif=exif_data)
    return buf.getvalue()


def get_dominant_color_channel(pixel: tuple[int, int, int]) -> str:
    """Return dominant color channel: 'red', 'green', 'blue', 'yellow', or 'other'."""
    r, g, b = pixel

    # Check for yellow (high red and green, low blue)
    if r > 200 and g > 200 and b < 100:
        return "yellow"

    # Check primary colors
    if r > max(g, b) + 100:
        return "red"
    if g > max(r, b) + 100:
        return "green"
    if b > max(r, g) + 100:
        return "blue"

    return "other"


class TestInspectImage:
    """Tests for inspect_image function."""

    def test_inspect_png(self):
        """Programmatically generated PNG returns correct format, MIME, dimensions, frames."""
        data = generate_png(800, 600)
        info = inspect_image(data)

        assert info.format == "png"
        assert info.mime_type == "image/png"
        assert info.width == 800
        assert info.height == 600
        assert info.frames == 1

    def test_inspect_jpeg(self):
        """Programmatically generated JPEG returns correct metadata."""
        data = generate_jpeg(1024, 768)
        info = inspect_image(data)

        assert info.format == "jpg"
        assert info.mime_type == "image/jpeg"
        assert info.width == 1024
        assert info.height == 768
        assert info.frames == 1

    def test_inspect_webp(self):
        """Programmatically generated WebP returns correct metadata."""
        data = generate_webp(640, 480)
        info = inspect_image(data)

        assert info.format == "webp"
        assert info.mime_type == "image/webp"
        assert info.width == 640
        assert info.height == 480
        assert info.frames == 1

    def test_inspect_single_frame_gif(self):
        """Single-frame GIF is accepted."""
        data = generate_gif(500, 500)
        info = inspect_image(data)

        assert info.format == "gif"
        assert info.mime_type == "image/gif"
        assert info.width == 500
        assert info.height == 500
        assert info.frames == 1

    def test_reject_empty_bytes(self):
        """Empty bytes raises ValueError."""
        with pytest.raises(ValueError, match="empty|invalid|cannot"):
            inspect_image(b"")

    def test_reject_corrupted_bytes(self):
        """Random corrupted bytes raises ValueError."""
        with pytest.raises(ValueError, match="invalid|cannot|identify"):
            inspect_image(b"\x89PNG\r\n\x1a\ncorrupted_data_here")

    def test_reject_oversized_bytes(self):
        """Data exceeding MAX_IMAGE_BYTES raises ValueError."""
        # Temporarily patch constant to avoid large memory allocation
        with patch("hermes_post_design.chiyi_core.images.MAX_IMAGE_BYTES", 1000):
            large_data = b"\x00" * 1001
            with pytest.raises(ValueError, match="exceeds|maximum|size|25"):
                inspect_image(large_data)

    def test_reject_unsupported_bmp(self):
        """BMP format raises ValueError."""
        img = Image.new("RGB", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="BMP")

        with pytest.raises(ValueError, match="unsupported|format|BMP"):
            inspect_image(buf.getvalue())

    def test_reject_unsupported_tiff(self):
        """TIFF format raises ValueError."""
        img = Image.new("RGB", (100, 100))
        buf = io.BytesIO()
        img.save(buf, format="TIFF")

        with pytest.raises(ValueError, match="unsupported|format|TIFF"):
            inspect_image(buf.getvalue())

    def test_reject_excessive_pixels(self):
        """Image with pixels > MAX_IMAGE_PIXELS raises ValueError."""
        # Generate 7000x6000 = 42MP image in mode '1' (1-bit) to keep file small
        img = Image.new("1", (7000, 6000))
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()

        # Temporarily disable Pillow's own decompression bomb check
        original_max = Image.MAX_IMAGE_PIXELS
        try:
            Image.MAX_IMAGE_PIXELS = None
            with pytest.raises(ValueError, match="exceeds|maximum|pixels|40"):
                inspect_image(data)
        finally:
            Image.MAX_IMAGE_PIXELS = original_max

    def test_declared_mime_correct(self):
        """Correct declared_mime passes validation."""
        data = generate_png(100, 100)
        info = inspect_image(data, declared_mime="image/png")
        assert info.format == "png"

    def test_declared_mime_case_insensitive(self):
        """declared_mime is case-insensitive."""
        data = generate_jpeg(100, 100)
        info = inspect_image(data, declared_mime="IMAGE/JPEG")
        assert info.format == "jpg"

    def test_declared_mime_with_charset_parameter(self):
        """declared_mime with charset parameter is handled."""
        data = generate_png(100, 100)
        info = inspect_image(data, declared_mime="image/png; charset=utf-8")
        assert info.format == "png"

    def test_reject_non_image_mime(self):
        """Non-image MIME type raises ValueError."""
        data = generate_png(100, 100)
        with pytest.raises(ValueError, match="mime|type|image"):
            inspect_image(data, declared_mime="text/plain")

    def test_reject_unsupported_image_mime(self):
        """Unsupported image MIME type raises ValueError."""
        data = generate_png(100, 100)
        with pytest.raises(ValueError, match="(?i)unsupported|mime"):
            inspect_image(data, declared_mime="image/bmp")

    def test_reject_mime_format_mismatch(self):
        """Declared MIME not matching actual format raises ValueError."""
        data = generate_png(100, 100)
        with pytest.raises(ValueError, match="mismatch|declared|actual"):
            inspect_image(data, declared_mime="image/jpeg")

    def test_reject_multi_frame_gif(self):
        """Multi-frame animated GIF raises ValueError."""
        data = generate_multi_frame_gif(200, 200)
        with pytest.raises(ValueError, match="animated|multiple.*frame"):
            inspect_image(data)

    def test_reject_animated_webp(self):
        """Multi-frame animated WebP raises ValueError."""
        try:
            data = generate_animated_webp(200, 200, frames=2)
        except Exception as e:
            pytest.skip(f"Animated WebP generation not supported: {e}")

        # Verify it's actually multi-frame before testing rejection
        img = Image.open(io.BytesIO(data))
        n_frames = getattr(img, "n_frames", 1)
        img.close()

        if n_frames <= 1:
            pytest.skip("Generated WebP is not multi-frame")

        with pytest.raises(ValueError, match="animated|multiple.*frame"):
            inspect_image(data)

    def test_reject_apng(self):
        """Multi-frame APNG raises ValueError."""
        try:
            data = generate_apng(200, 200, frames=2)
        except RuntimeError as e:
            pytest.skip(str(e))

        # Verify it's actually multi-frame
        img = Image.open(io.BytesIO(data))
        n_frames = getattr(img, "n_frames", 1)
        img.close()

        if n_frames <= 1:
            pytest.skip("Generated PNG is not multi-frame")

        with pytest.raises(ValueError, match="animated|multiple.*frame"):
            inspect_image(data)

    def test_reject_non_bytes_input(self):
        """Non-bytes input raises ValueError."""
        with pytest.raises(ValueError, match="bytes"):
            inspect_image("not bytes")  # type: ignore

        with pytest.raises(ValueError, match="bytes"):
            inspect_image(bytearray(b"test"))  # type: ignore

    def test_decompression_bomb_warning_as_error(self):
        """Decompression bomb warning is caught and raised as ValueError."""
        # Create 100x100 PNG (10k pixels)
        data = generate_png(100, 100)

        # Patch MAX_IMAGE_PIXELS to 5000 (10k > 2x warning threshold)
        original_max = Image.MAX_IMAGE_PIXELS
        try:
            Image.MAX_IMAGE_PIXELS = 5000

            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                with pytest.raises(ValueError, match="decompression|pixels|too large"):
                    inspect_image(data)

                # Verify no unhandled DecompressionBombWarning leaked
                bomb_warnings = [x for x in w if issubclass(x.category, Image.DecompressionBombWarning)]
                assert len(bomb_warnings) == 0, "DecompressionBombWarning should not leak"

        finally:
            Image.MAX_IMAGE_PIXELS = original_max

    def test_decompression_bomb_error_as_valueerror(self):
        """Pillow DecompressionBombError is caught and mapped to ValueError."""
        # Create 100x100 PNG (10k pixels)
        data = generate_png(100, 100)

        # Patch to 4000 (10k > 2.5x = error threshold)
        original_max = Image.MAX_IMAGE_PIXELS
        try:
            Image.MAX_IMAGE_PIXELS = 4000

            with pytest.raises(ValueError, match="decompression|pixels|too large"):
                inspect_image(data)

        finally:
            Image.MAX_IMAGE_PIXELS = original_max

    def test_verify_stage_decompression_bomb_warning_as_error(self):
        """Second Image.open in verify stage catches DecompressionBombWarning as ValueError."""
        # Create valid 100x100 PNG
        data = generate_png(100, 100)

        # Track Image.open calls
        call_count = [0]
        original_open = Image.open

        def tracking_open(fp, *args, **kwargs):
            call_count[0] += 1
            # First call: normal (header check)
            if call_count[0] == 1:
                return original_open(fp, *args, **kwargs)
            # Second call (verify stage): inject warning then open
            elif call_count[0] == 2:
                import warnings
                warnings.warn("verify-stage bomb", Image.DecompressionBombWarning)
                return original_open(fp, *args, **kwargs)
            return original_open(fp, *args, **kwargs)

        with patch("PIL.Image.open", side_effect=tracking_open):
            import warnings
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Should raise ValueError, not leak warning
                with pytest.raises(ValueError, match="decompression|too large|pixels"):
                    inspect_image(data)

                # Verify no unhandled DecompressionBombWarning leaked
                bomb_warnings = [x for x in w if issubclass(x.category, Image.DecompressionBombWarning)]
                assert len(bomb_warnings) == 0, "DecompressionBombWarning should not leak from verify stage"

    def test_verify_stage_decompression_bomb_error_as_valueerror(self):
        """Second Image.open in verify stage catches DecompressionBombError as ValueError."""
        # Create valid 100x100 PNG
        data = generate_png(100, 100)

        # Track Image.open calls
        call_count = [0]
        original_open = Image.open

        def tracking_open(fp, *args, **kwargs):
            call_count[0] += 1
            # First call: normal (header check)
            if call_count[0] == 1:
                return original_open(fp, *args, **kwargs)
            # Second call (verify stage): raise DecompressionBombError
            elif call_count[0] == 2:
                raise Image.DecompressionBombError("verify-stage error")
            return original_open(fp, *args, **kwargs)

        with patch("PIL.Image.open", side_effect=tracking_open):
            # Should raise ValueError with decompression message, NOT "corrupted data"
            with pytest.raises(ValueError, match="decompression|too large|pixels"):
                inspect_image(data)


class TestNormalizeImage:
    """Tests for normalize_image function."""

    def test_same_size_returns_original(self):
        """Source 1024x1024 to target 1024x1024 returns original bytes, normalized=False."""
        data = generate_png(1024, 1024)
        result_data, normalized = normalize_image(data, target_width=1024, target_height=1024)

        assert result_data == data
        assert normalized is False

    def test_different_size_center_crop(self):
        """Different size performs center crop with LANCZOS to exact target."""
        data = generate_png(2000, 1000)
        result_data, normalized = normalize_image(data, target_width=800, target_height=600)

        assert result_data != data
        assert normalized is True

        # Verify result dimensions
        result_info = inspect_image(result_data)
        assert result_info.width == 800
        assert result_info.height == 600

    def test_maintains_aspect_ratio_center_crop(self):
        """Normalization uses center crop, not stretch."""
        # 1200x800 source with three vertical color bands: left red, center green, right blue
        # Each band is 400px wide
        img = Image.new("RGB", (1200, 800))
        pixels = img.load()
        for y in range(800):
            for x in range(1200):
                if x < 400:
                    pixels[x, y] = (255, 0, 0)  # Left: red
                elif x < 800:
                    pixels[x, y] = (0, 255, 0)  # Center: green
                else:
                    pixels[x, y] = (0, 0, 255)  # Right: blue

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        # Normalize to 600x600 - should center crop, not stretch
        result_data, normalized = normalize_image(data, target_width=600, target_height=600)

        assert normalized is True
        result_info = inspect_image(result_data)
        assert result_info.width == 600
        assert result_info.height == 600

        # Verify center crop preserves green band in middle
        # If stretched, x=175 would show red, x=425 would show blue
        # With center crop from 1200x800, we crop to 800x800 centered (200px off each side)
        # Then scale to 600x600, so middle 400px of original (green) becomes 300px in output
        # Output should be: ~150px left edge, 300px green center, ~150px right edge
        result_img = Image.open(io.BytesIO(result_data))
        pixels_out = result_img.load()

        # Sample x=175 (should be in green band if center-cropped)
        pixel_175 = pixels_out[175, 300]
        color_175 = get_dominant_color_channel(pixel_175)
        assert color_175 == "green", f"x=175 should be green (center crop), got {color_175}"

        # Sample x=425 (should be in green band if center-cropped)
        pixel_425 = pixels_out[425, 300]
        color_425 = get_dominant_color_channel(pixel_425)
        assert color_425 == "green", f"x=425 should be green (center crop), got {color_425}"

        # Verify left edge has some red/green transition
        pixel_left = pixels_out[10, 300]
        color_left = get_dominant_color_channel(pixel_left)
        # Due to LANCZOS resampling, edge might be blended, but should lean toward red or be transitional
        assert color_left in ["red", "green", "other"], f"Left edge unexpected: {color_left}"

        # Verify right edge has some blue/green transition
        pixel_right = pixels_out[590, 300]
        color_right = get_dominant_color_channel(pixel_right)
        assert color_right in ["blue", "green", "other"], f"Right edge unexpected: {color_right}"

    @pytest.mark.parametrize("orientation,expected_corners", [
        # Orientation 2: horizontal flip (left-right mirror)
        # TL red → green, TR green → red, BL blue → yellow, BR yellow → blue
        (2, {"TL": "green", "TR": "red", "BL": "yellow", "BR": "blue"}),
        # Orientation 3: 180° rotation
        # TL red → yellow, TR green → blue, BL blue → green, BR yellow → red
        (3, {"TL": "yellow", "TR": "blue", "BL": "green", "BR": "red"}),
        # Orientation 4: vertical flip (top-bottom mirror)
        # TL red → blue, TR green → yellow, BL blue → red, BR yellow → green
        (4, {"TL": "blue", "TR": "yellow", "BL": "red", "BR": "green"}),
    ])
    def test_exif_orientation_same_size_forces_normalization(self, orientation, expected_corners):
        """EXIF orientations 2/3/4 with same target size must normalize and transform pixels."""
        # Create 1024x1024 image with orientation 2/3/4
        # Source and target are same size, but orientation requires transformation
        data = generate_jpeg_with_exif_orientation(1024, 1024, orientation=orientation)

        result_data, normalized = normalize_image(data, target_width=1024, target_height=1024)

        # Must be normalized (not fast path)
        assert normalized is True

        # Bytes must have changed
        assert result_data != data

        # Verify EXIF orientation is cleared in output
        result_img = Image.open(io.BytesIO(result_data))
        exif = result_img.getexif()
        orientation_out = exif.get(0x0112)
        assert orientation_out is None or orientation_out == 1

        # Verify pixel transformation
        result_img = Image.open(io.BytesIO(result_data))
        pixels = result_img.load()

        # Sample corners (with 10% margin to avoid JPEG artifacts)
        margin = 102  # 10% of 1024
        corners = {
            "TL": pixels[margin, margin],
            "TR": pixels[1024 - margin - 1, margin],
            "BL": pixels[margin, 1024 - margin - 1],
            "BR": pixels[1024 - margin - 1, 1024 - margin - 1],
        }

        # Check each corner matches expected color
        for corner_name, pixel in corners.items():
            expected_color = expected_corners[corner_name]
            actual_color = get_dominant_color_channel(pixel)
            assert actual_color == expected_color, (
                f"Corner {corner_name} expected {expected_color}, got {actual_color} (pixel={pixel})"
            )

    def test_exif_orientation_6_requires_normalization(self):
        """EXIF Orientation=6 (90° CW) with non-square must normalize and transform."""
        # Create 1000x500 image with orientation 6
        # After transpose, it becomes 500x1000, so we target 500x1000 to avoid extra cropping
        data = generate_jpeg_with_exif_orientation(1000, 500, orientation=6)

        result_data, normalized = normalize_image(data, target_width=500, target_height=1000)

        # Must be normalized
        assert normalized is True

        # Verify dimensions
        result_info = inspect_image(result_data)
        assert result_info.width == 500
        assert result_info.height == 1000

        # Verify EXIF orientation is cleared in output
        result_img = Image.open(io.BytesIO(result_data))
        exif = result_img.getexif()
        orientation_out = exif.get(0x0112)
        assert orientation_out is None or orientation_out == 1

        # Verify 90° CW rotation (Pillow's ROTATE_270 transpose)
        # Original: TL=red, TR=green, BL=blue, BR=yellow (1000w x 500h)
        # After 90° CW (orientation 6): becomes 500w x 1000h
        # New TL = old BL (blue), TR = old TL (red), BL = old BR (yellow), BR = old TR (green)
        result_img = Image.open(io.BytesIO(result_data))
        pixels = result_img.load()

        margin_x = 50  # 10% of 500
        margin_y = 100  # 10% of 1000

        corners = {
            "TL": pixels[margin_x, margin_y],
            "TR": pixels[500 - margin_x - 1, margin_y],
            "BL": pixels[margin_x, 1000 - margin_y - 1],
            "BR": pixels[500 - margin_x - 1, 1000 - margin_y - 1],
        }

        expected = {"TL": "blue", "TR": "red", "BL": "yellow", "BR": "green"}

        for corner_name, pixel in corners.items():
            expected_color = expected[corner_name]
            actual_color = get_dominant_color_channel(pixel)
            assert actual_color == expected_color, (
                f"Corner {corner_name} expected {expected_color}, got {actual_color} (pixel={pixel})"
            )

    def test_exif_orientation_6_square_no_fast_path(self):
        """EXIF Orientation=6 on square image (600x600→600x600) must still normalize."""
        # Even though dimensions don't change, orientation must be corrected
        data = generate_jpeg_with_exif_orientation(600, 600, orientation=6)

        result_data, normalized = normalize_image(data, target_width=600, target_height=600)

        # Must be normalized (not fast path)
        assert normalized is True

        # Bytes must have changed
        assert result_data != data

        # Verify EXIF orientation is cleared
        result_img = Image.open(io.BytesIO(result_data))
        exif = result_img.getexif()
        orientation_out = exif.get(0x0112)
        assert orientation_out is None or orientation_out == 1

    def test_preserves_png_format(self):
        """PNG input produces PNG output."""
        data = generate_png(1200, 800)
        result_data, normalized = normalize_image(data, target_width=600, target_height=400)

        result_info = inspect_image(result_data)
        assert result_info.format == "png"

    def test_preserves_jpeg_format(self):
        """JPEG input produces JPEG output."""
        data = generate_jpeg(1200, 800)
        result_data, normalized = normalize_image(data, target_width=600, target_height=400)

        result_info = inspect_image(result_data)
        assert result_info.format == "jpg"

    def test_preserves_webp_format(self):
        """WebP input produces WebP output."""
        data = generate_webp(1200, 800)
        result_data, normalized = normalize_image(data, target_width=600, target_height=400)

        result_info = inspect_image(result_data)
        assert result_info.format == "webp"

    def test_preserves_gif_format(self):
        """Single-frame GIF input produces GIF output."""
        data = generate_gif(1200, 800)
        result_data, normalized = normalize_image(data, target_width=600, target_height=400)

        result_info = inspect_image(result_data)
        assert result_info.format == "gif"

    def test_reject_invalid_target_width(self):
        """target_width <= 0 raises ValueError."""
        data = generate_png(1024, 1024)
        with pytest.raises(ValueError, match="width|positive|invalid"):
            normalize_image(data, target_width=0, target_height=1024)

        with pytest.raises(ValueError, match="width|positive|invalid"):
            normalize_image(data, target_width=-100, target_height=1024)

    def test_reject_invalid_target_height(self):
        """target_height <= 0 raises ValueError."""
        data = generate_png(1024, 1024)
        with pytest.raises(ValueError, match="height|positive|invalid"):
            normalize_image(data, target_width=1024, target_height=0)

        with pytest.raises(ValueError, match="height|positive|invalid"):
            normalize_image(data, target_width=1024, target_height=-100)

    def test_reject_oversized_output(self):
        """Normalization result exceeding MAX_IMAGE_BYTES raises ValueError."""
        import random
        from PIL import ImageOps

        # Generate deterministic high-entropy source JPEG
        # Use random seed for reproducibility
        rng = random.Random(0)
        raw = rng.randbytes(1024 * 1024 * 3)
        img = Image.frombytes("RGB", (1024, 1024), raw)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=5, optimize=True)
        source_data = buf.getvalue()

        # Get baseline output under default MAX_IMAGE_BYTES
        baseline_output, normalized = normalize_image(
            source_data, target_width=1023, target_height=1024
        )
        assert normalized is True, "Baseline normalization must occur"
        assert len(baseline_output) > len(source_data), (
            f"Baseline output ({len(baseline_output)}) must exceed source ({len(source_data)})"
        )

        # Calculate limit between source and output
        limit = (len(source_data) + len(baseline_output)) // 2
        assert len(source_data) < limit < len(baseline_output), (
            f"Limit must be between source and output: {len(source_data)} < {limit} < {len(baseline_output)}"
        )

        # Patch MAX_IMAGE_BYTES to limit and spy on ImageOps.fit
        with patch("hermes_post_design.chiyi_core.images.MAX_IMAGE_BYTES", limit):
            with patch("hermes_post_design.chiyi_core.images.ImageOps.fit", wraps=ImageOps.fit) as fit_spy:
                # Must raise ValueError with specific message about normalized output
                with pytest.raises(ValueError, match="Normalized image exceeds maximum size"):
                    normalize_image(source_data, target_width=1023, target_height=1024)

                # Verify ImageOps.fit was called, proving input inspection passed
                fit_spy.assert_called_once()

    def test_reject_target_exceeds_max_pixels(self):
        """Target dimensions exceeding MAX_IMAGE_PIXELS raises ValueError before ImageOps.fit."""
        # Create small source image
        data = generate_png(1024, 1024)

        # Target that exceeds MAX_IMAGE_PIXELS (40M)
        # 7000 x 6000 = 42M pixels
        target_width = 7000
        target_height = 6000

        # Patch ImageOps.fit to ensure it's never called
        with patch("hermes_post_design.chiyi_core.images.ImageOps.fit") as mock_fit:
            with pytest.raises(ValueError, match="target.*pixels|MAX_IMAGE_PIXELS|40"):
                normalize_image(data, target_width=target_width, target_height=target_height)

            # Verify ImageOps.fit was never called
            mock_fit.assert_not_called()

    def test_normalized_output_passes_inspection(self):
        """Normalized output can be inspected successfully."""
        data = generate_jpeg(1500, 1000)
        result_data, normalized = normalize_image(data, target_width=800, target_height=600)

        # Should not raise
        result_info = inspect_image(result_data)
        assert result_info.width == 800
        assert result_info.height == 600

    def test_cmyk_jpeg_normalization_closes_fitted_image(self):
        """CMYK JPEG normalization must close original fitted image after RGB conversion."""
        # Create 1200x1024 CMYK JPEG
        data = generate_cmyk_jpeg(1200, 1024)

        # Track fitted images returned by ImageOps.fit
        fitted_images = []
        original_fit = ImageOps.fit

        def tracking_fit(*args, **kwargs):
            result = original_fit(*args, **kwargs)
            fitted_images.append(result)
            return result

        with patch("hermes_post_design.chiyi_core.images.ImageOps.fit", side_effect=tracking_fit):
            result_data, normalized = normalize_image(data, target_width=1024, target_height=1024)

        # Must be normalized
        assert normalized is True

        # Verify output format is JPEG
        result_info = inspect_image(result_data)
        assert result_info.format == "jpg"
        assert result_info.width == 1024
        assert result_info.height == 1024

        # Verify the original fitted image was closed
        assert len(fitted_images) == 1
        fitted_img = fitted_images[0]

        # Try to use the fitted image - should raise ValueError for closed image
        with pytest.raises(ValueError, match="closed"):
            fitted_img.getbbox()  # or load() - both raise on closed image
