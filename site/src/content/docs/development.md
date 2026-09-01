---
title: Development
description: Local development, fixture testing, and the release process.
order: 6
sidebarGroup: Reference
updated: 2026-08-31
---

# Development

This page is for people who want to contribute to Argus itself — fixing review rules, improving docs, or running the project locally. If you only *use* Argus, you can skip this page.

## Prerequisites

- **Git** — to clone the repository and create pull requests
- **Python 3** — the test and tooling scripts are written in Python
- **`make`** — optional but recommended (it runs the common commands; see [Commands](/docs/commands))
- **A GitHub account** — to open issues and PRs

## The big idea: Argus is just Markdown

Argus is a **pure documentation repository** — there's no `npm install`, no build step, no compiled code. The "engine" is two files that any AI agent reads:

- `AGENTS.md` — the agent's identity, hard rules, and review dimensions
- `SKILL.md` — the detailed review skill with trigger phrases and per-framework rules

**Why this matters:** contributing is mostly editing Markdown and validating that the structure stays correct. You don't need to run a server or understand a framework.

## Local setup

```bash
git clone https://github.com/cgartlab/argus.git   # download the repository
cd argus                                          # go into the folder
```

That's it. You can now run `make validate` to see if the project is healthy.

## What to contribute

| Type | How |
|---|---|
| Bug report | Open an issue with the code that was incorrectly flagged or missed |
| Review improvement | PR with the specific scenario where Argus's review was wrong or incomplete |
| Documentation | Direct PR for typos, clarity, or missing content |
| Skill improvement | PR with updated `SKILL.md` — describe the real-world scenario that prompted the change |

> **Important:** for new review rules, new severity assignments, or breaking changes, open an issue *first*. Direct PRs without prior discussion may be closed.

## File conventions

- `AGENTS.md` — behavioral rules; never removed or weakened
- `SKILL.md` — skill definition with trigger phrases; description must have 3+ real-world trigger phrases
- `.github/actions/argus-review/action.yml` — the composite action wrapping OpenCode CLI + rule injection
- `VERSION` — a single line with the semantic version
- All Markdown files — no emoji decorations in headings or lists

## Branch naming

```bash
fix/<desc>      # bug fixes — e.g. fix/flag-empty-alt
feat/<desc>     # new features — e.g. feat/svelte-5-rules
docs/<desc>     # documentation only — e.g. docs/typo-fixes
chore/<desc>    # refactor, format, tooling — e.g. chore/format-tools
```

## Fixture regression tests

**What is a fixture?** In testing, a "fixture" is a fixed sample input paired with the exact output you expect. Argus's fixtures are small, deliberately broken code files (like a CSS file with hardcoded colors) paired with a `.expected` file listing what the review should find.

**Why this matters:** fixtures are how Argus proves its rules work. Every time you change a rule, you update or add a fixture — then the test suite checks that the rule produces the expected findings. This catches regressions ("I fixed rule A and accidentally broke rule B") before they reach users.

The `tests/fixtures/` suite covers four categories:

| Category | Example fixture | Expected findings |
|---|---|---|
| `design-tokens/` | `bad-hardcoded-colors.css` | 5 P0 findings (bare oklch/hex/rgb) |
| `design-tokens/` | `missing-dark-mode.css` | 3 P0 findings (missing dark override) |
| `accessibility/` | `missing-aria.html` | 4 P1 findings (icon buttons, missing alt) |
| `hardcoded-values/` | `bad-magic-numbers.css` | 4 P1 findings (magic px values) |
| `css-quality/` | `duplicate-rules.css` | 2 P2 findings (duplicate declarations) |

Run them in static mode (no API key needed):

```bash
make test-fixtures    # run the whole suite
```

Or directly with flags:

```bash
python3 tools/run_fixture_tests.py --dry-run                     # check .expected files are valid
python3 tools/run_fixture_tests.py --category design-tokens      # only one category
python3 tools/run_fixture_tests.py --fixture bad-hardcoded-colors --verbose  # one fixture, verbose output
python3 tools/run_fixture_tests.py --json                        # machine-readable output
```

**Rule:** every rule change must be accompanied by a fixture update — CI verifies that input and `.expected` file counts match per category.

## Adding a new review rule

1. Identify the review dimension (token, a11y, dark mode, etc.)
2. Assign a severity with a rationale (why P1 and not P2?)
3. Add the rule to `SKILL.md` under the correct dimension, with wrong/right code examples
4. Add it to the review checklist in `AGENTS.md`
5. Add a fixture pair (input + `.expected`) and run `make test-fixtures`
6. Verify the composite action still works (dynamic loading means no action change needed)
7. Update `VERSION` if the change is meaningful

## Composite action maintenance

`.github/actions/argus-review/action.yml` is the integration point for automated reviews:

- **Dynamic rule injection** — `AGENTS.md` and `SKILL.md` are read at runtime and written to `$GITHUB_ENV` as `PROMPT`
- **No hardcoded prompt** — updating the rule files changes review behavior for all consumer repositories
- **Update `action.yml`** when adding steps, changing PROMPT construction, or updating the model/CLI installation
- **Do NOT update `action.yml`** for rule changes — edit `AGENTS.md` or `SKILL.md` only

## Release process

```bash
make bump-patch   # update VERSION + CHANGELOG
make test         # validate + fixture tests (full pre-release check)
make release      # commit → tag → push → triggers release workflow
```

Pushing a `v*` tag triggers the release workflow (`.github/workflows/release.yml`), which:

1. Validates versioning consistency (`VERSION` ↔ `CHANGELOG.md`)
2. Builds the full archive (`dist/argus-v{VERSION}.tar.gz` + `.zip`)
3. Builds the skill package (`dist/argus-skill-v{VERSION}.zip`)
4. Creates a GitHub Release with all artifacts

## Pull request checklist

Before you open a PR, confirm:

- [ ] `AGENTS.md` and `SKILL.md` remain consistent with each other
- [ ] `.github/actions/argus-review/action.yml` is consistent with `AGENTS.md` and `SKILL.md`
- [ ] `VERSION` bumped if this is a meaningful change
- [ ] No emoji decorations in prose
- [ ] `SKILL.md` description has 3+ trigger phrases
- [ ] New review rules have severity assigned with rationale