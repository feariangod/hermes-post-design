# Task 5 Report: Cross-Platform Browser Resolution And Structured Runtime Failures

## Scope

- Added one shared browser resolver used by both `render-poster.mjs` and `inspect-poster.mjs`.
- Added platform candidate matrices for standard Chrome/Edge installations on macOS, Linux, and Windows.
- Preserved the existing project-local Playwright fallback: when no system candidate is accessible, `resolveExecutable()` returns `null` and `chromium.launch()` uses the Playwright browser available to the transferred project.
- Made strict inspection runtime failures write a structured `qa-report.json` before returning a nonzero exit status.
- Did not access live Agent homes, invoke paid providers, or make external API calls. Test project dependency installs used `npm ci --ignore-scripts --offline`.

## RED

Command run before implementation:

```bash
node --test tests/runtime/browser-paths.test.mjs tests/runtime/structured-failures.test.mjs
```

Exit status: `1`

Relevant output:

```text
Error [ERR_MODULE_NOT_FOUND]: Cannot find module '.../scripts/browser-paths.mjs'
Subtest: tests/runtime/browser-paths.test.mjs
not ok 1 - tests/runtime/browser-paths.test.mjs
```

The same first red run also showed that the failure fixture needed its own project-local dependencies before it could execute `prepare-project.mjs`:

```text
ENOENT: no such file or directory, copyfile '.../node_modules/@fontsource/ma-shan-zheng/...'
```

The test fixture was corrected to run `npm ci --ignore-scripts --offline` inside the temporary generated project. The missing resolver remained the behavioral red condition until implementation.

## GREEN

First focused green verification:

```bash
npm run runtime:sync --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/browser-paths.test.mjs tests/runtime/structured-failures.test.mjs
```

Output:

```text
{"success":true,"mode":"sync","updated":["templates/poster-starter/scripts/browser-paths.mjs","templates/poster-starter/scripts/render-poster.mjs","templates/poster-starter/scripts/inspect-poster.mjs"]}
tests 4
pass 4
fail 0
```

Final verification:

```bash
npm run runtime:sync --prefix src/hermes_post_design/resources/skills/creative/poster-design
npm run runtime:check --prefix src/hermes_post_design/resources/skills/creative/poster-design
node --test tests/runtime/browser-paths.test.mjs tests/runtime/structured-failures.test.mjs tests/runtime/project-portability.test.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/scripts/browser-paths.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/scripts/render-poster.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/scripts/inspect-poster.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/scripts/browser-paths.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/scripts/render-poster.mjs
node --check src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/scripts/inspect-poster.mjs
git diff --check
```

Relevant output:

```text
{"success":true,"mode":"sync","updated":[]}
{"success":true,"mode":"check","updated":[]}
tests 6
pass 6
fail 0
```

The no-argument transferred-project regression test passed `npm run render` without `--browser`.

## Files

- Added `src/hermes_post_design/resources/skills/creative/poster-design/scripts/browser-paths.mjs`.
- Added the synchronized starter copy at `src/hermes_post_design/resources/skills/creative/poster-design/templates/poster-starter/scripts/browser-paths.mjs`.
- Updated canonical and starter `render-poster.mjs` and `inspect-poster.mjs` to import the shared resolver.
- Updated `sync-runtime.mjs` and `init-poster.mjs` so generated projects receive the new runtime module.
- Added `tests/runtime/browser-paths.test.mjs` and `tests/runtime/structured-failures.test.mjs`.
- Updated `tests/runtime/project-portability.test.mjs` to render with ordinary no-argument flow.

## Behavior

`browserCandidates(platform, env)` includes these required candidates:

- macOS: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` and `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge`.
- Linux: `/usr/bin/google-chrome`, `/usr/bin/google-chrome-stable`, `/usr/bin/chromium`, and `/usr/bin/chromium-browser`.
- Windows: injected `ProgramFiles`, `ProgramFiles(x86)`, and `LOCALAPPDATA` paths for both Chrome and Edge, with standard `C:\\Program Files` fallbacks.

`resolveExecutable(choice, options)` accepts injected `platform`, `env`, and `access`, so the matrix tests do not depend on this macOS machine.

For inspection startup failures, the report now uses explicit blocker codes including `BROWSER_RESOLUTION_FAILED`, `BROWSER_LAUNCH_FAILED`, `BROWSER_STARTUP_FAILED`, `NAVIGATION_FAILED`, `FONT_LOAD_FAILED`, `PAGE_EVALUATION_FAILED`, and `OUTPUT_INSPECTION_FAILED`. In strict mode, these failures leave `status: "FAIL"`, `release.finalEligible: false`, and a nonzero process status.

## Self-Review

- Confirmed the canonical and starter `browser-paths.mjs` files are byte-identical.
- Confirmed both render and inspect import the same resolver; the prior duplicated Windows-only resolution code is removed.
- Confirmed initialized projects receive the resolver and pass a real no-argument render regression.
- Confirmed missing bundled fonts and an unresolved explicit browser both leave parseable failed reports with specific blockers.
- Confirmed no runtime synchronization drift, no syntax errors in either runtime copy, and no whitespace errors in the diff.

## Remaining Concerns

- The macOS, Linux, and Windows path matrices are injection-tested; this task did not execute Chrome/Edge binaries on Linux or Windows hosts.
- On this host no standard `/Applications` Chrome/Edge candidate was found, so the no-argument render regression used the retained project-local Playwright fallback. This validates fallback behavior, while candidate tests validate the portable discovery order.
