"""Test suite for Core models - strict TDD verification."""
from pathlib import Path
import dataclasses
import pytest
from typing import get_args, get_type_hints

from hermes_post_design.chiyi_core import (
    Operation,
    ErrorType,
    ImageSource,
    LoadedSource,
    CompletedArtifact,
    GenerateRequest,
    EditRequest,
    SizePlan,
    ImageInfo,
    ImageArtifact,
    CoreError,
    CoreResult,
)


class TestLiterals:
    """Test Literal type constraints."""

    def test_operation_literal_valid_values(self):
        """Operation must accept only 'generate' and 'edit'."""
        # Check that Operation Literal has exactly these two values
        assert get_args(Operation) == ("generate", "edit")

    def test_error_type_literal_valid_values(self):
        """ErrorType must have exactly 13 specified values, no invalid_request."""
        expected_types = {
            "invalid_argument",
            "auth_required",
            "auth_error",
            "configuration_error",
            "quota_error",
            "rate_limited",
            "network_error",
            "server_error",
            "protocol_error",
            "invalid_image",
            "resolution_mismatch",
            "compatibility_error",
            "artifact_error",
        }
        # Check the Literal type has exactly these 13 values
        actual_types = set(get_args(ErrorType))
        assert actual_types == expected_types
        assert len(actual_types) == 13
        # invalid_request should NOT be in the set
        assert "invalid_request" not in actual_types

    def test_generate_request_literal_fields(self):
        """GenerateRequest model and quality must be Literal types."""
        hints = get_type_hints(GenerateRequest)
        # Check model field is Literal["gpt-image-2"]
        model_type = hints["model"]
        assert get_args(model_type) == ("gpt-image-2",)
        # Check quality field is Literal["high"]
        quality_type = hints["quality"]
        assert get_args(quality_type) == ("high",)

    def test_edit_request_literal_fields(self):
        """EditRequest model and quality must be Literal types."""
        hints = get_type_hints(EditRequest)
        # Check model field is Literal["gpt-image-2"]
        model_type = hints["model"]
        assert get_args(model_type) == ("gpt-image-2",)
        # Check quality field is Literal["high"]
        quality_type = hints["quality"]
        assert get_args(quality_type) == ("high",)

    def test_core_result_literal_fields(self):
        """CoreResult provider, model, and quality must be Literal types."""
        hints = get_type_hints(CoreResult)
        # Check provider field is Literal["chiyi"]
        provider_type = hints["provider"]
        assert get_args(provider_type) == ("chiyi",)
        # Check model field is Literal["gpt-image-2"]
        model_type = hints["model"]
        assert get_args(model_type) == ("gpt-image-2",)
        # Check quality field is Literal["high"]
        quality_type = hints["quality"]
        assert get_args(quality_type) == ("high",)


