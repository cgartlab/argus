---
title: Configuration
description: The full .argus.yml consumer configuration reference.
order: 4
sidebarGroup: System
updated: 2026-08-31
---

# Configuration

This page explains `.argus.yml` — a small optional config file that customizes how Argus reviews your repository. If you never create one, Argus works fine with sensible defaults; this page is for when you want to adjust them.

**Prerequisites:** Argus installed and running (see [Getting Started](/docs/getting-started)), and an idea of which rule you want to change.

## The short version

Place a file named `.argus.yml` in the **root** of your repository. Every field is optional — leave one out and Argus uses its built-in default.

The most common config (keeps the defaults, and makes P0 and P1 findings block the merge):

```yaml
# .argus.yml
version: "0.3"          # schema version — always include this
skills:
  - design-review       # the review skill to activate

fail-on: [P0, P1]       # findings at these levels will fail CI (block merge)
```

## What happens if I create no config at all?

You get the defaults. Concretely:

- Argus uses the `design-review` skill only (design tokens, hardcoded values, dark mode, accessibility).
- It expects design tokens to start with `--ds-`.
- P0 and P1 findings block the merge; P2 and P3 are reported but don't block.
- It skips `node_modules/`, `dist/`, and `.git/` automatically.
- It reports up to 50 findings, grouped by severity.

## Full schema reference

```yaml
# ── Schema version ────────────────────────────────────────────────
version: "0.3"                        # string, must be "0.2" or "0.3"

# ── Skills to activate ────────────────────────────────────────────
skills:
  - design-review                     # the stable review skill
  # - security-review                 # (coming soon) secrets, SQL injection, CORS
  # - api-contract                    # (coming soon) REST conventions, error codes
  # - performance                     # (coming soon) N+1 queries, bundle size
  # - infrastructure                  # (coming soon) Dockerfile hygiene, K8s limits

# ── Rule overrides ────────────────────────────────────────────────
overrides:
  token-prefix: "--ds-"               # what your tokens start with (default: "--ds-")
  severity:
    hardcoded-spacing: P3             # downgrade this rule from P1 to P3 for this project
    bem-naming: P2                    # downgrade from P1 to P2

# ── Ignore list ───────────────────────────────────────────────────
ignore:
  paths:                              # files/directories to skip entirely
    - "src/legacy/**"
    - "tests/fixtures/**"
    - "vendor/**"
  rules:                              # rules to disable completely
    - bem-naming                      # e.g. this project doesn't use BEM

# ── Failure thresholds ────────────────────────────────────────────
fail-on:
  - P0
  - P1                               # default: [P0, P1]

# ── Output options ────────────────────────────────────────────────
output:
  group-by-severity: true            # group output P0 → P1 → P2 → P3 (default: true)
  show-token-names: true             # include "Token: var(--ds-*)" lines (default: true)
  max-findings: 50                   # cap findings per review (default: 50, max: 500)
```

## Field-by-field guide

### `version`

| | |
|---|---|
| Type | string |
| Required | No (default `"0.3"`) |
| Valid values | `"0.2"`, `"0.3"` |

**When to use it:** always. It declares which schema version your file follows.

**What happens if you omit it:** Argus assumes `"0.3"`. Including it protects you later — if the schema evolves, Argus can still parse your file correctly.

### `skills`

| | |
|---|---|
| Type | list of strings |
| Default | `["design-review"]` |

**When to use it:** rarely today — `design-review` is the only stable skill.

| ID | Status | Description |
|---|---|---|
| `design-review` | Stable | Design tokens, hardcoded values, dark mode, accessibility |
| `security-review` | Coming soon | Hardcoded secrets, SQL injection, CORS misconfiguration |
| `api-contract` | Coming soon | REST conventions, error codes, API versioning |
| `performance` | Coming soon | N+1 queries, bundle size, unused imports |
| `infrastructure` | Coming soon | Dockerfile hygiene, K8s resource limits, IaC drift |

**What happens if you omit it:** you get `design-review` — the current default and the only stable option.

### `overrides.token-prefix`

| | |
|---|---|
| Type | string |
| Default | `"--ds-"` |

**When to use it:** your design tokens use a different prefix, e.g. `--brand-` or `--my-prefix-`.

```yaml
overrides:
  token-prefix: "--brand-"
```

**What happens if you omit it:** Argus looks for `--ds-*` tokens. If your project uses another prefix, you'll get false positives — Argus flags correct code as "missing token."

### `overrides.severity`

