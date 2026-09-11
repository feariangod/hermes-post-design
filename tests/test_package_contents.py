import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

from hermes_post_design.install import _should_include_resource


FORBIDDEN_PARTS = {
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "coverage",
    "artifacts",
    "cache",
    "sessions",
}
FORBIDDEN_NAMES = {"auth.json", "config.yaml", "qa-report.json", "render-result.json", "visual-review.json"}
FORBIDDEN_SUFFIXES = (".db", ".log", ".pdf", ".png", ".sqlite", ".sqlite3")


def assert_clean_entries(names):
    for name in names:
        entry_parts = Path(name).parts
        parts = set(entry_parts)
        assert not parts & FORBIDDEN_PARTS, name
        if "resources" in entry_parts:
            relative_parts = entry_parts[entry_parts.index("resources") + 1:]
            assert not any(part.endswith((".dist-info", ".egg-info")) for part in relative_parts), name
            assert Path(name).name.lower() not in FORBIDDEN_NAMES, name
            assert not name.lower().endswith(FORBIDDEN_SUFFIXES), name
            assert _should_include_resource(relative_parts), name


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_clean_project(destination: Path) -> Path:
    shutil.copytree(
        _project_root(),
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            "*.egg-info",
            "build",
            "dist",
            "node_modules",
        ),
    )
    return destination


def _build_wheel(project: Path, output: Path) -> tuple[tuple[str, ...], dict[str, str]]:
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(output)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(output.glob("*.whl"))
    with ZipFile(wheel) as archive:
        names = tuple(sorted(archive.namelist()))
        resource_hashes = {
            name: sha256(archive.read(name)).hexdigest()
            for name in names
            if "resources" in Path(name).parts and not name.endswith("/")
        }
    return names, resource_hashes


def test_wheel_excludes_polluted_resource_tree(tmp_path):
    clean_project = _copy_clean_project(tmp_path / "clean-project")
    clean_entries, clean_resource_hashes = _build_wheel(clean_project, tmp_path / "clean-wheel")

    polluted_project = _copy_clean_project(tmp_path / "polluted-project")
    poster = polluted_project / "src/hermes_post_design/resources/skills/creative/poster-design"
    for relative in (
        "node_modules/example/index.js",
        "__pycache__/install.cpython-313.pyc",
        ".pytest_cache/v/cache/lastfailed",
        "coverage/html/index.html",
        "artifacts/render.png",
        "reports/render.log",
        ".env",
        "state/last-install.json",
        "metadata/hermes_post_design.egg-info/PKG-INFO",
        "metadata/hermes_post_design-0.1.0.dist-info/METADATA",
        "artifacts/render-result.json",
        "reports/qa-report.json",
        "reports/visual-review.json",
        "config.yaml",
        "auth.json",
        "sessions/current.json",
        "cache/result.json",
        "state/runtime.db",
        "state/runtime.sqlite3",
    ):
        path = poster / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    stale_sources = polluted_project / "src/hermes_post_design.egg-info/SOURCES.txt"
    stale_sources.parent.mkdir(parents=True, exist_ok=True)
    stale_sources.write_text(
        "\n".join(
            f"src/hermes_post_design/resources/skills/creative/poster-design/{relative}"
            for relative in (
                "node_modules/example/index.js",
                "metadata/hermes_post_design.egg-info/PKG-INFO",
                "metadata/hermes_post_design-0.1.0.dist-info/METADATA",
                "artifacts/render-result.json",
                "reports/qa-report.json",
                "reports/visual-review.json",
                "config.yaml",
                "auth.json",
                "sessions/current.json",
                "cache/result.json",
                "state/runtime.db",
                "state/runtime.sqlite3",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    stale_build_file = (
        polluted_project
        / "build/lib/hermes_post_design/resources/skills/creative/poster-design/node_modules/example/index.js"
    )
    stale_build_file.parent.mkdir(parents=True, exist_ok=True)
    stale_build_file.write_text("stale build output", encoding="utf-8")
    stale_skill = polluted_project / "build/lib/hermes_post_design/resources/skills/creative/poster-design/SKILL.md"
    stale_skill.parent.mkdir(parents=True, exist_ok=True)
    stale_skill.write_text("stale skill contents", encoding="utf-8")
    polluted_entries, polluted_resource_hashes = _build_wheel(polluted_project, tmp_path / "polluted-wheel")

    assert_clean_entries(polluted_entries)
    assert polluted_entries == clean_entries
    assert polluted_resource_hashes == clean_resource_hashes
