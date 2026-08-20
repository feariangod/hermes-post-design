"""Platform-neutral HTTP client and orchestration for Chiyi image operations."""
from __future__ import annotations

import base64
import binascii
import math
import time
from pathlib import Path
from typing import Any

from hermes_post_design.chiyi_core.artifacts import save_artifact
from hermes_post_design.chiyi_core.images import MAX_IMAGE_BYTES
from hermes_post_design.chiyi_core.models import (
    CompletedArtifact,
    CoreError,
    CoreResult,
    EditRequest,
    GenerateRequest,
    ImageSource,
    SizePlan,
)
from hermes_post_design.chiyi_core.sizing import resolve_size
from hermes_post_design.chiyi_core.sources import load_sources
from hermes_post_design.chiyi_core.streaming import parse_sse

_BASE_URL = "https://api.chiyi.cc/v1"
_CONNECT_TIMEOUT_SECONDS = 15
_MAX_SSE_EVENT_BYTES = 2 * 1024 * 1024
_MAX_BASE64_CHARS = 4 * ((MAX_IMAGE_BYTES + 2) // 3)


class ChiyiClient:
    """Execute fixed-contract Chiyi generation and edit requests."""

    def __init__(self, api_key, session, timeout_seconds=300, max_retries=1):
        if not isinstance(api_key, str):
            raise TypeError("api_key must be a string")
        if not api_key.strip():
            raise ValueError("api_key must be non-empty")
        if session is None or not callable(getattr(session, "post", None)):
            raise TypeError("session must provide post()")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
            raise TypeError("timeout_seconds must be an integer")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int):
            raise TypeError("max_retries must be an integer")
        if max_retries not in (0, 1):
            raise ValueError("max_retries must be 0 or 1")

        self._api_key = api_key
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    def generate(self, request: GenerateRequest) -> CoreResult:
        if not isinstance(request, GenerateRequest):
            raise TypeError("request must be GenerateRequest")

        prepared = self._preflight(request, modality="text")
        if isinstance(prepared, CoreResult):
            return prepared
        prompt, plan = prepared

        kwargs = {
            "headers": {
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
            "json": {
                "model": "gpt-image-2",
                "prompt": prompt,
                "size": plan.upstream,
                "quality": "high",
                "n": 1,
                "response_format": "b64_json",
            },
            "timeout": (_CONNECT_TIMEOUT_SECONDS, float(self._timeout_seconds)),
            "allow_redirects": False,
        }
        return self._execute(
            url=f"{_BASE_URL}/images/generations",
            kwargs=kwargs,
            request=request,
            plan=plan,
            modality="text",
            expect_stream=False,
        )

    def edit(self, request: EditRequest) -> CoreResult:
        if not isinstance(request, EditRequest):
            raise TypeError("request must be EditRequest")

        prepared = self._preflight(request, modality="image")
        if isinstance(prepared, CoreResult):
            return prepared
        prompt, plan = prepared

        if not isinstance(request.reference_images, tuple):
            return self._failure(request, "invalid_argument", "Invalid edit request", "image")
        if 1 + len(request.reference_images) > 16:
            return self._failure(request, "invalid_argument", "Too many image sources", "image")

        try:
            loaded = load_sources(request.primary_image, request.reference_images)
        except Exception:
            return self._failure(request, "invalid_image", "Image source validation failed", "image")
        expected_count = 1 + len(request.reference_images)
        if not isinstance(loaded, tuple) or len(loaded) != expected_count:
            return self._failure(request, "invalid_image", "Image source validation failed", "image")

        files = [
            ("image", (source.filename, source.data, source.mime_type))
            for source in loaded
        ]
        kwargs = {
            "headers": {
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "text/event-stream, application/json",
            },
            "data": {
                "model": "gpt-image-2",
                "prompt": prompt,
                "size": plan.upstream,
                "quality": "high",
                "n": "1",
                "response_format": "b64_json",
                "stream": "true",
                "partial_images": "1",
            },
            "files": files,
            "stream": True,
            "timeout": (_CONNECT_TIMEOUT_SECONDS, float(self._timeout_seconds)),
            "allow_redirects": False,
        }
        return self._execute(
            url=f"{_BASE_URL}/images/edits",
            kwargs=kwargs,
            request=request,
            plan=plan,
            modality="image",
            expect_stream=True,
        )

    def _preflight(self, request, *, modality):
        if not isinstance(request.prompt, str) or not request.prompt.strip():
            return self._failure(request, "invalid_argument", "Prompt must be non-empty", modality)
        if not isinstance(request.output_dir, Path):
            return self._failure(request, "invalid_argument", "output_dir must be Path", modality)
        try:
            if request.output_dir.is_symlink():
                return self._failure(request, "invalid_argument", "Invalid output directory", modality)
            if request.output_dir.exists() and not request.output_dir.is_dir():
                return self._failure(request, "invalid_argument", "Invalid output directory", modality)
        except OSError:
            return self._failure(request, "invalid_argument", "Invalid output directory", modality)
        try:
            plan = resolve_size(request.size)
        except Exception:
            return self._failure(request, "invalid_argument", "Invalid output size", modality)
        return request.prompt.strip(), plan

    def _execute(self, *, url, kwargs, request, plan, modality, expect_stream):
        for attempt in range(self._max_retries + 1):
            try:
                response = self._session.post(url, **kwargs)
            except Exception:
                return self._failure(
                    request,
                    "network_error",
                    "Chiyi request failed because of a network error",
                    modality,
                    plan=plan,
                )

            if response is None:
                return self._failure(
                    request, "protocol_error", "Chiyi returned an invalid response", modality, plan=plan
                )

            status = self._safe_attr(response, "status_code")
            if type(status) is not int or status <= 0:
                self._safe_close(response)
                return self._failure(
                    request, "protocol_error", "Chiyi returned an invalid response", modality, plan=plan
                )

            if status == 429 and attempt < self._max_retries:
                retry_after = self._retry_after(self._safe_attr(response, "headers"))
                self._safe_close(response)
                time.sleep(retry_after)
                continue

            try:
                if not 200 <= status < 300:
                    return self._failure(
                        request,
                        self._http_error_type(response, status),
                        self._http_error_message(status),
                        modality,
                        plan=plan,
                        retryable=status == 429,
                    )

                artifact = self._response_artifact(response, expect_stream=expect_stream)
                raw = self._artifact_bytes(artifact)
                try:
                    saved = save_artifact(raw, plan, request.output_dir)
                except OSError:
                    return self._failure(
                        request, "artifact_error", "Image artifact could not be saved", modality, plan=plan
                    )
                except ValueError as exc:
                    lowered = str(exc).lower()
                    error_type = (
                        "resolution_mismatch"
                        if "resolution" in lowered or "insufficient" in lowered
                        else "invalid_image"
                    )
                    return self._failure(
                        request, error_type, "Chiyi returned an invalid image artifact", modality, plan=plan
                    )
                except Exception:
                    return self._failure(
                        request, "artifact_error", "Image artifact could not be saved", modality, plan=plan
                    )

                return CoreResult(
                    success=True,
                    requested_size=plan.requested,
                    upstream_size=plan.upstream,
                    modality=modality,
                    artifact=saved,
                    error=None,
                )
            except _ClientFailure as exc:
                return self._failure(
                    request, exc.error_type, exc.message, modality, plan=plan, retryable=exc.retryable
                )
            finally:
                self._safe_close(response)

        return self._failure(request, "rate_limited", "Chiyi rate limit reached", modality, retryable=True)

    def _response_artifact(self, response, *, expect_stream):
        content_type = self._header(self._safe_attr(response, "headers"), "content-type")
        if expect_stream and content_type and "text/event-stream" in content_type.lower():
            try:
                lines = response.iter_lines(decode_unicode=False)
                return parse_sse(lines, max_event_bytes=_MAX_SSE_EVENT_BYTES)
            except Exception:
                raise _ClientFailure("protocol_error", "Chiyi returned an invalid event stream") from None

        try:
            body = response.json()
        except Exception:
            raise _ClientFailure("protocol_error", "Chiyi returned invalid JSON") from None
        if not isinstance(body, dict):
            raise _ClientFailure("protocol_error", "Chiyi response shape is invalid")
        data = body.get("data")
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise _ClientFailure("protocol_error", "Chiyi response shape is invalid")
        item = data[0]
        present = [name for name in ("b64_json", "url") if name in item]
        if len(present) != 1:
            raise _ClientFailure("protocol_error", "Chiyi response artifact is ambiguous")
        value = item[present[0]]
        if not isinstance(value, str) or not value.strip():
            raise _ClientFailure("protocol_error", "Chiyi response artifact is invalid")
        return CompletedArtifact(present[0], value.strip())

    def _artifact_bytes(self, artifact):
        if not isinstance(artifact, CompletedArtifact):
            raise _ClientFailure("protocol_error", "Chiyi response artifact is invalid")
        if artifact.kind == "b64_json":
            encoded = artifact.value
            if not isinstance(encoded, str) or len(encoded) > _MAX_BASE64_CHARS:
                raise _ClientFailure("invalid_image", "Chiyi returned an invalid image artifact")
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError):
                raise _ClientFailure("invalid_image", "Chiyi returned an invalid image artifact") from None
            if not raw or len(raw) > MAX_IMAGE_BYTES:
                raise _ClientFailure("invalid_image", "Chiyi returned an invalid image artifact")
            return raw
        if artifact.kind == "url":
            try:
                loaded = load_sources(ImageSource(artifact.value, role="primary"), ())
            except Exception:
                raise _ClientFailure("invalid_image", "Chiyi image URL could not be loaded") from None
            if not isinstance(loaded, tuple) or len(loaded) != 1:
                raise _ClientFailure("invalid_image", "Chiyi image URL could not be loaded")
            return loaded[0].data
        raise _ClientFailure("protocol_error", "Chiyi response artifact is invalid")

    def _failure(
        self,
        request,
        error_type,
        message,
        modality,
        *,
        plan=None,
        retryable=False,
    ):
        requested = plan.requested if plan is not None else (
            request.size if isinstance(getattr(request, "size", None), str) else "1024x1024"
        )
        return CoreResult(
            success=False,
            requested_size=requested,
            upstream_size=plan.upstream if plan is not None else None,
            modality=modality,
            artifact=None,
            error=CoreError(
                type=error_type,
                message=message[:300],
                retryable=retryable,
                request_id=getattr(request, "request_id", None),
            ),
        )

    @staticmethod
    def _safe_attr(obj, name):
        try:
            return getattr(obj, name, None)
        except Exception:
            return None

    @classmethod
    def _safe_close(cls, response):
        close = cls._safe_attr(response, "close")
        if callable(close):
            try:
                close()
            except Exception:
                pass

    @classmethod
    def _retry_after(cls, headers):
        raw = cls._header(headers, "retry-after")
        try:
            value = float(raw) if raw is not None else 1.0
        except (TypeError, ValueError):
            value = 1.0
        if not math.isfinite(value):
            value = 1.0
        return min(max(value, 0.0), 5.0)

    @staticmethod
    def _header(headers, name):
        if not hasattr(headers, "items"):
            return None
        try:
            for key, value in headers.items():
                if isinstance(key, str) and key.lower() == name.lower():
                    return value if isinstance(value, str) else None
        except Exception:
            return None
        return None

    @classmethod
    def _http_error_type(cls, response, status):
        if status in (401, 403):
            return "auth_error"
        if status == 429:
            return "rate_limited"
        body = None
        try:
            body = response.json()
        except Exception:
            pass
        if cls._contains_quota_marker(body):
            return "quota_error"
        if 500 <= status <= 599:
            return "server_error"
        if 400 <= status <= 499:
            return "invalid_argument"
        return "protocol_error"

    @staticmethod
    def _contains_quota_marker(body):
        markers = ("quota", "balance", "credit")
        stack = [body]
        visited = 0
        text_bytes = 0
        while stack and visited < 64 and text_bytes < 8192:
            value = stack.pop()
            visited += 1
            if isinstance(value, str):
                sample = value[: 8192 - text_bytes].lower()
                text_bytes += len(sample)
                if any(marker in sample for marker in markers):
                    return True
            elif isinstance(value, dict):
                stack.extend(list(value.keys())[:32])
                stack.extend(list(value.values())[:32])
            elif isinstance(value, (list, tuple)):
                stack.extend(value[:32])
        return False

    @staticmethod
    def _http_error_message(status):
        if status in (401, 403):
            return "Chiyi authentication failed"
        if status == 429:
            return "Chiyi rate limit reached"
        if 500 <= status <= 599:
            return "Chiyi server error"
        if 400 <= status <= 499:
            return "Chiyi rejected the request"
        return "Chiyi returned an invalid HTTP status"


class _ClientFailure(Exception):
    def __init__(self, error_type, message, *, retryable=False):
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.retryable = retryable
