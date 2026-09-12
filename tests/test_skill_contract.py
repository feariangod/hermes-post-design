import re
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


def _contains_unconditional_image_generate_instruction(body: str) -> bool:
    for sentence in re.split(r"(?<=[.!?])\s+", body):
        if "image_generate" not in sentence:
            continue
        if not re.search(
            r"(?:after|with|once|when) explicit authorization",
            sentence,
            re.IGNORECASE,
        ):
            return True
    return False


@pytest.fixture
def skill_root() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "src/hermes_post_design/resources/skills/creative/poster-design"
    )


@pytest.fixture
def operator_guide() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/guide.md").read_text(
        encoding="utf-8"
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
        route_lines = [
            line
            for line in body.splitlines()
            if f"references/{reference.name}" in line
        ]
        assert route_lines
        assert any(
            re.search(r"\bread\b", line, re.IGNORECASE)
            and re.search(r"\b(before|when)\b", line, re.IGNORECASE)
            for line in route_lines
        )


def test_entrypoint_does_not_unconditionally_call_an_image_tool(skill_root):
    body = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    assert not _contains_unconditional_image_generate_instruction(body)
    assert not _contains_unconditional_image_generate_instruction(
        "After explicit authorization, call `image_generate` once."
    )
    assert _contains_unconditional_image_generate_instruction(
        "Call `image_generate` once."
    )


def test_host_adapter_maps_each_supported_and_unknown_host(skill_root):
    adapter = (skill_root / "references/host-adapters.md").read_text(encoding="utf-8")
    for heading in (
        "## Codex adapter",
        "## Hermes adapter",
        "## Claude or MCP adapter",
        "## Unknown-host adapter",
    ):
        assert heading in adapter
    assert "Codex image generation capability" in adapter
    assert "Hermes `image_generate`" in adapter
    assert "Claude or MCP image capability" in adapter
    assert "deterministic local route" in adapter


def test_provider_commands_are_confined_to_host_adapter_reference(skill_root):
    references = skill_root / "references"
    for path in references.glob("*.md"):
        if path.name == "host-adapters.md":
            continue
        body = path.read_text(encoding="utf-8")
        assert "vision_analyze" not in body, path.name
        assert "image_generate" not in body, path.name
        assert "Chiyi uses" not in body, path.name
        assert "quality=high" not in body, path.name


def test_asset_policy_requires_structured_release_manifest(skill_root):
    body = (skill_root / "references/asset-policy.md").read_text(encoding="utf-8")
    assert "asset-manifest.json" in body
    for field in ("path", "sha256", "source", "creator", "license", "authorization", "attribution"):
        assert f"`{field}`" in body


def test_operator_guide_documents_every_portable_install_target(operator_guide):
    homes = {
        "agents": "AGENTS_HOME",
        "codex": "CODEX_HOME",
        "claude": "CLAUDE_HOME",
        "hermes": "HERMES_HOME",
    }
    for target, home in homes.items():
        assert f"hermes-post-design install-skill --target {target}" in operator_guide
        dry_run = (
            f"hermes-post-design install-skill --target {target} "
            f'--home "${home}"'
        )
        apply = f"{dry_run} --apply"
        assert dry_run in operator_guide
        assert apply in operator_guide
        assert operator_guide.index(dry_run) < operator_guide.index(apply)


def test_operator_guide_documents_portable_local_runtime(operator_guide):
    assert "python3 -m venv .venv" in operator_guide
    assert "./.venv/bin/python -m pip install -e \".[test]\"" in operator_guide
    assert "npm ci --prefix src/hermes_post_design/resources/skills/creative/poster-design" in operator_guide
    assert "host-adapters.md" in operator_guide
    assert "deterministic local" in operator_guide.lower()


def test_operator_guide_documents_external_call_and_secret_boundaries(operator_guide):
    assert "Before any billed or external image call" in operator_guide
    assert "explicit authorization" in operator_guide
    assert "Credentials must stay outside the repository" in operator_guide
