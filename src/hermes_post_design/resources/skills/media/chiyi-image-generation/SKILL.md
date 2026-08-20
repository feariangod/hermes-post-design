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

Use the native `image_generate` tool. The active backend fixes the request to the live Chiyi model `gpt-image-2` with `quality: high`; `low` and `medium` are not exposed. Control dimensions only with `size="WIDTHxHEIGHT"`, for example `1080x1920`; do not pass `aspect_ratio`. The default size is `1024x1024`. Sizes are deterministic final-output dimensions; report both the measured final dimensions and, when present, the upstream canvas, and never relabel either as native 4K.

## Count Rules

- When the user gives no image count, make exactly one `image_generate` call.
- When the user explicitly asks for 2-8 images, emit that many independent `image_generate` calls in the same assistant turn so Hermes executes them in parallel.
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
- If a paid edit returns a network error, do not loop retries because billing state is ambiguous. Inspect the structured exception/stream result, then use a fresh explicit user-authorized call only when another paid acceptance is necessary.

## Delivery

- Return every successful local image artifact through native media delivery.
- For partial batch failure, report requested, successful, and failed counts accurately, while still delivering successful images.
- Never invent paths for failed calls or claim an output resolution that was not measured from the returned artifact.
