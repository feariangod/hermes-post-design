# Portable Poster Skill Design

## Status

Approved in chat on 2026-09-11 for implementation.

## Objective

Turn the Hermes-specific poster workflow into one standards-compliant Agent Skill that can be installed and used by Codex, Claude Code, Hermes Agent, and hosts that discover skills from `~/.agents/skills`.

The portable Skill must retain the existing concept, publish, and release quality model without assuming that every host exposes Hermes `image_generate` or the Chiyi provider. A user who declines paid image generation, lacks credentials, or uses a host without an image tool must still be able to produce a deterministic HTML/CSS poster and run local release checks.

## Supported Hosts

The first release supports four installation targets:

| Target | Default Skill root | Additional resources |
|---|---|---|
| `agents` | `~/.agents/skills/poster-design` | Standard portable Skill only |
| `codex` | `${CODEX_HOME:-~/.codex}/skills/poster-design` | Standard portable Skill only |
| `claude` | `~/.claude/skills/poster-design` | Standard portable Skill only |
| `hermes` | `${HERMES_HOME:-~/.hermes}/skills/creative/poster-design` | Portable Skill plus the existing optional Chiyi plugin and image-generation Skill |

Installation is a dry run by default. Applying an installation may replace only the declared target paths, after copying existing targets to a timestamped backup below the selected host home.

## Architecture

### Canonical Skill

The packaged resource at `resources/skills/creative/poster-design` remains the canonical implementation distributed by the Python package. Its `SKILL.md` follows the common Agent Skills frontmatter schema:

- required `name` and `description`;
- `license` when applicable;
- version, author, host tags, and related capabilities nested under `metadata`;
- no host-specific unsupported top-level fields.

The entrypoint is reduced to routing and invariants. Detailed intake, provider selection, asset handling, typography, release commands, and QA rules live in linked references.

### Host Adapter Seam

`references/host-adapters.md` defines one capability-oriented interface instead of embedding host command names throughout the workflow:

1. Detect the host and available image-generation capability.
2. Identify whether the provider is local, externally hosted, or billed.
3. Obtain user authorization before the first billed or externally visible call when that authorization is not already explicit in the request.
4. Use the host adapter for image generation or editing.
5. Fall back to deterministic local composition when no compatible tool is available or the user declines the external call.

Adapters document how the interface maps to Codex image generation, Hermes `image_generate`, Claude/MCP image tools, and unknown hosts. The core workflow never requires a particular adapter.

### Deterministic Poster Runtime

The HTML/CSS release runtime remains host-neutral Node.js. An initialized poster project must be independently runnable after transfer:

- it contains a lockfile matching its `package.json`;
- its documented setup command installs project-local dependencies;
- required fonts and license texts are copied into the project or installed deterministically from pinned packages;
- render and inspect commands work from the project directory;
- Chrome, Edge, and Playwright Chromium discovery supports macOS, Linux, and Windows.

### Data Contracts

The canonical template includes machine-readable contracts for every workflow stage:

- `poster.json`: state, mode, revision budget, selected direction, approved copy, provider decision, and authorization record;
- `brief.json`: facts and QR destinations used by release validation;
- `publish-qa.json`: publish-stage size, fact, identity, logo, QR, mobile, artifact, and fix results;
- JSON schemas or deterministic validators for the new contracts.

Concept and Publish remain lighter than Release, but another Agent must be able to resume the project without reconstructing state from chat history.

## Workflow

### Intake And Routing

The Skill first establishes intended use, audience, approved copy, target dimensions, authorized assets, and visual direction. It loads only the references needed for the selected stage.

Before an image call it records:

- selected host adapter and provider;
- whether the call is billed or externally hosted;
- maximum authorized call count;
- whether the user authorized it;
- deterministic fallback when the call is unavailable or declined.

Automatic retries remain forbidden after ambiguous network failures. A new billed attempt requires fresh authorization unless it is already within an explicit authorized call budget.

