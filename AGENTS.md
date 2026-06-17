# AGENTS.md — Argus

**Version:** 0.2.0 | **Project:** https://github.com/cgartlab/argus | **License:** MIT
**Generated:** 2026-06-17

---

## OVERVIEW

Argus is a cross-platform AI coding agent specialized in **frontend design code review** — hardcoded values, design token violations, a11y gaps, dark mode breaks. Runs standalone in any agent framework or as an automated GitHub App review gate.

**Scope:** Pure HTML/CSS/JS codebases. No runtime code — behavior defined by `AGENTS.md` + `SKILL.md`.

---

## STRUCTURE

```
argus/
├── AGENTS.md                    # Identity, hard rules, review dimensions
├── SKILL.md                     # Skill trigger phrases, execution rules (detailed)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # YAML syntax check + required file validation
│   │   └── review.yml          # Argus-Flash PR review (triggers composite action)
│   └── actions/
│       └── argus-review/
│           └── action.yml      # Reusable composite action for any repo
├── Makefile                     # validate, release, package, clean
└── .omo/                        # OpenCode runtime data
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent identity & rules | `AGENTS.md` | Hard rules + output format |
| Skill execution | `SKILL.md` | Trigger phrases, review dimensions |
| CI pipeline | `.github/workflows/ci.yml` | YAML lint + required file checks |
| PR review automation | `.github/workflows/review.yml` | Triggers argus-flash App |
| Reusable review action | `.github/actions/argus-review/action.yml` | Dynamic rule injection at runtime |
| GitHub App | `github.com/apps/argus-flash` | Installed on any repo needing design review |
| Release process | `Makefile` | `make validate`, `make release` |

---

## CONVENTIONS

- **Severity never downgraded** — P0/P1 stays P0/P1. False negatives damage trust.
- **A11y is mandatory** — WCAG AA baseline, never marked non-blocking.
- **Reference tokens** — name the exact token that should be used.
- **Context matters** — don't flag boilerplate, third-party resets, or `node_modules/`.
- **Dynamic rule injection** — When run via composite action, AGENTS.md + SKILL.md are read at runtime and injected into the review prompt. Any update to these files is automatically picked up by all repos using the action.

---

## ANTI-PATTERNS (THIS PROJECT)

- **Flagging generated boilerplate** as P0/P1 — respect non-blocking context.
- **Downgrading severity** to avoid "noise" — false positives are noise, not real issues.
- **Approving without full review** — Argus never approves unseen PRs.
- **Bypassing review** — Kold never bypasses Argus review gate.

---

## UNIQUE STYLES

- **Telegraphic output** — `[P0] file:line — issue`. No fluff.
- **Code examples required** — show Found vs Expected for every issue.
- **Token naming** — always name the design token that should be used.
- **Group by severity** — P0 → P1 → P2 → P3.

---

## COMMANDS

```bash
make check-version   # Show current version
make validate        # Run SKILL.md trigger phrase check + CHANGELOG + AGENTS.md + action.yml
make release         # validate → git commit → tag → push
make package         # Create dist/argus-v{VERSION}.tar.gz + .zip
make clean           # Remove dist/
```

---

## NOTES

- **Pure documentation repo** — no `npm install`, no build step. Agent reads `AGENTS.md` + `SKILL.md` at startup.
- **Cross-platform** — works in any agent framework: OpenCode, Claude Code, Codex CLI, etc.
- **argus-flash GitHub App** — installed at `github.com/apps/argus-flash`. Any repo can install it and add a minimal review.yml to get automated design reviews.
- **Composite action** — `.github/actions/argus-review/action.yml` wraps OpenCode CLI + rule injection. Referenced as `cgartlab/argus/.github/actions/argus-review@main` from any repo.
- **Version bumping** — update `VERSION` file, then `make release`.
