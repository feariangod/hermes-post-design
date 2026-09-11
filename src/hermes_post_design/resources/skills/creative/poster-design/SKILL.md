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

Create a poster whose visual direction, readable copy, assets, and delivery claim are appropriate to the requested stage. Use only capabilities actually available in the current host.

## Route

1. Read [host-adapters.md](references/host-adapters.md) before selecting an image-led or deterministic-local route, or before any external operation.
2. Before gathering the brief, read [intake.md](references/intake.md) to collect only what changes the route, visual direction, or factual responsibility.
3. When no visual direction is explicit, read [concept-directions.md](references/concept-directions.md) and present two or three text-only directions before creating a concept.
4. Before using identity-bearing, branded, product, QR, or reference assets, read [asset-policy.md](references/asset-policy.md).
5. Before placing or accepting readable text, read [typography.md](references/typography.md).
6. Before reporting Concept, Publish, or Release status, read [quality-rubric.md](references/quality-rubric.md).

## Stages

```text
intake -> route_selected -> concept -> user confirmation -> publish -> release when requested
```

- **Concept:** make one final-size, near-production visual through the selected route. Label it `concept — awaiting confirmation`; it is never publish-ready.
- **Publish:** after confirmation, preserve the locked direction and make only bounded defect corrections. Deliver an exact-size PNG with the applicable Publish evidence.
- **Release:** enter only for print, PDF, full editability, localization, regulated/high-responsibility claims, paid-campaign evidence, or a complete source package. Reuse the locked visual and apply the strict publication workflow.

Do not invent unresolved critical facts. A generated readable string is not proof of a true claim. Independently verify names, dates, prices, places, URLs, contacts, rules, QR destinations, and scientific, legal, medical, or financial statements against the approved fact contract.

## Gates

- A user approving a brief or visual direction does not authorize a billed or external operation. Follow the explicit authorization and failure rules in [host-adapters.md](references/host-adapters.md).
- Do not advance from Concept until the user confirms the visual direction.
- After confirmation, preserve composition, visual center, palette, subject scale, information zones, and mood. Escalate a repeated failing element to deterministic local treatment instead of reopening visual exploration.
- Use authorized original assets for real identities, product/package details, logos, and QR codes wherever the asset policy requires fidelity.
- Report the actual stage and named blocker when a required check is absent or fails.

## Verification Truth

Inspect the rendered artifact, not merely a successful tool response. At the applicable stage, verify decoded dimensions, non-empty output, exact approved text and facts, authorized identity and brand treatment, QR payload when present, artifacts/clipping, and phone-scale readability. Release evidence becomes stale after a render or source change.
