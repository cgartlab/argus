# AGENTS.md — Argus

**Version:** 0.3.2 | **Project:** https://github.com/cgartlab/argus | **License:** MIT
**Updated:** 2026-08-21

---

## OVERVIEW

Argus is a cross-platform AI coding agent specialized in **frontend design code review** — hardcoded values, design token violations, a11y gaps, dark mode breaks, and stack-aware API usage with actionable code fixes. Runs standalone in any agent framework or as an automated GitHub App review gate.

Argus detects the project's technology stack and validates code against official documentation, then provides **copy-ready code fixes** just like Codex.

Consumer repositories can customize review behavior via a `.argus.yml` config file (see `docs/argus-config-schema.md`).

**Scope:** Pure HTML/CSS/JS codebases. No runtime code — behavior defined by `AGENTS.md` + `SKILL.md`.

---

## STRUCTURE

```
argus/
├── AGENTS.md                          # Identity, hard rules, review dimensions
├── SKILL.md                           # Skill trigger phrases, execution rules (detailed)
├── manifest.yaml                      # Agent manifest (name, version, capabilities)
├── CLAUDE.md                          # Claude Code integration (references AGENTS.md)
├── docs/
│   └── argus-config-schema.md         # .argus.yml consumer config reference
├── tests/
│   └── fixtures/                      # Fixture-based regression test suite
│       ├── README.md                  # How to add/run fixtures
│       ├── design-tokens/             # Design token & dark mode violations
│       ├── accessibility/             # ARIA, alt, semantic HTML violations
│       ├── hardcoded-values/          # Magic number spacing/radii/font-size
│       └── css-quality/               # Duplicate rules, BEM violations
├── src/
│   └── components/                    # Test components for review validation
├── tools/
│   ├── run_fixture_tests.py           # Fixture regression test runner
│   ├── load_config.py                 # Consumer .argus.yml loader + validator
│   ├── update_free_models.py          # Refresh config/free-models.yml from live opencode list
│   ├── bump_version.py                # Automated semver bumping
│   └── validate_versioning.py         # VERSION / CHANGELOG consistency check
├── config/
│   └── free-models.yml                # Auto-refreshed fallback model queue (every 12h)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # Lint + tool validation + fixture tests
│   │   ├── review.yml                 # Argus-Flash PR review (triggers composite action)
│   │   ├── release.yml                # Automated release workflow (tag-push triggers)
│   │   ├── update-free-models.yml     # 12h scheduled refresh of fallback model list
│   │   └── pr-automation.yml          # Auto-label/assign/project on PR open
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
| Agent manifest | `manifest.yaml` | Name, version, capabilities, inputs/outputs |
| Consumer configuration | `docs/argus-config-schema.md` | Full `.argus.yml` field reference |
| Config loader | `tools/load_config.py` | Merges defaults + consumer `.argus.yml` |
| Fixture test suite | `tests/fixtures/` | Regression tests for review rules |
| Fixture runner | `tools/run_fixture_tests.py` | `make test-fixtures` or directly |
| CI pipeline | `.github/workflows/ci.yml` | Lint + tool validation + fixture tests |
| PR review automation | `.github/workflows/review.yml` | Triggers argus-flash App |
| Release automation | `.github/workflows/release.yml` | Tag-push → validates → packages → GitHub Release |
| Reusable review action | `.github/actions/argus-review/action.yml` | Dynamic rule + config injection |
| Free model config | `config/free-models.yml` | Single source of truth for fallback model queue |
| Free model updater | `tools/update_free_models.py` | Refreshes config from live opencode list |
| Model refresh workflow | `.github/workflows/update-free-models.yml` | 12h scheduled refresh of fallback models |
| PR automation | `.github/workflows/pr-automation.yml` | Auto-label/assign/project on PR open |
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
- **Stack-aware review** — detect technology stack and reference official documentation for API usage validation.
- **Codex-style fixes** — always provide copy-ready code fixes, never just describe the problem.

---

## ANTI-PATTERNS (THIS PROJECT)

- **Flagging generated boilerplate** as P0/P1 — respect non-blocking context.
- **Downgrading severity** to avoid "noise" — false positives are noise, not real issues.
- **Approving without full review** — Argus never approves unseen PRs.
- **Bypassing review** — Kold never bypasses Argus review gate.
- **Skipping fixture tests** — every rule change must be accompanied by a fixture update.
- **Describing without fixing** — never just describe the problem; always provide the fix.

---

## UNIQUE STYLES

- **Telegraphic output** — `[P0] file:line — issue`. No fluff.
- **Code examples required** — show Found vs Expected for every issue.
- **Token naming** — always name the design token that should be used.
- **Group by severity** — P0 → P1 → P2 → P3.
- **Stack-aware** — reference official docs when flagging framework API issues.
- **Codex-style fixes** — provide copy-ready code fixes alongside every issue.

---

## OUTPUT FORMAT

All review feedback follows this fixed structure:

### Summary Header

```
## Argus Design Review Summary
- Total Issues: N (P0: X | P1: X | P2: X | P3: X)
- Files Reviewed: N
- Technology Stack: {detected stack}
- Documentation: {official docs URL}
```

### Severity Groups

Issues are grouped under headers in order: P0 → P1 → P2 → P3.

```
## P0 — Blocking Issues (must fix, CI will fail)

