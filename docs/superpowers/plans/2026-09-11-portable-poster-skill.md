# Portable Poster Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the Hermes-specific poster workflow into one standards-compliant, independently testable Agent Skill for Codex, Claude Code, Hermes, and generic `~/.agents/skills` hosts.

**Architecture:** Keep one canonical packaged `poster-design` Skill and place host differences behind a capability-oriented adapter reference and a generic installer module. Preserve the existing Hermes Chiyi adapter as optional functionality, while making deterministic local HTML/CSS composition a complete no-image-tool route. Repair packaging, project portability, font/license verification, browser discovery, and stage contracts before claiming Release readiness.

**Tech Stack:** Python 3.11-3.13, setuptools, pytest, Node.js 22, Node built-in test runner, Playwright, `pdf-lib`, `pngjs`, `jsqr`, Fontsource packages, Agent Skills `SKILL.md` schema.

**Spec:** `docs/superpowers/specs/2026-09-11-portable-poster-skill-design.md`

## Global Constraints

- Support installation targets `agents`, `codex`, `claude`, and `hermes`.
- Installation and migration commands remain dry-run unless `--apply` is present.
- Preserve `sync --hermes-home` as a compatibility wrapper for one release.
- Do not configure credentials, providers, host settings, or unrelated Skills.
- Do not make paid image requests during automated tests or forward tests.
- A user who declines or lacks an image tool must retain a deterministic local poster route.
- Python support remains `>=3.11,<3.14`; Node runtime tests use Node.js 22.
- Generated projects must run after transfer using project-local dependencies and assets.
- Final eligibility must fail when fonts, licenses, placeholders, facts, outputs, or evidence are mechanically invalid.

---

## File Map

**Canonical Skill and references**

- Modify `src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md`: concise standard entrypoint and stage router.
- Create `src/hermes_post_design/resources/skills/creative/poster-design/references/host-adapters.md`: capability detection, billing authorization, and fallback rules.
- Modify existing files under `references/`: remove duplicated entrypoint rules and make cross-links explicit.

**Installation**

- Create `src/hermes_post_design/install.py`: target layouts, planning, transactional application, and restore interface.
- Modify `src/hermes_post_design/sync.py`: Hermes compatibility wrappers over the generic installer.
- Modify `src/hermes_post_design/cli.py`: `install-skill` command and target-aware doctor output.
- Create `tests/test_install.py`; modify `tests/test_sync.py` and `tests/test_cli.py`.

**Portable project runtime**

- Create `scripts/browser-paths.mjs`: cross-platform browser resolution.
- Create `scripts/prepare-project.mjs`: copy pinned fonts/licenses and write their manifest.
- Modify `scripts/init-poster.mjs`, `render-poster.mjs`, `inspect-poster.mjs`, `poster-contract.mjs`, and `sync-runtime.mjs`.
- Create starter `poster.json`, `publish-qa.json`, `font-manifest.json`, and `package-lock.json` resources.
- Modify starter `package.json`, `styles.css`, `licenses.md`, `poster.html`, `brief.json`, and `poster.config.json`.
- Create Node tests under `tests/runtime/` and isolated fixtures under `tests/runtime/fixtures/`.

**Packaging and documentation**

- Modify `pyproject.toml` and create `MANIFEST.in` only if setuptools exclusion requires it.
- Modify `.github/workflows/ci.yml` to test forbidden wheel contents and portable installs.
- Modify `README.md` for generic installation, host capabilities, macOS/Linux development, and migration.

---

### Task 1: Standards-Compliant Portable Skill Core

