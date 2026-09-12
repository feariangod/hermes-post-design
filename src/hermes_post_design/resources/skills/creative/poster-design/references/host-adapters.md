# Host Adapters

This Skill names outcomes, not provider APIs. Inspect the current host's available capabilities and use only a compatible route that the host can perform locally and safely.

## Production Before Capability

Choose production from the design agreement first:

```text
design needs -> image-led / layered / deterministic production
generation needed -> compatible capability + authorization + remaining call budget
generation unnecessary -> local composition even when an image tool is available
generation unavailable or declined -> adapt to authorized local assets and composition
ambiguous external failure -> stop and reconcile before any repeat or failover
```

For layered production, map generation only to the layers that benefit from it. Retain original identity assets and compose editable copy locally. `design.route` records production intent; `provider` records the actual image-call capability and budget, or `deterministic-local` when no image calls are used. These are separate decisions.

An image tool is compatible only when it can produce the required layer or visual and accepts the required inputs. Final poster dimensions may be reached by deterministic composition; verify the decoded final size. Do not infer compatibility from a tool name, a prior host, or an undocumented option.

## Authorization Boundary

Before a billed or external call, establish explicit authorization covering the selected capability, external/billing implications, outputs, and bounded number of calls. Check whether the user's existing authorization already covers this operation and remaining budget. Do not ask again for each call within that same scope. A visual approval, generic request for a poster, or authorization for a different operation is not enough. Ask once for missing authorization; a direction-revision budget never grants call authorization.

If authorization is declined or no compatible image capability exists, continue with the deterministic local route and authorized assets. Disclose any material design compromise. Do not keep asking after a decline unless the user changes the request or offers new authorization. If authorization is merely missing, request it once or proceed locally without making the call.

Count every attempted call, including studies, refinements, and ambiguous failures. If a network failure is ambiguous, preserve artifacts and stop; reconcile whether the operation completed or was billed. Do not retry or fail over automatically. A possibly duplicate operation requires explicit user authorization that acknowledges that uncertainty; routine remaining budget alone does not resolve it.

## Deterministic Local Route

The deterministic local route is a complete delivery route and often the first choice for information-heavy work. Compose from authorized local assets, typography, and purposeful graphic elements. Keep critical facts, identity assets, logos, and QR codes deterministic; apply the same Concept, Publish, and Release gates.

When production or capability changes, record the reason in project state. Do not discard an accepted design because a new host offers a different tool. Without compositing/rendering or visual-review capability, hand off the project and name the missing check; do not claim to have delivered or inspected an image.

## Codex adapter

Map required generation to an available **Codex image generation capability** only after checking external/billing behavior and whether existing authorization covers the operation. Pass the layer brief, dimensions, approved assets, and edit/generation intent through the capability; do not expose provider-only flags in the core workflow. Use visual inspection capabilities for the relevant rendered artifacts. Missing image generation can use local composition; missing visual inspection requires an actual human review or an explicitly unverified handoff, never an invented manual-review result.

## Hermes adapter

Map the capability seam to Hermes `image_generate` when that tool is installed and compatible. The optional bundled Chiyi provider uses `size="WIDTHxHEIGHT"` and `quality=high`; it does not accept an `aspect_ratio` substitute. Treat Chiyi as external and potentially billed, keep credentials outside project state, and count every attempted call against the authorized budget. Hermes installations without the optional provider remain complete through the deterministic local route.

## Claude or MCP adapter

Map the seam to an available **Claude or MCP image capability** after reading that capability's documented generation, editing, asset, size, billing, and external-call behavior. Do not infer option names from Codex or Hermes. Use a host visual-analysis capability only when its observed result can be recorded; otherwise complete visual review manually from the rendered target and mobile artifacts. Missing or incompatible MCP tools route to deterministic local composition.

## Unknown-host adapter

Probe only documented local capabilities. If the host cannot prove compatible image generation/editing, billing visibility, and authorization accounting, select the deterministic local route. Never guess a command name, provider flag, retry policy, or credential location for an unknown host.

## Capability-oriented visual review

Release always requires inspection of the exact target and phone-scale artifacts. Use the current host's compatible visual-analysis capability when one exists, or perform a direct human-visible review and record it with `record-visual-review.mjs`. The core contract names the observable checks and evidence files; it never requires a provider-specific analysis command.
