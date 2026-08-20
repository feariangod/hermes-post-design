# Asset Policy V2

## Image 2 role

The active Chiyi `gpt-image-2` path is validated for text-to-image, single-image editing, and multi-reference editing. It can own most of a poster's visible scene: composition, lighting, materials, decoration, non-identity subjects, and concept text.

Its editing is **semantic constrained redraw**, not pixel-level preservation. A bottle, label, face, leaf, or package may keep its high-level structure while edges, typography, facial features, textures, and highlights are regenerated.

## Adaptive identity and brand policy

### No identity-bearing assets

Image 2 may create the complete Concept and, after user confirmation and Publish checks, the complete visual may remain model-generated.

### Real person

- Concept: Image 2 may receive the authorized photo as a composition reference.
- Publish: inspect face, age, identifying features, pose, and unwanted alterations. Any visible identity drift fails the generated person element.
- Recovery: cover the failing person area with the authorized original pixels or use a clearly framed authentic-photo treatment. Do not retry identity edits indefinitely.

### Real product or package

- Concept: Image 2 may use the source as content reference and generate the surrounding environment.
- Publish: retain the generated environment only when useful; cover package geometry, label, barcode, regulated copy, and identity-critical details with the authorized source.

### Real logo or brand mark

- Concept: use the source as a placement/style reference if helpful.
- Publish: always overlay the original authorized logo/mark. A recognizable generated imitation is not brand fidelity.

### Ordinary generated text

- Concept: Image 2 may render all text to reveal the intended information hierarchy.
- Publish: keep text only after character-by-character and claim verification. Use one targeted Image 2 edit for a meaningful non-identity defect; if it fails, cover the text deterministically.
- Release: rebuild release-critical text as editable deterministic DOM/SVG.

### Critical facts

Names, dates, times, prices, places, rules, contacts, claims, disclaimers, labels, scientific values, units, and legal copy require an approved fact contract. Legibility never substitutes for truth.

## QR policy

Generate a QR from an approved URL or use a supplied real QR. Never ask Image 2 to draw one. In Concept, a missing URL produces an explicit empty slot. In Publish, a missing URL blocks any “scan to register” claim; an available URL requires deterministic overlay and local decode of the final pixels against the approved payload.

## Visual references

Multiple references may be assigned explicit roles:

- content reference: subject, object count, pose, or composition;
- style reference: color, material, lighting, or visual atmosphere;
- layout reference: information zones or hierarchy.

State the roles in the prompt. Validate that prohibited geometry, logos, or identity details from a style-only reference were not copied into the result.

## External and project assets

Record source path/URL, creator, license, modification, and attribution requirement for every authorized asset used in Release. Final deterministic layers use project-local assets. Do not add executable scripts, inline event handlers, active embedded documents, or remote runtime dependencies to project HTML. Keep generated Image 2 files and source assets inside the project/archive directory.

## Resolution and cropping

Prefer original identity and product resolution. Preserve aspect ratio and disclose intentional cropping. The Chiyi adapter accepts `size="WIDTHxHEIGHT"` and returns a verified exact final decoded size; do not use `aspect_ratio`.
