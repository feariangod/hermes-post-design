# Typography Rules

## Shared exact-text contract

Concept and Publish both require exact readable text. Before Concept generation, record an approved-copy contract containing every permitted readable string, its role, and its factual source when applicable. Compare visible text character by character after declared Unicode and whitespace normalization. No unintended readable text, gibberish, fake brand, fake URL, invented label, or extra claim may remain.

Exact characters do not prove a true claim. Names, dates, times, places, prices, contacts, URLs, rules, units, labels, and professional claims must also match the approved fact contract. When a critical fact is unavailable, use only an approved neutral placeholder or a clearly empty reserved zone; never invent a plausible value.

Honor explicit user-requested omissions under the scope rules in `intake.md`; omitted required facts still block Publish, and no displayed substitute may be invented.

## Plan typography before Concept

Choose heading, body, and numeral roles for the brief before committing composition. Decide family character, weight, line length, hierarchy, and spacing together; reserve expressive display faces for short text. Plan critical or frequently changing copy as editable layers from the start.

`font-config.json` selects local families by semantic role:

```json
{
  "version": 1,
  "roles": { "heading": "Noto Serif SC", "body": "Noto Sans SC", "numeral": "Noto Sans SC" },
  "customFonts": []
}
```

Bundled choices are `Noto Sans SC`, `Noto Serif SC`, and `Ma Shan Zheng`. The new starter selects only Noto Sans SC; no brief must use all three. With no config, legacy projects keep the previous three-family behavior. `npm run prepare` materializes only selected families and defines `--font-heading`, `--font-body`, and `--font-numeral` for CSS. Change role selections, rerun prepare, then render and inspect actual text.

Prepared manifests bind the role selections as well as font files. Changing roles requires prepare again, even when the set of families stays the same; old font preparation and render evidence cannot establish the new typography.

## Concept

An authorized compatible image tool may render all Concept text, and that text may be non-editable, but it must be accurate before delivery. The purpose remains to judge hierarchy, density, type mood, and composition without asking the user to approve a visibly defective copy layer.

Choose the lowest-cost repair for the defect:

1. Correct editable text locally. For embedded generated text, use deterministic coverage or a targeted image edit within explicit authorization and remaining call budget.
2. If the image edit fails, use deterministic typography or coverage for the affected region. Do not keep rerendering correct regions for a text defect.
3. Reinspect the complete Concept at target and declared viewing contexts against the approved-copy and fact contracts.
4. Do not deliver a misspelled, clipped, fabricated, or unapproved readable string for confirmation.

Corrections are defect repairs, not direction revisions. Image edits still count as image calls. Typography, line breaks, and whitespace may change within the user's approved flexible scope; changes to a locked principle require renewed confirmation.

## Publish

Generated text may remain in the directly publishable PNG only when every character and claim is verified and editability is not required. Use the same bounded, local-first repair logic as Concept; Publish cannot use a lower text standard.

Use deterministic text by default for names, dates, times, places, prices, rules, contacts, labels, disclaimers, claims, and any item whose future editing matters. The overlay may be HTML/CSS, SVG, or a local raster composition layer; it does not require rebuilding the full image-led poster.

For phone delivery, review an actual phone-scale image. For print, assess declared physical size and viewing distance. Fix unreadable text through layout and hierarchy, not by claiming the full-size source is sufficient.

## Release license policy

Release projects use selected pinned open-source fonts or explicitly authorized project-local custom fonts. For bundled families, `npm run prepare` copies the selected families' complete WOFF2 shards and `unicode-range` declarations into `assets/fonts/` and hashes them in `font-manifest.json`. Complete licenses and per-file bindings live in `assets/licenses/` and `font-license-manifest.json`; `licenses.md` summarizes them.

Do not rely on online fonts, CSS imports, or fonts installed only on the current machine. System fallback blocks Release final eligibility.

## Authorized custom fonts

Add each selected custom family to `font-config.json.customFonts`. Each entry requires:

- `family`: a unique role-selectable family name; it cannot replace a bundled name.
- `file`: a project-local WOFF2, WOFF, TTF, or OTF file under `assets/fonts/`, and `sha256` of that exact binary. One file per family is currently supported; a variable font can provide multiple weights.
- `licenseFile` under `assets/licenses/`, `licenseSha256`, `licenseId`, `licenseName`, and `licenseVersion`.
- `source`: a concrete publisher HTTP(S) page or a named local delivery reference such as `project:Brand font delivery 2026-09-12`.
- `authorization`: `approved: true`, matching `fontSha256` and `licenseSha256`, plus a separate project-local `evidenceFile` and its `evidenceSha256`.

Obtain actual approval covering the intended use before setting `approved`. Record the supplied evidence, not an invented permission statement. Hashes prove file/record integrity, not legal authority; unresolved permission blocks that custom font. Do not fetch a font or authorize a paid license automatically. Use a suitable bundled family only when brand requirements permit substitution.

Preparation rejects missing evidence, digest drift, symlinks, paths outside the project, and invalid font binaries. Custom family aliases are allowed; the exact approved binary digest is their identity anchor. The actual poster still must pass glyph coverage and layout checks.

## Role choices

- Body and utility: a highly readable family such as bundled Noto Sans SC.
- Editorial display: an appropriate serif such as bundled Noto Serif SC.
- Chinese display/calligraphy: a licensed family appropriate to the brief, such as bundled Ma Shan Zheng when its glyphs and tone fit.
- Latin/numerals: a compatible bundled or authorized custom family with the required glyphs and numeral style.

Use display fonts for short headings, never dense body copy. Body copy prioritizes reading speed.

## Release loading and effects

Declare local files with `@font-face`, explicit weights, and `font-display: block`. Wait for `document.fonts.ready` before inspection or rendering. The strict inspector treats undeclared generic/system fallback as blocking.

CSS/SVG may add foil, stroke, shadow, emboss, seals, brush masks, and texture. Keep Release-critical semantic text in the DOM/SVG. If an exceptional hand-lettered title remains an image/path, include editable alternative text and never use it for a critical fact.

## Glyph coverage

Before Release final render, bind every readable DOM string with `data-copy` or `data-fact`. The inspector reads the computed first-choice family for every visible text run and verifies every glyph-bearing code point against that family's selected, verified project-local binaries. Fixed sample strings are only manifest sanity checks; they never substitute for actual poster coverage. Missing CJK glyphs, tofu boxes, mixed fallback, or altered punctuation block final eligibility.
