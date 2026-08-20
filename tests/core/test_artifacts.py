"""Tests for atomic artifact saving."""
import hashlib
import io
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from hermes_post_design.chiyi_core.artifacts import save_artifact
from hermes_post_design.chiyi_core.images import inspect_image
from hermes_post_design.chiyi_core.models import ImageArtifact, SizePlan
from hermes_post_design.chiyi_core.sizing import MIN_OUTPUT_SHORT_EDGE


def generate_png(width: int, height: int, color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    """Generate a PNG image programmatically."""
    import io
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_jpeg(width: int, height: int, color: tuple[int, int, int] = (0, 255, 0)) -> bytes:
    """Generate a JPEG image programmatically."""
    import io
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def generate_webp(width: int, height: int, color: tuple[int, int, int] = (0, 0, 255)) -> bytes:
    """Generate a WebP image programmatically."""
    import io
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=95)
    return buf.getvalue()


def generate_gif(width: int, height: int, color: tuple[int, int, int] = (255, 255, 0)) -> bytes:
    """Generate a single-frame GIF image programmatically."""
    import io
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="GIF")
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
        raise RuntimeError("APNG not supported by current Pillow version")


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hash of data."""
    return hashlib.sha256(data).hexdigest()


class TestSaveArtifact:
    """Tests for save_artifact function."""

    def test_reject_source_below_minimum_short_edge(self, tmp_path):
        """Source with short edge < MIN_OUTPUT_SHORT_EDGE (1024) raises ValueError."""
        # Create 800x1200 image (short edge = 800 < 1024)
        data = generate_png(800, 1200)
        plan = SizePlan(requested="800x1200", upstream="800x1200", target_width=800, target_height=1200)

        with pytest.raises(ValueError, match="resolution|short.*edge|1024"):
            save_artifact(data, plan, tmp_path)

        # Verify no files were created
        assert len(list(tmp_path.iterdir())) == 0

    def test_save_exact_size_no_normalization(self, tmp_path):
        """1024x1024 source saved as same size creates correct artifact."""
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, tmp_path)

        # Verify output directory was created
        assert tmp_path.exists()
        assert tmp_path.is_dir()

        # Verify artifact properties
        assert artifact.path.exists()
        assert artifact.path.is_absolute()
        assert artifact.path.parent == tmp_path.resolve()
        assert artifact.path.suffix == ".png"
        assert artifact.width == 1024
        assert artifact.height == 1024
        assert artifact.normalized is False

        # Verify SHA-256
        saved_data = artifact.path.read_bytes()
        expected_sha = compute_sha256(saved_data)
        assert artifact.sha256 == expected_sha

        # Verify file content matches
        assert saved_data == data

    def test_save_with_normalization(self, tmp_path):
        """1088x1920 source to 1080x1920 target performs normalization."""
        data = generate_png(1088, 1920)
        plan = SizePlan(requested="1080x1920", upstream="1088x1920", target_width=1080, target_height=1920)

        artifact = save_artifact(data, plan, tmp_path)

        # Verify dimensions are exact target
        assert artifact.width == 1080
        assert artifact.height == 1920
        assert artifact.normalized is True

        # Verify SHA corresponds to final file
        saved_data = artifact.path.read_bytes()
        expected_sha = compute_sha256(saved_data)
        assert artifact.sha256 == expected_sha

        # Verify saved file has exact dimensions
        info = inspect_image(saved_data)
        assert info.width == 1080
        assert info.height == 1920

    def test_jpeg_extension_correct(self, tmp_path):
        """JPEG format produces .jpg extension."""
        data = generate_jpeg(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, tmp_path)

        assert artifact.path.suffix == ".jpg"
        info = inspect_image(artifact.path.read_bytes())
        assert info.format == "jpg"

    def test_webp_extension_correct(self, tmp_path):
        """WebP format produces .webp extension."""
        data = generate_webp(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, tmp_path)

        assert artifact.path.suffix == ".webp"
        info = inspect_image(artifact.path.read_bytes())
        assert info.format == "webp"

    def test_gif_extension_correct(self, tmp_path):
        """Single-frame GIF format produces .gif extension."""
        data = generate_gif(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, tmp_path)

        assert artifact.path.suffix == ".gif"
        info = inspect_image(artifact.path.read_bytes())
        assert info.format == "gif"

    def test_atomic_save_with_replace(self, tmp_path):
        """Saves atomically using temporary file and os.replace."""
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        # Track os.replace calls
        original_replace = os.replace
        replace_calls = []

        def tracked_replace(src, dst):
            replace_calls.append((src, dst))
            return original_replace(src, dst)

        with patch("os.replace", side_effect=tracked_replace):
            artifact = save_artifact(data, plan, tmp_path)

        # Verify os.replace was called
        assert len(replace_calls) == 1
        temp_path, final_path = replace_calls[0]

        # Verify temp and final paths are in same directory
        assert Path(temp_path).parent == Path(final_path).parent
        assert Path(final_path) == artifact.path

        # Verify temp file was cleaned up (replaced)
        assert not Path(temp_path).exists()

        # Verify final file exists
        assert artifact.path.exists()

    def test_atomic_save_cleanup_on_replace_failure(self, tmp_path):
        """If os.replace fails, temporary file is cleaned up."""
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        temp_file_path = None

        def failing_replace(src, dst):
            nonlocal temp_file_path
            temp_file_path = src
            raise OSError("Simulated replace failure")

        with patch("os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="Simulated replace failure"):
                save_artifact(data, plan, tmp_path)

        # Verify temporary file was cleaned up
        if temp_file_path:
            assert not Path(temp_file_path).exists()

        # Verify no final file was created
        assert len(list(tmp_path.glob("chiyi_*.png"))) == 0

    def test_post_save_verification_failure_cleanup(self, tmp_path):
        """If post-replace verification fails, final file is cleaned up."""
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        # Track calls to inspect_image and os.replace
        call_count = [0]
        replace_count = [0]
        original_inspect = inspect_image
        original_replace = os.replace

        def counting_inspect(data, **kwargs):
            call_count[0] += 1
            # Let first 3 calls succeed (source check, normalized_data check, temp readback)
            # 4th call is post-replace final verification - fail it
            if call_count[0] == 4:
                raise ValueError("Simulated final post-replace verification failure")
            return original_inspect(data, **kwargs)

        def counting_replace(src, dst):
            replace_count[0] += 1
            return original_replace(src, dst)

        with patch("hermes_post_design.chiyi_core.artifacts.inspect_image", side_effect=counting_inspect):
            with patch("os.replace", side_effect=counting_replace):
                with pytest.raises(ValueError, match="Simulated final post-replace verification failure"):
                    save_artifact(data, plan, tmp_path)

        # Verify os.replace was called exactly once (temp → final happened)
        assert replace_count[0] == 1

        # Verify no chiyi_* file remains (cleaned up after post-replace failure)
        assert len(list(tmp_path.glob("chiyi_*.png"))) == 0

        # Verify no .tmp_* file remains
        assert len(list(tmp_path.glob(".tmp_*.png"))) == 0

    def test_output_directory_creation(self, tmp_path):
        """Output directory is created if it doesn't exist."""
        nested_dir = tmp_path / "nested" / "output"
        assert not nested_dir.exists()

        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, nested_dir)

        # Verify directory was created
        assert nested_dir.exists()
        assert nested_dir.is_dir()
        assert artifact.path.parent == nested_dir.resolve()

    def test_reject_output_dir_is_file(self, tmp_path):
        """Raises error if output_dir exists but is a file."""
        file_path = tmp_path / "notadir"
        file_path.write_text("I'm a file")

        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        with pytest.raises((ValueError, OSError, NotADirectoryError)):
            save_artifact(data, plan, file_path)

    def test_filename_format(self, tmp_path):
        """Filename follows format: chiyi_gpt-image-2_<12hex>.<ext>"""
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        artifact = save_artifact(data, plan, tmp_path)

        filename = artifact.path.name
        # Match pattern: chiyi_gpt-image-2_<12 hex chars>.png
        pattern = r"^chiyi_gpt-image-2_[0-9a-f]{12}\.png$"
        assert re.match(pattern, filename), f"Filename {filename} doesn't match expected pattern"

    def test_content_sha_consistency(self, tmp_path):
        """SHA-256 in artifact matches actual file content."""
        data = generate_jpeg(1200, 1080)
        plan = SizePlan(requested="1080x1080", upstream="1200x1080", target_width=1080, target_height=1080)

        artifact = save_artifact(data, plan, tmp_path)

        # Read file and compute SHA
        saved_data = artifact.path.read_bytes()
        actual_sha = compute_sha256(saved_data)

        assert artifact.sha256 == actual_sha

    def test_post_save_reinspection_matches(self, tmp_path):
        """Saved file can be re-inspected and matches artifact dimensions."""
        data = generate_webp(1088, 1920)
        plan = SizePlan(requested="1080x1920", upstream="1088x1920", target_width=1080, target_height=1920)

        artifact = save_artifact(data, plan, tmp_path)

        # Re-inspect saved file
        saved_data = artifact.path.read_bytes()
        info = inspect_image(saved_data)

        assert info.width == artifact.width
        assert info.height == artifact.height
        assert info.format == "webp"

    def test_reject_animated_webp(self, tmp_path):
        """Multi-frame animated WebP is rejected."""
        try:
            data = generate_animated_webp(1024, 1024, frames=2)
        except Exception as e:
            pytest.skip(f"Animated WebP generation not supported: {e}")

        # Verify it's actually multi-frame
        img = Image.open(io.BytesIO(data))
        n_frames = getattr(img, "n_frames", 1)
        img.close()

        if n_frames <= 1:
            pytest.skip("Generated WebP is not multi-frame")

        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        with pytest.raises(ValueError, match="animated|multiple.*frame"):
            save_artifact(data, plan, tmp_path)

        # Verify no files were created
        assert len(list(tmp_path.iterdir())) == 0

    def test_reject_apng(self, tmp_path):
        """Multi-frame APNG is rejected."""
        try:
            data = generate_apng(1024, 1024, frames=2)
        except RuntimeError as e:
            pytest.skip(str(e))

        # Verify it's actually multi-frame
        img = Image.open(io.BytesIO(data))
        n_frames = getattr(img, "n_frames", 1)
        img.close()

        if n_frames <= 1:
            pytest.skip("Generated PNG is not multi-frame")

        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        with pytest.raises(ValueError, match="animated|multiple.*frame"):
            save_artifact(data, plan, tmp_path)

        # Verify no files were created
        assert len(list(tmp_path.iterdir())) == 0

    def test_collision_no_overwrite(self, tmp_path):
        """12hex collision does not overwrite existing file."""
        # Create existing file with content "OLD"
        existing_file = tmp_path / "chiyi_gpt-image-2_aaaaaaaaaaaa.png"
        existing_file.write_text("OLD")

        # Mock uuid generation to first return 'aaaaaaaaaaaa' (collision) then 'bbbbbbbbbbbb' (success)
        # Need to account for temp file uuid call as well
        uuid_sequence = []

        def mock_uuid4():
            class MockUUID:
                def __init__(self, hex_value):
                    self.hex = hex_value

            if len(uuid_sequence) == 0:
                # First call: temp filename
                uuid_sequence.append("temp")
                return MockUUID("temp00000000000000000000000000000000")
            elif len(uuid_sequence) == 1:
                # Second call: final filename (collision)
                uuid_sequence.append("final1")
                return MockUUID("aaaaaaaaaaaa00000000000000000000")
            elif len(uuid_sequence) == 2:
                # Third call: placeholder for first attempt (collision)
                uuid_sequence.append("placeholder1")
                return MockUUID("aaaaaaaaaaaa00000000000000000000")
            elif len(uuid_sequence) == 3:
                # Fourth call: final filename (success)
                uuid_sequence.append("final2")
                return MockUUID("bbbbbbbbbbbb00000000000000000000")
            else:
                # Fifth call: placeholder for second attempt (success)
                uuid_sequence.append("placeholder2")
                return MockUUID("bbbbbbbbbbbb00000000000000000000")

        import uuid as uuid_module
        with patch.object(uuid_module, "uuid4", side_effect=mock_uuid4):
            data = generate_png(1024, 1024)
            plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

            artifact = save_artifact(data, plan, tmp_path)

        # Verify artifact uses bbbb... not aaaa...
        assert artifact.path.name == "chiyi_gpt-image-2_bbbbbbbbbbbb.png"

        # Verify old file is completely unchanged
        assert existing_file.read_text() == "OLD"

        # Verify new file exists and is valid
        assert artifact.path.exists()
        saved_data = artifact.path.read_bytes()
        info = inspect_image(saved_data)
        assert info.width == 1024
        assert info.height == 1024

    def test_collision_exhaustion_raises(self, tmp_path):
        """8 consecutive collisions raise FileExistsError."""
        # Pre-create 8 collision files
        for i in range(8):
            collision_file = tmp_path / f"chiyi_gpt-image-2_{chr(97+i)*12}.png"
            collision_file.write_text(f"OLD{i}")

        # Mock uuid to return collision sequence a-h, then success 'i'
        uuid_sequence = []

        def mock_uuid4():
            class MockUUID:
                def __init__(self, hex_value):
                    self.hex = hex_value

            idx = len(uuid_sequence)
            uuid_sequence.append(idx)

            if idx == 0:
                # Temp file
                return MockUUID("temp00000000000000000000000000000000")
            elif idx % 2 == 1:
                # Odd: final filename
                attempt = (idx - 1) // 2
                if attempt < 8:
                    char = chr(97 + attempt)  # a-h
                else:
                    char = chr(97 + attempt)  # i
                return MockUUID(f"{char * 12}00000000000000000000")
            else:
                # Even: placeholder reservation
                attempt = (idx - 2) // 2
                if attempt < 8:
                    char = chr(97 + attempt)
                else:
                    char = chr(97 + attempt)
                return MockUUID(f"{char * 12}00000000000000000000")

        import uuid as uuid_module
        with patch.object(uuid_module, "uuid4", side_effect=mock_uuid4):
            data = generate_png(1024, 1024)
            plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

            with pytest.raises(FileExistsError):
                save_artifact(data, plan, tmp_path)

        # Verify all old files are unchanged
        for i in range(8):
            collision_file = tmp_path / f"chiyi_gpt-image-2_{chr(97+i)*12}.png"
            assert collision_file.read_text() == f"OLD{i}"

        # Verify no new chiyi_* files
        all_chiyi = list(tmp_path.glob("chiyi_*.png"))
        assert len(all_chiyi) == 8  # Only the pre-existing ones

        # Verify no temp files
        assert len(list(tmp_path.glob(".tmp_*.png"))) == 0

    def test_reject_symlink_output_directory(self, tmp_path):
        """Symlink output directory is rejected before writing."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()

        link_dir = tmp_path / "link"

        try:
            # Try to create symlink
            link_dir.symlink_to(real_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            # Windows without admin privileges - use monkeypatch
            def mock_is_symlink(self):
                return str(self) == str(link_dir)

            with patch.object(Path, "is_symlink", mock_is_symlink):
                data = generate_png(1024, 1024)
                plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

                with pytest.raises(ValueError, match="symlink|reparse"):
                    save_artifact(data, plan, link_dir)

                # Verify no files in real_dir or link_dir
                assert len(list(real_dir.iterdir())) == 0
            return

        # Real symlink created
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        with pytest.raises(ValueError, match="symlink|reparse"):
            save_artifact(data, plan, link_dir)

        # Verify no files in real_dir (target)
        assert len(list(real_dir.iterdir())) == 0

    def test_reject_broken_symlink_output_directory(self, tmp_path):
        """Broken symlink (target doesn't exist) is rejected before resolving/creating target."""
        missing_target = tmp_path / "missing-target"
        # Do NOT create missing_target

        broken = tmp_path / "broken"

        try:
            # Try to create broken symlink pointing to non-existent target
            broken.symlink_to(missing_target, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("Cannot create symlinks on this system")

        # Verify broken symlink state
        assert not broken.exists(), "Broken symlink should report exists()=False"
        assert broken.is_symlink(), "Should be detected as symlink"

        # Attempt to save artifact to broken symlink
        data = generate_png(1024, 1024)
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)

        with pytest.raises(ValueError, match="symlink|reparse"):
            save_artifact(data, plan, broken)

        # Verify missing_target was NOT created (no follow-through)
        assert not missing_target.exists(), "Target should not have been created"

        # Verify broken symlink still exists as symlink
        assert broken.is_symlink(), "Broken symlink should remain"

        # Verify no chiyi/temp artifacts in tmp_path
        chiyi_files = list(tmp_path.glob("**/chiyi_*.png"))
        temp_files = list(tmp_path.glob("**/.tmp_*.png"))
        assert len(chiyi_files) == 0, f"No chiyi files should exist, found {chiyi_files}"
        assert len(temp_files) == 0, f"No temp files should exist, found {temp_files}"
