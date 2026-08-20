# Concept Directions and Prompt Compilation

Use this reference only before Concept generation. Select one archetype, make its visible design choices concrete, then compile one prompt. Archetypes are starting structures, not fixed visual styles.

## Direction option format

When the user has no explicit visual direction or reference, offer two or three text-only options. Each option contains:

- a short direction name;
- one-sentence visual proposition;
- hero and layout skeleton;
- palette and material language;
- one sentence explaining the fit.

Do not generate preview images at this gate. After selection, combine compatible details from only the selected option; do not create a hybrid of every option.

## Archetypes

### 1. Conversion-led event or course

- **Use when:** the poster must drive registration, attendance, or a time-bound action.
- **Avoid when:** the main value is an object, atmosphere, or title experiment rather than an offer.
- **Skeleton:** decisive headline zone, one human or symbolic hero, compact proof/fact band, isolated action zone.
- **Text budget:** one headline, one promise, essential facts, one call to action.
- **Craft controls:** directional light toward the action, high figure-ground contrast, restrained accent color, visible route from headline to action.
- **Failure modes:** marketing-card collage, equal emphasis everywhere, tiny facts, decorative hero unrelated to the offer.
- **Risk:** names, dates, prices, venues, contacts, logos, and QR destinations require approved sources.

### 2. Sports action Campaign

- **Use when:** motion, athletic identity, equipment, or competitive energy must dominate.
- **Avoid when:** the brief needs calm product inspection or dense explanatory copy.
- **Skeleton:** one athlete in a readable peak-action silhouette; one hero prop and the athlete's body/action line create a strong directional composition without breaking real grip or movement mechanics; title integrated with motion; sparse support copy.
- **Text budget:** one forceful headline, one short subheading, one call to action; data only when approved.
- **Craft controls:** low or tracking camera, directional blur confined to secondary edges, hard rim light, grounded contact shadow, disciplined brand-like palette. Choose a real action phase first, then align crop, body, prop, and type around that phase.
- **Failure modes:** noisy montage, anatomically impossible action, wrong equipment, detached or implausibly enlarged prop, forcing the prop axis to contradict real biomechanics, title covering the face or action joint.
- **Risk:** when technical action correctness is required, use an authorized action reference or choose a phase whose joints, grip, equipment contact, and balance can be verified from visible pixels; style words are not proof of biomechanics. A real athlete, kit, sponsor, team mark, or product must use authorized assets and Publish protection.

### 3. Product-led commercial hero

- **Use when:** product recognition, material, use benefit, or purchase intent is primary.
- **Avoid when:** a person, story, or information system is the real subject.
- **Skeleton:** one dominant product at an intentional angle, environment shaped around its silhouette, one benefit zone, one action zone.
- **Text budget:** product name, one promise, one or two verified benefits, one action.
- **Craft controls:** material-specific key and rim light, believable support/contact, controlled props, background contrast chosen for edge readability.
- **Failure modes:** random props, floating geometry, redesigned packaging, unreadable label, excessive promotional badges.
- **Risk:** package geometry, label, barcode, claims, and logo require the authorized source in Publish.

### 4. Conceptual typography

- **Use when:** a short title or phrase is the main meaning and visual structure.
- **Avoid when:** many facts, long copy, or precise identity imagery must compete with the title.
- **Skeleton:** one dominant title occupying the visual field; subject, object, or negative space intersects the letterforms; very little support copy.
- **Text budget:** one exact title and at most one supporting line.
- **Craft controls:** custom-looking weight, width, rhythm, edge, texture, cropping, and negative space; restrained four-to-six-color system.
- **Failure modes:** generic word art, moodboard sheet, unrelated icons, title detached from imagery, extra display text.
- **Risk:** exact spelling is the core asset; a famous person or protected campaign style requires identity and rights review.

### 5. Cinematic person-led narrative