class TestDataclassConstruction:
    """Test that all frozen dataclasses can be constructed by field."""

    def test_image_source_construction(self):
        """ImageSource can be constructed with value and optional role."""
        src = ImageSource(value="http://example.com/img.png")
        assert src.value == "http://example.com/img.png"
        assert src.role == "reference"

        src2 = ImageSource(value="path/to/img.png", role="primary")
        assert src2.value == "path/to/img.png"
        assert src2.role == "primary"

    def test_loaded_source_construction(self):
        """LoadedSource can be constructed with all fields."""
        src = LoadedSource(filename="test.png", data=b"fake_data", mime_type="image/png")
        assert src.filename == "test.png"
        assert src.data == b"fake_data"
        assert src.mime_type == "image/png"

    def test_completed_artifact_construction(self):
        """CompletedArtifact can be constructed with kind and value."""
        art1 = CompletedArtifact(kind="b64_json", value="base64data...")
        assert art1.kind == "b64_json"
        assert art1.value == "base64data..."

        art2 = CompletedArtifact(kind="url", value="http://example.com/result.png")
        assert art2.kind == "url"
        assert art2.value == "http://example.com/result.png"

    def test_generate_request_construction(self):
        """GenerateRequest can be constructed with required and optional fields."""
        req = GenerateRequest(prompt="A cat", output_dir=Path("/tmp"))
        assert req.prompt == "A cat"
        assert req.output_dir == Path("/tmp")
        assert req.size == "1024x1024"
        assert req.request_id is None
        assert req.model == "gpt-image-2"
        assert req.quality == "high"

    def test_generate_request_with_optional_fields(self):
        """GenerateRequest can be constructed with size and request_id."""
        req = GenerateRequest(
            prompt="A dog",
            output_dir=Path("/tmp"),
            size="512x512",
            request_id="req-123",
        )
        assert req.size == "512x512"
        assert req.request_id == "req-123"

    def test_edit_request_construction(self):
        """EditRequest can be constructed with required and optional fields."""
        primary = ImageSource(value="primary.png", role="primary")
        req = EditRequest(prompt="Edit this", output_dir=Path("/tmp"), primary_image=primary)
        assert req.prompt == "Edit this"
        assert req.output_dir == Path("/tmp")
        assert req.primary_image == primary
        assert req.reference_images == ()
        assert req.size == "1024x1024"
        assert req.request_id is None
        assert req.model == "gpt-image-2"
        assert req.quality == "high"

    def test_edit_request_with_references(self):
        """EditRequest can be constructed with reference_images."""
        primary = ImageSource(value="primary.png", role="primary")
        ref1 = ImageSource(value="ref1.png")
        ref2 = ImageSource(value="ref2.png")
        req = EditRequest(
            prompt="Edit",
            output_dir=Path("/tmp"),
            primary_image=primary,
            reference_images=(ref1, ref2),
        )
        assert len(req.reference_images) == 2
        assert req.reference_images[0] == ref1

    def test_size_plan_construction(self):
        """SizePlan can be constructed with all fields."""
        plan = SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)
        assert plan.requested == "1024x1024"
        assert plan.upstream == "1024x1024"
        assert plan.target_width == 1024
        assert plan.target_height == 1024

    def test_image_info_construction(self):
        """ImageInfo can be constructed with all fields."""
        info = ImageInfo(format="PNG", mime_type="image/png", width=1024, height=1024, frames=1)
        assert info.format == "PNG"
        assert info.mime_type == "image/png"
        assert info.width == 1024
        assert info.height == 1024
        assert info.frames == 1

    def test_image_artifact_construction(self):
        """ImageArtifact can be constructed with all fields."""
        art = ImageArtifact(
            path=Path("/tmp/out.png"),
            format="PNG",
            width=1024,
            height=1024,
            sha256="abc123",
            normalized=True,
        )
        assert art.path == Path("/tmp/out.png")
        assert art.format == "PNG"
        assert art.width == 1024
        assert art.height == 1024
        assert art.sha256 == "abc123"
        assert art.normalized is True

    def test_core_error_construction(self):
        """CoreError can be constructed with required and optional fields."""
        err = CoreError(type="network_error", message="Connection failed")
        assert err.type == "network_error"
        assert err.message == "Connection failed"
        assert err.retryable is False
        assert err.request_id is None

        err2 = CoreError(type="rate_limited", message="Too many requests", retryable=True, request_id="req-456")
        assert err2.retryable is True
        assert err2.request_id == "req-456"

    def test_core_result_construction(self):
        """CoreResult can be constructed with required and optional fields."""
        art = ImageArtifact(
            path=Path("/tmp/out.png"),
            format="PNG",
            width=1024,
            height=1024,
            sha256="abc123",
            normalized=True,
        )
        result = CoreResult(
            success=True,
            requested_size="1024x1024",
            artifact=art,
        )
        assert result.success is True
        assert result.provider == "chiyi"
        assert result.model == "gpt-image-2"
        assert result.quality == "high"
        assert result.requested_size == "1024x1024"
        assert result.upstream_size is None
        assert result.modality == "text"
        assert result.artifact == art
        assert result.error is None


def _make_image_source():
    return ImageSource(value="img.png")


def _make_loaded_source():
    return LoadedSource(filename="test.png", data=b"data", mime_type="image/png")


def _make_completed_artifact():
    return CompletedArtifact(kind="b64_json", value="data")


def _make_generate_request():
    return GenerateRequest(prompt="Test", output_dir=Path("/tmp"))


def _make_edit_request():
    return EditRequest(prompt="Test", output_dir=Path("/tmp"), primary_image=ImageSource(value="p.png"))


def _make_size_plan():
    return SizePlan(requested="1024x1024", upstream="1024x1024", target_width=1024, target_height=1024)


def _make_image_info():
    return ImageInfo(format="PNG", mime_type="image/png", width=1024, height=1024, frames=1)


def _make_image_artifact():
    return ImageArtifact(path=Path("/tmp/out.png"), format="PNG", width=1024, height=1024, sha256="abc", normalized=True)


def _make_core_error():
    return CoreError(type="network_error", message="Test")


def _make_core_result():
    return CoreResult(success=False, requested_size="1024x1024", error=CoreError(type="network_error", message="Test"))


_FROZEN_CASES = [
    ("ImageSource", _make_image_source, "value", "changed"),
    ("LoadedSource", _make_loaded_source, "filename", "changed"),
    ("CompletedArtifact", _make_completed_artifact, "value", "changed"),
    ("GenerateRequest", _make_generate_request, "prompt", "changed"),
    ("EditRequest", _make_edit_request, "prompt", "changed"),
    ("SizePlan", _make_size_plan, "requested", "changed"),
    ("ImageInfo", _make_image_info, "format", "JPEG"),
    ("ImageArtifact", _make_image_artifact, "sha256", "changed"),
    ("CoreError", _make_core_error, "message", "changed"),
    ("CoreResult", _make_core_result, "success", True),
]


