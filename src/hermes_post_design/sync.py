"""Backward-compatible Hermes wrappers for the generic installer."""
from __future__ import annotations

import json
from pathlib import Path

from hermes_post_design.install import InstallEntry, apply_install, plan_install, restore_install


SyncEntry = InstallEntry


def plan_sync(hermes_home: Path | str) -> tuple[SyncEntry, ...]:
    return plan_install("hermes", hermes_home)


def apply_sync(hermes_home: Path | str) -> dict:
    result = apply_install("hermes", hermes_home)
    if result["changed"]:
        backup = Path(result["backup"])
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        state = backup.parents[2] / "state" / "hermes-post-design"
        state.mkdir(parents=True, exist_ok=True)
        (state / "last-sync.json").write_text(
            json.dumps({"backup": str(backup), "created_at": manifest["created_at"]}, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def restore_backup(hermes_home: Path | str, backup: Path | str) -> dict:
    return restore_install("hermes", hermes_home, backup)
