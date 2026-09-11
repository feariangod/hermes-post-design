from pathlib import Path

import pytest


def read_frontmatter(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    _, frontmatter, _ = content.split("---", 2)
    metadata = {}
    current_mapping = None

    for raw_line in frontmatter.strip().splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith("  "):
            key, value = raw_line.strip().split(":", 1)
            metadata[current_mapping][key] = _read_value(value.strip())
            continue

        key, value = raw_line.split(":", 1)
        value = value.strip()
        if value:
            metadata[key] = _read_value(value)
            current_mapping = None
        else:
            metadata[key] = {}
            current_mapping = key

    return metadata


def _read_value(value: str):
    if value.startswith("[") and value.endswith("]"):
        return [item.strip() for item in value[1:-1].split(",") if item.strip()]
    return value.strip('"')


@pytest.fixture
def skill_root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src/hermes_post_design/resources/skills/creative/poster-design"
    )


def test_skill_frontmatter_uses_common_schema(skill_root):
    metadata = read_frontmatter(skill_root / "SKILL.md")
    assert set(metadata) <= {"name", "description", "license", "metadata", "allowed-tools"}
    assert metadata["name"] == "poster-design"
    assert metadata["description"] == (
        "Use when creating information-bearing posters for digital sharing, events, "
        "campaigns, long-form layouts, or print release packages."
    )
    assert metadata["license"] == "MIT"
    assert metadata["metadata"] == {
        "version": "0.4.0",
        "author": "feariangod",
        "hosts": ["agents", "codex", "claude", "hermes"],
    }


def test_entrypoint_routes_every_reference(skill_root):
    body = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    for reference in (skill_root / "references").glob("*.md"):
        assert f"references/{reference.name}" in body


def test_entrypoint_does_not_unconditionally_call_an_image_tool(skill_root):
    body = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    assert "image_generate" not in body


def test_host_adapter_requires_authorization_and_fallback(skill_root):
    adapter = (skill_root / "references/host-adapters.md").read_text(encoding="utf-8")
    assert "billed" in adapter
    assert "authorization" in adapter
    assert "deterministic local" in adapter
