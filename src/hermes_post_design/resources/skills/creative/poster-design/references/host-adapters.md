# Host Adapters

This Skill names outcomes, not provider APIs. Inspect the current host's available capabilities and use only a compatible route that the host can perform locally and safely.

## Capability Selection

Use this order without skipping a branch:

```text
authorized compatible image tool -> image-led concept
available but billed/external and not authorized -> request authorization once
declined, missing, or incompatible image tool -> deterministic local concept
ambiguous network failure -> stop; do not retry without fresh authorization
```

An image tool is compatible only when it can produce or edit the requested visual at the required size and accepts the assets needed by the brief. Do not infer compatibility from its name, a prior host, or an undocumented option.

## Authorization Boundary

Before a billed or external call, state the selected capability, that the call may be billed or leave the local environment, and the immediate output it will produce. Ask once for explicit authorization. A visual approval, a request for a poster, or an earlier authorization for a different call is not authorization for this call.

If authorization is declined, unavailable, or no compatible image capability exists, continue with the deterministic local route. Do not keep asking after a decline unless the user changes the request or offers a new authorization.

If a network failure is ambiguous, preserve the current artifacts and stop. Do not retry, fail over to another external capability, or make a billed call until fresh authorization is received.

## Deterministic Local Route

The deterministic local route is a complete delivery route, not a placeholder. Compose the poster from local or user-authorized assets, deterministic typography, shapes, gradients, and local rendering tools. Keep critical facts, identity assets, logos, and QR codes deterministic; render and inspect the same Concept, Publish, and Release gates required by the main Skill.

When the route changes, record the chosen route and reason with the project state so a resumed session does not silently switch capabilities.

## Codex adapter

Map the capability seam to an available **Codex image generation capability** only after checking whether the operation is external or billed and whether the current request already authorizes that call. Pass the brief, exact dimensions, approved assets, and edit/generation intent through the capability; do not expose provider-only flags in the core workflow. Use Codex visual inspection capabilities for target and phone-scale review when available. When image generation or visual inspection is unavailable, use the deterministic local route and record a manual visual-review result without inventing tool evidence.

## Hermes adapter

Map the capability seam to Hermes `image_generate` when that tool is installed and compatible. The optional bundled Chiyi provider uses `size="WIDTHxHEIGHT"` and `quality=high`; it does not accept an `aspect_ratio` substitute. Treat Chiyi as external and potentially billed, keep credentials outside project state, and count every attempted call against the authorized budget. Hermes installations without the optional provider remain complete through the deterministic local route.

## Claude or MCP adapter

Map the seam to an available **Claude or MCP image capability** after reading that capability's documented generation, editing, asset, size, billing, and external-call behavior. Do not infer option names from Codex or Hermes. Use a host visual-analysis capability only when its observed result can be recorded; otherwise complete visual review manually from the rendered target and mobile artifacts. Missing or incompatible MCP tools route to deterministic local composition.

## Unknown-host adapter

Probe only documented local capabilities. If the host cannot prove compatible image generation/editing, billing visibility, and authorization accounting, select the deterministic local route. Never guess a command name, provider flag, retry policy, or credential location for an unknown host.

## Capability-oriented visual review

Release always requires inspection of the exact target and phone-scale artifacts. Use the current host's compatible visual-analysis capability when one exists, or perform a direct human-visible review and record it with `record-visual-review.mjs`. The core contract names the observable checks and evidence files; it never requires a provider-specific analysis command.
