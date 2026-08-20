---
name: poster-design
description: Use when creating commercial, long-form, or A0/A1 posters.
version: 0.3.0
author: feariangod, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [poster, design, html, css, print, infographic]
    related_skills: [baoyu-infographic, chiyi-image-generation]
---

# Poster Design

Create posters with an **Image 2-led concept-to-publish workflow**. The default outcome is one directly publishable PNG, but the first step is always one final-size near-production concept for user confirmation. Preserve the confirmed Image 2 composition whenever it passes review; use deterministic layers only for facts, identity/brand assets, QR codes, exact size, and defects the model cannot safely own.

## First-Principles Invariants

1. **Responsibility before process:** default work ends with a publishable PNG; print, compliance, localization, and complete editability upgrade to `release`.
2. **Concept before commitment:** show one near-production concept at the requested final `size` and wait for confirmation before publish work.
3. **Image 2 is a compositor, not only a background maker:** it may own the scene, composition, lighting, materials, decoration, information hierarchy, and concept text.
4. **Semantic consistency is not pixel fidelity:** Image 2 editing can preserve object identity and structure while redrawing edges, labels, faces, packaging details, and textures.
5. **Deterministic protection:** all readable text must be exact in Concept and Publish; real people, brand logos, critical facts, real product packaging, QR codes, and release-critical text are checked and covered with authorized assets when exactness matters.
6. **Truth:** readable generated text is not proof of a true claim. Names, dates, prices, places, URLs, rules, contacts, and scientific/legal facts require independent checking.
7. **Fresh evidence:** a publish check describes the current output; a `release` review and hash binding become stale after any re-render.

## When to Use

Use for commercial, admissions, event, course, product, brand, recruitment, film, public-interest, long-form, social-media, scientific, conference, A0, or A1 posters.

Do not use for a plain illustration with no poster information architecture; use the active image-generation skill instead.

## Default Route and State Machine

The default mode is `publish`, with a mandatory concept confirmation gate:

```text
intake
  → explicit direction/reference → direction_locked
  → no explicit direction → direction_options
  → user selects one text-only option → direction_locked
  → prompt_compiled
  → concept_draft_1
  → user confirms → visual_locked
  → publish_build → publish_qa → publish_ready

concept_draft_1
  → one direction revision → concept_draft_2
  → still rejected → needs_rebrief

publish_ready
  → user requests print, compliance, complete editability, localization,
    PDF, A0/A1, paid campaign evidence, or full audit → release
```

Record the state in a compact project `poster.json` so a resumed session does not infer it from chat history:

```json
{
  "mode": "publish",
  "state": "direction_options",
  "conceptRevision": 0,
  "size": "1080x1920",
  "directionLocked": false,
  "releaseRequested": false
}
```

Rules:

- If the user provides an explicit visual direction or reference, skip direction options and adopt it as `direction_locked`. Otherwise present two or three text-only directions before any image call; never generate option images.
- Selecting a text-only direction does not consume the one direction revision. Only rejection of a generated Concept for visual direction consumes it.
- Concept direction changes are limited to one revision. A second rejection enters `needs_rebrief`; re-align audience, action, density, references, and asset boundaries instead of drawing indefinitely.
- After `visual_locked`, do not replace the overall style, composition, or visual center. Publish corrections may fix defects only.
- Publish allows one targeted defect-fix cycle. Repeated failures escalate the failing element to a deterministic layer or to `release`.
- Missing critical facts cannot be invented. Use only an approved neutral placeholder or an explicitly empty reserved zone in Concept; unresolved facts keep the work preview-only.

## Minimal Intake

Collect or infer only:

1. action and intended use;
2. audience and viewing context;
3. exact approved copy, with unresolved facts explicitly marked;
4. final `size="WIDTHxHEIGHT"`;
5. real people, products, logos, QR URL, and other authorized assets;
6. one visual direction or reference, when already known.

Ask one question only when the answer changes the route or visual direction materially. When direction is not explicit, read `references/concept-directions.md`, present two or three compact text-only options, and wait for selection. Each option contains a name, one-sentence concept, hero/layout skeleton, palette/material language, and fit reason. When direction is explicit, skip this gate. Give a one-sentence `Design Read` before the first generation. Do not require option images, three brief files, or a full publication audit before showing the concept.

Critical facts include names, dates, times, prices, places, URLs, QR destinations, contact details, claims, scientific values, units, and rules. Put them in `poster.json` or `brief.json` before publish work and mark unresolved facts explicitly.

Before Concept generation, record every permitted readable string in an approved-copy contract. Concept and Publish both require exact readable text: every intended string must match after declared Unicode/whitespace normalization, and no unintended readable words, gibberish, fake brands, URLs, or claims may remain.

