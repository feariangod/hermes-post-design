#!/usr/bin/env python3
"""Mechanically evaluate an isolated deterministic poster forward test."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_WIDTH = 1080
EXPECTED_HEIGHT = 1920
TEXT_SUFFIXES = frozenset({".html", ".json", ".md", ".svg", ".txt"})
READINESS_PATTERNS = (
    re.compile(r"\b(?:publish|publication|release)[ -]?ready\b", re.IGNORECASE),
    re.compile(
        r"\bready\s+for\s+(?:publication|publishing|publish|release)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:publish|release)\s+(?:approved|eligible|pass(?:ed)?)\b",
        re.IGNORECASE,
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, label: str, issues: list[str]):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        issues.append(f"{label} is unreadable JSON: {type(error).__name__}")
        return None
    if not isinstance(value, dict):
        issues.append(f"{label} must be a JSON object")
        return None
    return value


def _inside_file(
    workdir: Path, relative_value, label: str, issues: list[str]
) -> Path | None:
    if not isinstance(relative_value, str) or not relative_value.strip():
        issues.append(f"{label} path must be a non-empty relative string")
        return None
    relative = Path(relative_value)
    if relative.is_absolute():
        issues.append(f"{label} path must be relative to the workdir")
        return None
    candidate = (workdir / relative).resolve(strict=False)
    root = workdir.resolve()
    if candidate != root and root not in candidate.parents:
        issues.append(f"{label} path escapes the workdir")
        return None
    if not candidate.is_file():
        issues.append(f"{label} file is missing: {relative.as_posix()}")
        return None
    return candidate


def _verify_hash_entry(
    workdir: Path,
    label: str,
    entry,
    issues: list[str],
    expected_path: str | None = None,
) -> Path | None:
    if not isinstance(entry, dict):
        issues.append(f"{label} evidence must be an object")
        return None
    recorded_path = entry.get("path")
    if expected_path is not None and recorded_path != expected_path:
        issues.append(f"{label} evidence path does not match poster delivery")
    evidence_path = _inside_file(workdir, recorded_path, label, issues)
    if evidence_path is None:
        return None
    recorded_size = entry.get("byte_size")
    actual_size = evidence_path.stat().st_size
    if recorded_size != actual_size:
        issues.append(f"{label} byte_size does not match")
    recorded_hash = entry.get("sha256")
    actual_hash = _sha256(evidence_path)
    if recorded_hash != actual_hash:
        issues.append(f"{label} sha256 does not match")
    return evidence_path


def _png_dimensions(path: Path, label: str, issues: list[str]):
    data = path.read_bytes()
    if not data:
        issues.append(f"{label} PNG is empty")
        return None
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        issues.append(f"{label} is not a PNG with an IHDR")
        return None
    ihdr_length = struct.unpack(">I", data[8:12])[0]
    if data[12:16] != b"IHDR" or ihdr_length != 13:
        issues.append(f"{label} is not a PNG with an IHDR")
        return None
    width, height = struct.unpack(">II", data[16:24])
    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as error:
        issues.append(f"{label} PNG does not decode: {type(error).__name__}")
    return {"width": width, "height": height}


def _style_values(element) -> dict[str, str]:
    values = {}
    for declaration in element.attrib.get("style", "").split(";"):
        if ":" in declaration:
            key, value = declaration.split(":", 1)
            values[key.strip().lower()] = value.strip().lower()
    for key in ("display", "visibility", "opacity", "fill-opacity"):
        if key in element.attrib:
            values[key] = element.attrib[key].strip().lower()
    return values


def _is_visible_svg_label(source: Path) -> bool:
    if source.suffix.lower() != ".svg":
        return False
    try:
        root = ET.fromstring(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ET.ParseError):
        return False
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() != "text":
            continue
        text = " ".join("".join(element.itertext()).split())
        if "awaiting confirmation" not in text.lower():
            continue
        style = _style_values(element)
        if style.get("display") == "none":
            continue
        if style.get("visibility") in {"hidden", "collapse"}:
            continue
        if style.get("opacity") in {"0", "0.0"}:
            continue
        if style.get("fill-opacity") in {"0", "0.0"}:
            continue
        try:
            x = float(element.attrib["x"])
            y = float(element.attrib["y"])
        except (KeyError, ValueError):
            continue
        if 0 <= x <= EXPECTED_WIDTH and 0 <= y <= EXPECTED_HEIGHT:
            return True
    return False


def _check_readiness_claims(workdir: Path, poster: dict, issues: list[str]) -> None:
    qa = poster.get("qa")
    if isinstance(qa, dict):
        for key in ("publish_status", "release_status"):
            value = qa.get(key)
            if isinstance(value, str) and value.strip().lower() in {
                "approved",
                "eligible",
                "pass",
                "passed",
                "ready",
            }:
                issues.append(f"{key} makes a Publish or Release readiness claim")
    for path in sorted(workdir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in READINESS_PATTERNS):
            issues.append(
                f"Publish or Release readiness claim found in "
                f"{path.relative_to(workdir).as_posix()}"
            )


def evaluate_forward_test(workdir: Path) -> dict:
    root = workdir.expanduser().absolute()
    issues: list[str] = []
    poster = _load_json(root / "poster.json", "poster.json", issues)
    if poster is None:
        return {"success": False, "issues": issues}

    if poster.get("mode") != "concept":
        issues.append("poster mode must be concept")
    if poster.get("state") != "concept":
        issues.append("poster state must be concept")
    provider = poster.get("provider")
    expected_provider = {
        "adapter": "deterministic-local",
        "external": False,
        "billed": False,
        "authorizedCalls": 0,
        "usedCalls": 0,
    }
    if not isinstance(provider, dict):
        issues.append("poster provider must be an object")
        provider = {}
    for key, expected in expected_provider.items():
        if provider.get(key) != expected:
            issues.append(f"provider {key} must be {json.dumps(expected)}")

    label = poster.get("label")
    if not isinstance(label, str) or "awaiting confirmation" not in label.lower():
        issues.append("poster label must say awaiting confirmation")

    delivery = poster.get("delivery")
    qa = poster.get("qa")
    if not isinstance(delivery, dict):
        issues.append("poster delivery must be an object")
        delivery = {}
    if not isinstance(qa, dict):
        issues.append("poster qa must be an object")
        qa = {}
    verification_path = _inside_file(
        root, qa.get("verification_report"), "verification", issues
    )
    verification = (
        _load_json(verification_path, "verification", issues)
        if verification_path is not None
        else None
    )

    artifact_path = None
    source_path = None
    verified_hashes = []
    artifact_dimensions = None
    if verification is not None:
        if verification.get("stage") != "concept":
            issues.append("verification stage must be concept")
        verification_status = verification.get("status")
        if not isinstance(verification_status, str) or "awaiting_confirmation" not in verification_status:
            issues.append("verification status must remain awaiting_confirmation")
        artifact_path = _verify_hash_entry(
            root,
            "artifact",
            verification.get("artifact"),
            issues,
            delivery.get("artifact"),
        )
        if artifact_path is not None:
            verified_hashes.append("artifact")
            artifact_dimensions = _png_dimensions(artifact_path, "artifact", issues)
            if artifact_dimensions != {
                "width": EXPECTED_WIDTH,
                "height": EXPECTED_HEIGHT,
            }:
                issues.append("artifact PNG IHDR must be exactly 1080x1920")
        artifact_evidence = verification.get("artifact")
        if not isinstance(artifact_evidence, dict) or artifact_evidence.get("non_empty") is not True:
            issues.append("artifact evidence must record non_empty=true")
        if isinstance(artifact_evidence, dict) and artifact_evidence.get(
            "decoded_dimensions"
        ) != {"width": EXPECTED_WIDTH, "height": EXPECTED_HEIGHT}:
            issues.append("artifact evidence dimensions must be exactly 1080x1920")

        source_path = _verify_hash_entry(
            root,
            "source",
            verification.get("source"),
            issues,
            delivery.get("source"),
        )
        if source_path is not None:
            verified_hashes.append("source")
            if not _is_visible_svg_label(source_path):
                issues.append(
                    "source does not contain a visible awaiting-confirmation label"
                )

        phone = verification.get("phone_scale_review")
        if phone is not None:
            phone_path = _verify_hash_entry(
                root, "phone_scale_review", phone, issues
            )
            if phone_path is not None:
                verified_hashes.append("phone_scale_review")
                dimensions = _png_dimensions(phone_path, "phone_scale_review", issues)
                if isinstance(phone, dict) and dimensions != phone.get(
                    "decoded_dimensions"
                ):
                    issues.append("phone_scale_review dimensions do not match")
            if not isinstance(phone, dict) or phone.get("result") != "pass":
                issues.append("phone_scale_review must record result=pass")
            observations = phone.get("observations") if isinstance(phone, dict) else None
            if not isinstance(observations, list) or not any(
                isinstance(item, str)
                and "confirmation" in item.lower()
                and "readable" in item.lower()
                for item in observations
            ):
                issues.append(
                    "phone_scale_review must record readable confirmation evidence"
                )

        concept_qa = verification.get("concept_qa")
        if not isinstance(concept_qa, dict):
            issues.append("verification concept_qa must be an object")
        else:
            if concept_qa.get("rendered_artifact_inspected") is not True:
                issues.append("concept_qa must record rendered_artifact_inspected=true")
            if concept_qa.get("copy_matches_contract") is not True:
                issues.append("concept_qa must record copy_matches_contract=true")

    counters = poster.get("provider_counters")
    if isinstance(counters, dict):
        for key in (
            "external_image_generation_calls",
            "paid_image_generation_calls",
            "network_calls",
        ):
            if counters.get(key) != 0:
                issues.append(f"provider_counters {key} must be 0")
    _check_readiness_claims(root, poster, issues)

    result = {
        "success": not issues,
        "workdir": str(root),
        "artifact": {
            "path": str(artifact_path) if artifact_path else None,
            "dimensions": artifact_dimensions,
            "sha256": _sha256(artifact_path) if artifact_path else None,
        },
        "source": {
            "path": str(source_path) if source_path else None,
            "sha256": _sha256(source_path) if source_path else None,
        },
        "visible_label": "AWAITING CONFIRMATION" if source_path and _is_visible_svg_label(source_path) else None,
        "provider": {key: provider.get(key) for key in expected_provider},
        "verified_hashes": verified_hashes,
        "issues": issues,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_forward_test(args.workdir)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
