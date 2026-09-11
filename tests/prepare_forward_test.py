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
    _file_hashes,
    _validate_skill,
)


REQUEST = (
    "Create a 1080x1920 event poster concept without using any external or paid "
    "image-generation service. Use only local deterministic resources, leave the "
    "result labeled as awaiting confirmation, and report the verification evidence."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validator", type=Path)
    args = parser.parse_args()

    output = args.output.expanduser().absolute()
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing non-empty output directory: {output}")
    output.mkdir(parents=True, exist_ok=True)
    home = output / "codex-home"
    result = apply_install("codex", home)
    skill = home / "skills/poster-design"
    validator_output = _validate_skill(skill, args.validator)
    if _file_hashes(skill, filtered=False) != _file_hashes(
        CANONICAL_SKILL, filtered=True
    ):
        raise SystemExit("installed forward-test Skill failed filtered hash parity")

    workdir = output / "work"
    workdir.mkdir()
    contract = {
        "request": REQUEST,
        "skill_path": str(skill),
        "workdir": str(workdir),
        "required": {
            "artifact": "one non-empty PNG decoded as exactly 1080x1920",
            "visible_label": "awaiting confirmation",
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
            "report": "paths, decoded dimensions, non-empty evidence, state values, and actual QA status",
        },
        "forbidden": [
            "network or paid image request",
            "credential creation or use",
            "Publish, Release, publish-ready, or release-ready claim",
        ],
    }
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
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
