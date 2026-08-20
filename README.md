# Hermes Post Design

Private, reproducible Chiyi GPT Image 2 and poster workflow for Hermes Agent.

This repository packages four things that previously lived separately on one machine:

- a platform-neutral Chiyi client for text generation and multi-reference editing;
- a thin provider for the current Hermes `image_generate` plugin interface;
- the `chiyi-image-generation` and `poster-design` skills;
- a small CLI that installs, updates, backs up, and restores those Hermes resources.

## Scope

Version `0.1.0` intentionally keeps a narrow support boundary:

- Python `3.11` to `3.13`;
- current Hermes Agent ImageGen plugin API;
- Windows verified first; macOS/Linux use the same Python paths but are not yet machine-tested;
- Chiyi provider/model/quality fixed to `chiyi` / `gpt-image-2` / `high`;
- one image per paid request;
- exact final dimensions through `size="WIDTHxHEIGHT"`;
- up to 16 source images for editing;
- one automatic retry only for an explicit HTTP `429`.

Legacy Hermes compatibility shims, Docker validation, and a standalone visual poster editor are not part of v0.1.

## Install

Clone the private repository and install it into the Python environment used by Hermes:

```bash
git clone https://github.com/feariangod/hermes-post-design.git
cd hermes-post-design
python -m pip install .
```

Preview the files that would be deployed:

```bash
hermes-post-design sync --hermes-home "$HERMES_HOME"
```

Apply the deployment:

```bash
hermes-post-design sync --hermes-home "$HERMES_HOME" --apply
```

Install the optional Poster HTML/PDF runtime dependencies after the first sync:

```bash
npm ci --prefix "$HERMES_HOME/skills/creative/poster-design"
```

The renderer uses an installed Chrome/Edge when available. If neither is available, install Playwright Chromium explicitly:

```bash
npx --prefix "$HERMES_HOME/skills/creative/poster-design" playwright install chromium
```

The sync command manages only these paths:

```text
$HERMES_HOME/plugins/image_gen/chiyi/
$HERMES_HOME/skills/media/chiyi-image-generation/
$HERMES_HOME/skills/creative/poster-design/
```

It does not edit `.env`, `config.yaml`, provider credentials, or unrelated plugins and skills. Existing managed paths are copied to:

```text
$HERMES_HOME/backups/hermes-post-design/<UTC timestamp>/
```

## Configure Hermes

Store `CHIYI_IMAGE_API_KEY` using the normal Hermes secret/configuration workflow. Do not put it in this repository.

Enable the deployed user plugin and select it as the image provider using current Hermes commands:

```bash
hermes plugins enable chiyi
hermes tools
```

In `hermes tools`, choose Image Generation, select `Chiyi GPT Image 2`, and keep the fixed model and quality. Restart the gateway after changing plugin or provider configuration.

Check installation state without printing the key:

```bash
hermes-post-design doctor --hermes-home "$HERMES_HOME" --json
```

## Use In Hermes

Text generation:

```text
image_generate(
  prompt="A restrained editorial poster for an AI workshop",
  size="1080x1920"
)
```

Image editing:

```text
image_generate(
  prompt="Preserve the product and redesign the scene as a premium studio campaign",
  image_url="C:/path/to/primary.png",
  reference_image_urls=["C:/path/to/reference.png"],
  size="1080x1920"
)
```

Do not pass `aspect_ratio`, `quality`, `model`, or `n`. The provider fixes them deliberately.

## Standalone CLI

The CLI reads `CHIYI_IMAGE_API_KEY` from the process environment. It does not accept a key on the command line.

```bash
hermes-post-design generate "A typographic film poster" \
  --size 1080x1920 \
  --output-dir ./artifacts
```

```bash
hermes-post-design edit "Keep the subject; use the reference lighting" \
  --image ./primary.png \
  --reference ./lighting-reference.png \
  --size 1080x1920 \
  --output-dir ./artifacts
```

Add `--json` for machine-readable output.

## Update And Restore

Update the checkout, reinstall the package, preview the sync, then apply it:

```bash
git pull --ff-only
python -m pip install --upgrade .
hermes-post-design sync --hermes-home "$HERMES_HOME"
hermes-post-design sync --hermes-home "$HERMES_HOME" --apply
npm ci --prefix "$HERMES_HOME/skills/creative/poster-design"
```

Restore a backup created by sync:

```bash
hermes-post-design restore \
  --hermes-home "$HERMES_HOME" \
  --backup "$HERMES_HOME/backups/hermes-post-design/<timestamp>"
```

Restore only affects the three managed paths listed above.

## Architecture

```text
Hermes image_generate
        |
        v
thin ImageGen provider  ---- standalone CLI
        |                       |
        +----------+------------+
                   v
              Chiyi Core
  request models / sizing / source loading
  HTTP + bounded retry / SSE / image validation
  exact-size normalization / atomic artifact save
```

The provider contains no duplicated HTTP, image, or SSE implementation. This keeps Hermes adaptation small while the Core remains independently testable.

## Safety And Billing

The Core provides practical boundaries for this workflow:

- validates local files, strict Base64 data URLs, and public HTTP(S) sources;
- blocks private/loopback/link-local remote targets and revalidates redirects;
- limits compressed image inputs and outputs to 25 MiB and decoded images to 40 MP;
- rejects animated images;
- validates and atomically saves final image artifacts;
- disables redirects on paid POST requests;
- retries only an explicit HTTP `429`, at most once;
- does not retry ambiguous network failures, `5xx`, malformed success responses, SSE failures, downloads, or save failures;
- does not include keys, Authorization headers, image bytes, Base64 payloads, or URL queries in returned errors.

## Development

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[test]"
./.venv/Scripts/python.exe -m pytest -q -o "addopts="
./.venv/Scripts/python.exe -m pip wheel . --no-deps -w dist
```

The test suite is offline: it uses fakes and mocks and does not submit paid Chiyi requests.

## Repository Hygiene

The repository intentionally excludes:

- API keys and Hermes configuration;
- user images, logos, portraits, QR codes, and other private assets;
- generated PNG/PDF artifacts;
- Hermes logs, sessions, caches, backups, and databases;
- `.venv`, `node_modules`, build output, and test caches.

## License

MIT for repository code and templates. External assets, fonts, generated media, model outputs, and user-supplied material retain their own terms and are not included here.
