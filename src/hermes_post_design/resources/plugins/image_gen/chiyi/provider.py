"""Thin current-Hermes adapter for hermes-post-design."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from agent.image_gen_provider import ImageGenProvider, error_response, success_response
from agent.secret_scope import get_secret
from hermes_constants import get_hermes_home
from hermes_post_design.chiyi_core import ChiyiClient
from hermes_post_design.chiyi_core.models import EditRequest, GenerateRequest, ImageSource

_PROVIDER = "chiyi"
_MODEL = "gpt-image-2"
_QUALITY = "high"
_DEFAULT_SIZE = "1024x1024"


class ChiyiImageGenProvider(ImageGenProvider):
    @property
    def name(self) -> str:
        return _PROVIDER

    @property
    def display_name(self) -> str:
        return "Chiyi GPT Image 2"

    def is_available(self) -> bool:
        return bool(get_secret("CHIYI_IMAGE_API_KEY"))

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": _MODEL, "display": "GPT Image 2 (via Chiyi)", "strengths": "High-quality generation and editing"}]

    def default_model(self) -> Optional[str]:
        return _MODEL

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "max_reference_images": 16,
            "supports_custom_size": True,
            "size_only": True,
            "quality": _QUALITY,
        }

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "Chiyi GPT Image 2",
            "badge": "paid",
            "tag": "Fixed gpt-image-2/high backend with image editing",
            "env_vars": [{"key": "CHIYI_IMAGE_API_KEY", "prompt": "Chiyi image API key"}],
        }

    def generate(
        self,
        prompt: str,
        *,
        size: str = _DEFAULT_SIZE,
        image_url: Optional[str] = None,
        reference_image_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        del kwargs
        key = get_secret("CHIYI_IMAGE_API_KEY")
        if not key:
            return self._error("CHIYI_IMAGE_API_KEY is not configured", "auth_required", prompt)

        output_dir = get_hermes_home() / "cache" / "images"
        references = tuple(
            ImageSource(value)
            for value in (reference_image_urls or [])
            if isinstance(value, str) and value.strip()
        )
        try:
            with requests.Session() as session:
                client = ChiyiClient(api_key=key, session=session)
                if image_url or references:
                    primary = image_url or references[0].value
                    if not image_url:
                        references = references[1:]
                    result = client.edit(
                        EditRequest(
                            prompt=prompt,
                            output_dir=output_dir,
                            primary_image=ImageSource(primary, role="primary"),
                            reference_images=references,
                            size=size,
                        )
                    )
                else:
                    result = client.generate(GenerateRequest(prompt, output_dir, size))
        except (TypeError, ValueError):
            return self._error("Invalid Chiyi image request", "invalid_argument", prompt)

        if not result.success or result.artifact is None:
            error = result.error
            return self._error(
                error.message if error else "Chiyi image generation failed",
                error.type if error else "provider_error",
                prompt,
            )
        artifact = result.artifact
        response = success_response(
            image=str(artifact.path),
            model=_MODEL,
            prompt=prompt,
            aspect_ratio="square",
            provider=_PROVIDER,
            modality=result.modality,
            extra={
                "size": result.requested_size,
                "upstream_size": result.upstream_size,
                "width": artifact.width,
                "height": artifact.height,
                "sha256": artifact.sha256,
                "quality": _QUALITY,
            },
        )
        response.pop("aspect_ratio", None)
        return response

    @staticmethod
    def _error(message: str, error_type: str, prompt: str) -> Dict[str, Any]:
        response = error_response(
            error=message,
            error_type=error_type,
            provider=_PROVIDER,
            model=_MODEL,
            prompt=prompt,
            aspect_ratio="square",
        )
        response.pop("aspect_ratio", None)
        return response
