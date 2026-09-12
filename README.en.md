<h1 align="center">Poster Design Skill</h1>

<p align="center">One creative idea, carried through copy, typography, imagery, and the finished poster.</p>

<p align="center">
  <a href="https://github.com/feariangod/hermes-post-design/actions/workflows/ci.yml?query=branch%3Amain"><img src="https://img.shields.io/badge/CI-view_runs-0969da" alt="CI workflow runs"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-1f883d" alt="Code license: MIT"></a>
</p>

<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

<p align="center">
  <a href="#in-practice">In practice</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#creative-workflow">Workflow</a> ·
  <a href="#agent-support">Agent support</a> ·
  <a href="docs/guide.md">Full guide</a>
</p>

A poster-design Skill for **Agents, Codex, Claude, and Hermes**, with a creative workflow and local rendering, review, and delivery tools.

## In Practice

**Build On Site · Offline AI competition · Concept test**

<p align="center">
  <a href="docs/examples/ai-offline-competition.md"><img src="docs/assets/ai-competition-concept.png" alt="Concept poster with sculptural Chinese lettering, lime cursors, an orange joint, the September 28 date, and a visible pending-confirmation label" width="480"></a>
</p>

> **Concept / awaiting confirmation.** This is an actual case-test output, not an announcement of a real event. Year, time, and format are test assumptions; venue and registration remain unresolved. The headline is image lettering, not an editable font. The other 12 copy strings are editable HTML text.

Starting with an offline AI competition on September 28, this iteration makes the Chinese headline an object being assembled. Lettering, cursors, and components express one idea: hands-on creation.

[See the two iterations, design trade-offs, and verification scope](docs/examples/ai-offline-competition.md)

## Quick Start

You need **Python 3.11–3.13, Node.js 22, Git**, and a GitHub account with access to this repository. This example installs into Codex on macOS or Linux. The [full guide](docs/guide.md#prepare-the-checkout) covers Windows, other hosts, backups, and restore.

**1. Get the source and prepare the installer**

```bash
git clone https://github.com/feariangod/hermes-post-design.git
cd hermes-post-design
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
```

**2. Preview the installation**

```bash
./.venv/bin/hermes-post-design install-skill --target codex
```

The default is a dry run with no writes. Review the destination paths, then apply:

```bash
./.venv/bin/hermes-post-design install-skill --target codex --apply
```

For another host, replace `codex` in both commands with `agents`, `claude`, or `hermes`. Install only your chosen target. The installer manages Skill files and backs up existing versions; it does not set credentials, change unrelated configuration, or request an image.

**3. Make your first poster**

Reload Skills or start a new host session, confirm it can discover `poster-design`, then ask:

> Use poster-design to create a mobile-sharing poster for an offline AI competition on September 28. Establish a creative idea and carry it through copy, typography, and imagery. Time, venue, and registration are unconfirmed, so start with a clearly labeled Concept. Before external or billed image generation, explain the operation and call budget.

The first poster project also needs its own Node dependencies, prepared fonts, and an available Chrome, Edge, or Playwright Chromium browser. Have the agent follow the [local runtime steps](docs/guide.md#create-a-poster-project). Installing the Skill alone does not prepare a renderable project.

## Creative Workflow

**Communication brief → Creative proposition → Production route → Concept → Confirmation and refinement → Checked delivery**

| Step | Design focus |
| --- | --- |
| Communication | Identify the audience, first-glance message, and action. Separate confirmed facts from unresolved details. |
| Creative proposition | Carry a brief-specific idea through copy, type, imagery, composition, color, and material. Restraint can be an intentional role. |
| Typography | Assign heading, body, and numeral roles. A headline can become the key visual; critical information stays precise and readable. |
| Concept and refinement | Use a known direction directly, or compare inexpensive studies when composition is uncertain. Record locked principles and flexible details after confirmation. |
| Actual review | Inspect the real output and phone preview. Assess creative expression, factual accuracy, and technical delivery separately. |

### Three Production Routes

| Route | Best suited to | Approach |
| --- | --- | --- |
| **Image-led** | Key-visual-led posters with sparse copy | Generate useful visual layers, then verify and compose as the brief requires. |
| **Layered** | Real products, people, logos, or frequently revised information | Preserve required original assets and separate backgrounds, images, and editable information. |
| **Deterministic** | Information-dense posters and repeatable local rendering | Use HTML/CSS, local fonts, and authorized assets without an external image service. |

An available image tool does not decide the production route. Font licensing, asset provenance, and fact checks apply whichever tools are used.

## Agent Support

One [SKILL.md](src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md) carries the common workflow; [host adapters](src/hermes_post_design/resources/skills/creative/poster-design/references/host-adapters.md) describe environment-specific capabilities. The repository retains its `hermes-post-design` name, but the core Skill is no longer Hermes-only.

| Target | Installer flag | Installed components |
| --- | --- | --- |
| Common Agents directory | `--target agents` | Common Skill and local runtime |
| Codex | `--target codex` | Common Skill and local runtime |
| Claude | `--target claude` | Common Skill and local runtime |
| Hermes | `--target hermes` | Common Skill, local runtime, and optional-to-enable Chiyi Skill/plugin files |

**Verification boundary:** CI tests isolated installation and restore for all four targets. That is not an end-to-end creative test in four live agents. The current host must confirm actual image generation, image inspection, and external-call permissions. Without image generation, deterministic local production remains an option; missing visual review must be reported as unverified.

## Delivery And Boundaries

| Stage | Meaning |
| --- | --- |
| **Concept** | A visual direction awaiting confirmation, visibly labeled and not approved for publication. |
| **Publish** | Refinement within the user's approval, with applicable publication checks satisfied. |
| **Release** | Stricter delivery for print, complete source packages, and other demanding uses, with final-state, asset, font-license, and visual evidence. |

A rendered PNG is not acceptance, and passing technical checks does not prove expressive design. Generated lettering is not automatically editable type. A phone preview does not establish print readability.

Strict Release currently requires all approved copy to use visible DOM or SVG text; image/path-only lettering and hidden alternatives cannot satisfy that check. Verified image lettering may still be used in Concept or Publish when the applicable stage rules permit non-editable text.

External or billed image calls require explicit authorization and a bounded call budget; visual approval is not call authorization. Credentials stay outside the repository, copy, project configuration, command arguments, and logs. Installation and automated tests do not call an image service, although initial dependency installation may use the network.

## Documentation And Development

| Entry | Contents |
| --- | --- |
| [Operator guide](docs/guide.md) | Environment setup, four host targets, restore, local projects, and the optional Chiyi adapter |
| [Case notes](docs/examples/ai-offline-competition.md) | Two iterations of one brief, typography trade-offs, and verification scope |
| [Skill entry point](src/hermes_post_design/resources/skills/creative/poster-design/SKILL.md) | The agent-facing workflow, stages, and gates |
| [Development and verification](docs/guide.md#development-and-verification) | Python, Node, package parity, and install/restore checks |

Install test dependencies inside the source checkout; install each poster's runtime dependencies inside that poster project. Showcase images live in `docs/assets/` and are not included in the installed Skill or Python wheel.

## License

Repository code and templates use the [MIT License](LICENSE). Fonts, external assets, and model outputs retain their applicable terms. A showcased case is not a guarantee of third-party rights or suitability for commercial use.
