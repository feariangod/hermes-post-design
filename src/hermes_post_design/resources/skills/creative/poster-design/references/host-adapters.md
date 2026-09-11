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