| | |
|---|---|
| Type | map of `rule-id: severity` |
| Default | `{}` (no overrides) |
| Valid severities | `P0`, `P1`, `P2`, `P3` |

**When to use it:** a rule fires on code your team intentionally keeps (for example, a legacy file you'll migrate later). Downgrade it so it doesn't block work.

```yaml
overrides:
  severity:
    hardcoded-spacing: P3   # report it, but don't block merge
```

> **You can only downgrade, never upgrade.** You can't raise a rule from P1 to P0 — overrides only make rules less strict.

**What happens if you omit it:** every rule keeps its default severity.

### `ignore.paths`

| | |
|---|---|
| Type | list of glob strings |
| Default | `["node_modules/**", "dist/**", ".git/**"]` |

**When to use it:** you have folders Argus should skip — legacy code, generated files, third-party packages.

**What happens if you omit it:** Argus skips `node_modules`, `dist`, and `.git` automatically. Your custom paths are *added to* these defaults, not replacing them.

### `ignore.rules`

| | |
|---|---|
| Type | list of rule ID strings |
| Default | `[]` |

**When to use it:** a rule is completely wrong for your project (e.g. BEM naming in a project that doesn't use BEM).

**What happens if you omit it:** all rules stay active. Prefer downgrading via `overrides.severity` — a fully disabled rule leaves a documentation gap in your review.

### `fail-on`

| | |
|---|---|
| Type | list of severity strings |
| Default | `["P0", "P1"]` |
| Valid values | `P0`, `P1`, `P2`, `P3` |

**When to use it:** you want stricter or more lenient merge gates.

```yaml
# Only P0 findings block merge (lenient)
fail-on: [P0]

# All findings block merge (strict)
fail-on: [P0, P1, P2, P3]
```

**What happens if you omit it:** P0 and P1 findings make the CI check fail (exit code 1), blocking the merge. Lower-severity findings still appear in the comment but don't block.

### `output.max-findings`

| | |
|---|---|
| Type | integer |
| Default | `50` |
| Range | 1 – 500 |

**When to use it:** your repo is large and a single review finds hundreds of issues; cap the comment so it stays readable.

**What happens if you omit it:** Argus reports up to 50 findings — highest severity first — and adds a "N more findings suppressed" note when it hits the cap.

## Complete example

Here's a realistic `.argus.yml` for a team adopting Argus gradually on a large codebase:

```yaml
version: "0.3"                    # always include the schema version
skills:
  - design-review                 # activate the standard review skill

overrides:
  token-prefix: "--brand-"        # our tokens use the --brand- prefix
  severity:
    hardcoded-spacing: P3         # report spacing issues but don't block
    bem-naming: P3                # we're not using BEM yet — downgrade, don't disable

ignore:
  paths:
    - "src/legacy/**"             # old code we'll migrate later
    - "packages/third-party/**"   # vendor code we don't own

fail-on: [P0]                     # only P0 blocks merge during adoption

output:
  max-findings: 20                # keep review comments short
```

## How the config is loaded

1. At the start of every review, the composite action runs `tools/load_config.py`.
2. It looks for `.argus.yml` in **your repository's root** (not in the Argus repo).
3. Your fields are merged with the built-in defaults — missing fields use defaults.
4. The resolved config is written to `$GITHUB_ENV` so later steps can read it.
5. If your file has validation errors, the review fails immediately with a clear error message.

> **Tip:** you can validate a config locally before pushing:
>
> ```bash
> python3 tools/load_config.py --validate-only
> ```

## Troubleshooting

**Q: My config is invalid — the review fails with a config error.**
Run the validation command above. Common causes: a typo in a field name, a wrong `version` value, or a severity outside P0–P3.

**Q: Argus flags correct code as "missing token" everywhere.**
Your `token-prefix` is probably wrong. If your tokens are `--brand-*`, set `overrides.token-prefix: "--brand-"`. If you don't use tokens at all, you may want to downgrade token rules while you adopt them.

**Q: I set `fail-on: [P0]` but P1 findings still block the merge.**
The config file may not be where Argus expects it. Confirm the path is exactly `.argus.yml` at the repository **root** (not in a subfolder) and that the change is in the branch being reviewed.

**Q: I want to silence a rule completely, but I'm told to prefer downgrading.**
Downgrading keeps the finding visible (as P3) so you don't lose track of it. If a rule is genuinely irrelevant (like BEM in a non-BEM project), `ignore.rules` is the right tool.