## P1 — High Priority (must fix before merge)

## P2 — Medium Priority (should fix)

## P3 — Low Priority (optional polish)
```

### Issue Block (repeats per issue)

```
─────────────────────────────────────────────────
[P{severity}] {file}:{line} — {short description}

  Found:    {current code snippet}
  Expected: {correct code snippet}

  Fix:
  ```.{extension}
  {copy-ready fix code}
  ```

  Token:    {design token to use, if applicable}
  Reference: {official docs URL for this API}
  Note:     {optional context or explanation}
```

### Format Rules

- Each issue block starts with a `─────────────────────────────────────────────────` separator line
- Code snippets are shown inline, truncated to relevant portion (max 80 chars per line)
- **Fix code block is mandatory** — always provide the exact fix to copy
- Empty `Note:` line is omitted if not needed
- No issue = output `✓ No issues found` under each severity group
- Always include `Reference:` link when flagging framework API issues

---

## COMMANDS

```bash
make check-version    # Show current version
make bump-patch       # Bump PATCH version (0.3.0 → 0.3.1)
make bump-minor       # Bump MINOR version (0.3.0 → 0.4.0)
make bump-major       # Bump MAJOR version (0.3.0 → 1.0.0)
make validate         # Run SKILL.md trigger phrase check + CHANGELOG + AGENTS.md + action.yml
make test-fixtures    # Run fixture regression tests (static heuristic mode)
make test-fixtures-llm # Run fixture tests in LLM mode (requires OpenCode CLI + model)
make test             # validate + test-fixtures (full pre-release check)
make release          # validate → git commit → tag → push
make package-skill    # Create skill package only (argus-skill-v{VERSION}.zip)
make package          # Create all release archives (full + skill package)
make clean            # Remove dist/
make package-skill    # Create skill package only (argus-skill-v{VERSION}.zip)
make package          # Create all release archives (full + skill package)
make clean            # Remove dist/
```

---

## NOTES

- **Pure documentation repo** — no `npm install`, no build step. Agent reads `AGENTS.md` + `SKILL.md` at startup.
- **Cross-platform** — works in any agent framework: OpenCode, Claude Code, Codex CLI, etc.
- **argus-flash GitHub App** — installed at `github.com/apps/argus-flash`. Any repo can install it and add a minimal review.yml to get automated design reviews.
- **Composite action** — `.github/actions/argus-review/action.yml` wraps OpenCode CLI + rule injection + config loading. Referenced as `cgartlab/argus/.github/actions/argus-review@main` from any repo.
- **Version bumping** — run `make bump-patch` (or bump-minor/bump-major), then `make test && make release`.
- **Fixture tests** — run without an API key in static heuristic mode; full LLM mode requires OpenCode CLI + a configured model.
- **Release workflow** — pushing a `v*.*.*` tag triggers `.github/workflows/release.yml` which validates versioning, builds packages, and publishes a GitHub Release with both the full archive and the skill package (`argus-skill-v{VERSION}.zip`).
