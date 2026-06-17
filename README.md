# Argus

[![CI](https://github.com/cgartlab/argus/actions/workflows/ci.yml/badge.svg)](https://github.com/cgartlab/argus/actions/workflows/ci.yml)
[![Argus-Flash Review](https://github.com/cgartlab/argus/actions/workflows/review.yml/badge.svg)](https://github.com/cgartlab/argus/actions/workflows/review.yml)

Code review agent for frontend design. Runs as a GitHub App — install on any repo for automated PR reviews.

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
```

That's it. Every PR will automatically receive a design review comment from `argus-flash[bot]`.

## Rule Auto-Sync

`cgartlab/argus/.github/actions/argus-review@main` references the latest version of the Argus rules. When `AGENTS.md` or `SKILL.md` are updated in the argus repo, the composite action reads them at runtime — all consumer repos get the new rules instantly with no changes needed.

For a pinned version, use `@v0.2.0` instead of `@main`.

## Project Structure

```
argus/
├── AGENTS.md                    # Identity, hard rules, review dimensions
├── SKILL.md                     # Skill definition with trigger phrases
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # YAML syntax check + required file validation
│   │   └── review.yml          # Argus-Flash PR review workflow
│   └── actions/
│       └── argus-review/
│           └── action.yml      # Reusable composite action
├── Makefile                     # validate, release, package, clean
├── VERSION                      # Semantic version
└── LICENSE                      # MIT
```

## Commands

```bash
make check-version   # Show current version
make validate        # Run all quality checks
make release         # Tag and push a release
make package         # Create release archive
make clean           # Remove generated files
```

## Relationship with Kold

Argus and Kold are companion agents:

- **Kold** — produces frontend code
- **Argus** — reviews frontend code

They share design principles and can work in a Kold → Argus workflow, or independently. In the automated review setup, Argus acts as a gate without requiring Kold.

## License

MIT
