---
title: Architecture
description: How argus-flash flows from GitHub App to PR comment, and the three delivery forms.
order: 3
sidebarGroup: System
updated: 2026-08-31
---

# Architecture

This page explains what happens between "you open a pull request" and "the bot comments" — the moving parts and why each one exists. You don't need this to use Argus, but it helps when something goes wrong or when you want to pin versions safely.

## One analogy to keep in your head

Think of automated review like a **delivery service**:

| Piece | Analogy | What it really is |
|---|---|---|
| argus-flash App | The courier — a known, trusted sender | A GitHub App (official bot account) |
| workflow (review.yml) | The order form — says what to do when | A YAML file in `.github/workflows/` |
| composite action | The standard shipping box — pre-packed steps | A reusable step package in `argus/.github/actions/` |
| AGENTS.md + SKILL.md | The acceptance checklist | The rule files that define the review |
| Review result | The delivery report | A comment on your PR |

So: *the courier shows up when you place an order (a PR), the box contains the checklist (rules), and the report (comment) tells you what passed and what didn't.*

## Data flow: what happens on every PR

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

Step by step:

1. **PR opened** — you (or a teammate) open a pull request. GitHub sees the `pull_request` event.
2. **Workflow starts** — your `review.yml` wakes up and runs on a GitHub server.
3. **Token generated** — the workflow uses the two secrets (`ARGUS_FLASH_APP_ID`, `ARGUS_FLASH_PRIVATE_KEY`) to create a short-lived bot token. **Why it matters:** the bot needs to prove it's allowed to read code and comment — the token is that proof.
4. **Composite action runs** — the workflow calls `cgartlab/argus/.github/actions/argus-review@main`. This is a packaged set of steps. **Why it matters:** you don't copy the logic into your repo; you just reference it, like installing a library.
5. **Rules injected** — the action reads `AGENTS.md` and `SKILL.md` from the Argus repo at that moment and puts them into the review prompt. **Why it matters:** this is what makes rule updates automatic (see below).
6. **OpenCode CLI runs the review** — an AI model reads your changed files against the rules.
7. **Bot comments** — the result is posted as a PR comment. **Why it matters:** the whole team sees the review inline, where the code was changed.

## Dynamic rule injection (why updates are automatic)

The composite action **does not contain a hardcoded prompt**. Every review run:

1. Reads `AGENTS.md` and `SKILL.md` from the Argus repository, at the exact ref you referenced (`@main` or `@v0.4.0`).
2. Injects them into the prompt.
3. Runs the review with those rules.

**Why it matters:** when the Argus team improves a rule, every consumer repo picks it up on the next review — no workflow edits, no redeploys. The flip side: with `@main`, a rule change can alter your review behavior at any time. Pin the version if you want stability.

## Repository structure

```
argus/
├── AGENTS.md                          # Identity, hard rules, review dimensions
├── SKILL.md                           # Skill trigger phrases, execution rules (detailed)
├── docs/
│   └── argus-config-schema.md         # .argus.yml consumer config reference
├── tests/
│   └── fixtures/                      # Fixture-based regression test suite
│       ├── design-tokens/             # Design token & dark mode violations
│       ├── accessibility/             # ARIA, alt, semantic HTML violations
│       ├── hardcoded-values/          # Magic number spacing/radii/font-size
│       └── css-quality/               # Duplicate rules, BEM violations
├── tools/
│   ├── run_fixture_tests.py           # Fixture regression test runner
│   ├── load_config.py                 # Consumer .argus.yml loader + validator
│   ├── bump_version.py                # Automated semver bumping
│   └── validate_versioning.py         # VERSION / CHANGELOG consistency check
├── .github/
│   ├── workflows/                     # ci, review, release
│   └── actions/
│       └── argus-review/
│           └── action.yml             # Reusable composite action for any repo
├── Makefile                           # validate, test, release, package, clean
└── VERSION                            # Semantic version
```

You don't need to memorize this — it's the map for the rest of the docs. The three folders that matter most: `AGENTS.md` + `SKILL.md` (the rules), `tools/` (helper scripts), and `.github/actions/argus-review/action.yml` (the integration point).

## Three delivery forms

| Form | How it runs | Use case |
|---|---|---|
| **Local agent** | Reads `AGENTS.md` + `SKILL.md` at startup | OpenCode, Claude Code, Codex CLI |
| **GitHub App** | `argus-flash` + composite action | Automated PR review gate |
| **Skill package** | `argus-skill-v{VERSION}.zip` | Distribution to skill-marketplace runtimes |

**Why it matters:** the same rules power all three — learn the rules once, and they apply everywhere.

## Branch strategy for the composite action

| Ref | Behavior | Recommendation |
|---|---|---|
| `@main` | Latest rules at time of review run | Development / internal repos |
| `@v0.4.0` | Pinned to a release | Production / external consumer repos |

See [Getting Started](/docs/getting-started) for how to switch.