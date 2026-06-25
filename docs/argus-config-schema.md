# .argus.yml — Consumer Configuration Schema

> **Version:** 0.3 | Introduced in Argus v0.3.0

Place a `.argus.yml` file in the root of your repository to customize how Argus reviews your codebase. All fields are optional — omitting a field uses the built-in default.

---

## Quick Start

```yaml
# .argus.yml
version: "0.3"
skills:
  - design-review

fail-on: [P0, P1]
```

That's all you need for the most common case.

---

## Full Schema Reference

```yaml
# ── Schema version (required for forward-compatibility) ──────────────────────
version: "0.3"                        # string, must be "0.2" or "0.3"

# ── Skills to activate ───────────────────────────────────────────────────────
# List one or more review skill IDs. Each ID maps to a skill file in the
# Argus repo under skills/. Defaults to ["design-review"].
skills:
  - design-review                     # CSS/HTML design tokens, hardcoded values, dark mode
  # - security-review                 # (coming soon) SQL injection, hardcoded secrets, CORS
  # - api-contract                    # (coming soon) REST conventions, error codes, versioning
  # - performance                     # (coming soon) N+1 queries, bundle size, unused imports
  # - infrastructure                  # (coming soon) Dockerfile hygiene, K8s resource limits

# ── Rule overrides ────────────────────────────────────────────────────────────
overrides:
  # Design token prefix for this codebase. Argus expects var(--<prefix>*)
  # by default. Change this if your tokens use a different namespace.
  token-prefix: "--ds-"               # string  (default: "--ds-")

  # Per-rule severity adjustments. Use sparingly — prefer fixing the root cause.
  # Rule IDs are listed in SKILL.md under each review dimension.
  severity:
    hardcoded-spacing: P3             # downgrade from P1 to P3 for this project
    bem-naming: P2                    # downgrade from P1 to P2

# ── Ignore list ───────────────────────────────────────────────────────────────
ignore:
  # Glob patterns for files/directories Argus should skip entirely.
  # These are ANDed with the built-in exclusions (node_modules, dist, .git).
  paths:
    - "src/legacy/**"
    - "tests/fixtures/**"
    - "vendor/**"

  # Rule IDs to disable completely (all severities, all files).
  # Prefer using 'severity' overrides above to downgrade rather than silence.
  rules:
    - bem-naming                      # this project doesn't use BEM

# ── Failure thresholds ────────────────────────────────────────────────────────
# Severity levels that will cause the CI check to fail (exit 1).
# Findings below this threshold are reported but do not block merge.
fail-on:
  - P0
  - P1                               # default: [P0, P1]

# ── Output options ────────────────────────────────────────────────────────────
output:
  group-by-severity: true            # bool    — group output P0 → P1 → P2 → P3 (default: true)
  show-token-names: true             # bool    — include "Token: var(--ds-*)" lines (default: true)
  max-findings: 50                   # integer — cap findings to avoid overwhelming PRs (default: 50, max: 500)
```

---

## Field Reference

### `version`

| | |
|---|---|
| Type | string |
| Required | No |
| Default | `"0.3"` |
| Valid values | `"0.2"`, `"0.3"` |

Declares the schema version. Include this to ensure forward-compatible parsing when the schema evolves.

---

### `skills`

| | |
|---|---|
| Type | list of strings |
| Required | No |
| Default | `["design-review"]` |

Selects which Argus review skills are active for your repository.

| ID | Status | Description |
|---|---|---|
| `design-review` | ✅ Stable | Design tokens, hardcoded values, dark mode, accessibility |
| `security-review` | 🔜 Coming soon | Hardcoded secrets, SQL injection, CORS misconfiguration |
| `api-contract` | 🔜 Coming soon | REST conventions, error codes, API versioning |
| `performance` | 🔜 Coming soon | N+1 queries, bundle size, unused imports |
| `infrastructure` | 🔜 Coming soon | Dockerfile hygiene, K8s resource limits, IaC drift |

---

### `overrides.token-prefix`

| | |
|---|---|
| Type | string |
| Default | `"--ds-"` |

The CSS custom property prefix Argus expects for design tokens. If your design system uses `--brand-` or `--my-prefix-`, set this accordingly.

```yaml
overrides:
  token-prefix: "--brand-"
```

---

### `overrides.severity`

| | |
|---|---|
| Type | map of `rule-id: severity` |
| Default | `{}` (no overrides) |
| Valid severities | `P0`, `P1`, `P2`, `P3` |

Adjusts the severity of specific rules. Useful for projects that knowingly deviate from a default rule.

> ⚠️ You cannot upgrade a rule's severity (e.g., from P1 to P0). Overrides only downgrade.

Rule IDs are documented in [SKILL.md](../SKILL.md) under each review dimension header.

---

### `ignore.paths`

| | |
|---|---|
| Type | list of glob strings |
| Default | `["node_modules/**", "dist/**", ".git/**"]` |

Glob patterns for files Argus should skip. These are merged with (not replaced by) the built-in exclusions.

---

### `ignore.rules`

| | |
|---|---|
| Type | list of rule ID strings |
| Default | `[]` |

Completely disables a rule across all files. Prefer `overrides.severity` (downgrading to P3) over silencing entirely — disabled rules leave a documentation gap.

---

### `fail-on`

| | |
|---|---|
| Type | list of severity strings |
| Default | `["P0", "P1"]` |
| Valid values | `P0`, `P1`, `P2`, `P3` |

Severity levels that cause the CI check to exit with code 1 (blocking merge). Findings at lower severities are still reported in the PR comment but do not block.

**Examples:**

```yaml
# Only P0 findings block merge (lenient)
fail-on: [P0]

# All findings block merge (strict)
fail-on: [P0, P1, P2, P3]
```

---

### `output.max-findings`

| | |
|---|---|
| Type | integer |
| Default | `50` |
| Range | 1 – 500 |

Caps the number of findings reported in the PR comment. When the actual finding count exceeds this limit, Argus reports the highest-severity findings first and appends a "N more findings suppressed" note.

---

## Minimal Examples

### Design agency (strict, no legacy code)
```yaml
version: "0.3"
skills:
  - design-review
fail-on: [P0, P1, P2]
```

### Large existing codebase (gradual adoption)
```yaml
version: "0.3"
skills:
  - design-review
overrides:
  severity:
    hardcoded-spacing: P3
    bem-naming: P3
ignore:
  paths:
    - "src/legacy/**"
    - "packages/third-party/**"
fail-on: [P0]
output:
  max-findings: 20
```

### Custom token namespace
```yaml
version: "0.3"
skills:
  - design-review
overrides:
  token-prefix: "--brand-"
```

---

## How Config is Loaded

1. The composite action (`argus-review/action.yml`) runs `tools/load_config.py` at the start of each review.
2. The loader looks for `.argus.yml` in the **consumer repository root** (not in the Argus repo).
3. Fields from `.argus.yml` are merged with the built-in defaults. Missing fields use defaults.
4. The resolved config is written to `$GITHUB_ENV` so subsequent steps can read it.
5. If `.argus.yml` contains validation errors, the action fails immediately with a clear error message.

> **Tip:** Run `python3 tools/load_config.py --validate-only` locally (from your repo root, pointing to the Argus tools directory) to validate your config before pushing.
