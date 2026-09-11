from pathlib import Path

import pytest

from hermes_post_design.install import apply_install, plan_install, restore_install


@pytest.mark.parametrize(
    ("target", "relative"),
    [
        ("agents", "skills/poster-design"),
        ("codex", "skills/poster-design"),
        ("claude", "skills/poster-design"),
        ("hermes", "skills/creative/poster-design"),
    ],
)
def test_plan_install_targets_only_declared_skill(tmp_path, target, relative):
    home = tmp_path / "uncreated-home"

    plan = plan_install(target, home)

    assert any(Path(entry.target) == home / relative for entry in plan)
    assert not home.exists()


def test_hermes_adds_optional_provider_resources(tmp_path):
    plan = plan_install("hermes", tmp_path / "hermes")

    assert {entry.component for entry in plan} == {"skill", "image-skill", "plugin"}


@pytest.mark.parametrize(
    ("target", "expected_relative"),
    [
        ("agents", ".agents/skills/poster-design"),
        ("codex", ".codex/skills/poster-design"),
        ("claude", ".claude/skills/poster-design"),
        ("hermes", ".hermes/skills/creative/poster-design"),
    ],
)
def test_plan_install_uses_target_default_home(tmp_path, monkeypatch, target, expected_relative):
    user_home = tmp_path / "user"
    monkeypatch.setenv("HOME", str(user_home))
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)

    plan = plan_install(target)

    assert Path(plan[0].target) == user_home / expected_relative
    assert not user_home.exists()


@pytest.mark.parametrize(
    ("target", "variable", "relative"),
    [
        ("codex", "CODEX_HOME", "skills/poster-design"),
        ("hermes", "HERMES_HOME", "skills/creative/poster-design"),
    ],
)
def test_plan_install_honors_host_home_environment(tmp_path, monkeypatch, target, variable, relative):
    configured_home = tmp_path / "configured"
    monkeypatch.setenv(variable, str(configured_home))

    plan = plan_install(target)

    assert Path(plan[0].target) == configured_home / relative
    assert not configured_home.exists()


def test_apply_install_replaces_only_managed_target_and_restore_recovers_it(tmp_path):
    home = tmp_path / "codex"
    managed = home / "skills/poster-design"
    unrelated = home / "skills/other-skill"
    managed.mkdir(parents=True)
    unrelated.mkdir(parents=True)
    (managed / "local.txt").write_text("before", encoding="utf-8")
    (unrelated / "keep.txt").write_text("unchanged", encoding="utf-8")

    result = apply_install("codex", home)

    assert result["changed"] is True
    assert Path(result["backup"]).is_dir()
    assert not (managed / "local.txt").exists()
    assert (managed / "SKILL.md").is_file()
    assert (unrelated / "keep.txt").read_text(encoding="utf-8") == "unchanged"

    restored = restore_install("codex", home, result["backup"])

    assert restored["restored"] == ["skills/poster-design"]
    assert (managed / "local.txt").read_text(encoding="utf-8") == "before"
    assert (unrelated / "keep.txt").read_text(encoding="utf-8") == "unchanged"