**Files:**
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md`
- Create: `src/hermes_post_design/resources/skills/creative/poster-design/references/host-adapters.md`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/references/intake.md`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/references/asset-policy.md`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/references/typography.md`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/references/quality-rubric.md`
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Consumes: common Agent Skills frontmatter accepted by `quick_validate.py`.
- Produces: a host-neutral `poster-design` entrypoint and linked `host-adapters.md` contract used by all later tasks.

- [ ] **Step 1: Write failing Skill contract tests**

Create tests that parse the frontmatter, require only supported top-level fields, verify that every reference file is linked from `SKILL.md`, reject unconditional `image_generate` instructions, and require billing plus deterministic fallback language:

```python
def test_skill_frontmatter_uses_common_schema(skill_root):
    metadata = read_frontmatter(skill_root / "SKILL.md")
    assert set(metadata) <= {"name", "description", "license", "metadata", "allowed-tools"}
    assert metadata["name"] == "poster-design"


def test_entrypoint_routes_every_reference(skill_root):
    body = (skill_root / "SKILL.md").read_text(encoding="utf-8")
    for reference in (skill_root / "references").glob("*.md"):
        assert f"references/{reference.name}" in body


def test_host_adapter_requires_authorization_and_fallback(skill_root):
    adapter = (skill_root / "references/host-adapters.md").read_text(encoding="utf-8")
    assert "billed" in adapter
    assert "authorization" in adapter
    assert "deterministic local" in adapter
```

- [ ] **Step 2: Run tests and validator to establish RED**

Run:

```bash
./.venv/bin/python -m pytest tests/test_skill_contract.py -q
python3 /Users/jintiao/.codex/skills/.system/skill-creator/scripts/quick_validate.py src/hermes_post_design/resources/skills/creative/poster-design
```

Expected: tests fail because `host-adapters.md` is absent, reference routing is incomplete, and unsupported frontmatter keys remain; validator reports `author`, `platforms`, and `version`.

- [ ] **Step 3: Write the minimal portable Skill entrypoint**

Use this frontmatter shape:

```yaml
---
name: poster-design
description: Use when creating information-bearing posters for digital sharing, events, campaigns, long-form layouts, or print release packages.
license: MIT
metadata:
  version: 0.4.0
  author: feariangod
  hosts: [agents, codex, claude, hermes]
---
```

Keep only routing, stage definitions, confirmation gates, external-call authorization, and verification truth in `SKILL.md`. Link the six references with explicit read conditions. In `host-adapters.md`, define capability selection in this order:

```text
authorized compatible image tool -> image-led concept
available but billed/external and not authorized -> request authorization once
declined, missing, or incompatible image tool -> deterministic local concept
ambiguous network failure -> stop; do not retry without fresh authorization
```

- [ ] **Step 4: Run contract tests and validator to verify GREEN**

Run the two commands from Step 2. Expected: all tests pass and validator prints `Skill is valid!`.

- [ ] **Step 5: Commit**

```bash
git add tests/test_skill_contract.py src/hermes_post_design/resources/skills/creative/poster-design
git commit -m "feat: make poster skill host neutral"
```

---

### Task 2: Generic Four-Target Installer

**Files:**
- Create: `src/hermes_post_design/install.py`
- Modify: `src/hermes_post_design/sync.py`
- Modify: `src/hermes_post_design/cli.py`
- Create: `tests/test_install.py`
- Modify: `tests/test_sync.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes: canonical packaged resource `skills/creative/poster-design` from Task 1.
- Produces:
  - `InstallTarget = Literal["agents", "codex", "claude", "hermes"]`
  - `plan_install(target: str, home: Path | str | None = None) -> tuple[InstallEntry, ...]`
  - `apply_install(target: str, home: Path | str | None = None) -> dict`
  - `restore_install(target: str, home: Path | str, backup: Path | str) -> dict`
  - compatibility `plan_sync`, `apply_sync`, and `restore_backup` for Hermes.

- [ ] **Step 1: Write failing target-layout and transaction tests**

Cover default and explicit homes, dry-run purity, exact managed paths, replacement backup, restore, parent symlink escape, and target validation:

