# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

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
