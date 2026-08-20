"""Atomic artifact saving."""
import hashlib
import os
import stat
import uuid
from pathlib import Path

from hermes_post_design.chiyi_core.images import inspect_image, normalize_image
from hermes_post_design.chiyi_core.models import ImageArtifact, SizePlan
from hermes_post_design.chiyi_core.sizing import MIN_OUTPUT_SHORT_EDGE


def _reserve_final_path(output_path: Path, extension: str, max_attempts: int = 8) -> Path:
    """
    Reserve a unique final path using O_EXCL to prevent overwrites.

    Args:
        output_path: Output directory
        extension: File extension (e.g., ".png")
        max_attempts: Maximum number of collision retries

    Returns:
        Reserved final path with empty placeholder file created

    Raises:
        FileExistsError: If max_attempts collisions occur
    """
    for attempt in range(max_attempts):
        unique_id = uuid.uuid4().hex[:12]
        filename = f"chiyi_gpt-image-2_{unique_id}{extension}"
        final_path = output_path / filename

        try:
            # Atomically create empty placeholder with exclusive access
            fd = os.open(str(final_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            return final_path
        except FileExistsError:
            # Collision, try next UUID
            continue

    raise FileExistsError(f"Failed to reserve unique filename after {max_attempts} attempts")


def _check_no_symlinks_or_reparse(path: Path) -> None:
    """
    Check that path and all existing parent components are not symlinks or reparse points.

    This is a double-check to prevent misconfiguration or non-concurrent replacement
    of output paths. It does NOT protect against active attackers with write access
    to the output directory - callers must control authorization of output directories.

    Args:
        path: Path to check (should be absolute but not yet resolved)

    Raises:
        ValueError: If any component is a symlink or reparse point
    """
    # Check all existing components
    current = path
    components_to_check = []

    # Collect path and all parents
    while current != current.parent:
        components_to_check.append(current)
        current = current.parent
    components_to_check.append(current)  # Add root

    for component in components_to_check:
        # Check for symlink FIRST (before exists check)
        # This catches broken symlinks where exists()=False but is_symlink()=True
        if component.is_symlink():
            raise ValueError(f"Output path contains symlink or reparse point: {component}")

        # Check for Windows reparse point using lstat (doesn't follow symlinks)
        try:
            st = component.lstat()
            if hasattr(st, "st_file_attributes"):
                # Check FILE_ATTRIBUTE_REPARSE_POINT if available
                if hasattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT"):
                    if st.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                        raise ValueError(f"Output path contains symlink or reparse point: {component}")
        except FileNotFoundError:
            # Component doesn't exist - this is fine, continue checking parents
            continue
        except (OSError, AttributeError):
            # If lstat fails or attributes not available, skip this component
            # (but we've already checked is_symlink above)
            pass


def save_artifact(data: bytes, plan: SizePlan, output_dir: Path) -> ImageArtifact:
    """
    Save image artifact atomically with normalization if needed.

    Args:
        data: Source image bytes
        plan: Size plan with target dimensions
        output_dir: Directory to save artifact (created if needed).
                   Must be a real directory authorized by caller, not a symlink or reparse point.

    Returns:
        ImageArtifact with path, dimensions, SHA-256, and normalized flag

    Raises:
        ValueError: If source resolution insufficient, validation fails, or output_dir contains symlinks/reparse points
        OSError: If directory creation or file operations fail
    """
    # Inspect source image
    source_info = inspect_image(data)

    # Check source resolution meets minimum requirement
    source_short_edge = min(source_info.width, source_info.height)
    if source_short_edge < MIN_OUTPUT_SHORT_EDGE:
        raise ValueError(
            f"Source resolution insufficient: short edge {source_short_edge}px < "
            f"minimum {MIN_OUTPUT_SHORT_EDGE}px"
        )

    # Normalize output directory path (expanduser but not resolve yet)
    output_path = Path(output_dir).expanduser().absolute()

    # Check for symlinks/reparse points before resolving
    _check_no_symlinks_or_reparse(output_path)

    # Now safe to resolve
    output_path = output_path.resolve()

    # Create directory if needed
    output_path.mkdir(parents=True, exist_ok=True)

    # Re-check after mkdir (in case mkdir created it)
    _check_no_symlinks_or_reparse(output_path)

    # Verify it's a directory
    if not output_path.is_dir():
        raise ValueError(f"Output path exists but is not a directory: {output_path}")

    # Normalize image to target dimensions
    normalized_data, was_normalized = normalize_image(
        data,
        target_width=plan.target_width,
        target_height=plan.target_height,
    )

    # Re-inspect normalized image
    final_info = inspect_image(normalized_data)

    # Verify exact dimensions
    if final_info.width != plan.target_width or final_info.height != plan.target_height:
        raise ValueError(
            f"Normalization produced wrong dimensions: expected {plan.target_width}x{plan.target_height}, "
            f"got {final_info.width}x{final_info.height}"
        )

    # Determine file extension
    extension_map = {
        "png": ".png",
        "jpg": ".jpg",
        "webp": ".webp",
        "gif": ".gif",
    }
    extension = extension_map[final_info.format]

    # Generate temporary path in same directory for atomic write
    temp_filename = f".tmp_{uuid.uuid4().hex}{extension}"
    temp_path = output_path / temp_filename

    # Reserve final path with collision protection
    final_path = None
    try:
        # Write to temporary file
        temp_path.write_bytes(normalized_data)

        # Verify written file
        verify_data = temp_path.read_bytes()
        verify_info = inspect_image(verify_data)

        # Verify dimensions match
        if verify_info.width != plan.target_width or verify_info.height != plan.target_height:
            raise ValueError(
                f"Post-write verification failed: dimensions {verify_info.width}x{verify_info.height} "
                f"don't match expected {plan.target_width}x{plan.target_height}"
            )

        # Reserve final path atomically
        final_path = _reserve_final_path(output_path, extension)

        # Atomic replace
        os.replace(str(temp_path), str(final_path))

    except Exception:
        # Clean up temporary file on any error
        if temp_path.exists():
            temp_path.unlink()
        # Clean up reserved placeholder if replace failed
        if final_path is not None and final_path.exists():
            final_path.unlink()
        raise

    # Post-replace verification
    try:
        # Read final file
        final_data = final_path.read_bytes()

        # Verify it can be inspected
        final_verify_info = inspect_image(final_data)

        # Verify dimensions
        if final_verify_info.width != plan.target_width or final_verify_info.height != plan.target_height:
            raise ValueError(
                f"Final verification failed: file dimensions {final_verify_info.width}x{final_verify_info.height} "
                f"don't match expected {plan.target_width}x{plan.target_height}"
            )

        # Compute SHA-256 of final file
        sha256 = hashlib.sha256(final_data).hexdigest()

    except Exception:
        # Clean up final file if post-verification fails
        if final_path.exists():
            final_path.unlink()
        raise

    # Return ImageArtifact
    return ImageArtifact(
        path=final_path,
        format=final_info.format,
        width=plan.target_width,
        height=plan.target_height,
        sha256=sha256,
        normalized=was_normalized,
    )
