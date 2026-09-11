import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from hermes_post_design.install import _should_include_resource


FORBIDDEN_PARTS = {"node_modules", "__pycache__", ".pytest_cache", "coverage", "artifacts"}
FORBIDDEN_MEDIA_SUFFIXES = (".png", ".pdf", ".log")


def assert_clean_entries(names):
    for name in names:
        entry_parts = Path(name).parts
        parts = set(entry_parts)
        assert not parts & FORBIDDEN_PARTS, name
        assert not name.lower().endswith(FORBIDDEN_MEDIA_SUFFIXES), name
        if "resources" in entry_parts:
            relative_parts = entry_parts[entry_parts.index("resources") + 1:]
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


def _build_wheel(project: Path, output: Path) -> tuple[str, ...]:
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "-w", str(output)],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(output.glob("*.whl"))
    with ZipFile(wheel) as archive:
        return tuple(sorted(archive.namelist()))


def test_wheel_excludes_polluted_resource_tree(tmp_path):
    clean_project = _copy_clean_project(tmp_path / "clean-project")
    clean_entries = _build_wheel(clean_project, tmp_path / "clean-wheel")

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
    ):
        path = poster / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("generated", encoding="utf-8")
    stale_sources = polluted_project / "src/hermes_post_design.egg-info/SOURCES.txt"
    stale_sources.parent.mkdir(parents=True, exist_ok=True)
    stale_sources.write_text(
        "src/hermes_post_design/resources/skills/creative/poster-design/node_modules/example/index.js\n",
        encoding="utf-8",
    )
    stale_build_file = (
        polluted_project
        / "build/lib/hermes_post_design/resources/skills/creative/poster-design/node_modules/example/index.js"
    )
    stale_build_file.parent.mkdir(parents=True, exist_ok=True)
    stale_build_file.write_text("stale build output", encoding="utf-8")
    polluted_entries = _build_wheel(polluted_project, tmp_path / "polluted-wheel")

    assert_clean_entries(polluted_entries)
    assert polluted_entries == clean_entries