```python
@pytest.mark.parametrize("target,relative", [
    ("agents", "skills/poster-design"),
    ("codex", "skills/poster-design"),
    ("claude", "skills/poster-design"),
    ("hermes", "skills/creative/poster-design"),
])
def test_plan_install_targets_only_declared_skill(tmp_path, target, relative):
    plan = plan_install(target, tmp_path)
    assert any(Path(entry.target) == tmp_path / relative for entry in plan)
    assert not tmp_path.exists()


def test_hermes_adds_optional_provider_resources(tmp_path):
    plan = plan_install("hermes", tmp_path)
    assert {entry.component for entry in plan} == {"skill", "image-skill", "plugin"}
```

- [ ] **Step 2: Run focused tests to verify RED**

```bash
./.venv/bin/python -m pytest tests/test_install.py tests/test_sync.py tests/test_cli.py -q
```

Expected: import failure for `hermes_post_design.install` and CLI rejection of `install-skill`.

- [ ] **Step 3: Implement the installer module and compatibility wrappers**

Define immutable layouts:

```python
_TARGET_LAYOUTS = {
    "agents": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "codex": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "claude": (("skills/creative/poster-design", "skills/poster-design", "skill"),),
    "hermes": (
        ("skills/creative/poster-design", "skills/creative/poster-design", "skill"),
        ("skills/media/chiyi-image-generation", "skills/media/chiyi-image-generation", "image-skill"),
        ("plugins/image_gen/chiyi", "plugins/image_gen/chiyi", "plugin"),
    ),
}
```

Use one transactional implementation for digest, staging, backup, replace, and restore. Keep `sync.py` as thin Hermes wrappers to avoid breaking existing callers.

- [ ] **Step 4: Add CLI interface**

Add:

```text
hermes-post-design install-skill --target agents|codex|claude|hermes [--home PATH] [--apply] [--json]
```

Default home resolution:

```python
agents -> Path.home() / ".agents"
codex -> Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
claude -> Path.home() / ".claude"
hermes -> Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
```

- [ ] **Step 5: Run focused and compatibility tests**

```bash
./.venv/bin/python -m pytest tests/test_install.py tests/test_sync.py tests/test_cli.py -q
```

Expected: all pass; legacy Hermes sync tests retain their original behavior.

- [ ] **Step 6: Commit**

```bash
git add src/hermes_post_design/install.py src/hermes_post_design/sync.py src/hermes_post_design/cli.py tests/test_install.py tests/test_sync.py tests/test_cli.py
git commit -m "feat: install poster skill across agent hosts"
```

---

### Task 3: Resource Filtering And Reproducible Wheel Contents

**Files:**
- Modify: `src/hermes_post_design/install.py`
- Modify: `pyproject.toml`
- Create: `MANIFEST.in` if the wheel fixture proves setuptools still includes excluded files
- Create: `tests/test_package_contents.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: installer traversal from Task 2.
- Produces: `_should_include_resource(relative_parts: tuple[str, ...]) -> bool` used by digest and copy operations, plus wheel assertions shared by local tests and CI.

- [ ] **Step 1: Write failing resource and wheel tests**

Create a fake dependency tree under the canonical resource during the test and assert it is absent from installed output. Build a wheel into `tmp_path` and inspect its ZIP entries:

```python
FORBIDDEN_PARTS = {"node_modules", "__pycache__", ".pytest_cache", "coverage", "artifacts"}


def assert_clean_entries(names):
    for name in names:
        parts = set(Path(name).parts)
        assert not parts & FORBIDDEN_PARTS
        assert not name.lower().endswith((".png", ".pdf", ".log"))
