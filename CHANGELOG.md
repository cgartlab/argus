# Changelog

All notable changes are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

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
- `LICENSE` — MIT
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