# Adaptive Poster Intake

## Default responsibility

The default request is a directly publishable PNG, with a final-size near-production Concept approved before Publish. First understand the communication problem, then choose production and check host capabilities. Do not spend full production effort before direction confirmation.

## Minimal intake

Collect or infer:

1. objective, audience, viewing context, first-glance takeaway, intended feeling, and intended action;
2. exact approved copy and information priority, with unresolved facts explicitly marked;
3. requested outputs and final `size="WIDTHxHEIGHT"` for each canvas;
4. real people, products, logos, QR URL, authorized assets, and brand invariants;
5. known direction/references, desired editability, and an appropriate exploration budget.

Ask only when the answer materially changes the route, visual center, audience, or factual responsibility. Otherwise record reasonable assumptions and continue. Give a one-sentence `Design Read` before production: what this audience should understand or feel, and why they would care. Infer a suitable emotional register from the brief when none is supplied; warmth, precision, calm, urgency, and playfulness are choices, not defaults. Do not turn the agreement into a long questionnaire.

## Portable design agreement

`poster.json` owns stage, `approvedCopy`, and `design`; `brief.json` owns facts/QR; `poster.config.json` owns exact canvas dimensions. Notes explain decisions, not a second authoritative copy contract.

Fill `design` before `route_selected`:

- `objective`, `audience`, `viewingContext`, `firstGlance`, `action`: short design decisions.
- `informationDensity`: `low`, `medium`, or `high`; `hierarchy`: `{copyIndex, role, priority}` entries referencing `approvedCopy` (zero-based index; roles `headline`, `support`, `fact`, `cta`, `detail`; priority 1 is strongest, 5 weakest).
- `brand.preserve` and `brand.avoid`: non-negotiable features and forbidden treatments.
- `route`: `{kind, reason}`; kinds `image-led`, `layered`, `deterministic`.
- `layers`: `{id, role, treatment, source?}`; treatments `generated`, `original`, `editable`, `verified-image`. Original layers need an authorized source before Concept delivery. Plan perspective, crop, light, and space around these assets now.
- `exploration`: `{approach, maxStudies, directionBudget}`. `direct` uses zero studies; `studies` normally budgets two or three. The starter budgets two direction revisions; adjust to the brief, not a universal cap. This does not authorize external calls.
- `approval`: `{status, evidence, locked, flexible}`. Start `pending`; record the user's actual confirmation and disjoint property names before `visual_locked`. Typical locked principles are message, subject, mood, and brand treatment; typical flexible details are type size, line breaks, spacing, and crop. Agree exceptions explicitly.
- `reviewContexts`: actual viewing checks; `deliverables`: `{id, format, usage, config}` entries, with `png`, `pdf`, or `source` format and a canvas-config reference. For several canvases, render and validate each explicitly; this list is not a batch-export command.
- `rebriefReason`: a specific diagnosed conflict when entering `needs_rebrief`.

New projects validate this agreement in the existing state contract. Legacy projects without `design` still load with their old one-revision ceiling; populate the agreement for a different budget or revised creative workflow, without fabricating earlier approval evidence.

## Conditional direction gate

Choose the smallest useful exploration:

```text
known direction -> direct Concept
uncertain composition -> two or three inexpensive studies -> select -> Concept
user prefers verbal comparison -> text directions -> select -> Concept
```

Use `concept-directions.md` for comparisons. Studies test hierarchy, silhouette, scale, and negative space at low fidelity. They may be locally composed or generated within existing authorization. A study is not a final-size deliverable and does not require unresolved facts to be filled in.

Selecting a study or text option does not consume a direction revision. `conceptRevision` counts revised directions after a Concept is rejected for direction, regardless of production method. Copy repair, fact correction, whitespace, and approved layout refinement are not direction revisions; any image calls they use still consume the call budget.

## Production choice

| Design need | Starting route |
|---|---|
| emotional key visual, sparse copy, no exact asset/editability requirement | `image-led` |
| authentic product, person, logo, or editable facts combined with a visual environment | `layered` |
| dense schedule, data, long copy, precision, or frequently revised information | `deterministic` |

These are defaults, not a requirement to generate anything. A dense product sheet can be deterministic with original imagery. `recommendProductionRoute` offers the same heuristic; record any deliberate alternative and reason. Only then read `host-adapters.md` to map generation, compositing, text, and review to available capabilities. Keep the design goal when a tool is missing.

## Delivery responsibility

| Signal | Default behavior |
|---|---|
| user asks for a direction or says “先看看” | Concept only; wait for confirmation |
| ordinary social/event/course poster | Concept → Publish |
| real person, product, venue, institution, or logo | original-asset/layer planning before Concept; fidelity review throughout |
| prices, dates, addresses, rules, contacts, claims, or QR | Fact contract and Publish verification |
| print, A0/A1, PDF, paid campaign evidence, localization, full editability, legal/scientific/medical/financial responsibility | Upgrade to Release |

## Concept confirmation gate

Concept always uses the requested final size and attempts to look near-production. An authorized image-led route may use generated text; the deterministic-local route may compose text locally. It may contain an explicitly labeled empty QR slot. It is not publish-ready.

- Generate one concept.
- User accepts -> record approval evidence, locked principles, and flexible details -> `visual_locked`.
- User rejects for a visual-direction reason -> diagnose the mismatch, then revise within `directionBudget` and available call authorization.
- Repeated rejection -> re-align action, audience, density, references, and asset boundaries. Enter `needs_rebrief` when the brief conflicts or direction budget is exhausted, with a specific reason. Do not automatically expand budgets.
- Exhausting direction revisions does not forbid local refinement of an accepted Concept. Reopen approval only for a change to locked principles.
- A typo that does not change the direction is repaired before Concept delivery and is not a concept-direction revision.

## Fact contract

Before Concept generation, record every approved readable string in `poster.json.approvedCopy` and record critical facts in `brief.json`: names, dates, times, prices, places, contacts, URLs, QR destinations, claims, scientific values, units, and rules. Mark unresolved entries explicitly. Concept may use only an approved neutral placeholder or an empty reserved zone for unresolved facts; any unresolved critical fact blocks advancement to Publish.

Readable generated text is not factual verification. A clear but incorrect claim remains a failure.

A user's explicit instruction to omit an unconfirmed detail also applies to Concept when requested; record the omission rather than forcing a placeholder into the composition. If the detail remains essential to the intended action, it still blocks Publish. Only an explicit change to the brief can remove that requirement; do not silently drop required facts to obtain PASS.

## Asset intake

Record each supplied asset's role and authorization:

- identity photo;
- product or package source;
- original logo/brand mark;
- approved QR URL or real QR;
- visual/style reference;
- forbidden substitutions.

A visual reference may guide color, material, lighting, or composition. Do not infer permission to copy protected logos, identities, or exact artwork.