## Phase 1 — Concept: Near-Production Image 2 Draft

Goal: let the user judge the actual visual direction and information density before production effort is spent.

1. Resolve or select the visual direction, set `direction_locked`, and record why the chosen archetype fits. Text-only option selection is not a generated-Concept revision.
2. Resolve the final output size. With Chiyi use `size="WIDTHxHEIGHT"`; never use `aspect_ratio`. Keep Chiyi `quality` fixed at `high`.
3. Compile one maintainable prompt using the six blocks in `references/concept-directions.md`: deliverable and audience, core visual proposition, composition and information zones, subject and asset roles, approved copy hierarchy, and constraints and output. Set `state` to `prompt_compiled`.
4. Call `image_generate` once. Image 2 may generate the complete poster, including all concept text. Do not reduce it to a text-free background unless the brief calls for one.
5. Use the adaptive asset strategy:
   - no identity/brand asset: Image 2 may create the complete concept;
   - real person or product: pass the authorized source as a reference when useful, but inspect identity and geometry;
   - real logo: use it as a reference for placement, not as proof of logo fidelity;
   - real QR URL: generate the QR deterministically and place it over the concept;
   - no QR URL: use an explicit empty signup/QR slot; never ask Image 2 to draw a QR-like code.
6. Apply the Concept gates in `references/quality-rubric.md`: inspect non-empty output, severe clipping, hierarchy, artifacts, supplied-asset replacement, exact text/facts, logo-like marks, technical action when claimed, and an actual phone-scale render. If text fails, allow one targeted Image 2 text correction that preserves the direction; if any text still fails, apply deterministic typography only to the failing region and reinspect the complete Concept. Text repair does not consume the direction revision.
7. Deliver exactly one text-accurate concept PNG and wait for confirmation. Do not create PDF, full font package, release hashes, or a long QA narrative yet.

Concept text may be non-editable, but it may not be wrong, clipped, fabricated, or unapproved. Label the image `concept — awaiting confirmation`; do not call it publish-ready.

**Concept budget:** one initial generation, at most one targeted Image 2 text correction, deterministic text coverage when needed, plus one direction revision. A typo or text correction never consumes the direction revision and must be fixed before Concept delivery.

## Phase 2 — Publish: Image 2-Led Final PNG

Goal: deliver one directly publishable PNG while preserving the confirmed visual instead of rebuilding it unnecessarily.

1. Set `state` to `visual_locked` after user approval. Treat the approved concept as the visual contract: preserve composition, palette, subject scale, information zones, and mood.
2. Start from the approved Image 2 image. Image 2 should own approximately 80%–95% of the visible composition: scene, lighting, materials, decoration, non-identity objects, and ordinary visual text that passes review.
3. Run an element-by-element publish review:
   - **Ordinary generated text:** keep only when every character and claim is verified. If a small error is found, allow one targeted Image 2 edit; if it still fails, cover it deterministically.
   - **Names, dates, times, places, prices, rules, contacts, claims, labels, and disclaimers:** verify against `poster.json`/`brief.json`; cover with deterministic text whenever exactness or editability matters.
   - **Real person:** Image 2 may use the photo for composition, but a face/identity drift fails the publish check. Cover the person with the authorized original photo or use a clearly framed authentic-photo treatment.
   - **Real product or packaging:** keep the generated environment when useful; cover the package, label, barcode, and regulated copy with the authorized source when geometry or identity matters.
   - **Real logo/brand mark:** always use the original authorized asset in the publish image. Generated logo resemblance is not fidelity.
   - **QR:** always generate from the approved URL or use the supplied real QR; overlay it deterministically and decode the final rendered pixels locally.
4. Do not spend another image call on a failure that deterministic compositing can fix. A model edit is allowed once for a meaningful non-identity defect; then escalate the element to deterministic treatment.
5. Render or composite the final PNG at the exact requested `size`. Preserve the approved Image 2 base and keep any HTML/CSS or composition script minimal. Store source files and assets in the project directory even though the default user delivery is PNG only.
6. Run publish checks: actual PNG dimensions, non-empty image, critical fact transcription, identity/brand review, QR payload when present, severe artifact review, target-size visual review, and phone-scale readability of the call to action.
7. Write compact `publish-qa.json` with `status`, `size`, `facts`, `identity`, `logo`, `qr`, `mobile`, `artifacts`, and `fixes`. Deliver the PNG and state whether it is `publish-ready` or blocked by a named issue.

**Publish budget:** the original concept, at most one targeted Image 2 correction, one deterministic composition pass, and one publish defect-fix cycle. Do not restart visual exploration after `visual_locked`.

