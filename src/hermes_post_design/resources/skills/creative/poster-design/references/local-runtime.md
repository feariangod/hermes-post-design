# Local Poster Runtime

Use this guide when working from an installed Skill; the source repository and Python installer are not required. Read the stage-specific [quality rubric](quality-rubric.md) before claiming a delivery result.

## Resolve The Project

Resolve `SKILL_ROOT` to the absolute directory containing the loaded `SKILL.md`, regardless of host. Choose an absolute `PROJECT_DIR` outside the installed Skill. For an existing project, inspect its contracts and current artifacts and resume there; do not reinitialize or overwrite it.

The runtime needs Node.js 22, npm, and a compatible local Chromium browser. Keep dependencies project-local. Initial dependency or browser installation may download packages; rendering and inspection use local resources and make no image-service calls. Do not install globally, copy `node_modules` from the Skill, or request image credentials for this route.

The following examples use Bash on macOS/Linux. Set `SKILL_ROOT` and `PROJECT_DIR` to the resolved paths first; replace the example title and dimensions with the brief's values. On PowerShell, assign those variables with `$SKILL_ROOT = "..."` and `$PROJECT_DIR = "..."` and run each command on one line instead of using Bash's `\` continuations. No host-specific home path is required.

## Initialize And Prepare

For a new project only:

```bash
node "$SKILL_ROOT/scripts/init-poster.mjs" \
  --output "$PROJECT_DIR" --title "Event poster" \
  --type digital --width 1080 --height 1440
npm --prefix "$PROJECT_DIR" ci
npm --prefix "$PROJECT_DIR" run prepare
```

`--type` also accepts `long-form`, `a1-landscape`, `a1-portrait`, `a0-landscape`, and `a0-portrait`. Long-form uses `--height` as its minimum height; print presets set physical dimensions. Choose the type from the requested delivery, not from the example.

`npm ci` already runs the starter's `prepare` lifecycle. The explicit prepare command is safe to repeat and is required after changing font roles. It materializes selected pinned fonts and licenses, or validates evidenced project-local custom fonts, as described in [typography.md](typography.md).

The renderer discovers normal Chrome, Edge, and Playwright installations. Only when none is available, install the project's pinned Playwright Chromium from inside the initialized project:

```bash
cd "$PROJECT_DIR"
npx --no-install playwright install chromium
```

## Compose And Record State

The starter is an intake scaffold, not a finished poster. It has no selected direction or approved copy yet. Replace its sample content and set the real contracts before expecting QA to pass:

- `poster.json`: workflow mode/state, selected creative proposition, approved copy, design agreement, approval scope, and provider authorization/usage. Preserve pending user confirmation; local production uses `deterministic-local` with zero image calls.
- `brief.json`: approved facts and QR destinations. Unknown facts stay unresolved or explicitly omitted under [intake.md](intake.md); do not invent them to make a check pass.
- `poster.config.json`: canvas, output files, and viewing thresholds.
- `poster.html` and `styles.css`: the actual composition. Bind Release text with `data-copy` or `data-fact`; image `alt` or hidden alternatives cannot replace visible text.
- `font-config.json`: selected font roles and any authorized custom font evidence. Run prepare again after changes.
- `asset-manifest.json`: source, license, and hash records for every non-font file under `assets/`. An empty manifest is valid only when there are no such assets.
- `design-directions.md` and `qa-report.md`: rationale and observed review findings, not competing sources of workflow state.

## Render And Inspect

```bash
npm --prefix "$PROJECT_DIR" run render
npm --prefix "$PROJECT_DIR" run inspect
```

Read `render-result.json` and `qa-report.json`, including blockers, instead of relying only on exit status. Open the target and phone-scale PNGs and any additional declared crop or physical-viewing context. Record creative and technical findings separately in `qa-report.md`; correct the highest-impact problems and render again. Default output names are `poster.png`, `poster-mobile.png`, and `poster.pdf`; use the names in the project's config when customized.

Label Concept output as awaiting confirmation. A generated file or technical PASS is not permission to advance to Publish or Release. Publish needs the actual scoped approval and applicable `publish-qa.json` evidence. Strict Release additionally requires the visible-text, font, asset, source, output, and review contracts; verified image-only lettering may still block that stage.

## Record Release Evidence

Only after the requested Release contracts are complete and the final source has been rendered:

1. Inspect the exact target and mobile artifacts plus the declared delivery contexts. Record actual observations for hierarchy, composition, typography, coherence, artifacts, and mobile. Missing visual capability or a failed check stays unverified/failed; never fabricate an all-PASS review.
2. When all six checks genuinely pass, set `REVIEWER` to the actual reviewer identity and `REVIEW_NOTES` to concrete observations, then record the review:

```bash
npm --prefix "$PROJECT_DIR" run visual:record -- \
  --reviewer "$REVIEWER" \
  --hierarchy PASS --composition PASS --typography PASS \
  --coherence PASS --artifacts PASS --mobile PASS \
  --notes "$REVIEW_NOTES"
```

3. Complete `qa-report.md` with the current target/mobile SHA-256 values from the render/review evidence and the actual creative verdict. Verify that `poster.json` mode/state and Publish evidence meet the [Release gates](quality-rubric.md#release-gates), then run:

```bash
npm --prefix "$PROJECT_DIR" run inspect:final
```

Read `qa-report.json` again. Claim final Release only when final eligibility is true and no blocker or unverified required review remains. A source change or re-render invalidates prior Release evidence; repeat rendering, inspection, and review as needed. Do not alter contracts, hashes, or stage labels just to obtain PASS.

## Handoff

Hand off the project-local source, contracts, licensed assets, scripts, lockfile, outputs, and applicable evidence together, with the actual stage and outstanding checks. Exclude `node_modules`, caches, host configuration, and credentials. On another machine, install project dependencies with `npm ci`, prepare fonts, locate/install a compatible browser, and render and inspect again. Prior-machine review evidence does not establish that new outputs were reviewed.
