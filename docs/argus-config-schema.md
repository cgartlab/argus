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

## API keys are NOT configured here

`.argus.yml` holds **review configuration only** — skills, severity overrides, ignore paths, failure thresholds. The file is committed to your repository, so anything in it is visible to forks and collaborators.

**Never put an API key or token in `.argus.yml`.** A committed key is an instant leak.

API keys are configured out-of-band:

| Where | How |
|---|---|
| CI (GitHub Actions) | Add `OPENCODE_API_KEY` as a repository secret (**Settings → Secrets and variables → Actions**) — the argus-review action reads it via `api-key: ${{ secrets.OPENCODE_API_KEY }}` |
| Local | `opencode auth login` (choose **OpenCode**, paste your key) or set the `OPENCODE_API_KEY` environment variable |
| Key creation | Register at https://opencode.ai (free), create a key at https://opencode.ai/auth |

The argus-flash GitHub App provides GitHub identity only (the bot token) — it does **not** provide an LLM key. Even with the App installed, you still need your own OpenCode Zen API key to run reviews.

---

## Full Schema Reference

```yaml
# ── Schema version (required for forward-compatibility) ──────────────────────
version: "0.3"                        # string, must be "0.2" or "0.3"

# ── Design system (token mapping source) ──────────────────────────────────────
# Selects the built-in token mapping injected into the review prompt so Argus
# suggests real token names. 'auto' detects from package.json dependencies
# (antd >= 5 → antd5, @mui/material → material3, @shopify/polaris → polaris,
# otherwise custom). Overrides with token-prefix below are independent.
design-system: auto                   # string  (default: "auto")

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
  # Upgrades are allowed; downgrades of non-core rules are allowed; the P0/P1
  # core rules (dark-mode-coverage, bare-color, missing-alt, button-aria-label)
  # cannot be downgraded. Rule IDs are listed in SKILL.md under each review
  # dimension (see the rule-id × severity matrix).
  severity:
    hardcoded-spacing: P3             # downgrade from P2 to P3 for this project
    bem-naming: P3                    # downgrade from P2 to P3

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

### `design-system`

| | |
|---|---|
| Type | string (one of `auto` \| `antd5` \| `material3` \| `polaris` \| `custom`) |
| Required | No |
| Default | `auto` |

Decides which built-in design-token mapping is injected into the review prompt, so Argus suggests **real** token names (e.g. `--ant-color-primary` / `--md-sys-color-primary` / `--p-color-text`) instead of the generic `var(--ds-*)` placeholders.

| Value | Meaning |
|---|---|
| `auto` | Detect from `package.json` dependencies: `antd` ≥ 5 → `antd5`, `@mui/material` → `material3`, `@shopify/polaris` → `polaris`, otherwise `custom` |
| `antd5` | Ant Design v5 (CSS-in-JS design tokens) |
| `material3` | Material Design 3 (MUI) |
| `polaris` | Shopify Polaris |
| `custom` | No built-in mapping — any `var(--<any-name>)` is treated as a valid design token reference |

**Relationship to `overrides.token-prefix`:** the two settings are independent and complementary. `design-system` selects the **built-in token mapping** injected into the prompt (which real tokens the LLM should reference when suggesting fixes). `token-prefix` controls **custom namespace recognition** — which `var(--<prefix>*)` usages Argus accepts as valid without flagging. For a bespoke design system, combine both:

```yaml
design-system: custom
overrides:
  token-prefix: "--brand-"
```

> **Note:** When `auto` detection finds `antd` v4 (Less variables, unsupported), the review prompt reports `antd4-unsupported`. Configure `design-system: custom` explicitly, or migrate to antd v5.

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

**Upgrades are allowed** (e.g. `hardcoded-spacing: P1` raises it from P2). **Downgrades are allowed for non-core rules** (e.g. `hardcoded-spacing: P3`).

> ⛔ **P0/P1 core rules cannot be downgraded.** Setting any of the following rule IDs to `P2` or `P3` is a validation error — the config fails to load. This is consistent with AGENTS.md "Severity never downgraded" and the SKILL.md rule-id × severity matrix:

| Rule ID | Base severity | Reason |
|---|---|---|
| `dark-mode-coverage` | P0 | Dark mode break is a technical blocker |
| `bare-color` | P0 | Bare color in blocking context (component rules) |
| `missing-alt` | P1 | WCAG compliance (images) |
| `button-aria-label` | P1 | WCAG compliance (icon buttons) |

**Examples:**

```yaml
overrides:
  severity:
    hardcoded-spacing: P3        # ✅ legal — non-core downgrade (P2 → P3)
    missing-alt: P0              # ✅ legal — upgrade (P1 → P0)
    bare-color: P2               # ❌ validation error — 'bare-color' is P0 and cannot be downgraded
```

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

Completely disables a rule across all files. Prefer `overrides.severity` (downgrading a non-core rule to P3) over silencing entirely — disabled rules leave a documentation gap. Note that P0/P1 core rules (`dark-mode-coverage`, `bare-color`, `missing-alt`, `button-aria-label`) are non-downgradable; disabling them entirely is not supported by design.

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

Caps the number of findings reported in the PR comment. When the actual finding count exceeds this limit, Argus reports findings in severity order and outputs at most N findings, prioritizing P0/P1 (highest-severity first). This is a prompt-layer convention: the cap is enforced through the review prompt injected into the LLM, so the actual output follows the model's execution.

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

### Known design system (Ant Design v5)
```yaml
version: "0.3"
skills:
  - design-review
design-system: antd5
```

---

## How Config is Loaded

1. The composite action (`argus-review/action.yml`) runs `tools/load_config.py` at the start of each review.
2. The loader looks for `.argus.yml` in the **consumer repository root** (not in the Argus repo).
3. Fields from `.argus.yml` are merged with the built-in defaults. Missing fields use defaults.
4. The resolved config is written to `$GITHUB_ENV` so subsequent steps can read it.
5. If `.argus.yml` contains validation errors, the action fails immediately with a clear error message.

> **Tip:** Run `python3 tools/load_config.py --validate-only` locally (from your repo root, pointing to the Argus tools directory) to validate your config before pushing.
