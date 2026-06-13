# Development Guide — Argus

Agent framework: OpenClaw / Claude Code / OpenCode / Codex CLI / any agentskills.io-compatible runtime.

## Architecture

Argus is a pure documentation repository. The agent's behavior is defined entirely by:

- `AGENTS.md` — identity, hard rules, review dimensions
- `SKILL.md` — skill definition with trigger phrases and execution rules
- `skills/` — supplementary skill files with checklists and references

There is no runtime code. No `npm install`, no build step. The agent reads these files at startup and follows the instructions.

## AGENTS.md Structure

```
Identity
Core Capabilities
Hard Rules          <- invariants; severity and scope must not be weakened
Review Checklist    <- always run all checks
Output Format       <- format must be followed exactly
Version Management
Relationship with Kold
```

## SKILL.md Structure

```
YAML frontmatter (name, description, version)
Body:
  - Review Dimensions (with code examples of wrong/right)
  - Issue Severity Table
  - Output Format
  - Review Workflow
  - Non-Blocking Context
```

### Description Writing

The `description` field is a trigger mechanism, not a summary. It must contain 3+ real-world trigger phrases that a user would actually type.

```
description: "Use when reviewing frontend code for design quality,
  checking token usage, dark mode coverage, or accessibility.
  Trigger phrases: '帮我 review 这段代码'、'检查一下 hardcoded values'、'dark mode 有没有遗漏'"
```

## Severity Assignment

| Severity | When to use |
|---|---|
| P0 | Code will cause CI failure or silent runtime break |
| P1 | Accessibility violation or dark mode break |
| P2 | Hardcoded value, semantic violation, empty catch |
| P3 | Polish, cosmetic, code style |

Never downgrade a real P0 or P1 to P2/P3. False negatives damage trust more than false positives.

## Output Format

Each issue must report: severity, file:line, what was found, what was expected, which token should be used.

## Cross-Platform Compatibility

SKILL.md follows the agentskills.io open standard. It works in:

| Platform | Skill Path |
|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` |
| Codex CLI | `.agents/skills/<name>/SKILL.md` |
| OpenCode | `skills/<name>/SKILL.md` |
| OpenClaw | `<workspace>/skills/<name>/SKILL.md` |

## Version Bumping

```bash
echo "0.2.0" > VERSION
git add -A && git commit -m "chore(release): bump to v0.2.0"
git tag v0.2.0 && git push origin main --tags
```

## Adding a New Review Rule

1. Identify the review dimension (token, a11y, dark mode, etc.)
2. Assign severity with rationale
3. Add to SKILL.md under the correct dimension with wrong/right code examples
4. Add to review checklist in AGENTS.md
5. Update VERSION if meaningful