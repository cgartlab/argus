# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] — 2026-06-25

### Added

#### Direction 2 — Consumer Configuration Layer
- `docs/argus-config-schema.md` — Full `.argus.yml` field reference with schema, examples, and migration guide
- `tools/load_config.py` — Consumer config loader: reads `.argus.yml` from consumer repo, deep-merges with built-in defaults, validates all fields, emits `GITHUB_ENV` variables for use in subsequent Action steps
- `.argus.yml` support in `action.yml` — new `config-path` input (default: `.argus.yml`); `load-config` step runs before prompt build; consumer token-prefix, ignore rules/paths, fail-on thresholds, and max-findings are all injected into the LLM prompt at review time

#### Direction 3 — Fixture-Based Regression Testing
- `tests/fixtures/` — Regression test suite with 4 categories and 8 fixture pairs (input + `.expected`):
  - `design-tokens/bad-hardcoded-colors.css` — bare `oklch`/`hex`/`rgb` in component rules → 5 P0 findings expected
  - `design-tokens/missing-dark-mode.css` — `:root` color tokens without `[data-theme="dark"]` override → 3 P0 findings expected
  - `accessibility/missing-aria.html` — icon buttons, missing `alt`, `<a>`-as-button → 4 P1 findings expected
  - `hardcoded-values/bad-magic-numbers.css` — magic `px` spacing/radii/font-size → 4 P1 findings expected
  - `css-quality/duplicate-rules.css` — duplicate property declarations in same selector → 2 P2 findings expected
- `tests/fixtures/README.md` — `.expected` format spec, how to add fixtures, CI integration notes
- `tools/run_fixture_tests.py` — Fixture runner: parses `.expected` files, invokes Argus (OpenCode CLI) or falls back to built-in static heuristic scanner (no API key required), validates severity counts (±1 tolerance), checks `must-not-flag` rules, supports `--verbose`, `--dry-run`, `--json`, `--category`, `--fixture` flags

#### CI & Tooling
- `ci.yml` — Restructured into 3 jobs:
  - `lint` — YAML syntax validation (now includes `action.yml`) + 14 required file checks
  - `validate-tools` — Python syntax check for all 4 tools + `load_config` default and example config validation
  - `fixture-tests` — `.expected` dry-run parse, fixture directory structure verification, artifact upload
- `action.yml` — New `fixture-mode` input; when `"true"` runs `run_fixture_tests.py` instead of `opencode github run` (for Argus repo's own CI)

### Changed
- `AGENTS.md` — Updated to v0.3.0; expanded `STRUCTURE` tree (added `docs/`, `tests/`, full `tools/` listing); updated `WHERE TO LOOK` table (+6 rows); added fixture anti-pattern; updated `COMMANDS` section
- `Makefile` — New targets: `test-fixtures` (static heuristic mode), `test-fixtures-llm` (full LLM mode), `test` (= validate + test-fixtures); `validate` expanded to 7 checks (now includes Python syntax and `load_config` validation); `bump-*` completion hint updated to `make test && make release`
- `VERSION` — 0.2.0 → 0.3.0

### Notes
- **Backwards compatible** — existing consumers with no `.argus.yml` continue to work unchanged; all new config fields use safe defaults
- **No API key required for CI** — `run_fixture_tests.py` falls back to static heuristic mode when OpenCode CLI is not installed, allowing fixture structure validation to run in any CI environment
- **Fixture count tolerance** — severity count assertions allow ±1 variance to keep the suite stable across minor LLM updates
- **Consumer config is additive** — hard rules (P0 color violations, a11y baseline) cannot be fully disabled via `.argus.yml`; severity can be downgraded but not silenced entirely for critical rules

---

## [0.2.0] — 2026-06-17

### Added
- `.github/actions/argus-review/action.yml` — Reusable composite action wrapping OpenCode CLI + dynamic rule injection
- Dynamic runtime rule loading: `action.yml` reads `AGENTS.md` + `SKILL.md` from the argus repo at review time and injects their contents into the LLM prompt
- `argus-flash` GitHub App (`github.com/apps/argus-flash`) — replaces the default OpenCode Agent App for PR review authentication
- Workflow `use_github_token: true` support — enables custom GitHub App token usage instead of OIDC exchange
- `ci.yml` — Rewritten with proper YAML syntax validation and required file checks
- `review.yml` — Simplified to call the composite action; token generation via `actions/create-github-app-token@v1`

### Changed
- `AGENTS.md` — Updated structure, added composite action and `argus-flash` App to WHERE TO LOOK, added dynamic rule injection convention
- `SKILL.md` — Updated to v0.2.0, added automated PR review workflow section
- `README.md` — Full rewrite with architecture diagram, cross-repo usage guide, and rule auto-sync explanation
- `DEVELOPMENT-GUIDE.md` — Updated for new architecture (composite action, argus-flash App, GitHub Actions integration)
- `CONTRIBUTING.md` — Added action.yml to pull request checklist
- `Makefile` — Added `.github/actions/argus-review/action.yml` existence check to validate target
- `VERSION` — 0.1.1-test-2 → 0.2.0

### Removed
- `opencode.jsonc` — No longer needed; permissions are managed via GitHub App token
- `.github/workflows/release.yml` — Release process moved to local `make release`
- Old workflow files: `argus-test.yml`, `flash-review.yml`, `opencode.yml`

### Notes
- Any repo can install `argus-flash` GitHub App and add a minimal 26-line review.yml to get automated design reviews
- Rules are auto-synced via the composite action's `@main` ref — update AGENTS.md/SKILL.md in the argus repo and all consumers pick up changes at the next review run
- For pinned version usage, use `@v0.2.0` instead of `@main`

## [0.1.1] — 2026-06-17

### Added
- `opencode.jsonc` — Argus agent configuration for OpenCode, auto-loads AGENTS.md + SKILL.md
- `.github/workflows/argus-review.yml` — GitHub App PR review workflow (triggers on PR open/sync/reopen)

### Changed
- `AGENTS.md` — refreshed format with init-deep template (STRUCTURE, WHERE TO LOOK, CONVENTIONS, ANTI-PATTERNS sections)
- `LICENSE` — migrated from MIT to BSL 1.1 for commercial readiness
- `VERSION` — 0.1.1

### Notes
- Argus-flash GitHub App (https://github.com/apps/argus-flash) now integrated for PR review
- BSL 1.1 allows research/fork but prohibits commercial production use; auto-converts to Apache 2.0 after 5 years

## [0.1.0] — 2026-06-13

### Added
- `AGENTS.md` — identity, hard rules, Kold-Argus workflow, review dimensions, severity guide
- `SKILL.md` — design review skill with issue format, workflow, non-blocking context
- `README.md` — project overview, usage, project structure
- `VERSION` — 0.1.0
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `DEVELOPMENT-GUIDE.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `LICENSE` — MIT (upgraded to BSL 1.1 in v0.1.1)
- `CLAUDE.md` — Claude Code compatibility bridge
- `Makefile` — check-version, validate, release, package
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

### Changed
- AGENTS.md: Kold-Argus workflow formally documented; Argus connects to GitHub Argus App
- AGENTS.md: review dimensions table added
- SKILL.md: non-blocking context clarified

### Notes
- Kold and Argus are companion agents sharing the same design principles
- Argus is the review gate; Kold never bypasses the review
- All merge operations require human approval
