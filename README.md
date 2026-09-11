# Portable Poster Design Skill

This repository provides a portable `poster-design` Agent Skill, a deterministic local poster runtime, and an optional Chiyi image adapter for Hermes Agent. The common Skill installs into Agents, Codex, Claude, or Hermes without changing host credentials or unrelated configuration.

## Support Boundary

- Python `3.11` to `3.13` for the installer and optional Chiyi client.
- Node.js `22` for the poster project runtime and automated tests.
- Four installer targets: `agents`, `codex`, `claude`, and `hermes`.
- Deterministic local poster concepts are the fallback on every host.
- External or billed image capabilities are optional host adapters and require authorization for each bounded call budget.
- Hermes remains the only target that also installs the optional `chiyi-image-generation` Skill and Chiyi plugin.

The repository does not configure a host, store credentials, publish a poster, or make an image request during installation or tests.

## Prepare The Checkout

On macOS or Linux:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[test]"
npm ci --prefix src/hermes_post_design/resources/skills/creative/poster-design
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[test]"
npm ci --prefix src/hermes_post_design/resources/skills/creative/poster-design
```

Keep `npm ci` project-local. Do not install these dependencies globally or copy the source checkout's `node_modules` into an installed Skill.

## Install The Skill

Choose isolated home variables for the examples below. `AGENTS_HOME` and `CLAUDE_HOME` are shell conveniences passed through `--home`; the installer also understands the native `CODEX_HOME` and `HERMES_HOME` defaults.

```bash
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
```

Always preview first. These dry runs report the managed paths and write nothing:

```bash
hermes-post-design install-skill --target agents --home "$AGENTS_HOME"
hermes-post-design install-skill --target codex --home "$CODEX_HOME"
hermes-post-design install-skill --target claude --home "$CLAUDE_HOME"
hermes-post-design install-skill --target hermes --home "$HERMES_HOME"
```

After reviewing the dry-run output, apply only the selected target:

```bash
hermes-post-design install-skill --target agents --home "$AGENTS_HOME" --apply
hermes-post-design install-skill --target codex --home "$CODEX_HOME" --apply
hermes-post-design install-skill --target claude --home "$CLAUDE_HOME" --apply
hermes-post-design install-skill --target hermes --home "$HERMES_HOME" --apply
```

Without `--home`, the target roots are:

```text
agents -> $HOME/.agents
codex  -> $CODEX_HOME or $HOME/.codex
claude -> $HOME/.claude
hermes -> $HERMES_HOME or $HOME/.hermes
```

The common Skill is installed at `skills/poster-design` for Agents, Codex, and Claude, and at `skills/creative/poster-design` for Hermes. Hermes additionally receives:

```text
skills/media/chiyi-image-generation
plugins/image_gen/chiyi
```

Apply creates a timestamped backup under `<host-home>/backups/hermes-post-design/`. The Python API `restore_install(target, home, backup)` restores exactly the paths recorded by that target-aware backup. The legacy Hermes command remains available:

```bash
hermes-post-design restore --hermes-home "$HERMES_HOME" --backup "$HERMES_HOME/backups/hermes-post-design/<timestamp>"
```

## Select A Host Adapter

Before creating a concept, read the installed Skill's `references/host-adapters.md` and inspect the capabilities actually available in the current host. Use this order:

```text
authorized compatible image tool -> image-led concept
available but billed/external and not authorized -> request authorization once
declined, missing, or incompatible image tool -> deterministic local concept
ambiguous network failure -> stop; do not retry without fresh authorization
```

The deterministic local route is a complete fallback. It uses project-local HTML, CSS, fonts, shapes, gradients, and authorized local assets, then runs the same Concept, Publish, and Release gates as an image-led route.

Before any billed or external image call, name the selected capability, state that the call may be billed or leave the local environment, describe the immediate artifact, and obtain explicit authorization. Authorization for a poster, a visual direction, or an earlier call does not authorize another billed or external call.

Credentials must stay outside the repository. Keep provider keys in the host's secret store or process environment, never in project JSON, logs, errors, command arguments, committed `.env` files, or generated evidence.

## Create A Poster Project

Run the installed Skill through the current host, or initialize the same local runtime directly:

```bash
node "$CODEX_HOME/skills/poster-design/scripts/init-poster.mjs" \
  --output ./poster-project \
  --title "Event poster" \
  --type digital \
  --width 1080 \
  --height 1920
