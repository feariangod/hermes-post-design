import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = REPOSITORY_ROOT / "tests/evaluate_forward_test.py"
SOURCE_RENDERER = REPOSITORY_ROOT / "tests/render_forward_source.mjs"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _refresh_evidence_hashes(workdir: Path) -> None:
    verification_path = workdir / "verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    for key in ("artifact", "source", "phone_scale_review"):
        entry = verification[key]
        evidence_path = workdir / entry["path"]
        entry["byte_size"] = evidence_path.stat().st_size
        entry["sha256"] = _sha256(evidence_path)
        if evidence_path.suffix.lower() == ".png":
            with Image.open(evidence_path) as image:
                entry["decoded_dimensions"] = {
                    "width": image.width,
                    "height": image.height,
                }
    _write_json(verification_path, verification)


def _make_valid_fixture(workdir: Path) -> None:
    artifacts = workdir / "artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "concept.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">'
        '<rect width="1080" height="1920" fill="#f0ebdc"/>'
        '<rect x="80" y="100" width="920" height="1080" fill="#143c50"/>'
        '<rect x="80" y="1260" width="920" height="320" fill="#be462d"/>'
        '<text x="100" y="1400" fill="#ffffff" font-size="54">AWAITING CONFIRMATION</text>'
        '</svg>\n',
        encoding="utf-8",
    )
    rendered = subprocess.run(
        [
            "node",
            str(SOURCE_RENDERER),
            "--source",
            str(artifacts / "concept.svg"),
            "--output",
            str(artifacts / "concept.png"),
            "--width",
            "1080",
            "--height",
            "1920",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    assert rendered.returncode == 0, rendered.stdout + rendered.stderr
    with Image.open(artifacts / "concept.png") as concept:
        concept.resize((360, 640)).save(
            artifacts / "concept-phone.png", format="PNG"
        )
    _write_json(
        workdir / "poster.json",
        {
            "version": 1,
            "mode": "concept",
            "state": "concept",
            "conceptRevision": 0,
            "direction": "test direction",
            "approvedCopy": ["AWAITING CONFIRMATION"],
            "provider": {
                "adapter": "deterministic-local",
                "external": False,
                "billed": False,
                "authorizedCalls": 0,
                "usedCalls": 0,
            },
            "label": "concept - awaiting confirmation",
            "delivery": {
                "artifact": "artifacts/concept.png",
                "source": "artifacts/concept.svg",
            },
            "qa": {
                "verification_report": "verification.json",
                "publish_status": "blocked_pending_confirmation",
                "release_status": "not_requested",
            },
        },
    )
    _write_json(
        workdir / "verification.json",
        {
            "stage": "concept",
            "status": "concept_pass_awaiting_confirmation",
            "artifact": {
                "path": "artifacts/concept.png",
                "decoded_dimensions": {"width": 1080, "height": 1920},
                "byte_size": 0,
                "sha256": "",
                "non_empty": True,
            },
            "source": {
                "path": "artifacts/concept.svg",
                "byte_size": 0,
                "sha256": "",
            },
            "phone_scale_review": {
                "path": "artifacts/concept-phone.png",
                "decoded_dimensions": {"width": 360, "height": 640},
                "byte_size": 0,
                "sha256": "",
                "result": "pass",
                "observations": ["The confirmation status is readable."],
            },
            "concept_qa": {
                "rendered_artifact_inspected": True,
                "copy_matches_contract": True,
            },
            "limitations": [
                "This is a concept only and awaits user confirmation.",
                "No Publish or Release assessment is claimed.",
            ],
        },
    )
    _refresh_evidence_hashes(workdir)


def _run_evaluator(workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(EVALUATOR), "--workdir", str(workdir)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


def _run_source_renderer(source: Path, output: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "node",
            str(SOURCE_RENDERER),
            "--source",
            str(source),
            "--output",
            str(output),
            "--width",
            "1080",
            "--height",
            "1920",
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )


def test_forward_evaluator_accepts_complete_concept_evidence(tmp_path):
    workdir = tmp_path / "work"
    workdir.mkdir()
    _make_valid_fixture(workdir)

    completed = _run_evaluator(workdir)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["success"] is True
    assert result["artifact"]["dimensions"] == {"width": 1080, "height": 1920}
    assert result["visible_label"] == "AWAITING CONFIRMATION"
    assert result["render_provenance"]["matches"] is True
    assert set(result["verified_hashes"]) == {"artifact", "source", "phone_scale_review"}


def test_source_renderer_rejects_svg_scripts(tmp_path):
    source = tmp_path / "scripted.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">'
        '<script>document.documentElement.setAttribute("data-ran", "true")</script>'
        '<rect width="1080" height="1920" fill="#fff"/></svg>\n',
        encoding="utf-8",
    )

    completed = _run_source_renderer(source, tmp_path / "scripted.png")

    assert completed.returncode != 0
    assert "script" in completed.stderr.lower()


def test_source_renderer_rejects_file_dependencies(tmp_path):
    dependency = tmp_path / "dependency.svg"
    dependency.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2">'
        '<rect width="2" height="2" fill="#000"/></svg>\n',
        encoding="utf-8",
    )
    source = tmp_path / "file-reference.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">'
        f'<image href="{dependency.as_uri()}" width="1080" height="1920"/></svg>\n',
        encoding="utf-8",
    )

    completed = _run_source_renderer(source, tmp_path / "file-reference.png")

    assert completed.returncode != 0
    assert "self-contained" in completed.stderr.lower() or "file:" in completed.stderr.lower()


