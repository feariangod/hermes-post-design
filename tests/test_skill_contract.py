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
def readme() -> str:
    return (Path(__file__).resolve().parents[1] / "README.md").read_text(
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


def test_host_adapter_requires_authorization_and_fallback(skill_root):
    adapter = (skill_root / "references/host-adapters.md").read_text(encoding="utf-8")
    assert """authorized compatible image tool -> image-led concept
available but billed/external and not authorized -> request authorization once
declined, missing, or incompatible image tool -> deterministic local concept
ambiguous network failure -> stop; do not retry without fresh authorization""" in adapter
    assert "Ask once for explicit authorization." in adapter
    assert (
        "If authorization is declined, unavailable, or no compatible image capability "
        "exists, continue with the deterministic local route."
    ) in adapter
    assert "Do not retry, fail over to another external capability" in adapter


def test_readme_documents_every_portable_install_target(readme):
    homes = {
        "agents": "AGENTS_HOME",
        "codex": "CODEX_HOME",
        "claude": "CLAUDE_HOME",
        "hermes": "HERMES_HOME",
    }
    for target, home in homes.items():
        assert f"hermes-post-design install-skill --target {target}" in readme
        dry_run = (
            f"hermes-post-design install-skill --target {target} "
            f'--home "${home}"'
        )
        apply = f"{dry_run} --apply"
        assert dry_run in readme
        assert apply in readme
        assert readme.index(dry_run) < readme.index(apply)


def test_readme_documents_portable_local_runtime(readme):
    assert "python3 -m venv .venv" in readme
    assert "./.venv/bin/python -m pip install -e \".[test]\"" in readme
    assert "npm ci --prefix src/hermes_post_design/resources/skills/creative/poster-design" in readme
    assert "host-adapters.md" in readme
    assert "deterministic local" in readme.lower()


def test_readme_documents_external_call_and_secret_boundaries(readme):
    assert "Before any billed or external image call" in readme
    assert "explicit authorization" in readme
    assert "Credentials must stay outside the repository" in readme
