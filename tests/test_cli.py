import json
from pathlib import Path
from unittest.mock import Mock, patch

from hermes_post_design import cli


def test_doctor_json_reports_key_presence_without_value(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHIYI_IMAGE_API_KEY", "doctor-secret-key")
    exit_code = cli.main(["doctor", "--hermes-home", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["key"] == "present"
    assert "doctor-secret-key" not in json.dumps(payload)


def test_sync_defaults_to_dry_run_and_apply_writes(tmp_path, capsys):
    home = tmp_path / "hermes"
    assert cli.main(["sync", "--hermes-home", str(home), "--json"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["dry_run"] is True
    assert not home.exists()

    assert cli.main(["sync", "--hermes-home", str(home), "--apply", "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["changed"] is True
    assert (home / "plugins/image_gen/chiyi/provider.py").is_file()


def test_generate_without_key_is_structured_and_does_not_echo_environment(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("CHIYI_IMAGE_API_KEY", raising=False)
    exit_code = cli.main(["generate", "poster", "--output-dir", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["error"]["type"] == "auth_required"


def test_generate_maps_core_result(monkeypatch, capsys, tmp_path):
    artifact = Mock(path=tmp_path / "image.png", format="png", width=1024, height=1024, sha256="a" * 64, normalized=False)
    result = Mock(success=True, provider="chiyi", model="gpt-image-2", quality="high", requested_size="1024x1024", upstream_size="1024x1024", modality="text", artifact=artifact, error=None)
    client = Mock()
    client.generate.return_value = result
    with patch.object(cli, "_make_client", return_value=client):
        exit_code = cli.main(["generate", "poster", "--output-dir", str(tmp_path), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["artifact"]["path"].endswith("image.png")
