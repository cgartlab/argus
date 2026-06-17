# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

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