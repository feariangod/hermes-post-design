# Adaptive Poster Intake

## Default responsibility

The default request is a directly publishable PNG, but the user must first approve one final-size near-production concept. Determine the authorized image-led or deterministic-local route through `host-adapters.md` before beginning Concept work. Do not spend full production effort before this confirmation.

## Minimal intake

Collect or infer:

1. intended action and use channel;
2. audience and viewing context;
3. exact approved copy, with unresolved facts explicitly marked;
4. final `size="WIDTHxHEIGHT"`;
5. real people, products, logos, QR URL, and authorized assets;
6. one visual direction or reference, when already known.

Ask one question only when the answer materially changes the route, visual center, audience, or factual responsibility. Give a one-sentence `Design Read` before the first generation.

## Conditional direction gate

Before any image call:

```text
explicit visual direction or reference → skip options → direction_locked
no explicit visual direction → direction_options → user selects → direction_locked
direction_locked → prompt_compiled → concept_draft_1
```

When no direction is explicit, use `concept-directions.md` to present two or three text-only options. Each option contains a short name, one-sentence concept, hero/layout skeleton, palette/material language, and fit reason. Do not generate option images, moodboards, sample grids, or presentation boards.

Selecting a text-only option does not consume the direction revision. The revision budget starts only after a generated concept is rejected for visual direction. Copy repair, fact correction, and deterministic coverage are defect fixes, not direction revisions.

## Risk signals and route

| Signal | Default behavior |
|---|---|
| user asks for a direction or says “先看看” | Concept only; wait for confirmation |
| ordinary social/event/course poster | Concept → Publish |
| real person, product, venue, institution, or logo | selected-route concept with authentic-asset review; Publish protects identity/brand assets |
| prices, dates, addresses, rules, contacts, claims, or QR | Fact contract and Publish verification |
| print, A0/A1, PDF, paid campaign evidence, localization, full editability, legal/scientific/medical/financial responsibility | Upgrade to Release |

## Concept confirmation gate

Concept always uses the requested final size and attempts to look near-production. An authorized image-led route may use generated text; the deterministic-local route may compose text locally. It may contain an explicitly labeled empty QR slot. It is not publish-ready.

- Generate one concept.
- User accepts → `visual_locked`.
- User rejects for a visual-direction reason → allow one direction revision.
- A second rejection → `needs_rebrief`; re-align action, audience, density, references, and asset boundaries instead of generating indefinitely.
- A typo that does not change the direction is repaired before Concept delivery and is not a concept-direction revision.

## Fact contract

Before Concept generation, record every approved readable string in `poster.json.approvedCopy` and record critical facts in `brief.json`: names, dates, times, prices, places, contacts, URLs, QR destinations, claims, scientific values, units, and rules. Mark unresolved entries explicitly. Concept may use only an approved neutral placeholder or an empty reserved zone for unresolved facts; any unresolved critical fact blocks advancement to Publish.

Readable generated text is not factual verification. A clear but incorrect claim remains a failure.

## Asset intake

Record each supplied asset's role and authorization:

- identity photo;
- product or package source;
- original logo/brand mark;
- approved QR URL or real QR;
- visual/style reference;
- forbidden substitutions.

A visual reference may guide color, material, lighting, or composition. Do not infer permission to copy protected logos, identities, or exact artwork.
