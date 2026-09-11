import hashlib
import subprocess
from pathlib import Path

import pytest

from tests.skill_inventory import (
    assert_file_hash_parity,
    directory_file_hashes,
    git_tracked_file_hashes,
)


def test_git_tracked_inventory_ignores_untracked_source_pollution(tmp_path):
    repository = tmp_path / "repository"
    skill = repository / "skill"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("tracked skill\n", encoding="utf-8")
    (skill / "references").mkdir()
    (skill / "references/host.md").write_text("tracked reference\n", encoding="utf-8")
    (skill / "node_modules/example").mkdir(parents=True)
    (skill / "node_modules/example/index.js").write_text("untracked\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "add", "skill/SKILL.md", "skill/references/host.md"],
        check=True,
    )

    inventory = git_tracked_file_hashes(repository, skill)

    assert inventory == {
        "SKILL.md": hashlib.sha256(b"tracked skill\n").hexdigest(),
        "references/host.md": hashlib.sha256(b"tracked reference\n").hexdigest(),
    }


def test_file_hash_parity_rejects_missing_and_unexpected_installed_files(tmp_path):
    installed = tmp_path / "installed"
    installed.mkdir()
    (installed / "kept.md").write_text("kept\n", encoding="utf-8")
    expected = {
        "kept.md": hashlib.sha256(b"kept\n").hexdigest(),
        "missing.md": hashlib.sha256(b"missing\n").hexdigest(),
    }

    with pytest.raises(AssertionError, match="missing tracked files: missing.md"):
        assert_file_hash_parity(expected, directory_file_hashes(installed), "fixture")

    (installed / "missing.md").write_text("missing\n", encoding="utf-8")
    (installed / "unexpected.log").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="unexpected installed files: unexpected.log"):
        assert_file_hash_parity(expected, directory_file_hashes(installed), "fixture")


def test_installer_and_forward_fixture_do_not_reuse_production_inventory_helpers():
    repository = Path(__file__).resolve().parents[1]
    for relative in ("tests/installer_smoke.py", "tests/prepare_forward_test.py"):
        source = (repository / relative).read_text(encoding="utf-8")
        for private_helper in (
            "_should_include_resource",
            "_tree_digest",
            "_path_digest",
            "_copy_resource_tree",
        ):
            assert private_helper not in source
