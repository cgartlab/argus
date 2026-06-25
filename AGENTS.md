# AGENTS.md — Argus

**Version:** 0.3.0 | **Project:** https://github.com/cgartlab/argus | **License:** MIT
**Updated:** 2026-06-25

---

## OVERVIEW

Argus is a cross-platform AI coding agent specialized in **frontend design code review** — hardcoded values, design token violations, a11y gaps, dark mode breaks. Runs standalone in any agent framework or as an automated GitHub App review gate.

Consumer repositories can customize review behavior via a `.argus.yml` config file (see `docs/argus-config-schema.md`).

**Scope:** Pure HTML/CSS/JS codebases. No runtime code — behavior defined by `AGENTS.md` + `SKILL.md`.

---

## STRUCTURE

```
argus/
├── AGENTS.md                          # Identity, hard rules, review dimensions
├── SKILL.md                           # Skill trigger phrases, execution rules (detailed)
├── docs/
│   └── argus-config-schema.md         # .argus.yml consumer config reference
├── tests/
│   └── fixtures/                      # Fixture-based regression test suite
│       ├── README.md                  # How to add/run fixtures
│       ├── design-tokens/             # Design token & dark mode violations
│       ├── accessibility/             # ARIA, alt, semantic HTML violations
│       ├── hardcoded-values/          # Magic number spacing/radii/font-size
│       └── css-quality/               # Duplicate rules, BEM violations
├── tools/
│   ├── run_fixture_tests.py           # Fixture regression test runner
│   ├── load_config.py                 # Consumer .argus.yml loader + validator
│   ├── bump_version.py                # Automated semver bumping
│   └── validate_versioning.py         # VERSION / CHANGELOG consistency check
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Lint + tool validation + fixture tests
│   │   └── review.yml                 # Argus-Flash PR review (triggers composite action)
│   └── actions/
│       └── argus-review/
│           └── action.yml             # Reusable composite action for any repo
├── Makefile                           # validate, test, release, package, clean
└── .omo/                              # OpenCode runtime data
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Agent identity & rules | `AGENTS.md` | Hard rules + output format |
| Skill execution | `SKILL.md` | Trigger phrases, review dimensions |
| Consumer configuration | `docs/argus-config-schema.md` | Full `.argus.yml` field reference |
| Config loader | `tools/load_config.py` | Merges defaults + consumer `.argus.yml` |
| Fixture test suite | `tests/fixtures/` | Regression tests for review rules |
| Fixture runner | `tools/run_fixture_tests.py` | `make test-fixtures` or directly |
| CI pipeline | `.github/workflows/ci.yml` | Lint + tool validation + fixture tests |
| PR review automation | `.github/workflows/review.yml` | Triggers argus-flash App |
| Reusable review action | `.github/actions/argus-review/action.yml` | Dynamic rule + config injection |
| GitHub App | `github.com/apps/argus-flash` | Installed on any repo needing design review |
| Release process | `Makefile` | `make validate`, `make release` |

---

## CONVENTIONS

- **Severity never downgraded** — P0/P1 stays P0/P1. False negatives damage trust.
- **A11y is mandatory** — WCAG AA baseline, never marked non-blocking.
- **Reference tokens** — name the exact token that should be used.
- **Context matters** — don't flag boilerplate, third-party resets, or `node_modules/`.
- **Dynamic rule injection** — When run via composite action, AGENTS.md + SKILL.md are read at runtime and injected into the review prompt. Any update to these files is automatically picked up by all repos using the action.
- **Consumer config respected** — `.argus.yml` in the consumer repo adjusts token prefix, severity overrides, ignore paths, and failure thresholds. Hard rules (P0 color violations, a11y) cannot be fully disabled.

---

## ANTI-PATTERNS (THIS PROJECT)

- **Flagging generated boilerplate** as P0/P1 — respect non-blocking context.
- **Downgrading severity** to avoid "noise" — false positives are noise, not real issues.
- **Approving without full review** — Argus never approves unseen PRs.
- **Bypassing review** — Kold never bypasses Argus review gate.
- **Skipping fixture tests** — every rule change must be accompanied by a fixture update.

---

## UNIQUE STYLES

- **Telegraphic output** — `[P0] file:line — issue`. No fluff.
- **Code examples required** — show Found vs Expected for every issue.
- **Token naming** — always name the design token that should be used.
- **Group by severity** — P0 → P1 → P2 → P3.

---

## COMMANDS

```bash
make check-version    # Show current version
make validate         # Run SKILL.md trigger phrase check + CHANGELOG + AGENTS.md + action.yml
make test-fixtures    # Run fixture regression tests (static heuristic mode)
make test             # validate + test-fixtures (full pre-release check)
make release          # validate → git commit → tag → push
make package          # Create dist/argus-v{VERSION}.tar.gz + .zip
make clean            # Remove dist/
```

---

## NOTES

- **Pure documentation repo** — no `npm install`, no build step. Agent reads `AGENTS.md` + `SKILL.md` at startup.
- **Cross-platform** — works in any agent framework: OpenCode, Claude Code, Codex CLI, etc.
- **argus-flash GitHub App** — installed at `github.com/apps/argus-flash`. Any repo can install it and add a minimal review.yml to get automated design reviews.
- **Composite action** — `.github/actions/argus-review/action.yml` wraps OpenCode CLI + rule injection + config loading. Referenced as `cgartlab/argus/.github/actions/argus-review@main` from any repo.
- **Version bumping** — update `VERSION` file, then `make release`.
- **Fixture tests** — run without an API key in static heuristic mode; full LLM mode requires OpenCode CLI + a configured model.
