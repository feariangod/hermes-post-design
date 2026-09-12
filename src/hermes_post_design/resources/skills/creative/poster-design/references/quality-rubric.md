# Staged Quality Rubric

Quality gates scale with the delivery responsibility. Concept proves the direction, Publish proves the directly shareable PNG, and Release proves the complete publication package. Never apply a lower stage label to a higher-responsibility claim.

## Design review

Choose viewing checks in `design.reviewContexts` before production. Inspect the full canvas and the relevant real-use view: phone-size for phone sharing, representative thumbnail/crop for feeds, physical-size and viewing-distance checks for print. A generated mobile preview is supplementary for print, not proof of print quality.

Ask what is seen first, what is understood next, and whether the intended action can be found. Review hierarchy, density, contrast, rhythm, negative space, brand character, and integration of original assets. Review identity/product treatment at full size as well as thumbnail scale.

Report one to three highest-impact findings with location, observed problem, intended improvement, and scoped fix. Hard blockers still all need recording. Fix the problem and recheck; do not assign aesthetic PASS from file presence, a successful render, or a numerical score alone. State unverified visual checks honestly.

### Creative review

Review the rendered poster against the proposition recorded in `poster.json.direction`, using the connected decisions in `concept-directions.md`. Evaluate these observable questions:

- **Meaning and feeling:** what can a viewer understand or feel from the image itself? Name the gesture, word-image relationship, rhythm, or restraint that carries it; the treatment note is not visible evidence.
- **Specificity:** could an unrelated title replace this one without changing anything else? If so, look for a missing subject-specific relationship. This is a diagnostic, not a demand for novelty in a constrained brand system.
- **Integration:** do typography, imagery, composition, color, and material reinforce the same intent? A striking hero with an unrelated default text overlay needs refinement when the brief calls for expressive integration.
- **Restraint and context:** which elements earn attention, and which should recede? Confirm that expression survives the actual phone, crop, or print view without sacrificing critical information.

Report technical findings and creative findings separately in the existing review notes or `qa-report.md`. Use an evidence-based creative verdict such as `convincing`, `needs refinement`, or `not reviewed`, with a concrete observation. These are narrative judgments, not new runtime states. An unrendered plan can be reviewed as a plan but cannot receive a rendered creative or visual PASS.

A technically clean but creatively weak Concept remains a draft for local refinement; explain the expressive gap rather than presenting technical PASS as complete design quality. Do not record an all-PASS `visual-review.json` solely because text matches, fonts load, and boxes fit. Its existing checks and notes must reflect actual composition, typographic expression or justified restraint, and the intended feeling as well as readability.

When feedback says "stiff", "generic", or "lifeless", locate the largest expressive gap and revise the relevant relationship first: wording where editable, title treatment, subject interaction, spacing/rhythm, or light/material. Preserve working elements. Recheck the whole poster at the delivery size; apply the existing direction budget, locked/flexible approval scope, and image-call authorization. Do not default to more effects or regenerate every layer.

## Composition study gates

Studies need clear alternative compositions, comparable scale/aspect ratio, readable displayed approved copy, and no invented facts or misleading identity claim. They may omit unresolved facts and leave blank zones. Label them `composition study - not for publication`; do not apply final-size, complete-copy, QR, or Release gates to these early comparisons. Develop the selected study into one complete Concept before asking for publication-stage approval.

## Concept gates

A Concept passes when:

- exactly one requested final-size PNG exists and decodes;
- the image is non-empty and not severely clipped;
- the subject, visual center, hierarchy, and intended action are judgeable;
- every intended readable string matches approved copy character by character after declared normalization;
- no unintended readable text, gibberish, fake brand, fake URL, invented label, or extra claim appears;
- every visible fact or claim matches the approved fact contract; unavailable facts use only approved neutral placeholders, empty zones, or explicit user-requested omission as recorded in `intake.md`;
- when technical action correctness matters, the action follows an authorized reference or its phase, joints, grip, equipment contact, and balance pass review from visible pixels; style language alone is not evidence;
- unbranded people, clothing, products, and equipment contain no logo-like marks, brand-like marks, pseudo-lettering, signature shapes, or sponsor-style graphics;
- the full canvas and declared viewing-context renders prove the intended hierarchy and critical readability; for phone delivery use an actual phone-scale render, normally 360px wide;
- supplied real assets were not silently replaced without disclosure;
- there is no fake QR; a missing URL uses an explicit empty slot;
- text failures are repaired locally or within the bounded authorized image-edit sequence, with deterministic coverage for repeated failures and complete reinspection;
- the output is labeled `concept — awaiting confirmation`.

Concept text may be generated and non-editable, but wrong, clipped, fabricated, or unapproved readable text blocks delivery. Text repair is a defect fix and does not consume the direction revision.

## Publish gates

A Publish PNG passes when:

### Content

- every critical fact matches `brief.json`, while workflow stage and approved readable copy come only from `poster.json`;
- generated text retained in the final image has been checked character by character;
- no unresolved name, date, time, place, price, URL, rule, contact, claim, label, or disclaimer remains;
- readable generated professional or scientific copy has independent factual support.

### Identity and assets

- real people match authorized source assets; face/age/identity drift is covered with authentic pixels;
- product/package geometry, label, barcode, and regulated copy use the authorized source when identity matters;
- every real Logo or brand mark uses the original authorized asset;
- image-tool content/style/layout references were used only for their declared roles;
- no unauthorized extra logo, watermark, identity, or product claim appears.

### QR

- a real URL or supplied QR is required for a scan-to-act design;
- the QR is deterministic, has a quiet zone, and locally decodes from final rendered pixels;
- decoded payload matches the approved destination byte for byte;
- without a URL, the Publish image removes the scan claim or remains blocked.

