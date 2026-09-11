# Typography Rules

## Shared exact-text contract

Concept and Publish both require exact readable text. Before Concept generation, record an approved-copy contract containing every permitted readable string, its role, and its factual source when applicable. Compare visible text character by character after declared Unicode and whitespace normalization. No unintended readable text, gibberish, fake brand, fake URL, invented label, or extra claim may remain.

Exact characters do not prove a true claim. Names, dates, times, places, prices, contacts, URLs, rules, units, labels, and professional claims must also match the approved fact contract. When a critical fact is unavailable, use only an approved neutral placeholder or a clearly empty reserved zone; never invent a plausible value.

## Concept

An authorized compatible image tool may render all Concept text, and that text may be non-editable, but it must be accurate before delivery. The purpose remains to judge hierarchy, density, type mood, and composition without asking the user to approve a visibly defective copy layer.

Concept text repair follows one bounded sequence:

1. Allow one targeted compatible-tool text correction while preserving the selected direction, composition, subject, and information zones.
2. If any intended or unintended readable text still fails, apply deterministic typography or a deterministic cover only to the failing region.
3. Reinspect the complete Concept at target and phone scale against the approved-copy and fact contracts.
4. Do not deliver a misspelled, clipped, fabricated, or unapproved readable string for confirmation.

The correction and deterministic cover are defect repairs. They do not consume the direction revision, which is reserved for rejection of a generated visual direction.

## Publish

Generated text may remain in the directly publishable PNG only when every character and claim is verified. A small non-identity text defect gets at most one targeted compatible-tool edit; failure escalates that text to a deterministic overlay. Publish cannot use a lower text standard than Concept.

Use deterministic text by default for names, dates, times, places, prices, rules, contacts, labels, disclaimers, claims, and any item whose future editing matters. The overlay may be HTML/CSS, SVG, or a local raster composition layer; it does not require rebuilding the full image-led poster.

Phone-scale review must show that the call to action and critical facts remain readable. Fix unreadable text through layout/coverage, not by claiming the full-size source is sufficient.

## Release license policy

Release projects use commercially usable open-source fonts. `npm run prepare` copies every WOFF2 shard and `unicode-range` declaration from the pinned Fontsource packages into `assets/fonts/` and writes exact file hashes to `font-manifest.json`. Complete license files and per-file bindings live in `assets/licenses/` and `font-license-manifest.json`; `licenses.md` is the human-readable summary.

Do not rely on online fonts, CSS imports, or fonts installed only on the current machine. System fallback blocks Release final eligibility.

## Release roles

- Body and utility: Noto Sans CJK SC or Source Han Sans.
- Editorial display and scientific hierarchy: Noto Serif CJK SC or Source Han Serif.
- Chinese display/calligraphy: a verified OFL/equivalent family appropriate to the brief.
- Latin/numerals: an open-source family compatible with the Chinese role.

Use display fonts for short headings, never dense body copy. Body copy prioritizes reading speed.

## Release loading and effects

Declare local files with `@font-face`, explicit weights, and `font-display: block`. Wait for `document.fonts.ready` before inspection or rendering. The strict inspector treats undeclared generic/system fallback as blocking.

CSS/SVG may add foil, stroke, shadow, emboss, seals, brush masks, and texture. Keep Release-critical semantic text in the DOM/SVG. If an exceptional hand-lettered title remains an image/path, include editable alternative text and never use it for a critical fact.

## Glyph coverage

Before Release final render, bind every readable DOM string with `data-copy` or `data-fact`. The inspector reads the computed first-choice family for every visible text run and verifies every glyph-bearing code point against the union of that family's pinned project-local binaries. Fixed sample strings are only manifest sanity checks; they never substitute for coverage of the actual poster. Missing CJK glyphs, tofu boxes, mixed fallback, or altered punctuation block final eligibility.