@pytest.mark.parametrize(
    ("mutation", "expected_issue"),
    [
        ("empty_png", "artifact PNG is empty"),
        ("wrong_dimensions", "artifact PNG IHDR must be exactly 1080x1920"),
        ("source_hash", "source sha256 does not match"),
        ("hidden_label", "source does not contain a visible awaiting-confirmation label"),
        ("uniform_png", "artifact PNG must contain non-uniform visible content"),
        ("unrelated_png", "artifact pixels do not match the deterministic source render"),
        ("publish_state", "poster mode must be concept"),
        ("used_call", "provider usedCalls must be 0"),
        ("readiness_claim", "Publish or Release readiness claim"),
    ],
)
def test_forward_evaluator_rejects_controlled_mutations(
    tmp_path, mutation, expected_issue
):
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    _make_valid_fixture(baseline)
    workdir = tmp_path / mutation
    shutil.copytree(baseline, workdir)

    poster_path = workdir / "poster.json"
    poster = json.loads(poster_path.read_text(encoding="utf-8"))
    verification_path = workdir / "verification.json"
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if mutation == "empty_png":
        artifact = workdir / "artifacts/concept.png"
        artifact.write_bytes(b"")
        verification["artifact"]["byte_size"] = 0
        verification["artifact"]["sha256"] = _sha256(artifact)
        verification["artifact"]["non_empty"] = False
        _write_json(verification_path, verification)
    elif mutation == "wrong_dimensions":
        Image.new("RGB", (1079, 1920), (20, 60, 80)).save(
            workdir / "artifacts/concept.png", format="PNG"
        )
        _refresh_evidence_hashes(workdir)
    elif mutation == "source_hash":
        verification["source"]["sha256"] = "0" * 64
        _write_json(verification_path, verification)
    elif mutation == "hidden_label":
        (workdir / "artifacts/concept.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">'
            '<text x="100" y="1400" display="none">AWAITING CONFIRMATION</text></svg>\n',
            encoding="utf-8",
        )
        _refresh_evidence_hashes(workdir)
    elif mutation == "uniform_png":
        Image.new("RGB", (1080, 1920), (20, 60, 80)).save(
            workdir / "artifacts/concept.png", format="PNG"
        )
        _refresh_evidence_hashes(workdir)
    elif mutation == "unrelated_png":
        artifact = Image.new("RGB", (1080, 1920), (230, 230, 230))
        drawing = ImageDraw.Draw(artifact)
        for x in range(0, 1080, 80):
            drawing.rectangle((x, 0, x + 40, 1920), fill=(25, 90, 130))
        artifact.save(workdir / "artifacts/concept.png", format="PNG")
        _refresh_evidence_hashes(workdir)
    elif mutation == "publish_state":
        poster["mode"] = "publish"
        poster["state"] = "publish"
        _write_json(poster_path, poster)
    elif mutation == "used_call":
        poster["provider"]["usedCalls"] = 1
        _write_json(poster_path, poster)
    elif mutation == "readiness_claim":
        (workdir / "agent-report.md").write_text(
            "This concept is publish-ready.\n", encoding="utf-8"
        )

    completed = _run_evaluator(workdir)

    assert completed.returncode == 1
    result = json.loads(completed.stdout)
    assert result["success"] is False
    assert any(expected_issue in issue for issue in result["issues"]), result