- **Use when:** one person's emotion, role, or story creates the poster's meaning.
- **Avoid when:** identity cannot be supplied or the poster is primarily an information chart.
- **Skeleton:** one large face or body gesture, layered foreground/background event cues, title placed in controlled negative space, facts kept secondary.
- **Text budget:** title, short premise, essential facts, optional action.
- **Craft controls:** motivated key light, clear eye-line, lens and crop chosen for emotion, atmospheric depth tied to the narrative event.
- **Failure modes:** generic cinematic haze, unrelated scenery, face/title collision, collage with several competing portraits.
- **Risk:** a real person requires authorized pixels and identity comparison; generated resemblance is not fidelity.

### 6. Information or science explainer

- **Use when:** relationships, comparison, sequence, or evidence must be understood quickly.
- **Avoid when:** the brief only needs an atmospheric key visual.
- **Skeleton:** one dominant thesis/subject, three to five modules, explicit reading order, visual connectors only where they carry meaning.
- **Text budget:** short labels and one- or two-line explanations; move dense verified copy to deterministic layout.
- **Craft controls:** consistent module grammar, semantic color groups, meaningful scale differences, disciplined spacing, hero subject large enough to inspect.
- **Failure modes:** too many modules, equal-size everything, tiny paragraphs, ornamental arrows, card-grid UI replacing information design.
- **Risk:** scientific values, units, species, processes, and claims require independent fact verification.

### 7. Cultural material narrative

- **Use when:** history, place, craft, ritual, or material tradition is central.
- **Avoid when:** the brief calls for generic nostalgia without a specific cultural anchor.
- **Skeleton:** one authentic material or spatial motif as the frame, one narrative subject, title treated as part of the material system, restrained contextual details.
- **Text budget:** one title, one short contextual line, essential facts only.
- **Craft controls:** name the period/place/material, define surface behavior and edge quality, use negative space deliberately, keep modern elements out unless the concept requires contrast.
- **Failure modes:** mixed periods, souvenir aesthetics, indiscriminate motifs, fake calligraphy, overloaded ornamental borders.
- **Risk:** historical claims, scripts, symbols, dress, objects, and sacred imagery require source and cultural-context checks.

## Six-block prompt compiler

Compile the selected direction in this order:

1. **Deliverable and audience** — purpose, intended action, audience, viewing context, and exact final `size="WIDTHxHEIGHT"`.
2. **Core visual proposition** — selected archetype, one visual metaphor, mood, and first-glance message.
3. **Composition and information zones** — hero scale/position, title, support, facts/action zones, safe margins, depth, and reading order.
4. **Subject and asset roles** — subject/action, hero prop, camera, lighting, and explicit content/style/layout role for every reference.
5. **Approved copy hierarchy** — exact approved strings grouped as headline, subheading, facts, call to action, and permitted microcopy; allow no invented readable text.
6. **Constraints and output** — single finished poster, prohibited content/artifacts, exact dimensions, and provider constraints.

## Normalization

- Chiyi uses `size="WIDTHxHEIGHT"`; never pass `aspect_ratio`.
- Keep `quality=high`; do not expose another quality level.
- Remove resolution theater such as `2K/4K/8K`; report measured decoded dimensions instead.
- Ask for one finished poster, never a main-and-alternate pair, moodboard, process sheet, or option grid.
- Convert vague style words into visible composition, light, material, palette, lens, and typography choices.
- Keep approved copy in one authoritative block; never repeat conflicting variants.
- Reference preservation is semantic unless deterministic asset protection is required.
- Inspect unbranded subjects and equipment for logo-like marks, brand-like marks, pseudo-lettering, and signature shapes; a prompt saying “no logo” is not proof that none were generated.
- Render an actual phone-scale review image. Headline, subheading, facts, and call to action must all remain readable; do not infer subheading or CTA readability from the full-size canvas.

## Provenance boundary

Method inspiration was reviewed from `https://github.com/freestylefly/awesome-gpt-image-2` at revision `76fcd0e6b3961ef2b041547aac654f1efd1ef270`. This reference is an original synthesis. Do not copy upstream case images. Do not copy upstream full prompts. The upstream repository is not a runtime dependency. Review third-party rights independently before commercial use.