### Concept

When an image tool is authorized, the Skill may use it for a near-production concept. Without one, it builds the concept with local HTML/CSS and supplied assets. Both routes produce one exact-size concept and require user confirmation before Publish.

### Publish

Publish preserves the confirmed visual direction and produces one directly usable PNG. Critical text, facts, real identities, logos, product packaging, and QR codes use deterministic or authorized source layers. `publish-qa.json` records the observable checks.

### Release

Release creates the complete portable project and runs deterministic render, inspection, visual review recording, and final inspection. Final eligibility requires current output hashes and must not be satisfied by family-name-only font checks or a self-declared visual PASS when mechanically detectable blockers remain.

## Resource And Packaging Rules

Source and package traversal must exclude at least:

- `node_modules`;
- Python caches and editable-install metadata;
- test coverage output;
- generated images, PDFs, reports, logs, and temporary files;
- local credentials, configuration, and host state.

Wheel CI verifies both required resources and forbidden entries. A build performed after local `npm ci` must produce the same resource set as a clean checkout.

## Font And License Verification

The starter project must not reference missing files. Release inspection verifies:

- every declared font path exists inside the project;
- the loaded file hash matches the declaration in a machine-readable manifest;
- the corresponding license file exists;
- declared font families load without system fallback;
- required glyph samples are covered;
- license declarations and files remain bound to the current font artifacts.

The inspector writes a structured failure report even when font loading or browser evaluation throws.

## Installer Interface

The CLI exposes a host-neutral command while preserving the existing Hermes command during migration:

```text
hermes-post-design install-skill --target agents|codex|claude|hermes [--home PATH] [--apply]
```

Behavior:

- without `--apply`, return a read-only plan;
- resolve the target home without following an escaping symlink;
- back up only existing managed paths;
- copy only canonical packaged resources;
- for Hermes, optionally include the Chiyi plugin and related image Skill;
- never modify credentials, provider selection, unrelated Skills, or host configuration;
- return structured JSON when `--json` is used.

The legacy `sync --hermes-home` interface remains as a compatibility wrapper for one release.

## Migration

1. Make the current poster Skill schema-compliant and host-neutral.
2. Add host-adapter and release-runtime references.
3. Add generic installation planning and application while preserving Hermes sync behavior.
4. Repair package filtering, fonts, project dependency portability, browser discovery, and structured failures.
5. Add Concept/Publish data contracts and validators.
6. Update README instructions around the portable workflow and host-specific optional capabilities.

Existing Hermes users retain their current Chiyi provider behavior after installing the new version. No automatic migration writes to a live host home.

## Verification

Implementation is accepted only when all of the following pass from a clean or isolated environment:

1. Official `quick_validate.py` validates the canonical Skill.
2. Python tests pass after Node dependencies have been installed in the source tree.
3. Node runtime checks and dependency audit pass.
4. Wheels contain required resources and no forbidden dependency/cache/media entries.
5. Dry-run and apply tests pass for `agents`, `codex`, `claude`, and `hermes` targets, including backup and restore boundaries.
6. An initialized project installs dependencies and renders from its own directory.
7. macOS, Linux, and Windows browser resolution paths have focused tests.
8. Strict inspection returns structured failures for missing fonts, false license declarations, placeholders, stale outputs, and invalid visual evidence.
9. A no-image-tool forward test reaches a deterministic Concept without an external call.
10. An authorized image-tool scenario records provider and call budget without embedding credentials.
11. An independent Agent completes a realistic isolated poster task using only the Skill and linked resources.

No live Agent home is modified and no paid image request is made during automated verification.

## Out Of Scope

- Supporting every proprietary image provider directly.
- Automatic credential configuration or login.
- Publishing posters to external services.
- Claiming pixel-identical edits across generative providers.
- Replacing the current Chiyi core client or its request security model.