```

Allow only explicitly declared template media when a later task adds one; do not use a blanket binary extension ban after that point.

- [ ] **Step 2: Run tests to verify RED**

```bash
./.venv/bin/python -m pytest tests/test_package_contents.py tests/test_install.py::test_install_excludes_development_dependencies -q
```

Expected: installed output and wheel contain the current `node_modules` tree.

- [ ] **Step 3: Implement one inclusion predicate**

Apply `_should_include_resource` consistently in tree digest and tree copy so planning and application compare the same filtered content. Configure setuptools `exclude-package-data` for dependency/cache directories; add `MANIFEST.in` recursive exclusions only if the failing wheel test demonstrates it is required.

- [ ] **Step 4: Add CI forbidden-entry verification**

Extend the wheel job to fail on forbidden path parts and unexpected generated media, not merely check that required files exist.

- [ ] **Step 5: Verify clean and locally polluted builds**

```bash
./.venv/bin/python -m pytest tests/test_package_contents.py tests/test_install.py -q
./.venv/bin/python -m pip wheel . --no-deps -w /tmp/poster-skill-wheel-check
```

Expected: tests pass and the wheel contains zero `node_modules` entries even while the source dependency directory exists.

- [ ] **Step 6: Commit**

```bash
git add src/hermes_post_design/install.py pyproject.toml MANIFEST.in tests/test_package_contents.py .github/workflows/ci.yml
git commit -m "fix: exclude development artifacts from poster package"
```

---

### Task 4: Self-Contained Project Contracts, Dependencies, Fonts, And Licenses

**Files:**
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/package.json`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/package-lock.json`
- Create: `src/hermes_post_design/resources/skills/creative/poster-design/scripts/prepare-project.mjs`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/scripts/init-poster.mjs`
- Modify: `src/hermes_post_design/resources/skills/creative/poster-design/scripts/sync-runtime.mjs`
- Create: starter `poster.json`, `publish-qa.json`, `font-manifest.json`, and `package-lock.json`
- Modify: starter `package.json`, `styles.css`, `licenses.md`, `brief.json`, and `poster.config.json`
- Create: `tests/runtime/project-portability.test.mjs`

**Interfaces:**
- Consumes: stage contracts from Task 1.
- Produces:
  - `node scripts/prepare-project.mjs --project PATH`
  - initialized `poster.json` and `publish-qa.json`
  - `assets/fonts/font-manifest.json` entries `{family, file, sha256, licenseFile, samples}`
  - transferable project setup: `npm ci && npm run prepare && npm run render`.

- [ ] **Step 1: Write failing project portability tests**

Use Node's built-in test runner to initialize a temporary project, assert contract files and lockfile exist, run `npm ci` inside the project, run `npm run prepare`, and assert every manifest font/license exists with matching SHA-256. Assert project-local `npm run render -- --browser <known fixture browser or installed browser>` no longer fails with `ERR_MODULE_NOT_FOUND`.

- [ ] **Step 2: Run the Node test to verify RED**

```bash
node --test tests/runtime/project-portability.test.mjs
```

Expected: missing `poster.json`, `publish-qa.json`, lockfile, fonts, and project-local Playwright dependency.

- [ ] **Step 3: Add stage contract templates**

Initialize `poster.json` with:

```json
{
  "version": 1,
  "mode": "publish",
  "state": "intake",
  "conceptRevision": 0,
  "direction": null,
  "approvedCopy": [],
  "provider": {"adapter": "deterministic-local", "external": false, "billed": false, "authorizedCalls": 0, "usedCalls": 0}
}
```

Initialize `publish-qa.json` with explicit `PENDING` values for `size`, `facts`, `identity`, `logo`, `qr`, `mobile`, and `artifacts`; it cannot be interpreted as a pass until every applicable field is updated.

- [ ] **Step 4: Add pinned project setup and font preparation**

Add a starter lockfile consistent with starter `package.json`. `prepare-project.mjs` copies the pinned Fontsource Chinese and Latin WOFF2 assets and package license texts from project-local `node_modules` into `assets/fonts` and `assets/licenses`, then writes actual SHA-256 values to `assets/fonts/font-manifest.json` and updates `licenses.md` from those values.

Change CSS URLs to the files actually produced by `prepare-project.mjs`; do not reference absent TTF files.

- [ ] **Step 5: Synchronize runtime copies and run GREEN tests**

```bash
npm run runtime:sync --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/project-portability.test.mjs
npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design
```

Expected: project portability test and runtime drift check pass.

- [ ] **Step 6: Commit**

```bash
git add src/hermes_post_design/resources/skills/creative/poster-design tests/runtime/project-portability.test.mjs
git commit -m "feat: make poster projects independently runnable"
```

