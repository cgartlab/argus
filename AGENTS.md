# AGENTS.md — Argus

**Version:** 0.1.1 | **Project:** https://github.com/cgartlab/argus | **License:** MIT
**Generated:** 2026-06-17

---

## OVERVIEW

Argus is a cross-platform AI coding agent specialized in **frontend design code review** — hardcoded values, design token violations, a11y gaps, dark mode breaks. Runs standalone in any agent framework or as Kold's review gate.

**Scope:** Pure HTML/CSS/JS codebases. No runtime code — behavior defined by `AGENTS.md` + `SKILL.md`.

---

## STRUCTURE

```
argus/
├── AGENTS.md              # Identity, hard rules, review dimensions
├── SKILL.md               # Skill trigger phrases, execution rules (detailed)
├── Makefile               # validate, release, package, clean
├── .github/workflows/     # CI + release pipelines
└── .omo/                  # OpenCode runtime data
```

---

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Review workflow | `AGENTS.md` | Hard rules + output format |
| Skill execution | `SKILL.md` | Trigger phrases, review dimensions |
| Release process | `Makefile` | `make validate`, `make release` |
| CI pipelines | `.github/workflows/` | CI + release YAML |

---

## CONVENTIONS

- **Severity never downgraded** — P0/P1 stays P0/P1. False negatives damage trust.
- **A11y is mandatory** — WCAG AA baseline, never marked non-blocking.
- **Reference tokens** — name the exact token that should be used.
- **Context matters** — don't flag boilerplate, third-party resets, or `node_modules/`.

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
make validate        # Run SKILL.md trigger phrase check + CHANGELOG + AGENTS.md
make release         # validate → git commit → tag → push
make package         # Create dist/argus-v{VERSION}.tar.gz + .zip
make clean           # Remove dist/
```

---

## NOTES

- **Pure documentation repo** — no `npm install`, no build step. Agent reads `AGENTS.md` + `SKILL.md` at startup.
- **Cross-platform** — works in OpenClaw, Claude Code, OpenCode, Codex CLI, agentskills.io-compatible runtimes.
- **Version bumping** — update `VERSION` file, then `make release`.