# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.3.1] — 2026-08-02

### Added

- **Fixed Output Format** — Added standardized, readable feedback format with summary header, severity groups (P0-P3), and consistent issue block structure
- **Stack-Aware API Review** — New framework detection (React, Vue, Angular, Svelte, Astro) with official documentation references for accurate syntax validation
- **Framework Anti-Patterns Library** — Comprehensive pattern catalog (React, Vue, Svelte, Angular, Astro, JS/TS) with detection rules, examples, and copy-ready fixes
- **Release Automation** — New `.github/workflows/release.yml` triggered by `v*` tag pushes: validates versioning, builds packages, and publishes a GitHub Release with full archive and skill package
- **Skill Package** — New `make package-skill` target creates `dist/argus-skill-v{VERSION}.zip` containing `SKILL.md`, `AGENTS.md`, and `manifest.yaml` for agent skill distribution
- **GitHub Release Workflow** — Automated release publishing via `softprops/action-gh-release` with CHANGELOG body and artifact uploads

### Changed

- **SKILL.md** — Added Technology Stack Detection section, expanded Review Dimensions with 7th dimension (Framework API Usage), added Framework Anti-Patterns Library, updated Output Format with new fields
- **AGENTS.md** — Added OUTPUT FORMAT section; updated STRUCTURE with release workflow, WHERE TO LOOK with release automation entry, COMMANDS with `package-skill` target, and NOTES with release workflow documentation
- **README.md** — Updated project structure, version references, and added skill package documentation
- **CONTRIBUTING.md** — Updated version management section with bump-patch workflow and release process
- **DEVELOPMENT-GUIDE.md** — Updated version references, added release workflow documentation, and branch strategy for composite action
- **manifest.yaml** — Version updated from 0.2.0 to 0.3.1
- **Makefile** — Added `package-skill` target, updated `package` to depend on it, updated `clean`, and refreshed version comments
- **.gitignore** — Added `dist/` exclusion pattern

### Fixed

- **Version consistency** — All stale 0.2.0 references in documentation updated to 0.3.0/0.3.1
- **SKILL.md corruption** — Repaired escaped code fences and bash-quoting artifacts that broke YAML frontmatter and Markdown rendering

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
- `action.yml` — New `fixture-mode` input; when `"true"` runs `run_fixture_tests.py` instead of `opencode github run` (for Argus repo own CI)
