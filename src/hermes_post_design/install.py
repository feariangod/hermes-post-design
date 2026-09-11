"""Install packaged poster resources into supported agent host homes."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Literal


InstallTarget = Literal["agents", "codex", "claude", "hermes"]


@dataclass(frozen=True)
class InstallEntry:
    component: str
    target: str
    action: str


_TARGET_LAYOUTS = MappingProxyType({
    "agents": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "codex": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "claude": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "hermes": (
        ("skills/creative/poster-design", "skills/creative/poster-design", "skill"),
        ("skills/media/chiyi-image-generation", "skills/media/chiyi-image-generation", "image-skill"),
        ("plugins/image_gen/chiyi", "plugins/image_gen/chiyi", "plugin"),
    ),
})

_BACKUP_DIRECTORY = "hermes-post-design"

_EXCLUDED_RESOURCE_PARTS = frozenset({
    ".agents",
    ".claude",
    ".codex",
    ".eggs",
    ".hermes",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "__pypackages__",
    "artifacts",
    "backups",
    "build",
    "coverage",
    "credentials",
    "dist",
    "htmlcov",
    "logs",
    "node_modules",
    "reports",
    "secrets",
    "state",
    "temp",
    "tmp",
    "venv",
})
_EXCLUDED_RESOURCE_NAMES = frozenset({
    ".coverage",
    ".env",
    ".npmrc",
    ".pypirc",
    "coverage.xml",
    "credentials.json",
    "last-install.json",
})
_GENERATED_MEDIA_SUFFIXES = frozenset({
    ".avi",
    ".gif",
    ".jpeg",
    ".jpg",
    ".log",
    ".mov",
    ".mp4",
    ".pdf",
    ".png",
    ".tmp",
    ".webp",
})


def _resource_root():
    return resources.files("hermes_post_design").joinpath("resources")


def _checked_target(value: str) -> InstallTarget:
    if value not in _TARGET_LAYOUTS:
        supported = ", ".join(_TARGET_LAYOUTS)
        raise ValueError(f"Unsupported install target: {value}. Supported targets: {supported}")
    return value  # type: ignore[return-value]


def _default_home(target: InstallTarget) -> Path:
    if target == "agents":
        return Path.home() / ".agents"
    if target == "codex":
        return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    if target == "claude":
        return Path.home() / ".claude"
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))


def _checked_home(value: Path | str) -> Path:
    home = Path(value).expanduser().absolute()
    if home.is_symlink():
        raise ValueError("Install home must not be a symlink")
    if home.exists() and not home.is_dir():
        raise ValueError("Install home must be a directory")
    return home.resolve()


def _resolve_home(target: InstallTarget, home: Path | str | None) -> Path:
    return _checked_home(_default_home(target) if home is None else home)


def _managed_target(home: Path, relative: str, home_label: str) -> Path:
    target = home.joinpath(*relative.split("/"))
    resolved = target.resolve(strict=False)
    if resolved != home and home not in resolved.parents:
        raise ValueError(f"Managed target escapes {home_label}: {relative}")
    return target


def _should_include_resource(relative_parts: tuple[str, ...]) -> bool:
    """Return whether a resource path belongs in an installation or wheel."""
    if not relative_parts:
        return False
    lowered = tuple(part.lower() for part in relative_parts)
    name = lowered[-1]
    if any(part in _EXCLUDED_RESOURCE_PARTS for part in lowered):
        return False
    if name in _EXCLUDED_RESOURCE_NAMES or name.startswith(".env."):
        return False
    return not any(name.endswith(suffix) for suffix in _GENERATED_MEDIA_SUFFIXES)


def _iter_included_resources(node, relative_parts: tuple[str, ...] = ()):
    for child in sorted(node.iterdir(), key=lambda item: item.name):
        child_parts = relative_parts + (child.name,)
        if not _should_include_resource(child_parts):
            continue
        if child.is_dir():
            yield child, child_parts, True
            yield from _iter_included_resources(child, child_parts)
        elif child.is_file():
            yield child, child_parts, False


def _tree_digest(node) -> str:
    digest = hashlib.sha256()
    for child, relative_parts, is_directory in _iter_included_resources(node):
        relative = "/".join(relative_parts).encode("utf-8")
        if is_directory:
            digest.update(b"D\0" + relative + b"\0")
        else:
            digest.update(b"F\0" + relative + b"\0")
            digest.update(child.read_bytes())
    return digest.hexdigest()


def _path_digest(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None

    def plain_entries(directory: Path, relative_parts: tuple[str, ...] = ()):
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            if child.is_symlink():
                raise ValueError
            child_parts = relative_parts + (child.name,)
            if child.is_dir():
                yield child, child_parts, True
                yield from plain_entries(child, child_parts)
            elif child.is_file():
                yield child, child_parts, False
            else:
                raise ValueError

    digest = hashlib.sha256()
    try:
        entries = plain_entries(path)
        for child, relative_parts, is_directory in entries:
            relative = "/".join(relative_parts).encode("utf-8")
            if is_directory:
                digest.update(b"D\0" + relative + b"\0")
            else:
                digest.update(b"F\0" + relative + b"\0")
                digest.update(child.read_bytes())
    except ValueError:
        return None
    return digest.hexdigest()


def _copy_resource_tree(source, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child, relative_parts, is_directory in _iter_included_resources(source):
        target = destination.joinpath(*relative_parts)
        if is_directory:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(child.read_bytes())


def _assert_plain_tree(path: Path, label: str) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing symlink in {label}")
    if not path.exists():
        return
    if not path.is_dir():
        raise ValueError(f"Managed target must be a directory: {label}")
    for child in path.rglob("*"):
        if child.is_symlink():
            raise ValueError(f"Refusing symlink in {label}")


def _backup_root(home: Path, home_label: str) -> Path:
    return _managed_target(home, f"backups/{_BACKUP_DIRECTORY}", home_label)


def _restore_target(target: Path, backup_target: Path, existed: bool) -> None:
    if target.exists():
        shutil.rmtree(target)
    if existed:
        shutil.copytree(backup_target, target)


def plan_install(target: str, home: Path | str | None = None) -> tuple[InstallEntry, ...]:
    install_target = _checked_target(target)
    install_home = _resolve_home(install_target, home)
    root = _resource_root()
    entries = []
    for source_rel, target_rel, component in _TARGET_LAYOUTS[install_target]:
        source = root.joinpath(*source_rel.split("/"))
        managed = _managed_target(install_home, target_rel, f"{install_target.capitalize()} home")
        current = _path_digest(managed)
        expected = _tree_digest(source)
        action = "unchanged" if current == expected else ("update" if managed.exists() else "create")
        entries.append(InstallEntry(component, str(managed), action))
    return tuple(entries)


def apply_install(target: str, home: Path | str | None = None) -> dict:
    install_target = _checked_target(target)
    install_home = _resolve_home(install_target, home)
    home_label = f"{install_target.capitalize()} home"
    plan = plan_install(install_target, install_home)
    changes = [entry for entry in plan if entry.action != "unchanged"]
    if not changes:
        return {"changed": False, "backup": None, "entries": [asdict(item) for item in plan]}

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = _backup_root(install_home, home_label) / timestamp
    backup.mkdir(parents=True, exist_ok=False)
    root = _resource_root()
    manifest = {"version": 2, "target": install_target, "created_at": timestamp, "targets": []}
    prepared = []

    try:
        for source_rel, target_rel, _component in _TARGET_LAYOUTS[install_target]:
            managed = _managed_target(install_home, target_rel, home_label)
            entry = next(item for item in plan if item.target == str(managed))
            if entry.action == "unchanged":
                continue
            _assert_plain_tree(managed, target_rel)
            existed = managed.exists()
            backup_target = backup.joinpath("files", *target_rel.split("/"))
            if existed:
                shutil.copytree(managed, backup_target, symlinks=False)
            manifest["targets"].append({"relative": target_rel, "existed": existed})

            staging = managed.parent / f".{managed.name}.hermes-post-design-{timestamp}.tmp"
            if staging.exists():
                shutil.rmtree(staging)
            _copy_resource_tree(root.joinpath(*source_rel.split("/")), staging)
            prepared.append((managed, staging, backup_target, existed))

        (backup / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

        replaced = []
        try:
            for managed, staging, backup_target, existed in prepared:
                managed.parent.mkdir(parents=True, exist_ok=True)
                replaced.append((managed, backup_target, existed))
                if managed.exists():
                    shutil.rmtree(managed)
                os.replace(staging, managed)
        except Exception:
            for managed, backup_target, existed in reversed(replaced):
                _restore_target(managed, backup_target, existed)
            raise
    except Exception:
        for _, staging, _, _ in prepared:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
        raise

    state = install_home / "state" / _BACKUP_DIRECTORY
    state.mkdir(parents=True, exist_ok=True)
    (state / "last-install.json").write_text(
        json.dumps({"backup": str(backup), "created_at": timestamp, "target": install_target}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"changed": True, "backup": str(backup), "entries": [asdict(item) for item in plan]}


def restore_install(target: str, home: Path | str, backup: Path | str) -> dict:
    install_target = _checked_target(target)
    install_home = _resolve_home(install_target, home)
    home_label = f"{install_target.capitalize()} home"
    backup_path = Path(backup).expanduser().absolute()
    allowed_root = _backup_root(install_home, home_label)
    resolved_allowed_root = allowed_root.resolve(strict=False)
    resolved_backup = backup_path.resolve(strict=False)
    if backup_path.is_symlink() or resolved_allowed_root not in resolved_backup.parents:
        raise ValueError("Backup must be under the application backup directory")
    manifest = json.loads((backup_path / "manifest.json").read_text(encoding="utf-8"))
    manifest_target = manifest.get("target")
    if manifest_target is None and install_target != "hermes":
        raise ValueError("Backup manifest target is required for this install target")
    if manifest_target is not None and manifest_target != install_target:
        raise ValueError("Backup was created for a different install target")

    managed = {target_rel for _, target_rel, _ in _TARGET_LAYOUTS[install_target]}
    items = []
    seen = set()
    for item in manifest.get("targets", []):
        if not isinstance(item, dict):
            raise ValueError("Backup manifest is invalid")
        relative = item.get("relative")
        existed = item.get("existed")
        if relative not in managed or relative in seen or type(existed) is not bool:
            raise ValueError("Backup contains an unmanaged or invalid target")
        seen.add(relative)
        managed_target = _managed_target(install_home, relative, home_label)
        source = backup_path.joinpath("files", *relative.split("/"))
        if existed:
            if not source.is_dir():
                raise ValueError(f"Backup is incomplete for {relative}")
            _assert_plain_tree(source, f"backup {relative}")
        items.append((relative, managed_target, source, existed))

    prepared = []
    for relative, managed_target, source, existed in items:
        staging = managed_target.parent / f".{managed_target.name}.hermes-post-design-restore.tmp"
        previous = managed_target.parent / f".{managed_target.name}.hermes-post-design-before-restore.tmp"
        for temporary in (staging, previous):
            if temporary.exists():
                shutil.rmtree(temporary)
        if existed:
            shutil.copytree(source, staging)
        prepared.append((relative, managed_target, staging, previous, existed))

    restored = []
    switched = []
    try:
        for relative, managed_target, staging, previous, existed in prepared:
            managed_target.parent.mkdir(parents=True, exist_ok=True)
            had_current = managed_target.exists()
            if had_current:
                os.replace(managed_target, previous)
            switched.append((managed_target, previous, had_current))
            if existed:
                os.replace(staging, managed_target)
            restored.append(relative)
    except Exception:
        for managed_target, previous, had_current in reversed(switched):
            if managed_target.exists():
                shutil.rmtree(managed_target)
            if had_current and previous.exists():
                os.replace(previous, managed_target)
        raise
    finally:
        for _, _, staging, previous, _ in prepared:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            if previous.exists():
                shutil.rmtree(previous, ignore_errors=True)
    return {"restored": restored, "backup": str(backup_path)}