def test_install_excludes_development_dependencies(tmp_path, monkeypatch):
    import hermes_post_design.install as install_module

    resource_root = tmp_path / "resources"
    source = resource_root / "skills/creative/poster-design"
    (source / "templates").mkdir(parents=True)
    (source / "SKILL.md").write_text("canonical skill", encoding="utf-8")
    (source / "templates/brief.md").write_text("canonical template", encoding="utf-8")
    (source / "node_modules/example/index.js").mkdir(parents=True)
    (source / "node_modules/example/index.js/package.json").write_text("{}", encoding="utf-8")
    (source / "__pycache__/install.cpython-313.pyc").mkdir(parents=True)
    (source / "__pycache__/install.cpython-313.pyc/cache.pyc").write_bytes(b"cache")
    (source / ".pytest_cache/state").mkdir(parents=True)
    (source / ".pytest_cache/state/lastfailed").write_text("{}", encoding="utf-8")
    (source / "coverage/html/index.html").mkdir(parents=True)
    (source / "coverage/html/index.html/report.html").write_text("report", encoding="utf-8")
    (source / "artifacts/render.png").mkdir(parents=True)
    (source / "artifacts/render.png/poster.png").write_bytes(b"png")
    (source / "reports/run.log").mkdir(parents=True)
    (source / "reports/run.log/render.log").write_text("log", encoding="utf-8")
    (source / ".env").write_text("SECRET=not-packaged", encoding="utf-8")
    (source / "state/last-install.json").mkdir(parents=True)
    (source / "state/last-install.json/host.json").write_text("state", encoding="utf-8")
    monkeypatch.setattr(install_module, "_resource_root", lambda: resource_root)

    result = apply_install("codex", tmp_path / "codex")
    installed = tmp_path / "codex/skills/poster-design"

    assert result["changed"] is True
    assert (installed / "SKILL.md").is_file()
    assert (installed / "templates/brief.md").is_file()
    assert not any(
        (installed / excluded).exists()
        for excluded in (
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            "coverage",
            "artifacts",
            "reports",
            ".env",
            "state",
        )
    )
    assert plan_install("codex", tmp_path / "codex")[0].action == "unchanged"


def test_apply_install_rolls_back_replacements_when_a_switch_fails(tmp_path, monkeypatch):
    import hermes_post_design.install as install_module

    home = tmp_path / "hermes"
    originals = {}
    for relative in (
        "plugins/image_gen/chiyi",
        "skills/media/chiyi-image-generation",
        "skills/creative/poster-design",
    ):
        target = home.joinpath(*relative.split("/"))
        target.mkdir(parents=True)
        marker = target / "local.txt"
        marker.write_text(relative, encoding="utf-8")
        originals[relative] = marker

    real_replace = install_module.os.replace
    calls = 0

    def fail_second(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        return real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_second)

    with pytest.raises(OSError, match="injected replace failure"):
        apply_install("hermes", home)

    for relative, marker in originals.items():
        assert marker.read_text(encoding="utf-8") == relative


def test_apply_install_rejects_backup_parent_symlink_that_escapes_home(tmp_path):
    home = tmp_path / "codex"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    try:
        (home / "backups").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="escapes Codex home"):
        apply_install("codex", home)

    assert not list(outside.iterdir())


def test_parent_symlink_cannot_redirect_managed_targets(tmp_path):
    home = tmp_path / "codex"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    try:
        (home / "skills").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="escapes"):
        plan_install("codex", home)
    assert not list(outside.iterdir())


def test_unknown_target_is_rejected_without_creating_home(tmp_path):
    home = tmp_path / "uncreated-home"

    with pytest.raises(ValueError, match="Unsupported install target"):
        plan_install("unknown", home)

    assert not home.exists()


def test_restore_install_rejects_backup_path_through_escaping_intermediate_symlink(tmp_path):
    import json

    home = tmp_path / "codex"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    (home / "backups").mkdir()
    try:
        (home / "backups/hermes-post-design").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")
    backup = home / "backups/hermes-post-design/escaped"
    backup.mkdir(parents=True)
    (backup / "manifest.json").write_text(
        json.dumps({"version": 2, "target": "codex", "targets": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes|Backup must be under"):
        restore_install("codex", home, backup)


@pytest.mark.parametrize("target", ["agents", "codex", "claude"])
def test_restore_install_rejects_targetless_manifest_for_non_hermes_targets(tmp_path, target):
    import json

    home = tmp_path / target
    backup = home / "backups/hermes-post-design/legacy"
    backup.mkdir(parents=True)
    (backup / "manifest.json").write_text(json.dumps({"version": 1, "targets": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="target"):
        restore_install(target, home, backup)


def test_restore_install_accepts_targetless_legacy_manifest_for_hermes(tmp_path):
    import json

    home = tmp_path / "hermes"
    backup = home / "backups/hermes-post-design/legacy"
    backup.mkdir(parents=True)
    (backup / "manifest.json").write_text(json.dumps({"version": 1, "targets": []}), encoding="utf-8")

    assert restore_install("hermes", home, backup)["restored"] == []