## Phase 3 — Release: Existing Strict Publication Engine

Enter `release` only when the user requests printing, A0/A1, PDF, paid public campaign evidence, full editability, localization, brand governance, legal/scientific/medical/financial responsibility, or a complete source package.

Reuse the visually locked Publish artifact; do not restart creative exploration. Rebuild release-critical text, charts, logos, QR, and identity assets as editable deterministic DOM/SVG or authorized local assets where required. Then use the existing strict engine:

```bash
node scripts/init-poster.mjs --output <project-dir> --title "<title>" --type <digital|long-form|a0-landscape|a0-portrait|a1-landscape|a1-portrait> [--width 1080 --height 1920]
node scripts/render-poster.mjs --project <project-dir> --browser chrome
node scripts/inspect-poster.mjs --project <project-dir> --browser chrome --strict
node scripts/record-visual-review.mjs --project <project-dir> --reviewer vision_analyze --hierarchy PASS --composition PASS --typography PASS --coherence PASS --artifacts PASS --mobile PASS --notes "<evidence>"
node scripts/inspect-poster.mjs --project <project-dir> --browser chrome --final
```

`release` requires the current strict fact contract, bundled fonts and licenses, PNG/mobile/PDF dimensions, QR decoding, active-content and external-request rejection, output freshness, visual review, SHA-256 bindings, and `release.finalEligible: true`. Automated PASS is not final status.

Release delivery may include:

```text
brief.json, poster.json, poster.html, styles.css, assets/, fonts/, licenses.md,
poster.png, poster-mobile.png, poster.pdf, qa-report.json, qa-report.md,
visual-review.json, and current output evidence.
```

## Image 2 Capability Boundaries

The active Chiyi `gpt-image-2` adapter has been locally validated for:

- text-to-image with controlled object counts, colors, composition, exclusions, and short text;
- single-image editing that changes a background or lighting while preserving high-level subject structure;
- multi-reference editing that separates a content reference from a style reference;
- exact final decoded dimensions through `size="WIDTHxHEIGHT"`, with fixed `quality=high`.

These are semantic controls, not guarantees of pixel-level identity. Treat generated results as unreliable for:

- a real person's face, age, or identifying features;
- a standard logo, product package, barcode, label typography, or regulated copy;
- a QR code or any scannable transaction entry;
- professional claims merely because their text is legible;
- future pixel-consistent re-edits.

## Deliverables by Stage

| Stage | User receives | Project retains |
|---|---|---|
| Concept | one final-size concept PNG and status | `poster.json`, prompt, concept image, supplied/generated assets |
| Publish | one publish-ready PNG by default | concept, final PNG, minimal source/composition files, assets, `publish-qa.json` |
| Release | requested full package | complete editable project, licenses, PDF, strict QA and visual evidence |

Do not generate PDF, mobile derivatives, font packages, or audit reports for a PNG-only Concept or Publish request unless the user asks for them. Source files remain in the project directory and are provided on request.

## Pitfalls

- A clear generated character is not automatically a correct person, brand, claim, or product.
- A successful API response is not a successful poster; inspect the visible artifact.
- A QR-looking patch is not a QR; decode final pixels against the approved URL.
- Do not call a concept publish-ready before user confirmation and publish checks.
- Do not use a second concept revision to repair a typo that does not change the visual direction.
- Do not keep retrying identity edits after a visible face or logo drift; cover the failing element with the authorized source.
- Do not silently replace a rejected direction with a new style after `visual_locked`.
- Never weaken strict `release` gates to make a project pass.
- Never edit generated runtime copies directly; change canonical scripts and run `npm run runtime:sync` followed by `npm run runtime:check`.

## Verification

For Concept, verify one final-size non-empty PNG, severe clipping/artifacts, asset strategy, every readable string character by character against approved copy, absence of unintended readable text, and explicit `awaiting confirmation` status.

For Publish, verify exact decoded dimensions, critical facts, identity/brand assets, QR payload when present, target and phone-scale visual quality, and `publish-qa.json` status. Any unresolved critical fact or identity/QR failure blocks `publish-ready`.

For Release, all of the following are required:

- `npm run runtime:check` exits zero;
- `inspect-poster.mjs --final` exits zero;
- `qa-report.json` has no blockers and `release.finalEligible` is true;
- every QR payload matches the approved contract;
- bundled fonts load and licenses are present;
- target PNG, mobile PNG, and PDF dimensions match configuration;
- current visual review passes target and mobile views;
- `visual-review.json` and `qa-report.md` bind the current output hashes.

If a check is absent or fails, report the actual stage and named blocker instead of claiming completion.
