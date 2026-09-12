---
name: poster-design
description: Use when creating information-bearing posters for digital sharing, events, campaigns, long-form layouts, or print release packages.
license: MIT
metadata:
  version: 0.4.0
  author: feariangod
  hosts: [agents, codex, claude, hermes]
---

# Poster Design

Design the communication first, choose the production method second, then use the capabilities actually available in the current host. A poster succeeds when its intended audience sees the right message and can take the intended action.

Carry one brief-specific creative proposition through the whole poster. Copy, typography, imagery, composition, color, and material each need an intentional role in that expression; restraint can be the right role. Preserve the idea through production and refinement, and assess its visible expression separately from technical correctness.

## Route

1. Before creating the brief, read [intake.md](references/intake.md). Record the audience, viewing context, first-glance message, action, information hierarchy, and brand constraints in `poster.json.design`.
2. Before choosing production, read [asset-policy.md](references/asset-policy.md). Plan which layers must retain original pixels, which need editable text, and which benefit from generation. Choose image-led, layered, or deterministic production for those needs, not because an image tool exists.
3. Read [host-adapters.md](references/host-adapters.md) before executing the chosen production method or any external operation. Check capability, existing authorization, and remaining call budget; record any necessary adaptation.
4. Before developing or refining a visual direction, read [concept-directions.md](references/concept-directions.md). Make the creative proposition visible across the planned layers, including a direct Concept. Use an explicit direction directly; when composition is uncertain, offer two or three inexpensive studies within the agreed budget. Text options are available, not a mandatory gate.
5. Before composing or accepting readable text, read [typography.md](references/typography.md). Decide how type expresses or supports the idea, then choose heading, body, and numeral roles using local licensed fonts and exact approved copy.
6. Before reporting a study, Concept, Publish, or Release result, read [quality-rubric.md](references/quality-rubric.md). Review creative expression and technical correctness in the actual viewing context; address the highest-impact problems first.

Before initializing, preparing, rendering, inspecting, or handing off a local poster project, read [local-runtime.md](references/local-runtime.md). It contains the installed Skill's self-contained commands and evidence sequence.

## Stages

```text
design agreement -> production route -> optional studies -> concept -> scoped confirmation -> refinement -> delivery
```

- **Studies:** optional low-cost composition comparisons, labeled `composition study - not for publication`. They may omit unresolved facts and use blank zones, but must not invent facts or misspell displayed approved copy. They are activities within `route_selected`, not finished Concepts.
- **Concept:** develop one selected direction into a final-size, near-production visual. Label it `concept — awaiting confirmation`; it is never publish-ready.
- **Publish:** record what the user approved and what may still change. Refine typography, spacing, crop, and factual details within that scope; deliver an exact-size PNG with applicable Publish evidence.
- **Release:** enter only for print, PDF, full editability, localization, regulated/high-responsibility claims, paid-campaign evidence, or a complete source package. Apply the strict publication workflow to the approved design.

Runtime stages remain `intake -> route_selected -> concept -> visual_locked -> publish -> release`, with `needs_rebrief` for a diagnosed brief conflict. Studies and refinements do not add stages.

Do not invent unresolved critical facts. A generated readable string is not proof of a true claim. Independently verify names, dates, prices, places, URLs, contacts, rules, QR destinations, and scientific, legal, medical, or financial statements against the approved fact contract.

## Gates

- A user approving a brief or visual direction does not authorize a billed or external operation. Follow the explicit authorization and failure rules in [host-adapters.md](references/host-adapters.md).
- Do not advance from Concept until the user confirms the visual direction.
- Record approval evidence and separate locked principles from flexible details in `design.approval`. A local readability correction is not automatically a new direction; a change to a locked principle requires renewed confirmation.
- Count rejected directions in `conceptRevision`, bounded by `design.exploration.directionBudget`. Count actual image calls separately in `provider`. Diagnose repeated rejection; do not impose a universal one-revision limit or generate indefinitely.
- Use authorized original assets for real identities, product/package details, logos, and QR codes wherever the asset policy requires fidelity.
- Report the actual stage and named blocker when a required check is absent or fails.

## Verification Truth

Inspect the rendered artifact, not merely a successful tool response. Verify dimensions, content, authentic assets, QR payloads, and artifacts at the applicable stage. Use phone previews for phone delivery, representative crops for feeds, and physical-size/distance checks for print. Release retains target and mobile evidence; a mobile check does not prove print readability. Report the actual stage and unverified checks. Release evidence becomes stale after a render or source change.
