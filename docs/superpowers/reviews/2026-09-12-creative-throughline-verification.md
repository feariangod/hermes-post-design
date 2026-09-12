# Creative Throughline Verification

## Scope

User direction: creativity must carry through the whole poster, not stop at ideation or image generation. The local Skill instructions were refined in place. Runtime stages, contracts, authorization, facts, asset fidelity, and existing approval boundaries stay unchanged. No live installation update or new image generation is included.

## Baseline Evidence

The real September 28 case produced a technically valid Concept using a generated cursor sculpture and a large, heavy Noto Sans SC title. User feedback identified stiff expression and insufficient typographic creativity. Technical and visual checks from that run do not prove that the creative intent was fully expressed.

A read-only agent replay used the fixed source revision `61bfb6e` and all six references. English rendering of the evaluation brief:

> Use one case to test the entire poster Skill: September 28 AI offline competition; other content is delegated. The poster should feel expressive, not stiff. For this evaluation, output only an actionable pre-production Concept plan and a self-review within 900 Chinese characters. Do not generate images, write files, call external services, or fabricate user confirmation.

The baseline already proposed a meaningful scene: a participant turns a laptop toward a partner, with the viewer placed at the table. It connected gesture, viewpoint, light, palette, and hierarchy to a welcoming feeling. Typography remained a Noto Sans SC bold title plus regular utility copy, justified as avoiding equal emphasis. Self-review correctly withheld visual acceptance without a render; it did not state a specific test for title-image integration beyond narrative and readability.

This is partial behavioral coverage, not proof that the old Skill lacks creativity. The change targets reliable continuation and review of creative decisions. No single agent replay establishes general aesthetic superiority.

## Evaluation Scenarios

Run these against the revised working-tree instructions without media generation or file writes by the evaluation agents:

1. Repeat the same AI competition brief and pre-production output constraint. Look for a coherent, audience-relevant proposition, visible choices across the layers, an intentional title role, and an honest unrendered status.
2. Plan a dense community schedule using supplied exact copy, a locked brand font, and a quiet, clear brief. Creativity should emerge through hierarchy, rhythm, and relationships, without forced custom lettering, invented facts, new approval gates, or extra image calls.
3. Review a technically clean, large stock-font title over an unrelated polished key visual, where the user requests expressive integration. Identify the creative gap separately from technical success; propose a scoped repair and require a new rendered review, not a fabricated PASS.

Evaluate concrete decisions rather than the presence of style adjectives or a required font effect. Scenarios 1 and 2 are plan-only tests; scenario 3 is a hypothetical review, not a new visual acceptance of the existing image.

## Results

| Check | Observed result |
|---|---|
| Revised AI competition replay | Expected planning behavior observed: a beginning-of-match gesture, an offset two-part title, and a red key/date association express one opening moment. The agent named the risk of looking like a generic coding event and withheld visual acceptance because no image was rendered. |
| Quiet community schedule | Expected restraint observed: one locked font, white background, aligned time columns, grouped whitespace, exact supplied copy, and a reserved original-logo location pending the asset. No forced lettering, imagery, or decoration. |
| Hypothetical stiff-poster review | Expected evidence boundary observed: identified word-image integration as a hypothesis, distinguished reported technical PASS from unverified creativity, requested the actual image for visual judgment, and proposed a local repair with copy and theme preserved. |
| Independent instruction review | No supported issue found in added process overhead, forced ornament, factual/authorization weakening, or completion criteria. Parent additionally clarified that title comparisons use an existing study allowance; local refinement does not create mandatory studies. |
| Focused Python checks | `./.venv/bin/python -m pytest tests/test_skill_contract.py tests/test_skill_inventory.py tests/test_package_contents.py -q`: final run 13 passed in 1.42 seconds. |
| Runtime parity | `npm test --prefix src/hermes_post_design/resources/skills/creative/poster-design`: PASS; `runtime:check` reports no updates needed. Runtime source and starter scripts were not changed. |
| Whitespace | `git diff --check`: PASS. |

The replay evidence comes from separate read-only agents. The old-version replay used `61bfb6e`; the new-version replays used the working-tree instructions. They are qualitative, single-run behavior probes, not blinded aesthetic ratings or a statistical performance claim. All three revised scenarios produced text only, with zero image calls and no agent file writes.

## Actual Case Reassessment

The parent directly viewed the existing `artifacts/ai-offline-competition-2026-09-28-run-01/poster.png` at 1080x1440 and `poster-mobile.png` at 360x480 again. No artwork was changed. Against the user's clarified expressive brief, the creative verdict is **needs refinement**, even though the earlier technical checks passed:

1. Preserve the cursor/prototype relationship, material contrast, strong date signal, and readable copy. They already support the idea of making something together; the image is not simply unrelated decoration.
2. The title is a heavy, uniform line above the sculpture. Its structure and placement do not yet participate in the joining/building idea. A scoped next experiment would connect the title's line or letter structure to that relationship while retaining character accuracy.
3. The title zone, hero, and dark information band read as separate stacked regions. Test a clearer visual handoff between them while retaining the phone-scale hierarchy. Extra fonts or effects alone would not address that relationship.

This reassessment does not overwrite the historical QA records or grant/revoke user approval on the user's behalf. The actual case remains Concept/pending, and no new visually accepted revision exists. Its old all-PASS declaration must not be cited as proof that the clarified creative brief is satisfied.

## Change Boundary

Only the entrypoint and four existing creative references were changed: intake, concept direction, typography, and quality review. Creative intent uses the existing `poster.json.direction`; narrative review uses existing notes or `qa-report.md`. No new stage, schema, approval gate, font dependency, or machine aesthetic score was added.

The runtime remains a technical verifier. The stronger creative acceptance instructions require agent judgment supported by actual rendered evidence; automated test success cannot prove that future posters will be expressive.

No full Python/Node suite was rerun for these instruction-only edits. Existing targeted contract, inventory, package, and runtime-parity checks cover the affected mechanical surface. No live Agent-home sync, install, commit, push, publication, or image generation occurred. Actual visual improvement and cross-host runtime behavior remain unverified in this turn.
