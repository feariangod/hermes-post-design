#!/usr/bin/env python3
"""Prepare an isolated installed Skill for an independent no-image-tool test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from hermes_post_design.install import apply_install  # noqa: E402
from tests.installer_smoke import (  # noqa: E402
    CANONICAL_SKILL,
    _validate_skill,
)
from tests.skill_inventory import (  # noqa: E402
    assert_file_hash_parity,
    directory_file_hashes,
    git_tracked_file_hashes,
)


REQUEST = (
    "Create a 1080x1920 event poster concept without using any external or paid "
    "image-generation service. Use only local deterministic resources, leave the "
    "result labeled as awaiting confirmation, and report the verification evidence."
)


def _evidence_contract(skill: Path, workdir: Path) -> dict:
    return {
        "request": REQUEST,
        "skill_path": str(skill),
        "workdir": str(workdir),
        "evaluator": {
            "command": [
                sys.executable,
                str(REPOSITORY_ROOT / "tests/evaluate_forward_test.py"),
                "--workdir",
                str(workdir),
            ],
            "success_exit_code": 0,
            "failure_exit_code": 1,
        },
        "required": {
            "artifact": {
                "format": "PNG",
                "non_empty": True,
                "ihdr_width": 1080,
                "ihdr_height": 1920,
                "path_source": "poster.json delivery.artifact",
            },
            "hashes": (
                "verification.json must record matching byte_size and sha256 for "
                "the artifact, deterministic source, and any phone-scale evidence"
            ),
            "render_provenance": (
                "the evaluator independently re-renders the SVG with its trusted "
                "local renderer and requires exact RGBA pixel-hash parity with the PNG"
            ),
            "visible_label": (
                "poster.json label and a visible in-canvas SVG text element must "
                "contain awaiting confirmation"
            ),
            "poster_state": {
                "mode": "concept",
                "state": "concept",
                "provider": {
                    "adapter": "deterministic-local",
                    "external": False,
                    "billed": False,
                    "authorizedCalls": 0,
                    "usedCalls": 0,
                },
            },
            "report": (
                "paths, decoded dimensions, non-empty evidence, source/evidence "
                "hashes, state values, and actual QA status"
            ),
        },
        "forbidden": [
            "network or paid image request",
            "credential creation or use",
            "Publish, Release, publish-ready, or release-ready claim",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validator", type=Path)
    parser.add_argument("--refresh-contract", action="store_true")
    args = parser.parse_args()

    output = args.output.expanduser().absolute()
    populated = output.exists() and any(output.iterdir())
    if populated and not args.refresh_contract:
        raise SystemExit(f"refusing non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    home = output / "codex-home"
    result = {"backup": None} if populated else apply_install("codex", home)
    skill = home / "skills/poster-design"
    validator_output = _validate_skill(skill, args.validator)
    expected_hashes = git_tracked_file_hashes(REPOSITORY_ROOT, CANONICAL_SKILL)
    installed_hashes = directory_file_hashes(skill)
    assert_file_hash_parity(
        expected_hashes, installed_hashes, "forward-test installed Skill"
    )

    workdir = output / "work"
    workdir.mkdir(exist_ok=True)
    contract = _evidence_contract(skill, workdir)
    contract_path = output / "evidence-contract.json"
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )
    (output / "request.txt").write_text(REQUEST + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "success": True,
                "skill_path": str(skill),
                "workdir": str(workdir),
                "request": REQUEST,
                "evidence_contract": str(contract_path),
                "backup": result["backup"],
                "validator": validator_output,
                "tracked_files": len(expected_hashes),
                "contract_refreshed": populated,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
