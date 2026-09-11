# Staged Quality Rubric

Quality gates scale with the delivery responsibility. Concept proves the direction, Publish proves the directly shareable PNG, and Release proves the complete publication package. Never apply a lower stage label to a higher-responsibility claim.

## Concept gates

A Concept passes when:

- exactly one requested final-size PNG exists and decodes;
- the image is non-empty and not severely clipped;
- the subject, visual center, hierarchy, and intended action are judgeable;
- every intended readable string matches approved copy character by character after declared normalization;
- no unintended readable text, gibberish, fake brand, fake URL, invented label, or extra claim appears;
- every visible fact or claim matches the approved fact contract; unavailable facts use only approved neutral placeholders or empty reserved zones;
- when technical action correctness matters, the action follows an authorized reference or its phase, joints, grip, equipment contact, and balance pass review from visible pixels; style language alone is not evidence;
- unbranded people, clothing, products, and equipment contain no logo-like marks, brand-like marks, pseudo-lettering, signature shapes, or sponsor-style graphics;
- an actual phone-scale render, normally 360px wide, proves headline, subheading, facts, and call-to-action readability; do not infer mobile readability from the full-size canvas;
- supplied real assets were not silently replaced without disclosure;
- there is no fake QR; a missing URL uses an explicit empty slot;
- text failures have completed the bounded repair sequence: one targeted compatible-tool correction, then deterministic coverage if needed, followed by complete reinspection;
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
- the call to action and critical facts remain readable at phone scale;
- the image remains faithful to the `visual_locked` concept rather than introducing a new direction;
- `publish-qa.json` reports `PASS` for size, facts, identity, logo, QR when applicable, mobile, and artifacts.

Allow one targeted Publish defect-fix cycle. A failed compatible-tool correction escalates only the failing element to a deterministic layer; do not restart concept exploration.

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
- Fonts are bound by the font manifests and pinned license policy; every non-font asset is bound by `asset-manifest.json`.
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

`CONFIG_INVALID`, `BRIEF_INVALID`, `POSTER_STATE_INVALID`, `PUBLISH_QA_INVALID`, `ACTIVE_CONTENT`, `ASSET_OUTSIDE_PROJECT`, `EXTERNAL_RESOURCE_BLOCKED`, `ASSET_LICENSE_INVALID`, `ASSET_LICENSE_MISSING`, `ASSET_HASH_MISMATCH`, `UNRESOLVED_PLACEHOLDER`, `COPY_MISMATCH`, `COPY_UNBOUND`, `COPY_NOT_VISIBLE`, `ELEMENT_OVERFLOW`, `MIN_FONT_SIZE`, `MOBILE_CRITICAL_SIZE`, `BROKEN_IMAGE`, `UNDECLARED_FONT`, `FONT_SOURCE_INVALID`, `FONT_MANIFEST_INVALID`, `FONT_MANIFEST_MISMATCH`, `FONT_FILE_MISSING`, `FONT_PATH_INVALID`, `FONT_HASH_MISMATCH`, `FONT_BINARY_INVALID`, `FONT_BINARY_FAMILY_MISMATCH`, `FONT_GLYPH_MISSING`, `FONT_POSTER_GLYPH_MISSING`, `FONT_LICENSE_MISSING`, `FONT_LICENSE_BINDING_MISMATCH`, `FONT_LOAD_FAILED`, `FACT_CARDINALITY`, `FACT_MISMATCH`, `FACT_NOT_VISIBLE`, `FACT_UNDECLARED`, `QR_CARDINALITY`, `QR_NOT_VISIBLE`, `QR_UNDECLARED`, `QR_DECODE_FAILED`, `QR_PAYLOAD_MISMATCH`, `QR_TOO_SMALL`, `QR_MOBILE_TOO_SMALL`, `SOURCE_MISSING`, `SOURCE_INVALID`, `RENDER_MANIFEST_INVALID`, `SOURCE_HASH_MISMATCH`, `OUTPUT_HASH_MISMATCH`, `OUTPUT_MISSING`, `OUTPUT_EMPTY`, `OUTPUT_INVALID`, `OUTPUT_BLANK`, `OUTPUT_STALE`, `PNG_SIZE_MISMATCH`, `MOBILE_SIZE_MISMATCH`, `PDF_PAGE_COUNT`, `PDF_SIZE_MISMATCH`, `STATUS_NOT_FINAL`, `PUBLISH_QA_NOT_PASS`, `VISUAL_REVIEW_MISSING`, `VISUAL_REVIEW_INVALID`, `VISUAL_REVIEW_STALE`, `VISUAL_REVIEW_FAILED`, `QA_NARRATIVE_STALE`.

Optional facts and QR entries may be absent in Release only when their absence is declared; duplicate keys remain blocking cardinality failures.
