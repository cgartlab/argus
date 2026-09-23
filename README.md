# Argus

[![CI](https://github.com/cgartlab/argus/actions/workflows/ci.yml/badge.svg)](https://github.com/cgartlab/argus/actions/workflows/ci.yml)
[![Argus-Flash Review](https://github.com/cgartlab/argus/actions/workflows/review.yml/badge.svg)](https://github.com/cgartlab/argus/actions/workflows/review.yml)
[![Release](https://github.com/cgartlab/argus/actions/workflows/release.yml/badge.svg)](https://github.com/cgartlab/argus/actions/workflows/release.yml)

Code review agent for frontend design. Runs as a GitHub App — install on any repo for automated PR reviews. Official site: https://argus.cgartlab.com

## What is Argus?

Argus is a cross-platform AI coding agent specialized in frontend design code review. Core strength: catches what others miss — hardcoded values, design token violations, a11y issues, dark mode gaps.

The **argus-flash** GitHub App (`github.com/apps/argus-flash`) runs Argus as an automated PR reviewer. Install it on any repo, add a minimal workflow, and every PR gets a full design review.

## Capabilities

- Design token audit (detect bare oklch/hex/rgb outside `:root`)
- Hardcoded value detection (magic numbers in spacing, radii, type scale)
- Accessibility review (aria-label, alt text, focus indicators, WCAG AA contrast)
- Dark mode coverage verification
- CSS consistency (duplicate rules, invalid BEM, empty catch blocks)
- HTML structure validation (semantic elements, link vs button)
- Framework API usage validation (React, Vue, Angular, Svelte, Astro)

## Local Toolchain & Integrations

Beyond the GitHub App, Argus ships a zero-dependency local toolchain (all under `tools/`, stdlib-only):

| Tool | What it does |
|---|---|
| `argus_review.py` | Local review CLI — same rules as the App, static or LLM (`--mode auto` complexity routing) |
| `argus_report.py` | Findings JSON → shareable static HTML report; `--wcag` adds a WCAG 2.2 compliance summary |
| `argus_rules.py` | Team-defined custom rules (rule DSL) — `config/argus-rules.schema.json` |
| `argus_webhook.py` | Forward findings reports to any webhook (Slack / Feishu / dashboards) |
| `eval_quality.py` | Precision / recall / F1 metrics + regression gates vs `config/quality-baseline.json` |
| `validate_argus_schema.py` | `.argus.yml` JSON Schema validation (zero-dep) |
| `validate_severity_matrix.py` | rule-id × severity matrix consistency |
| `add_fp_appeal.py` | File a false-positive appeal as a regression fixture |

Integrations: GitHub App (PR reviews) · GitLab MR template (`.gitlab/argus-review.yml`) · skill registries (SkillHub / ClawHub / skills.sh) · men agent team.

## Architecture

```
                     ┌─────────────────────────┐
                     │    argus-flash App       │
                     │  github.com/apps/argus-  │
                     │  flash                   │
                     └──────────┬──────────────┘
                                │ installation token
                     ┌──────────▼──────────────┐
                     │  workflow (review.yml)   │
                     │  in your repo            │
                     └──────────┬──────────────┘
                                │ uses:
                     ┌──────────▼──────────────┐
                     │  composite action        │
                     │  cgartlab/argus/.github/ │
                     │  actions/argus-review    │
                     │  @main                   │
                     └──────────┬──────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
         AGENTS.md          SKILL.md         OpenCode CLI
         (hard rules)   (review dims)     (run review)
              │                 │                 │
              └────────┬────────┘                 │
                       │ injected into            │
                       │ PROMPT at runtime        │
                       ▼                          │
              ┌──────────────────┐                │
              │  Review result   │◄───────────────┘
              │  → PR comment    │
              └──────────────────┘
```

Rules in `AGENTS.md` + `SKILL.md` are read dynamically at runtime by the composite action. Update them in the argus repo → all consumer repos pick up changes automatically.

## Quick Start

### In the Argus repo

```bash
git clone https://github.com/cgartlab/argus.git
cd argus
```

No installation, no build step.

### In any other repo

1. Install the **argus-flash** GitHub App at `github.com/apps/argus-flash`
2. Add `ARGUS_FLASH_APP_ID` and `ARGUS_FLASH_PRIVATE_KEY` to your repo's Actions secrets
3. Create `.github/workflows/argus-review.yml`:

```yaml
name: Argus-Flash Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with: { persist-credentials: false }

      - name: Generate argus-flash token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.ARGUS_FLASH_APP_ID }}
          private-key: ${{ secrets.ARGUS_FLASH_PRIVATE_KEY }}

      - uses: cgartlab/argus/.github/actions/argus-review@main
        with:
          github-token: ${{ steps.app-token.outputs.token }}
          api-key: ${{ secrets.OPENCODE_API_KEY }}
```

That's it. Every PR will automatically receive a design review comment from `argus-flash[bot]`.

### Configure your own API key

Argus reviews run on the **OpenCode Zen free model** (IDs end in `-free`). The model costs 0 USD per token, but every call still needs an **API key** — Argus never ships with one.

1. Register at https://opencode.ai (free) and create an API key at https://opencode.ai/auth
2. Add it as a repository secret: **Settings → Secrets and variables → Actions → New repository secret** → name `OPENCODE_API_KEY`
3. The workflow above already passes it through (`api-key: ${{ secrets.OPENCODE_API_KEY }}`) — no workflow changes needed
4. Re-trigger the review (re-run the workflow, or push a new commit to the PR)

**Local runs:** `opencode auth login` — choose **OpenCode** and paste your key — or set the `OPENCODE_API_KEY` environment variable.

> **Never** put your API key in `.argus.yml` or any committed file — forks and collaborators would see it.

## Rule Auto-Sync

`cgartlab/argus/.github/actions/argus-review@main` references the latest version of the Argus rules. When `AGENTS.md` or `SKILL.md` are updated in the argus repo, the composite action reads them at runtime — all consumer repos get the new rules instantly with no changes needed.

For a pinned version, use `@v0.4.1` instead of `@main`.

## Project Structure

```
argus/
├── AGENTS.md                    # Identity, hard rules, review dimensions
├── SKILL.md                     # Skill definition with trigger phrases
├── manifest.yaml                # Structured skill metadata
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # YAML syntax check + required file validation
│   │   ├── review.yml          # Argus-Flash PR review workflow
│   │   └── release.yml         # Automated release workflow (tag-push)
│   └── actions/
│       └── argus-review/
│           └── action.yml      # Reusable composite action
├── tools/
│   ├── bump_version.py         # Automated semver bumping
│   ├── load_config.py          # Consumer .argus.yml loader
│   ├── run_fixture_tests.py    # Fixture regression test runner
│   ├── validate_versioning.py  # VERSION/CHANGELOG consistency check
│   └── validate_model_scores.py  # config/model-scores.yml schema validator
├── Makefile                     # validate, release, package, clean
├── VERSION                      # Semantic version
└── LICENSE                      # MIT
```

## Commands

```bash
make check-version   # Show current version
make validate        # Run all quality checks
make test            # validate + test-fixtures (full pre-release check)
make package-skill   # Create skill package (argus-skill-v{VERSION}.zip)
make package         # Create all release archives
make release         # Tag and push a release
make clean           # Remove generated files
```

## Men Agent Team Integration (Optional)

Argus can be invoked by the **men agent team** (cgartlab/men) as an optional frontend design review capability. This integration is purely additive — Argus runs standalone in any agent framework or as the argus-flash GitHub App with **no men dependency**.

See [docs/men-integration.md](docs/men-integration.md) for the full reference: context detection, routing, the men output contract, chi judge verification, and protocol versioning.

## Relationship with Kold

Argus and Kold are companion agents:

- **Kold** — produces frontend code
- **Argus** — reviews frontend code

They share design principles and can work in a Kold → Argus workflow, or independently. In the automated review setup, Argus acts as a gate without requiring Kold.

## Project Status

Argus tracks a commercial product roadmap in [docs/strategic-plan.md](docs/strategic-plan.md) (version governance: the product version stays `0.x` until the owner approves `1.0`). All P1/P2/P3 roadmap items are delivered as of the 2026-09 consolidation:

- **Trust & quality engine** — fixture regression suite (incl. golden eval set), precision/recall/F1 CI gates, severity matrix, FP appeal loop
- **Config experience** — `.argus.yml` JSON Schema + zero-dep validator
- **CLI, reports & compliance** — local review CLI, shareable HTML reports, WCAG 2.2 compliance
- **Platforms** — GitHub App, GitLab MR template, multi-registry skill publishing
- **Extensibility** — custom rules DSL, webhook API
- **GTM** — Marketplace listing prep ([docs/marketplace-listing.md](docs/marketplace-listing.md)), self-hosting guide ([docs/self-hosting.md](docs/self-hosting.md))

Quality gates: `make test` (validate + fixture regression) and `make eval-gate` (precision/recall vs baseline) must stay green on every change.

## License

MIT
