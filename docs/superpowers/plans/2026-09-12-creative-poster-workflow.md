# Creative Poster Workflow Implementation Plan

> Execute the user-approved creative workflow in the existing local branch. Use bounded implementation and independent review tasks where they improve verification; preserve the paused safety changes and do not deploy.

**Goal:** Make poster-design follow communication goal -> information hierarchy and brand constraints -> production route -> optional composition exploration -> concept approval -> layered refinement -> context-specific visual review -> requested exports.

**Architecture:** Keep the existing Concept / Publish / Release responsibilities. Persist the design agreement inside `poster.json.design`, separate its production route from host/provider capability, and use the existing references for progressive disclosure. Add one small contract helper for design validation and route recommendations. Make fonts selectable by semantic role and support evidenced project-local custom fonts.

**Tech Stack:** Markdown, JSON, Node.js ES modules, Playwright, fontkit, existing Python installer and pytest.

**Spec:** The user's approval of the seven design recommendations in this conversation: strategy-led routes, portable design decisions, optional composition studies, early layer planning, scoped approvals and revision budgets, contextual visual critique, configurable brand typography.

## Constraints

- Continue on `codex/portable-poster-skill`; preserve all existing uncommitted changes.
- No live Agent home installs, commits, pushes, paid image requests, or external publication.
- Facts and readable content remain exact at the stage where they are presented; exploration may omit unresolved detail using clearly marked empty zones.
- Reuse authorization already given for the same operation and budget. Design approval alone must not create paid-call authorization.
- Preserve old version-1 poster projects without a design agreement; new initialized projects carry the agreement.
- Keep current stage names; studies and refinement are creative activities, not extra Release states.
- Use actual regression and isolated behavioral checks, not prose snapshot tests.

## Tasks

### 1. Creative Workflow And Portable Design Agreement

Files: canonical `SKILL.md`, existing references, `templates/poster-starter/poster.json`, `design-directions.md`, `content.md`, new `scripts/design-contract.mjs`, state/revision validation in `scripts/poster-contract.mjs`, `scripts/sync-runtime.mjs`, README.

- [x] Add tests demonstrating strategy-led routes even when an image tool is available; recorded revision budgets above one; separate copy/layout adjustments; invalid approval scopes; incomplete advanced-stage design agreements.
- [x] Implement `recommendProductionRoute(design)` for image-led, layered, and deterministic layouts using subject fidelity and information density.
- [x] Implement `validateDesignAgreement(design, state, conceptRevision, approvedCopy)` and use it only when a project supplies the new contract, preserving legacy projects.
- [x] Store design decisions in `poster.json.design` and typography roles in `font-config.json`, avoiding duplicate ownership.
- [x] Rewrite references around conditional discovery and refinement; replace mandatory text-only selection and unconditional one-revision limits for new design agreements.
- [x] Add context-specific review criteria with prioritized actionable findings and short evidence notes.

Expected route checks:

```js
assert.equal(recommendProductionRoute({ informationDensity: 'high', layers: [] }), 'deterministic');
assert.equal(recommendProductionRoute({ informationDensity: 'low', layers: [{ treatment: 'original' }] }), 'layered');
assert.equal(recommendProductionRoute({ informationDensity: 'low', layers: [] }), 'image-led');
```

### 2. Selectable Typography

Files: `prepare-project.mjs`, font-specific validation in `poster-contract.mjs`, optional shared font helper, starter font-role config/CSS, focused runtime font tests.

- [x] Prove a one-family design can prepare and validate without the other bundled families.
- [x] Prove a supplied local font requires source, file/license hashes, and authorization evidence; malformed or substituted fonts still fail.
- [x] Use selected heading/body/numeral roles when preparing local CSS and fonts; keep bundled pinned license checks.
- [x] Support authorized custom fonts without requiring all projects to use a particular family.

### 3. Integration And Verification

- [x] Synchronize canonical runtime into the starter template and validate JSON/frontmatter/reference links.
- [x] Run focused design, font, stage, and portability tests; final full suites passed with 512 Python tests and 104 Node tests.
- [x] Build/check the wheel and use isolated four-host installer smoke tests.
- [x] Independently replay supplied-brand, dense-information, composition-study, and follow-up-edit requests; also execute a real local typographic Concept without paid calls.
- [x] Record outcomes and limitations in `docs/superpowers/reviews/2026-09-12-creative-workflow-verification.md`; the previously paused security audit is not declared complete.
