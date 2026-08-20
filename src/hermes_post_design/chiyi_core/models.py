"""Core data models for Chiyi image generation and editing requests."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Type aliases
Operation = Literal["generate", "edit"]
ErrorType = Literal[
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
]


@dataclass(frozen=True)
class ImageSource:
    """Reference to an image source."""
    value: str
    role: str = "reference"


@dataclass(frozen=True)
class LoadedSource:
    """A loaded image with metadata."""
    filename: str
    data: bytes
    mime_type: str


@dataclass(frozen=True)
class CompletedArtifact:
    """Artifact returned by upstream provider."""
    kind: Literal["b64_json", "url"]
    value: str


@dataclass(frozen=True)
class GenerateRequest:
    """Request for text-to-image generation."""
    prompt: str
    output_dir: Path
    size: str = "1024x1024"
    request_id: str | None = None
    model: Literal["gpt-image-2"] = field(default="gpt-image-2", init=False)
    quality: Literal["high"] = field(default="high", init=False)


@dataclass(frozen=True)
class EditRequest:
    """Request for image-to-image editing."""
    prompt: str
    output_dir: Path
    primary_image: ImageSource
    reference_images: tuple[ImageSource, ...] = field(default_factory=tuple)
    size: str = "1024x1024"
    request_id: str | None = None
    model: Literal["gpt-image-2"] = field(default="gpt-image-2", init=False)
    quality: Literal["high"] = field(default="high", init=False)


@dataclass(frozen=True)
class SizePlan:
    """Size resolution plan."""
    requested: str
    upstream: str
    target_width: int
    target_height: int


@dataclass(frozen=True)
class ImageInfo:
    """Image metadata."""
    format: str
    mime_type: str
    width: int
    height: int
    frames: int


@dataclass(frozen=True)
class ImageArtifact:
    """Final saved image artifact."""
    path: Path
    format: str
    width: int
    height: int
    sha256: str
    normalized: bool


@dataclass(frozen=True)
class CoreError:
    """Error information."""
    type: ErrorType
    message: str
    retryable: bool = False
    request_id: str | None = None


@dataclass(frozen=True)
class CoreResult:
    """Result of a core operation."""
    success: bool
    provider: Literal["chiyi"] = field(default="chiyi", init=False)
    model: Literal["gpt-image-2"] = field(default="gpt-image-2", init=False)
    quality: Literal["high"] = field(default="high", init=False)
    requested_size: str = "1024x1024"
    upstream_size: str | None = None
    modality: Literal["text", "image"] = "text"
    artifact: ImageArtifact | None = None
    error: CoreError | None = None

    def __post_init__(self) -> None:
        """Validate success/artifact/error consistency."""
        if self.success:
            if self.artifact is None:
                raise ValueError("success=True requires artifact to be set")
            if self.error is not None:
                raise ValueError("success=True requires error to be None")
        else:
            if self.error is None:
                raise ValueError("success=False requires error to be set")
            if self.artifact is not None:
                raise ValueError("success=False requires artifact to be None")
