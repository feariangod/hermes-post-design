#!/usr/bin/env python3
"""Exercise one or all portable installers in fresh temporary homes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from hermes_post_design.install import restore_install  # noqa: E402
from tests.skill_inventory import (  # noqa: E402
    assert_file_hash_parity,
    directory_file_hashes,
    git_tracked_file_hashes,
)


TARGETS = ("agents", "codex", "claude", "hermes")
SKILL_PATHS = {
    "agents": Path("skills/poster-design"),
    "codex": Path("skills/poster-design"),
    "claude": Path("skills/poster-design"),
    "hermes": Path("skills/creative/poster-design"),
}
CANONICAL_SKILL = (
    SOURCE_ROOT
    / "hermes_post_design/resources/skills/creative/poster-design"
)


def _snapshot(root: Path) -> dict[str, str]:
    entries = {}
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[relative] = f"symlink:{os.readlink(path)}"
        elif path.is_dir():
            entries[relative] = "directory"
        elif path.is_file():
            entries[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            entries[relative] = "other"
    return entries


def _run_cli(target: str, home: Path, *, apply: bool) -> dict:
    command = [
        sys.executable,
        "-m",
        "hermes_post_design.cli",
        "install-skill",
        "--target",
        target,
        "--home",
        str(home),
        "--json",
    ]
    if apply:
        command.append("--apply")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(SOURCE_ROOT), env.get("PYTHONPATH")))
    )
    completed = subprocess.run(
        command,
        cwd=REPOSITORY_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _validate_skill(skill: Path, validator: Path | None) -> str:
    required = (
        "SKILL.md",
        "references/host-adapters.md",
        "references/local-runtime.md",
        "scripts/init-poster.mjs",
        "templates/poster-starter/poster.json",
    )
    for relative in required:
        if not (skill / relative).is_file():
            raise AssertionError(f"installed Skill is missing {relative}")
    if validator is None:
        skill_text = (skill / "SKILL.md").read_text(encoding="utf-8")
        if not skill_text.startswith("---\nname: poster-design\n"):
            raise AssertionError("installed Skill frontmatter is invalid")
        return "structural"
    completed = subprocess.run(
        ["python3", str(validator), str(skill)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or "official validator exited zero"


def run_target(target: str, validator: Path | None) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"poster-{target}-smoke-") as directory:
        home = Path(directory) / "home"
        prior_skill = home / SKILL_PATHS[target]
        prior_skill.mkdir(parents=True)
        (prior_skill / "SKILL.md").write_text(
            "prior installed skill\n", encoding="utf-8"
        )
        (prior_skill / "seed.txt").write_text(
            f"prior-{target}\n", encoding="utf-8"
        )
        prior_skill_snapshot = _snapshot(prior_skill)
        before_dry_run = _snapshot(home)

        dry_run = _run_cli(target, home, apply=False)
        if dry_run.get("dry_run") is not True or dry_run.get("changed") is not False:
            raise AssertionError(f"invalid dry-run result for {target}: {dry_run}")
        if _snapshot(home) != before_dry_run:
            raise AssertionError(f"dry run wrote to the {target} home")

        applied = _run_cli(target, home, apply=True)
        if applied.get("changed") is not True:
            raise AssertionError(f"apply did not change the {target} home")
        backup = Path(applied["backup"])
        if not backup.is_dir():
            raise AssertionError(f"apply did not create a backup for {target}")

        installed_skill = home / SKILL_PATHS[target]
        validator_output = _validate_skill(installed_skill, validator)
        canonical_hashes = git_tracked_file_hashes(
            REPOSITORY_ROOT, CANONICAL_SKILL
        )
        installed_hashes = directory_file_hashes(installed_skill)
        assert_file_hash_parity(
            canonical_hashes, installed_hashes, f"{target} installed Skill"
        )

        restored = restore_install(target, home, backup)
        if SKILL_PATHS[target].as_posix() not in restored["restored"]:
            raise AssertionError(f"restore omitted the seeded {target} Skill")
        if _snapshot(prior_skill) != prior_skill_snapshot:
            raise AssertionError(f"restore did not preserve the seeded {target} Skill")

        digest = hashlib.sha256(
            json.dumps(canonical_hashes, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return {
            "target": target,
            "dry_run_entries": len(dry_run["entries"]),
            "apply_entries": len(applied["entries"]),
            "installed_files": len(installed_hashes),
            "tracked_hash_manifest_sha256": digest,
            "tracked_files": len(canonical_hashes),
            "validator": validator_output,
            "restore_preserved_seed": True,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=(*TARGETS, "all"), required=True)
    parser.add_argument("--validator", type=Path)
    args = parser.parse_args()
    targets = TARGETS if args.target == "all" else (args.target,)
    for target in targets:
        print(json.dumps(run_target(target, args.validator), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
