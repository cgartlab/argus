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
# Bump version (updates VERSION + CHANGELOG + site version markers, stages the files)
make bump-patch   # 0.4.0 → 0.4.1 (bug fixes, minor changes)
make bump-minor   # 0.4.0 → 0.5.0 (new features)
make bump-major   # 0.4.0 → 1.0.0 (breaking changes)

# Fill in the new CHANGELOG section, review, then commit the bump:
#   git commit -m "chore(release): prepare vX.Y.Z"

# Full pre-release check
make test

# Cut a release (release-gate → tag → push → triggers release workflow)
# `make release` refuses to re-release an existing tag or an older version.
make release
```

Pushing a `v*.*.*` tag triggers `.github/workflows/release.yml` which:
1. Validates versioning consistency (VERSION ↔ CHANGELOG)
2. Builds full archive (`dist/argus-v{VERSION}.tar.gz` + `.zip`)
3. Builds skill package (`dist/argus-skill-v{VERSION}.zip`)
4. Creates a GitHub Release with all artifacts
5. Publishes the same skill package to SkillHub when `SKILLHUB_API_KEY` is configured
6. Publishes the skill package to ClawHub when `CLAWHUB_TOKEN` secret + `CLAWHUB_OWNER` variable are set

skills.sh indexing is a separate one-time manual step: run the **skills.sh Index Request** workflow (Actions tab → "Run workflow") after a release is public. It ensures discovery topics on this repo and files an index-request issue in `vercel-labs/skills` (needs a `SKILLS_SH_GH_TOKEN` PAT with `repo` scope; without it, only topics are synced).

### Multi-Registry Secrets/Variables

| Name | Kind | Purpose |
|---|---|---|
| `SKILLHUB_API_KEY` | secret | SkillHub auto-publish (`release.yml` skillhub job) |
| `CLAWHUB_TOKEN` | secret | ClawHub auto-publish (`release.yml` clawhub job); a `clh_...` API token |
| `CLAWHUB_OWNER` | variable | ClawHub owner handle (org/personal); publishes as `@<owner>/argus-design-review` |
| `SKILLS_SH_GH_TOKEN` | secret | PAT with `repo` scope, for the cross-org `vercel-labs/skills` index issue |

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
- [ ] SKILL.md has SkillHub frontmatter: `slug`, `displayName`, `version`, `description`
- [ ] Config changes conform to `config/argus-config.schema.json` (`make validate-schema`)
- [ ] Rule/model changes pass `make eval-gate` (quality regression gates vs baseline); raise the baseline only after an intentional, verified improvement
- [ ] Rule/severity changes pass `make validate-severity` (matrix consistency: config ↔ SKILL.md ↔ load_config)
- [ ] FP appeals are filed via `tools/add_fp_appeal.py` (creates the false-positives fixture pair + scanner check)
- [ ] SKILL.md has ClawHub-required frontmatter: `name` (kebab), `description`, `version`
- [ ] New review rules have severity assigned with rationale