class TestFrozenBehavior:
    """Test that all 10 public frozen dataclasses cannot be modified."""

    @pytest.mark.parametrize(
        "name, factory, attr, new_value",
        _FROZEN_CASES,
        ids=[case[0] for case in _FROZEN_CASES],
    )
    def test_dataclass_frozen(self, name, factory, attr, new_value):
        """Mutating any field raises dataclasses.FrozenInstanceError."""
        instance = factory()
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(instance, attr, new_value)

    def test_all_public_dataclasses_covered(self):
        """The frozen parametrization must cover exactly the 10 public dataclasses."""
        covered = {case[0] for case in _FROZEN_CASES}
        expected = {
            "ImageSource",
            "LoadedSource",
            "CompletedArtifact",
            "GenerateRequest",
            "EditRequest",
            "SizePlan",
            "ImageInfo",
            "ImageArtifact",
            "CoreError",
            "CoreResult",
        }
        assert covered == expected


class TestInitFalseConstraints:
    """Test that model and quality cannot be passed during construction."""

    def test_generate_request_model_init_false(self):
        """GenerateRequest construction with model argument raises TypeError."""
        with pytest.raises(TypeError):
            GenerateRequest(prompt="Test", output_dir=Path("/tmp"), model="custom-model")

    def test_generate_request_quality_init_false(self):
        """GenerateRequest construction with quality argument raises TypeError."""
        with pytest.raises(TypeError):
            GenerateRequest(prompt="Test", output_dir=Path("/tmp"), quality="standard")

    def test_edit_request_model_init_false(self):
        """EditRequest construction with model argument raises TypeError."""
        primary = ImageSource(value="primary.png")
        with pytest.raises(TypeError):
            EditRequest(prompt="Test", output_dir=Path("/tmp"), primary_image=primary, model="custom-model")

    def test_edit_request_quality_init_false(self):
        """EditRequest construction with quality argument raises TypeError."""
        primary = ImageSource(value="primary.png")
        with pytest.raises(TypeError):
            EditRequest(prompt="Test", output_dir=Path("/tmp"), primary_image=primary, quality="standard")

    def test_core_result_provider_init_false(self):
        """CoreResult construction with provider argument raises TypeError."""
        err = CoreError(type="network_error", message="Test")
        with pytest.raises(TypeError):
            CoreResult(success=False, requested_size="1024x1024", error=err, provider="custom-provider")

    def test_core_result_model_init_false(self):
        """CoreResult construction with model argument raises TypeError."""
        err = CoreError(type="network_error", message="Test")
        with pytest.raises(TypeError):
            CoreResult(success=False, requested_size="1024x1024", error=err, model="custom-model")

    def test_core_result_quality_init_false(self):
        """CoreResult construction with quality argument raises TypeError."""
        err = CoreError(type="network_error", message="Test")
        with pytest.raises(TypeError):
            CoreResult(success=False, requested_size="1024x1024", error=err, quality="standard")


class TestCoreResultValidation:
    """Test CoreResult __post_init__ validation logic."""

    def test_success_true_requires_artifact(self):
        """CoreResult with success=True and artifact=None raises ValueError."""
        with pytest.raises(ValueError):
            CoreResult(success=True, requested_size="1024x1024", artifact=None)

    def test_success_true_requires_no_error(self):
        """CoreResult with success=True and error set raises ValueError."""
        art = ImageArtifact(
            path=Path("/tmp/out.png"),
            format="PNG",
            width=1024,
            height=1024,
            sha256="abc123",
            normalized=True,
        )
        err = CoreError(type="network_error", message="Test")
        with pytest.raises(ValueError):
            CoreResult(success=True, requested_size="1024x1024", artifact=art, error=err)

    def test_success_false_requires_error(self):
        """CoreResult with success=False and error=None raises ValueError."""
        with pytest.raises(ValueError):
            CoreResult(success=False, requested_size="1024x1024", error=None)

    def test_success_false_requires_no_artifact(self):
        """CoreResult with success=False and artifact set raises ValueError."""
        art = ImageArtifact(
            path=Path("/tmp/out.png"),
            format="PNG",
            width=1024,
            height=1024,
            sha256="abc123",
            normalized=True,
        )
        err = CoreError(type="network_error", message="Test")
        with pytest.raises(ValueError):
            CoreResult(success=False, requested_size="1024x1024", artifact=art, error=err)

    def test_success_true_valid(self):
        """CoreResult with success=True, artifact set, and error=None is valid."""
        art = ImageArtifact(
            path=Path("/tmp/out.png"),
            format="PNG",
            width=1024,
            height=1024,
            sha256="abc123",
            normalized=True,
        )
        result = CoreResult(success=True, requested_size="1024x1024", artifact=art, error=None)
        assert result.success is True
        assert result.artifact == art
        assert result.error is None

    def test_success_false_valid(self):
        """CoreResult with success=False, error set, and artifact=None is valid."""
        err = CoreError(type="network_error", message="Connection failed")
        result = CoreResult(success=False, requested_size="1024x1024", artifact=None, error=err)
        assert result.success is False
        assert result.error == err
        assert result.artifact is None
