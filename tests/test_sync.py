from pathlib import Path

import pytest

from hermes_post_design.sync import apply_sync, plan_sync, restore_backup


def test_plan_is_read_only_and_lists_three_managed_components(tmp_path):
    home = tmp_path / "hermes"
    before = list(tmp_path.rglob("*"))
    plan = plan_sync(home)
    assert len(plan) == 3
    assert all(item.action == "create" for item in plan)
    assert list(tmp_path.rglob("*")) == before


def test_apply_sync_is_idempotent_and_deploys_resources(tmp_path):
    home = tmp_path / "hermes"
    first = apply_sync(home)
    assert first["changed"] is True
    assert Path(first["backup"]).is_dir()
    assert (home / "plugins/image_gen/chiyi/plugin.yaml").is_file()
    assert (home / "skills/media/chiyi-image-generation/SKILL.md").is_file()
    assert (home / "skills/creative/poster-design/SKILL.md").is_file()

    second = apply_sync(home)
    assert second["changed"] is False
    assert all(item["action"] == "unchanged" for item in second["entries"])


def test_apply_sync_keeps_legacy_last_sync_state_record(tmp_path):
    import json

    home = tmp_path / "hermes"
    result = apply_sync(home)

    state = json.loads((home / "state/hermes-post-design/last-sync.json").read_text(encoding="utf-8"))
    assert state["backup"] == result["backup"]


def test_update_creates_backup_and_restore_recovers_previous_content(tmp_path):
    home = tmp_path / "hermes"
    plugin = home / "plugins/image_gen/chiyi"
    plugin.mkdir(parents=True)
    (plugin / "custom.txt").write_text("local", encoding="utf-8")

    result = apply_sync(home)
    assert result["changed"] is True
    assert not (plugin / "custom.txt").exists()
    restored = restore_backup(home, result["backup"])
    assert "plugins/image_gen/chiyi" in restored["restored"]
    assert (plugin / "custom.txt").read_text(encoding="utf-8") == "local"


def test_apply_failure_rolls_back_all_replaced_targets(tmp_path, monkeypatch):
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
    try:
        apply_sync(home)
    except OSError:
        pass
    else:
        raise AssertionError("replace failure should propagate")

    for relative, marker in originals.items():
        assert marker.read_text(encoding="utf-8") == relative


def test_restore_validates_every_backup_before_touching_current_install(tmp_path):
    import json

    home = tmp_path / "hermes"
    current = home / "plugins/image_gen/chiyi"
    current.mkdir(parents=True)
    marker = current / "current.txt"
    marker.write_text("keep", encoding="utf-8")
    backup = home / "backups/hermes-post-design/broken"
    backup.mkdir(parents=True)
    (backup / "manifest.json").write_text(
        json.dumps({
            "targets": [
                {"relative": "plugins/image_gen/chiyi", "existed": True},
                {"relative": "skills/media/chiyi-image-generation", "existed": True},
            ]
        }),
        encoding="utf-8",
    )
    first_source = backup / "files/plugins/image_gen/chiyi"
    first_source.mkdir(parents=True)
    (first_source / "old.txt").write_text("old", encoding="utf-8")

    try:
        restore_backup(home, backup)
    except ValueError as exc:
        assert "incomplete" in str(exc)
    else:
        raise AssertionError("incomplete backup should be rejected")
    assert marker.read_text(encoding="utf-8") == "keep"


def test_parent_symlink_cannot_redirect_managed_targets(tmp_path):
    home = tmp_path / "hermes"
    outside = tmp_path / "outside"
    home.mkdir()
    outside.mkdir()
    try:
        (home / "skills").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this platform")

    with pytest.raises(ValueError, match="escapes Hermes home"):
        plan_sync(home)
    assert not list(outside.iterdir())


def test_restore_failure_rolls_back_restore_transaction(tmp_path, monkeypatch):
    import hermes_post_design.install as install_module

    home = tmp_path / "hermes"
    current_values = {}
    for relative in (
        "plugins/image_gen/chiyi",
        "skills/media/chiyi-image-generation",
    ):
        target = home.joinpath(*relative.split("/"))
        target.mkdir(parents=True)
        marker = target / "current.txt"
        marker.write_text(f"current:{relative}", encoding="utf-8")
        current_values[relative] = marker

    applied = apply_sync(home)
    backup = Path(applied["backup"])
    for relative in current_values:
        target = home.joinpath(*relative.split("/"))
        marker = target / "after-sync.txt"
        marker.write_text(f"after:{relative}", encoding="utf-8")
        current_values[relative] = marker

    real_replace = install_module.os.replace
    calls = 0

    def fail_fourth(source, target):
        nonlocal calls
        calls += 1
        if calls == 4:
            raise OSError("injected restore failure")
        return real_replace(source, target)

    monkeypatch.setattr(install_module.os, "replace", fail_fourth)
    with pytest.raises(OSError, match="injected restore failure"):
        restore_backup(home, backup)

    for relative, marker in current_values.items():
        assert marker.read_text(encoding="utf-8") == f"after:{relative}"


def test_restore_refuses_backup_outside_application_backup_root(tmp_path):
    home = tmp_path / "hermes"
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        restore_backup(home, outside)
    except ValueError as exc:
        assert "application backup" in str(exc)
    else:
        raise AssertionError("outside backup should be rejected")
