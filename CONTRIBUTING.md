# Contributing to Argus

Thank you for your interest in contributing to Argus.

## Code of Conduct

This project follows [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md). By participating, you agree to uphold its terms.

## What to Contribute

| Type | How |
|---|---|
| Bug report | Open an issue with the code that was incorrectly flagged or missed |
| Review improvement | PR with the specific scenario where Argus's review was wrong or incomplete |
| Documentation | Direct PR for typos, clarity, or missing content |
| Skill improvement | PR with updated SKILL.md — describe the real-world scenario that prompted the change |

**Important:** For new review rules, new severity assignments, or breaking changes, open an issue first. Direct PRs without prior discussion may be closed.

## Development Setup

No build step required. Argus runs anywhere that can read Markdown files.

```bash
git clone https://github.com/cgartlab/argus.git
cd argus
```

## File Conventions

- `AGENTS.md` — behavioral rules, never removed or weakened
- `SKILL.md` — skill definition with trigger phrases; description must have 3+ real-world trigger phrases
- `.github/actions/argus-review/action.yml` — composite action wrapping OpenCode CLI + rule injection
- `VERSION` — single line, semantic versioning
- All Markdown files — no emoji decorations in headings or lists

## Version Management

```bash
# Bump version (automatically updates VERSION + CHANGELOG)
make bump-patch   # 0.3.0 → 0.3.1 (bug fixes, minor changes)
make bump-minor   # 0.3.0 → 0.4.0 (new features)
make bump-major   # 0.3.0 → 1.0.0 (breaking changes)

# Full pre-release check
make test

# Cut a release (commit → tag → push → triggers release workflow)
make release
```

Pushing a `v*.*.*` tag triggers `.github/workflows/release.yml` which:
1. Validates versioning consistency (VERSION ↔ CHANGELOG)
2. Builds full archive (`dist/argus-v{VERSION}.tar.gz` + `.zip`)
3. Builds skill package (`dist/argus-skill-v{VERSION}.zip`)
4. Creates a GitHub Release with all artifacts

## Branch Naming

- `fix/<desc>` — bug fixes
- `feat/<desc>` — new features
- `docs/<desc>` — documentation only
- `chore/<desc>` — refactor, format, tooling

## Pull Request Checklist

- [ ] `AGENTS.md` and `SKILL.md` remain consistent with each other
- [ ] `.github/actions/argus-review/action.yml` is consistent with `AGENTS.md` and `SKILL.md`
- [ ] VERSION bumped if this is a meaningful change
- [ ] No emoji decorations in prose
- [ ] SKILL.md description has 3+ trigger phrases
- [ ] New review rules have severity assigned with rationale