---

### Task 5: Cross-Platform Browser Resolution And Structured Runtime Failures

**Files:**
- Create: `src/hermes_post_design/resources/skills/creative/poster-design/scripts/browser-paths.mjs`
- Modify: `render-poster.mjs`
- Modify: `inspect-poster.mjs`
- Modify: `sync-runtime.mjs`
- Create: `tests/runtime/browser-paths.test.mjs`
- Create: `tests/runtime/structured-failures.test.mjs`

**Interfaces:**
- Consumes: self-contained project from Task 4.
- Produces:
  - `browserCandidates(platform, env) -> {chrome: string[], edge: string[]}`
  - `resolveExecutable(choice, options) -> Promise<string | null>`
  - structured `qa-report.json` on browser, font, navigation, or page-evaluation failure.

- [ ] **Step 1: Write failing browser matrix tests**

Assert candidate lists include:

```text
macOS Chrome: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
macOS Edge: /Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge
Linux Chrome: /usr/bin/google-chrome, /usr/bin/google-chrome-stable
Linux Chromium: /usr/bin/chromium, /usr/bin/chromium-browser
Windows: current Program Files and LOCALAPPDATA paths
```

Inject `access` so the resolver can be tested without depending on the current machine.

- [ ] **Step 2: Write failing structured-error test**

Create a project with a missing font and assert `inspect --strict` exits nonzero but still writes:

```json
{
  "status": "FAIL",
  "release": {"finalEligible": false},
  "blockers": [{"code": "FONT_LOAD_FAILED"}]
}
```

- [ ] **Step 3: Run tests to verify RED**

```bash
node --test tests/runtime/browser-paths.test.mjs tests/runtime/structured-failures.test.mjs
```

Expected: macOS/Linux candidates are absent and font evaluation throws before a report is written.

- [ ] **Step 4: Extract browser resolution and wrap runtime failures**

Import the shared resolver from both renderer and inspector. Convert known font load, navigation, browser launch, and page evaluation errors into blockers and call `writeStartupFailure`; retain nonzero exit status in strict mode.

- [ ] **Step 5: Synchronize copies and verify GREEN**

```bash
npm run runtime:sync --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/browser-paths.test.mjs tests/runtime/structured-failures.test.mjs
```

- [ ] **Step 6: Commit**

```bash
git add src/hermes_post_design/resources/skills/creative/poster-design/scripts src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/scripts tests/runtime
git commit -m "fix: support portable browser and failure handling"
```

---

### Task 6: Truthful Stage And Release Validation

**Files:**
- Modify: `poster-contract.mjs`
- Modify: `inspect-poster.mjs`
- Modify: starter `poster.html`
- Modify: starter `qa-report.md`
- Create: `tests/runtime/release-negative-cases.test.mjs`
- Create: `tests/runtime/stage-contracts.test.mjs`

**Interfaces:**
- Consumes: `poster.json`, `publish-qa.json`, and font manifest from Task 4.
- Produces:
  - `validatePosterState(value) -> string[]`
  - `validatePublishQa(value) -> string[]`
  - `validateFontManifest(project, manifest) -> Promise<Finding[]>`
  - final eligibility derived only after all mechanical and visual evidence checks pass.

- [ ] **Step 1: Write failing stage-contract tests**

Reject invalid state transitions, used calls greater than authorized calls, Publish PASS with a pending field, and external/billed provider records without authorization.

- [ ] **Step 2: Write failing Release negative tests**

Create independent cases for:

- a single system font masquerading as all declared families;
- mismatched font SHA-256;
- missing license file;
- starter copy `PREVIEW` and `Replace this starter content after the brief is approved.`;
- stale output hashes;
- visual declaration whose hashes do not match current outputs.

Each case must exit nonzero and include a specific blocker code such as `FONT_HASH_MISMATCH`, `FONT_LICENSE_MISSING`, `UNRESOLVED_PLACEHOLDER`, or `VISUAL_REVIEW_STALE`.

- [ ] **Step 3: Run tests to verify RED**