### Output and visual quality

- final PNG decoded dimensions equal the requested `size`;
- the image is non-empty and visually coherent;
- no severe clipping, generation artifact, broken composite edge, or unintended overlap;
- the call to action and critical facts remain readable in the declared delivery contexts, including phone scale for phone delivery;
- the image respects `design.approval.locked`; changes within `flexible` are permitted, while changes to locked principles have renewed user confirmation;
- `publish-qa.json` reports `PASS` for size, facts, identity, logo, QR when applicable, mobile, and artifacts.

Prioritize the highest-impact defects and repair them within the approved scope and call budget. Local fixes do not consume direction revisions. A failed image-tool correction escalates the affected element to deterministic treatment; do not restart concept exploration for a spacing or text defect. Existing `publish-qa.json.mobile` remains a required runtime check; for print it supplements, not replaces, the recorded physical-context review.

## Release gates

Release retains the existing strict publication engine. A final Release poster passes only when every blocking gate passes and evidence is current.

### Content and layout

- Every critical `brief.json` fact appears at its intended `data-fact` binding and matches after normalization.
- Every fact/QR binding is declared and visibly rendered; hidden or undeclared bindings block release.
- No unresolved placeholder, pseudo-character, stale copy, invented claim, overflow, clipping, unintended overlap, or unreadably small critical text.
- Mobile and physical-viewing typography meet declared thresholds.

### Assets and security

- All images decode and have sufficient source resolution.
- Identity-bearing images use authorized sources.
- Fonts are bound by manifests and the selected bundled/custom license policy; every non-font asset is bound by `asset-manifest.json`.
- Every visible Release string is bound by `data-copy` or `data-fact`, and the complete visible `data-copy` multiset matches `poster.json.approvedCopy`.
- Every `file:` resource stays inside the project; resource symlinks and network resources are blocked.
- Project HTML is static; active content and external requests are rejected.

### Functional output

- QR payloads decode and match approved destinations.
- PNG, mobile PNG, and PDF dimensions equal `poster.config.json`.
- Outputs open, are non-empty, and contain visible non-uniform content.
- `render-result.json` binds current source files and outputs by SHA-256.

### Visual evidence

Use the selected host adapter's compatible visual-analysis capability, or direct human-visible review, on target and mobile outputs. Record an all-PASS `visual-review.json` with `record-visual-review.mjs`; re-rendering makes it stale. Final eligibility requires `poster.json` mode/state `release`, a PASS Publish contract, and matching current hashes in `qa-report.md`.

Automated PASS is not final status. `visual-review.json` is an audit declaration, not cryptographic reviewer authentication.

## Release blocking codes

Invalid or unverified font-role/custom-font configuration blocks with `FONT_CONFIG_INVALID` in addition to the manifest and binary checks below.

`CONFIG_INVALID`, `BRIEF_INVALID`, `POSTER_STATE_INVALID`, `PUBLISH_QA_INVALID`, `ACTIVE_CONTENT`, `ASSET_OUTSIDE_PROJECT`, `EXTERNAL_RESOURCE_BLOCKED`, `ASSET_LICENSE_INVALID`, `ASSET_LICENSE_MISSING`, `ASSET_HASH_MISMATCH`, `UNRESOLVED_PLACEHOLDER`, `COPY_MISMATCH`, `COPY_UNBOUND`, `COPY_NOT_VISIBLE`, `ELEMENT_OVERFLOW`, `MIN_FONT_SIZE`, `MOBILE_CRITICAL_SIZE`, `BROKEN_IMAGE`, `UNDECLARED_FONT`, `FONT_SOURCE_INVALID`, `FONT_MANIFEST_INVALID`, `FONT_MANIFEST_MISMATCH`, `FONT_FILE_MISSING`, `FONT_PATH_INVALID`, `FONT_HASH_MISMATCH`, `FONT_BINARY_INVALID`, `FONT_BINARY_FAMILY_MISMATCH`, `FONT_GLYPH_MISSING`, `FONT_POSTER_GLYPH_MISSING`, `FONT_LICENSE_MISSING`, `FONT_LICENSE_BINDING_MISMATCH`, `FONT_LOAD_FAILED`, `FACT_CARDINALITY`, `FACT_MISMATCH`, `FACT_NOT_VISIBLE`, `FACT_UNDECLARED`, `QR_CARDINALITY`, `QR_NOT_VISIBLE`, `QR_UNDECLARED`, `QR_DECODE_FAILED`, `QR_PAYLOAD_MISMATCH`, `QR_TOO_SMALL`, `QR_MOBILE_TOO_SMALL`, `SOURCE_MISSING`, `SOURCE_INVALID`, `RENDER_MANIFEST_INVALID`, `SOURCE_HASH_MISMATCH`, `OUTPUT_HASH_MISMATCH`, `OUTPUT_MISSING`, `OUTPUT_EMPTY`, `OUTPUT_INVALID`, `OUTPUT_BLANK`, `OUTPUT_STALE`, `PNG_SIZE_MISMATCH`, `MOBILE_SIZE_MISMATCH`, `PDF_PAGE_COUNT`, `PDF_SIZE_MISMATCH`, `STATUS_NOT_FINAL`, `PUBLISH_QA_NOT_PASS`, `VISUAL_REVIEW_MISSING`, `VISUAL_REVIEW_INVALID`, `VISUAL_REVIEW_STALE`, `VISUAL_REVIEW_FAILED`, `QA_NARRATIVE_STALE`.

Optional facts and QR entries may be absent in Release only when their absence is declared; duplicate keys remain blocking cardinality failures.
