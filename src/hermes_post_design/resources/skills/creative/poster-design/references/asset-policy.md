# Asset Policy

## Image-capability role

An authorized compatible image tool may own most of a poster's visible scene: composition, lighting, materials, decoration, non-identity subjects, and concept text. Select it only through `host-adapters.md`.

Its editing is **semantic constrained redraw**, not pixel-level preservation. A bottle, label, face, leaf, or package may keep its high-level structure while edges, typography, facial features, textures, and highlights are regenerated.

## Plan layers before Concept

Record `design.layers` before production: each layer's role, original/generated/editable/verified-image treatment, and source when required. Start with approved product silhouette, face, logo, and copy zones; design perspective, lighting, contact shadows, crop, and background around them. Do not postpone fidelity until a last-minute overlay that breaks the composition.

Use original pixels for identity-critical material and editable layers for critical or changeable text. Generation can supply environment, texture, non-identity imagery, or a visual sketch. When authentic assets are missing, use an explicitly labeled placeholder or request the asset; do not present a generated substitute as the final identity treatment.

## Adaptive identity and brand policy

### No identity-bearing assets

The selected image tool may create the complete Concept and, after user confirmation and Publish checks, the complete visual may remain model-generated.

### Real person

- Concept: compose the authorized photo as an original layer when identity matters. It may also guide surrounding composition, but a generated resemblance is not the protected identity layer.
- Publish: inspect face, age, identifying features, pose, and unwanted alterations. Any visible identity drift fails the generated person element.
- Recovery: cover the failing person area with the authorized original pixels or use a clearly framed authentic-photo treatment. Do not retry identity edits indefinitely.

### Real product or package

- Concept: retain the original product/package layer and generate only a compatible environment when needed. A generated placement sketch must be disclosed as such and cannot establish product fidelity.
- Publish: retain the generated environment only when useful; cover package geometry, label, barcode, regulated copy, and identity-critical details with the authorized source.

### Real logo or brand mark

- Concept: place the original mark in the layer plan; keep its proportions, clear space, and authorized treatment. A blank position marker may be used in a study.
- Publish: always overlay the original authorized logo/mark. A recognizable generated imitation is not brand fidelity.

### Ordinary generated text

- Concept: the selected image tool may render all text to reveal the intended information hierarchy.
- Publish: keep text only after character-by-character and claim verification. Prefer local correction for editable text; use a bounded authorized image edit only when useful. Repeated failures move the affected region to deterministic treatment.
- Release: rebuild release-critical text as editable deterministic DOM/SVG.

### Critical facts

Names, dates, times, prices, places, rules, contacts, claims, disclaimers, labels, scientific values, units, and legal copy require an approved fact contract. Legibility never substitutes for truth.

## QR policy

Generate a QR from an approved URL or use a supplied real QR. Never ask an image tool to draw one. In Concept, a missing URL produces an explicit empty slot. In Publish, a missing URL blocks any “scan to register” claim; an available URL requires deterministic overlay and local decode of the final pixels against the approved payload.

## Visual references

Multiple references may be assigned explicit roles:

- content reference: subject, object count, pose, or composition;
- style reference: color, material, lighting, or visual atmosphere;
- layout reference: information zones or hierarchy.

State the roles in the prompt. Validate that prohibited geometry, logos, or identity details from a style-only reference were not copied into the result.

## External and project assets

Every non-font file below `assets/` used in Release must have exactly one record in `asset-manifest.json`. Each record contains exactly `path`, `sha256`, `source`, `creator`, `license`, `authorization`, and `attribution`, all bound to the current project-local file. The validator rejects missing files, unrecorded files, duplicate paths, incomplete rights metadata, symlinks, and hash drift. A starter project with no non-font assets uses `{ "version": 1, "assets": [] }` and remains fully usable.

Final deterministic layers use project-local assets. Do not add executable scripts, inline event handlers, active embedded documents, or remote runtime dependencies to project HTML. Keep generated images and source assets inside the project/archive directory. `font-config.json`, `font-manifest.json`, and `font-license-manifest.json` separately bind selected bundled or authorized custom fonts; see `typography.md`.

## Resolution and cropping

Prefer original identity and product resolution. Preserve aspect ratio and disclose intentional cropping. Use only dimensions and controls supported by the selected route, then verify the final decoded size.
