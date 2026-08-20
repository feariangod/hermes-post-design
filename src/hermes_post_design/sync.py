"""Install packaged Hermes resources with a small backup-and-restore workflow."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path


@dataclass(frozen=True)
class SyncEntry:
    component: str
    target: str
    action: str


_RESOURCE_TARGETS = (
    ("plugins/image_gen/chiyi", "plugins/image_gen/chiyi", "plugin"),
    ("skills/media/chiyi-image-generation", "skills/media/chiyi-image-generation", "skill"),
    ("skills/creative/poster-design", "skills/creative/poster-design", "skill"),
)


def _resource_root():
    return resources.files("hermes_post_design").joinpath("resources")


def _tree_digest(node) -> str:
    digest = hashlib.sha256()
    for child in sorted(node.iterdir(), key=lambda item: item.name):
        if child.is_dir():
            digest.update(b"D\0" + child.name.encode("utf-8") + b"\0")
            digest.update(_tree_digest(child).encode("ascii"))
        else:
            digest.update(b"F\0" + child.name.encode("utf-8") + b"\0")
            digest.update(child.read_bytes())
    return digest.hexdigest()


def _path_digest(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None

    def digest_dir(directory: Path) -> str | None:
        digest = hashlib.sha256()
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                return None
            if child.is_dir():
                nested = digest_dir(child)
                if nested is None:
                    return None
                digest.update(b"D\0" + child.name.encode("utf-8") + b"\0")
                digest.update(nested.encode("ascii"))
            elif child.is_file():
                digest.update(b"F\0" + child.name.encode("utf-8") + b"\0")
                digest.update(child.read_bytes())
        return digest.hexdigest()

    return digest_dir(path)


def _checked_home(value: Path | str) -> Path:
    home = Path(value).expanduser().absolute()
    if home.is_symlink():
        raise ValueError("Hermes home must not be a symlink")
    if home.exists() and not home.is_dir():
        raise ValueError("Hermes home must be a directory")
    return home.resolve()


def _managed_target(home: Path, relative: str) -> Path:
    target = home.joinpath(*relative.split("/"))
    resolved = target.resolve(strict=False)
    if resolved != home and home not in resolved.parents:
        raise ValueError(f"Managed target escapes Hermes home: {relative}")
    return target


def plan_sync(hermes_home: Path | str) -> tuple[SyncEntry, ...]:
    home = _checked_home(hermes_home)
    root = _resource_root()
    entries = []
    for source_rel, target_rel, component in _RESOURCE_TARGETS:
        source = root.joinpath(*source_rel.split("/"))
        target = _managed_target(home, target_rel)
        current = _path_digest(target)
        expected = _tree_digest(source)
        action = "unchanged" if current == expected else ("update" if target.exists() else "create")
        entries.append(SyncEntry(component, str(target), action))
    return tuple(entries)


def _copy_resource_tree(source, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_resource_tree(child, target)
        else:
            target.write_bytes(child.read_bytes())


def _assert_plain_tree(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing symlink in {label}")
    if not path.exists():
        return
    for child in path.rglob("*"):
        if child.is_symlink():
            raise ValueError(f"Refusing symlink in {label}")


def _restore_target(target: Path, backup_target: Path, existed: bool) -> None:
    if target.exists():
        shutil.rmtree(target)
    if existed:
        shutil.copytree(backup_target, target)


def apply_sync(hermes_home: Path | str) -> dict:
    home = _checked_home(hermes_home)
    plan = plan_sync(home)
    changes = [entry for entry in plan if entry.action != "unchanged"]
    if not changes:
        return {"changed": False, "backup": None, "entries": [asdict(item) for item in plan]}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = home / "backups" / "hermes-post-design" / timestamp
    backup.mkdir(parents=True, exist_ok=False)
    root = _resource_root()
    manifest = {"version": 1, "created_at": timestamp, "targets": []}
    prepared = []

    try:
        for source_rel, target_rel, component in _RESOURCE_TARGETS:
            target = _managed_target(home, target_rel)
            entry = next(item for item in plan if item.target == str(target))
            if entry.action == "unchanged":
                continue
            _assert_plain_tree(target, target_rel)
            existed = target.exists()
            backup_target = backup.joinpath("files", *target_rel.split("/"))
            if existed:
                shutil.copytree(target, backup_target, symlinks=False)
            manifest["targets"].append({"relative": target_rel, "existed": existed})

            staging = target.parent / f".{target.name}.hermes-post-design-{timestamp}.tmp"
            if staging.exists():
                shutil.rmtree(staging)
            prepared.append((target, staging, backup_target, existed))
            _copy_resource_tree(root.joinpath(*source_rel.split("/")), staging)

        (backup / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

        replaced = []
        try:
            for target, staging, backup_target, existed in prepared:
                target.parent.mkdir(parents=True, exist_ok=True)
                replaced.append((target, backup_target, existed))
                if target.exists():
                    shutil.rmtree(target)
                os.replace(staging, target)
        except Exception:
            for target, backup_target, existed in reversed(replaced):
                _restore_target(target, backup_target, existed)
            raise
    except Exception:
        for _, staging, _, _ in prepared:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        raise

    state = home / "state" / "hermes-post-design"
    state.mkdir(parents=True, exist_ok=True)
    (state / "last-sync.json").write_text(
        json.dumps({"backup": str(backup), "created_at": timestamp}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"changed": True, "backup": str(backup), "entries": [asdict(item) for item in plan]}


def restore_backup(hermes_home: Path | str, backup: Path | str) -> dict:
    home = _checked_home(hermes_home)
    backup_path = Path(backup).expanduser().absolute()
    allowed_root = (home / "backups" / "hermes-post-design").absolute()
    if allowed_root not in backup_path.parents:
        raise ValueError("Backup must be under the Hermes application backup directory")
    manifest_path = backup_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = []
    managed = {target for _, target, _ in _RESOURCE_TARGETS}
    for item in manifest.get("targets", []):
        if not isinstance(item, dict):
            raise ValueError("Backup manifest is invalid")
        relative = item.get("relative")
        existed = item.get("existed")
        if relative not in managed or type(existed) is not bool:
            raise ValueError("Backup contains an unmanaged or invalid target")
        target = _managed_target(home, relative)
        source = backup_path.joinpath("files", *relative.split("/"))
        if existed:
            if not source.is_dir():
                raise ValueError(f"Backup is incomplete for {relative}")
            _assert_plain_tree(source, f"backup {relative}")
        items.append((relative, target, source, existed))

    prepared = []
    for relative, target, source, existed in items:
        staging = target.parent / f".{target.name}.hermes-post-design-restore.tmp"
        previous = target.parent / f".{target.name}.hermes-post-design-before-restore.tmp"
        for temporary in (staging, previous):
            if temporary.exists():
                shutil.rmtree(temporary)
        if existed:
            shutil.copytree(source, staging)
        prepared.append((relative, target, staging, previous, existed))

    restored = []
    switched = []
    try:
        for relative, target, staging, previous, existed in prepared:
            target.parent.mkdir(parents=True, exist_ok=True)
            had_current = target.exists()
            if had_current:
                os.replace(target, previous)
            switched.append((target, previous, had_current))
            if existed:
                os.replace(staging, target)
            restored.append(relative)
    except Exception:
        for target, previous, had_current in reversed(switched):
            if target.exists():
                shutil.rmtree(target)
            if had_current and previous.exists():
                os.replace(previous, target)
        raise
    finally:
        for _, _, staging, previous, _ in prepared:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            if previous.exists():
                shutil.rmtree(previous, ignore_errors=True)
    return {"restored": restored, "backup": str(backup_path)}
