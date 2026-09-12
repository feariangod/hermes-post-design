---
name: chiyi-image-generation
description: "Use for Chiyi GPT Image 2 generation and editing."
version: 1.1.0
author: Hermes Agent
license: MIT
created_by: agent
metadata:
  hermes:
    tags: [image-generation, chiyi, gpt-image-2]
---

# Chiyi GPT Image 2 Generation

## When to Use

Use this skill whenever a user asks Hermes to generate, edit, or create multiple images through the active Chiyi backend.

Before any generation, edit, or batch, read the shared [authorization boundary](../../creative/poster-design/references/host-adapters.md#authorization-boundary). Chiyi is external and potentially billed. Confirm that explicit authorization covers this capability, its external/billing implications, intended outputs, and the remaining call budget before using the native `image_generate` tool. A visual approval or requested image count alone is not that authorization.

For a poster project, record the capability and authorized/used calls in `poster.json.provider`. For a standalone image request, keep the same authorization scope and attempt count in the task record. Count every attempted call, including failed calls; neither a new batch nor a new turn resets the budget.

The active backend fixes the request to the live Chiyi model `gpt-image-2` with `quality: high`; `low` and `medium` are not exposed. Control dimensions only with `size="WIDTHxHEIGHT"`, for example `1080x1920`; do not pass `aspect_ratio`. The default size is `1024x1024`. Sizes are deterministic final-output dimensions; report both the measured final dimensions and, when present, the upstream canvas, and never relabel either as native 4K.

## Count Rules

- When the user gives no image count, plan one `image_generate` call, only within an existing or newly granted authorization.
- When the user explicitly asks for 2-8 images, plan that many independent calls only if the remaining authorized budget covers them. Account for the whole planned batch before dispatch; independent calls may then run in parallel.
- If the requested count exceeds the remaining budget, explain the shortfall and ask once for additional authorization or a reduced count. Clearly identify any partial batch that the existing authorization already covers; never silently expand it to the requested count.
- Never emit more than eight image calls for one user request.
- Each call produces one image. Do not ask the backend for `n > 1`.

## Prompt Rules

- If the user requests exact repeats, use the identical prompt and parameters for every call.
- Otherwise, small composition or lighting variations are allowed when useful; disclose that variation briefly.
- Preserve the user's requested dimensions through `size`. Do not silently substitute the default output.
- Never pass `aspect_ratio` to the Chiyi backend.
- Custom sizes must stay within the provider's validated pixel and aspect-ratio limits; do not promise arbitrary upstream-native dimensions.

## Editing Rules

- Put the primary source in `image_url` and additional references in `reference_image_urls`.
- Reuse the same primary and reference image set for every image in an explicit multi-image edit request.
- The backend supports at most 16 total source/reference images.
- Validate the source's actual decoded format, not only its file extension. Chiyi rejects a WEBP payload renamed to `.jpg`; convert it to a real PNG or JPEG before an edit request.
- Chiyi multi-reference edits are long-running streaming requests. The provider must use repeated `image` multipart fields, request SSE with `stream=true`, `partial_images=1`, and `Accept: text/event-stream, application/json`, ignore partial previews, and save only a completed image. Do not revert to synchronous `image[]` requests: they can be closed by the upstream/CDN after roughly 60 seconds of response silence.

## Failure Boundary

For generation, editing, or a batch, an ambiguous network failure counts as an attempt. Preserve successful artifacts, inspect the structured exception/stream result, and reconcile whether the operation completed or was billed. Do not automatically retry or switch providers. Another possibly duplicate call requires explicit user authorization acknowledging the uncertainty, even when routine budget remains. Apply the shared authorization boundary above to every retry or new batch.

## Delivery

- Return every successful local image artifact through native media delivery.
- For partial batch failure, report requested, successful, and failed counts accurately, while still delivering successful images.
- Never invent paths for failed calls or claim an output resolution that was not measured from the returned artifact.
