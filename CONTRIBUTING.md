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
- `VERSION` — single line, semantic versioning
- All Markdown files — no emoji decorations in headings or lists

## Version Management

```bash
# After changing any content
echo "0.1.1" > VERSION
git add -A && git commit -m "chore(release): bump to v0.1.1"
git tag v0.1.1 && git push origin main --tags
```

## Branch Naming

- `fix/<desc>` — bug fixes
- `feat/<desc>` — new features
- `docs/<desc>` — documentation only
- `chore/<desc>` — refactor, format, tooling

## Pull Request Checklist

- [ ] `AGENTS.md` and `SKILL.md` remain consistent with each other
- [ ] VERSION bumped if this is a meaningful change
- [ ] No emoji decorations in prose
- [ ] SKILL.md description has 3+ trigger phrases
- [ ] New review rules have severity assigned with rationale