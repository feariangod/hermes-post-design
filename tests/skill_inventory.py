"""Independent Git-backed inventory checks for installed poster Skills."""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_tracked_file_hashes(
    repository_root: Path, skill_root: Path
) -> dict[str, str]:
    repository = repository_root.resolve()
    skill = skill_root.resolve()
    if repository != skill and repository not in skill.parents:
        raise AssertionError("canonical Skill must be inside the Git repository")
    pathspec = skill.relative_to(repository).as_posix()
    completed = subprocess.run(
        ["git", "-C", str(repository), "ls-files", "-z", "--", pathspec],
        check=True,
        capture_output=True,
    )
    tracked = [
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    ]
    if not tracked:
        raise AssertionError(f"Git tracks no files below {pathspec}")

    hashes = {}
    for repository_relative in tracked:
        source = repository / Path(repository_relative)
        if source.is_symlink():
            raise AssertionError(f"tracked canonical file is a symlink: {source}")
        if not source.is_file():
            raise AssertionError(f"tracked canonical file is missing: {source}")
        relative = source.relative_to(skill).as_posix()
        hashes[relative] = _sha256(source)
    return dict(sorted(hashes.items()))


def directory_file_hashes(root: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise AssertionError(f"unexpected installed symlink: {path}")
        if path.is_file():
            hashes[path.relative_to(root).as_posix()] = _sha256(path)
    return hashes


def assert_file_hash_parity(
    expected: dict[str, str], actual: dict[str, str], label: str
) -> None:
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected))
    mismatched = sorted(
        relative
        for relative in set(expected) & set(actual)
        if expected[relative] != actual[relative]
    )
    issues = []
    if missing:
        issues.append(f"missing tracked files: {', '.join(missing)}")
    if unexpected:
        issues.append(f"unexpected installed files: {', '.join(unexpected)}")
    if mismatched:
        issues.append(f"hash mismatches: {', '.join(mismatched)}")
    if issues:
        raise AssertionError(f"{label} parity failed: {'; '.join(issues)}")
