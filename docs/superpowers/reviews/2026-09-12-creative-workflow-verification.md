# Creative Workflow Verification

Date: 2026-09-12. Branch: `codex/portable-poster-skill`.

## Scope

Implemented the approved creative line in the local source checkout: communication agreement, information hierarchy and brand constraints, design-led production choice, optional composition studies, scoped Concept approval, layered refinement, contextual review, and requested exports. Existing Concept/Publish/Release states remain unchanged.

The entrypoint, six references, starter notes/configuration, runtime contracts, and README now agree. Heading/body/numeral font roles select bundled families or evidenced project-local custom fonts. New projects carry `poster.json.design`; legacy projects without it retain their previous revision ceiling. The normal Git index and live Agent homes were not used for this verification.

## Verification

| Check | Observed result |
|---|---|
| Skill Creator `quick_validate.py` | `Skill is valid!`, using `/usr/local/bin/python3.12` with PyYAML |
| `npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design` | PASS; canonical and starter runtime match |
| Full Python suite | 512 passed in 16.17 seconds |
| Final full Node suite | 104 passed, zero failures/skips, in 108.49 seconds |
| Isolated Agents/Codex/Claude/Hermes install, dry run, restore | All four PASS; 47 Skill files each; dry run read-only and seeded prior installation restored |
| Clean/polluted wheel regression | PASS as part of the full Python suite |
| Built wheel inventory and hashes | 47 Skill files match; no forbidden entries |
| Four independent behavioral scenarios | Product/brand layering, dense schedule, optional studies, and approved local refinement follow the revised flow |
| Independent issue recheck | 14 related regressions passed; all four reported issues resolved |
| Actual deterministic Concept forward run | Latest prepare/render/inspect all exited 0; strict PASS, zero blockers/warnings; parent independently checked state, fonts, and both images |
| Scoped whitespace check | PASS; global check still reports a pre-existing trailing blank line in `tests/test_install.py:416` |

Python's count is one lower than the earlier 513 because the obsolete exact-prose image-first routing assertion was removed. Executable authorization/state tests remain; realistic route scenarios and new design/font regressions cover the changed behavior.

The repository's inventory checks intentionally use Git-tracked paths. New resource files are not staged in the normal index, so this run used an isolated `GIT_INDEX_FILE=/tmp/poster-creative-qa.77BgMl/index`, initialized from HEAD plus the five new canonical/starter resource files. It did not relax inventory checks or stage the user's work. The resulting 47-file manifest digest is `31d6ae7d00c1bb0f9916a631d8ef834a77e11378b26a81c35f50f1339574cd65`.

Wheel: `/tmp/poster-creative-qa.77BgMl/wheel/hermes_post_design-0.1.0-py3-none-any.whl`.
Wheel SHA-256: `6c9049e14704a6efc944fe90e6a44041cf0e12fdcf171474d317bb3aa15c2e52`.

## Independent Findings Fixed

1. Changing heading/body roles within the same family set now rejects the old prepared manifest; rerunning prepare restores validity. Font config also participates in render source hashes.
2. A legacy project cannot silently gain an unlimited direction budget by omitting `design`.
3. Valid custom font licenses with non-`.txt` names and authorized evidence are recognized by their exact verified paths; unrelated assets still require their own manifest records.
4. Custom font inputs cannot collide with prepare outputs. Preflight checks resolved paths and file identity before writing and preserves colliding evidence, including hard-linked aliases.

Design/budget regressions, initial font-selection tests, stale-role checks, and the reported collision/ownership reproductions were observed failing before their fixes passed. Document replay also found and corrected whole-poster versus layer-output wording, requested unknown-fact omissions, and the prohibition on inventing manual visual-review evidence.

## Actual Forward Run

Project: `/tmp/poster-forward-editorial-20260912` (temporary test artifact, not a real event).
The exact Chinese copy is marked TEST-FIXTURE in the project records. Production is deterministic, with Noto Serif SC headings and Noto Sans SC body/numerals. Target PNG is 1080x1440; phone PNG is 360x480. All five strings are editable and readable in both inspected images, without clipping or overlap.

State readback: `mode=concept`, `state=concept`, approval `pending`, evidence `null`, authorized/used image calls `0`, and `finalEligible=false`. The standard renderer's PDF is an intermediate diagnostic artifact, not a Release claim. Local runtime scripts were refreshed and prepare/render/inspect rerun after the final fixes.

- Target PNG SHA-256: `ed743d66ebd1957226f043c0392c520cd76c1b6083007be9a1648b041c7f9c09`.
- Phone PNG SHA-256: `0f80efa4251048d1e807031a47462e1e2a7756ae4e356d4a1cc1f08ff17de05d`.

## Boundaries

- No live Agent-home update, commit, push, external publication, or paid image call was performed.
- Four-target installation parity is not live generation/editing validation inside four different Agent hosts. Native Windows/Linux execution and paid provider behavior remain unverified here.
- Custom fonts currently support one binary per family, including variable fonts. Recorded authorization integrity does not independently prove legal permission.
- The deliverables list records intended exports; each canvas must still be rendered and checked separately. It is not a batch-export engine.
- The earlier paused security audit is not declared complete by these creative-workflow results. Its existing changes were preserved.
- The earlier paused test fixture was preserved outside packaged resources at `/tmp/poster-creative-qa.77BgMl/paused-release-negative-gwIev7`; temporary paths may later be cleaned by the OS.
