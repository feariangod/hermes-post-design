"""Backward-compatible Hermes wrappers for the generic installer."""
from __future__ import annotations

from pathlib import Path

from hermes_post_design.install import InstallEntry, apply_install, plan_install, restore_install


SyncEntry = InstallEntry

_LEGACY_ORDER = (
    ("plugins/image_gen/chiyi", "plugin"),
    ("skills/media/chiyi-image-generation", "skill"),
    ("skills/creative/poster-design", "skill"),
)


def _legacy_entries(entries: tuple[InstallEntry, ...] | list[dict]) -> tuple[SyncEntry, ...]:
    normalized = []
    for entry in entries:
        if isinstance(entry, InstallEntry):
            normalized.append(entry)
        else:
            normalized.append(InstallEntry(**entry))
    by_suffix = {
        Path(entry.target).as_posix(): entry
        for entry in normalized
    }
    adapted = []
    for suffix, component in _LEGACY_ORDER:
        match = next(
            entry for target, entry in by_suffix.items()
            if target.endswith(f"/{suffix}")
        )
        adapted.append(SyncEntry(component, match.target, match.action))
    return tuple(adapted)


def plan_sync(hermes_home: Path | str) -> tuple[SyncEntry, ...]:
    return _legacy_entries(plan_install("hermes", hermes_home))


def apply_sync(hermes_home: Path | str) -> dict:
    result = apply_install("hermes", hermes_home)
    result["entries"] = [entry.__dict__ for entry in _legacy_entries(result["entries"])]
    return result


def restore_backup(hermes_home: Path | str, backup: Path | str) -> dict:
    return restore_install("hermes", hermes_home, backup)
