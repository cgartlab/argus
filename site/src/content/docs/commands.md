---
title: Commands
description: Makefile commands and GitHub App usage reference.
order: 5
sidebarGroup: System
updated: 2026-08-31
---

# Commands

This page is a reference for the Argus command-line commands. Most Argus users never touch these — but if you're contributing to the project or releasing new versions, this is your checklist.

A note on `make`: `make` is a common build tool that runs commands defined in a `Makefile`. You only need it if you're working *inside* the Argus repository itself.

## The short version

| Command | What it does | When you need it | New-user friendly? |
|---|---|---|---|
| `make check-version` | Shows the current version | Confirming a release | Yes |
| `make validate` | Runs all quality checks | Before a release, or after editing rules | Occasionally |
| `make test-fixtures` | Runs the regression tests | After changing review rules | Occasionally |
| `make test` | validate + test-fixtures | Before every release | For contributors |
| `make release` | Commits, tags, and pushes a release | When cutting a new version | No — maintainers only |
| `make package-skill` | Builds the skill package zip | Before a release | No |
| `make package` | Builds all release archives | Before a release | No |
| `make clean` | Removes generated files | Tidying up | Yes |

## Daily commands

These are safe to run any time from the repository root:

```bash
make check-version    # Show current version — e.g. "Current version: 0.4.0"
make clean            # Remove generated files (the dist/ folder)
```

`make check-version` is useful right before a release to confirm which version you're about to ship.

## Quality checks

Run these after you edit review rules or documentation:

```bash
make validate         # Check SKILL.md trigger phrases, CHANGELOG, required files, Python syntax
make test-fixtures    # Run fixture regression tests (static mode — no API key needed)
make test             # Everything: validate + test-fixtures (the full pre-release check)
```

**Why:** `validate` makes sure nothing is broken (missing files, inconsistent version, malformed scripts). `test-fixtures` confirms the review rules still produce the expected results on sample files. `make test` is both together — run it before any release.

## Version bumping

These update the version number and the changelog for you:

```bash
make bump-patch   # e.g. 0.4.0 → 0.4.1 (bug fixes, minor changes)
make bump-minor   # e.g. 0.4.0 → 0.5.0 (new features)
make bump-major   # e.g. 0.4.0 → 1.0.0 (breaking changes)
```

**Why it matters:** bump targets automatically update `VERSION` and `CHANGELOG.md` and stage the changes. You then review, run `make test`, and release.

## Releasing

```bash
make test        # validate + fixture tests (full pre-release check)
make release     # validate → git commit → tag → push
```

**Why it matters:** `make release` creates the version tag and pushes it. Pushing a `v*.*.*` tag triggers the release workflow, which validates versioning, builds the release archives, and publishes a GitHub Release.

> Only maintainers should run `make release` — it pushes to the shared repository.

## Using Argus (not developing it)

You don't need `make` at all to *use* Argus:

- **GitHub App:** install [argus-flash](https://github.com/apps/argus-flash) and add a workflow — see [Getting Started](/docs/getting-started). GitHub runs everything for you.
- **Local agent:** point OpenCode, Claude Code, or Codex CLI at the repository. Argus loads automatically from `AGENTS.md` + `SKILL.md`; no commands required.

## Advanced: running the tools directly

For contributors who want finer control:

| Command | Location | Notes |
|---|---|---|
| `make validate` | `Makefile` | Trigger phrase check + CHANGELOG + required files + Python tool syntax |
| `make test-fixtures` | `Makefile` | Static heuristic mode, no API key required |
| `make test-fixtures-llm` | `Makefile` | LLM mode — requires OpenCode CLI + a configured model |
| `make release` | `Makefile` | Commits, tags, and pushes; release workflow handles the rest |
| `python3 tools/run_fixture_tests.py` | `tools/` | Flags: `--dry-run`, `--category`, `--fixture`, `--verbose`, `--json` |
| `python3 tools/load_config.py --validate-only` | `tools/` | Checks a `.argus.yml` without running a review |