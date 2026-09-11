# Repository Architecture And Audit Boundary

## Audit Date And Scope

This document describes the repository architecture as of 2026-09-11 on the implementation branch `codex/portable-poster-skill`. It replaces the pre-feature baseline that described a two-file repository without tests or CI.

The current repository is a portable Agent Skill and deterministic poster runtime with an optional Hermes-specific Chiyi adapter. This audit records the code and verification boundary; it is not evidence that the Skill has been deployed to a live host or that any poster is Publish or Release ready.

## Current Components

- `src/hermes_post_design/install.py`: target-aware dry-run, transactional install, backup, and restore for Agents, Codex, Claude, and Hermes.
- `src/hermes_post_design/resources/skills/creative/poster-design`: canonical portable Skill, references, starter project, pinned Node runtime, and QA scripts.
- `src/hermes_post_design/chiyi_core`: platform-neutral optional Chiyi client with bounded requests, source validation, artifact normalization, and redacted errors.
- `src/hermes_post_design/resources/plugins/image_gen/chiyi`: thin Hermes provider over the shared client.
- `src/hermes_post_design/resources/skills/media/chiyi-image-generation`: Hermes-only image-generation Skill.
- `tests`: Python contract, installer, packaging, client, provider, and zero-network fixture coverage plus Node runtime integration tests.
- `.github/workflows/ci.yml`: Python 3.11-3.13, Node 22, wheel, and four-target installer verification.

## Installation Boundary

The generic installer manages only these target paths:

```text
agents: skills/poster-design
codex:  skills/poster-design
claude: skills/poster-design
hermes: skills/creative/poster-design
        skills/media/chiyi-image-generation
        plugins/image_gen/chiyi
```

Planning is read-only. Apply stages filtered resources, backs up prior managed paths under the selected temporary or host home, and replaces them transactionally. Restore accepts only a target-matched backup below that same home's application backup directory. Parent and resource symlink escapes are rejected.

No installer path writes host credentials, `.env`, provider selection, gateway configuration, unrelated skills, or external state. Verification must use explicit temporary homes unless a live host change is separately authorized.

## Poster Runtime Boundary

The portable Skill routes each request through `references/host-adapters.md`:

```text
authorized compatible image capability -> image-led concept
unauthorized billed/external capability -> one authorization request
declined, absent, or incompatible capability -> deterministic local concept
ambiguous network result -> stop pending fresh authorization
```

The deterministic route is fully local and remains subject to the same stage and QA contracts. Each initialized project contains its own package lock, scripts, state schemas, templates, font preparation, font/license manifests, renderer, inspector, and visual-review recorder. Runtime dependencies are installed into that project with `npm ci`.

`poster.json` records the adapter name, whether it is external or billed, and authorized/used call counts. Used calls cannot exceed the authorized budget. Credentials and raw provider errors are not valid project state or evidence.

## Truthful Delivery Boundary

- Concept is final-size and near-production, but remains labeled as awaiting confirmation.
- Publish requires user confirmation and applicable mechanical QA evidence.
- Release is a stricter state requiring final configuration, exact artifacts, source and font/license evidence, fresh render hashes, and recorded visual review.
- Successful rendering or an image adapter artifact alone does not prove Publish or Release readiness.

## Packaging And Sensitive Content

One shared resource predicate controls installation digests and copies. Setuptools exclusions and `MANIFEST.in` provide a second packaging boundary. Tests compare clean and deliberately polluted wheel resources and reject:

- `node_modules`, virtual environments, caches, coverage, build output, and package metadata inside resources;
- generated PNG/PDF and other media, logs, reports, sessions, and state databases;
- `.env` variants, auth/config files, credentials, and secret directories;
- host homes, backups, temporary projects, and user artifacts.

The repository must not contain API keys, access tokens, passwords, private host configuration, personal absolute paths, unlicensed private assets, or generated production artifacts.

## CI And Local Verification

CI runs:

- the full Python suite on Python 3.11, 3.12, and 3.13;
- the Skill runtime sync test and every `tests/runtime/*.test.mjs` test on Node 22;
- clean/polluted wheel parity plus an independently inspected wheel built from a source tree containing `node_modules`;
- isolated dry-run, apply, installed-tree parity, and restore smoke tests for `agents`, `codex`, `claude`, and `hermes`.

Local release verification additionally runs the official Skill validator against the canonical Skill and each isolated installed copy. Fake adapter verification is local, deterministic, and contains no network code or paid request.

## Preserved Restrictions

- Do not write live `~/.agents`, `~/.codex`, `~/.claude`, or `~/.hermes` during tests.
- Do not call a paid or external image provider without explicit authorization for that bounded call.
- Do not commit credentials, generated media, host state, dependency directories, or build artifacts.
- Do not push, publish, deploy, or claim host-runtime readiness from CI alone.
- Preserve the MIT license and record separate licenses for external assets and bundled project fonts.

The repository owner retains the decision to review, merge, install into a live host, publish artifacts, or authorize any external provider call.