```bash
node --test tests/runtime/stage-contracts.test.mjs tests/runtime/release-negative-cases.test.mjs
```

Expected: current inspector incorrectly accepts at least the font substitution, license, and starter-copy cases.

- [ ] **Step 4: Implement deterministic validators**

Validate exact manifest paths, hashes, license files, declared families, glyph samples, state values, authorization counters, and Publish QA status. Mark starter copy with explicit machine-detectable attributes and also include the exact starter phrases in placeholder detection.

Do not treat visual self-declaration as sufficient to override mechanical blockers. Compute `finalEligible` only after the complete blocker list is final.

- [ ] **Step 5: Synchronize runtime and verify all negative cases**

```bash
npm run runtime:sync --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/stage-contracts.test.mjs tests/runtime/release-negative-cases.test.mjs
npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design
```

- [ ] **Step 6: Commit**

```bash
git add src/hermes_post_design/resources/skills/creative/poster-design tests/runtime
git commit -m "fix: make poster release eligibility truthful"
```

---

### Task 7: Documentation, CI Matrix, Full Verification, And Independent Forward Test

**Files:**
- Modify: `README.md`
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/repo-audit.md`
- Test: all Python and Node tests

**Interfaces:**
- Consumes: all previous tasks.
- Produces: documented portable installation/use contract and final verification evidence.

- [ ] **Step 1: Write documentation assertions before editing README**

Extend `tests/test_skill_contract.py` to require README examples for all four targets, macOS/Linux virtual-environment commands, project-local `npm ci`, deterministic fallback, and the paid-call authorization boundary.

- [ ] **Step 2: Run documentation assertions to verify RED**

```bash
./.venv/bin/python -m pytest tests/test_skill_contract.py -q
```

Expected: current Hermes-only README lacks the four-target commands and portable fallback.

- [ ] **Step 3: Update README and CI**

Document:

```text
install-skill --target agents
install-skill --target codex
install-skill --target claude
install-skill --target hermes
```

Show dry-run before `--apply`, project-local dependency preparation, host adapter selection, deterministic fallback, and credentials kept outside the repository. Update `docs/repo-audit.md` to describe current architecture rather than the pre-feature branch baseline.

CI must run Python 3.11-3.13, Node 22 runtime tests, clean/polluted wheel checks, and isolated installer smoke tests for all targets.

- [ ] **Step 4: Run full local verification**

```bash
python3 /Users/jintiao/.codex/skills/.system/skill-creator/scripts/quick_validate.py src/hermes_post_design/resources/skills/creative/poster-design
./.venv/bin/python -m pytest -q -o "addopts="
npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/*.test.mjs
git diff --check
```

Expected: validator and every test command exit zero.

- [ ] **Step 5: Run four isolated installation smoke tests**

For each target, use a fresh temporary home, assert dry-run writes nothing, apply, run the installed Skill validator, compare canonical and installed hashes after filtering, and restore a seeded previous Skill.

- [ ] **Step 6: Run no-image-tool forward test**

Give an independent Agent only this request and the installed Skill path:

```text
Create a 1080x1920 event poster concept without using any external or paid image-generation service. Use only local deterministic resources, leave the result labeled as awaiting confirmation, and report the verification evidence.
```

Require a non-empty exact-size Concept, `poster.json` provider set to `deterministic-local`, zero authorized and used external calls, and no Publish or Release claim.

- [ ] **Step 7: Run authorized-adapter contract test without network**

Use a fake image adapter to verify provider name, external/billed flags, authorized call budget, used-call accounting, artifact handoff, and absence of credentials in state or errors.

- [ ] **Step 8: Commit documentation and final verification changes**

```bash
git add README.md .github/workflows/ci.yml docs/repo-audit.md tests
git commit -m "docs: publish portable poster skill workflow"
```

- [ ] **Step 9: Final repository readback**

```bash
git status --short --branch
git log --oneline --decorate -8
```

Expected: no tracked working-tree changes and a task-by-task commit trail after the plan commit.