cd poster-project
npm ci
npm run prepare
```

`npm ci` belongs inside each initialized project. It materializes pinned Fontsource packages, Playwright, and inspection dependencies without relying on the source checkout. `npm run prepare` then copies the complete pinned WOFF2 shard sets, their `unicode-range` declarations, and license files into the project. Rendering and inspection make no network calls.

The project starts in `intake` with provider `deterministic-local`, `external=false`, `billed=false`, and zero authorized or used calls. `poster.json` is the sole workflow-stage and approved-copy authority. `brief.json` owns facts and QR destinations; every visible Release string must use `data-copy` or `data-fact`. Record every non-font file below `assets/` in `asset-manifest.json`; the starter's empty manifest is valid when no external assets are used. Update `poster.html`, `styles.css`, and those contracts as the work advances. Then render and inspect:

```bash
npm run render
npm run inspect
```

Concept output must remain labeled as awaiting confirmation. A rendered PNG is not by itself a Publish or Release claim. Publish requires user confirmation plus applicable QA evidence; Release requires the stricter final-state, artifact, source, font, license, and visual-review evidence enforced by `npm run inspect:final`.

The renderer resolves an explicit browser first and otherwise searches normal Chrome, Edge, and Playwright locations on macOS, Linux, and Windows. Install Playwright Chromium only when no compatible local browser is available:

```bash
npx playwright install chromium
```

## Optional Hermes Chiyi Adapter

The Hermes target preserves the existing Chiyi workflow. Store `CHIYI_IMAGE_API_KEY` through the normal Hermes secret/configuration flow, then enable and select the provider with current Hermes controls:

```bash
hermes plugins enable chiyi
hermes tools
hermes-post-design doctor --hermes-home "$HERMES_HOME" --json
```

The provider fixes model `gpt-image-2`, quality `high`, one output image, and exact requested dimensions. The standalone CLI reads the key only from the process environment:

```bash
hermes-post-design generate "A typographic event poster" --size 1080x1920 --output-dir ./artifacts
```

It validates sources and outputs, blocks private or local remote targets, bounds input size and decoded pixels, disables redirects on paid POST requests, retries only one explicit HTTP `429`, and redacts credentials and sensitive payloads from errors.

## Architecture

```text
Agents / Codex / Claude / Hermes
              |
              v
     portable poster-design Skill
              |
      host-adapters.md routing
        /                 \
       v                   v
deterministic local    authorized image adapter
       \                   /
        +--------+---------+
                 v
       project-local runtime
 init -> prepare -> render -> inspect -> evidence
```

The installed Skill carries its templates, runtime scripts, pinned project dependencies, stage contracts, and QA rules. Generated artifacts, dependencies, credentials, host state, and backups are filtered out of the canonical install and Python wheel.

## Development And Verification

Run the repository checks without contacting an image service:

```bash
./.venv/bin/python -m pytest -q -o "addopts="
npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/*.test.mjs
./.venv/bin/python tests/evaluate_forward_test.py --workdir "$FORWARD_TEST_WORKDIR"
git diff --check
```

The forward-test evaluator checks the PNG signature and dimensions, rejects blank or nearly uniform pixels, independently re-renders the deterministic SVG with a trusted local Playwright renderer, requires exact RGBA pixel-hash parity, verifies the visible awaiting-confirmation source label and Concept state, checks deterministic-local provider counters, and rejects positive Publish or Release readiness claims.

CI runs Python `3.11`, `3.12`, and `3.13`; Node `22`; clean and deliberately polluted wheel comparisons; Git-tracked canonical Skill file/hash parity; and isolated install/restore smoke tests for all four host targets. Test adapters and image results are deterministic local fixtures. They do not submit paid or external requests.

## Repository Hygiene

The resource filter and package configuration exclude dependency trees, caches, build output, generated media, reports, host homes, sessions, state databases, backups, configuration, and credentials. External assets, fonts, generated media, model outputs, and user-supplied material retain their own terms and must be recorded in the project evidence when used.

## License

MIT for repository code and templates. Bundled project fonts retain the licenses recorded in their project-local manifests.
