# Development Guide — Argus

Agent framework: OpenCode / Claude Code / Codex CLI / any agentskills.io-compatible runtime.

## Architecture

Argus has two operating modes:

### 1. Local Agent Mode

The agent's behavior is defined entirely by reading `AGENTS.md` and `SKILL.md` at startup. Pure documentation — no runtime code, no `npm install`, no build step.

### 2. Automated PR Review Mode (argus-flash App)

When a PR is opened in any repo that has the `argus-flash` GitHub App installed:

```
PR opened → GitHub Actions triggers review.yml
         → generate installation token via actions/create-github-app-token
         → call cgartlab/argus/.github/actions/argus-review@main
         → composite action:
             1. Configures git with the token
             2. Installs OpenCode CLI
             3. Reads AGENTS.md + SKILL.md at runtime, injects into PROMPT
             4. Runs `opencode github run`
             5. argus-flash bot comments review on the PR
```

The composite action dynamically loads rules from the argus repo at the referenced ref (`@main` or `@v0.2.0`). There is no hardcoded prompt — the review behavior is always driven by `AGENTS.md` + `SKILL.md`.

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

## Composite Action Maintenance

The composite action at `.github/actions/argus-review/action.yml` is the integration point for automated reviews. Key behaviors:

- **Dynamic rule injection**: `AGENTS.md` and `SKILL.md` are read via `cat ${{ github.action_path }}/../../../` and written to `$GITHUB_ENV` as `PROMPT`. This happens at runtime on every review run.
- **No hardcoded prompt**: The LLM prompt is entirely composed from the rule files. Updating AGENTS.md or SKILL.md changes review behavior for all consumer repos.
- **Token handling**: The `github-token` input is used for git operations and API calls. `actions/create-github-app-token@v1` is the recommended way to generate it.

### When to update action.yml

- Adding a new step (e.g., pre-processing files)
- Changing how PROMPT is constructed
- Updating the model name or CLI installation method
- Adding new inputs or changing defaults

### When NOT to update action.yml

- Adding/modifying review rules → edit `AGENTS.md` or `SKILL.md` only
- Adding trigger phrases → edit `SKILL.md` frontmatter only

## argus-flash App Integration

Any repo can use the composite action with the `argus-flash` GitHub App:

```yaml
- uses: cgartlab/argus/.github/actions/argus-review@main
  with:
    github-token: ${{ steps.app-token.outputs.token }}
```

Prerequisites:
1. Install `argus-flash` App at `github.com/apps/argus-flash` on the target repo
2. Add `ARGUS_FLASH_APP_ID` and `ARGUS_FLASH_PRIVATE_KEY` to repo Secrets
3. Create a minimal `review.yml` workflow

## Branch Strategy for Composite Action

| Ref | Behavior | Recommendation |
|---|---|---|
| `@main` | Latest rules at time of review run | Development / internal repos |
| `@v0.2.0` | Pinned to a release | Production / external consumer repos |

## Cross-Platform Compatibility

Argus runs in any framework that reads Markdown instructions:

| Platform | Instruction File | Notes |
|---|---|---|
| OpenCode | `AGENTS.md` | Also loads `SKILL.md` via config |
| Claude Code | `CLAUDE.md`->`@AGENTS.md` | Bridge file |
| Codex CLI | `AGENTS.md` | Read automatically |
| GitHub Actions | `action.yml` + `opencode github run` | Automated mode |

## Version Bumping

```bash
echo "0.2.0" > VERSION
make validate
make release   # validate → commit → tag → push
```

## Adding a New Review Rule

1. Identify the review dimension (token, a11y, dark mode, etc.)
2. Assign severity with rationale
3. Add to SKILL.md under the correct dimension with wrong/right code examples
4. Add to review checklist in AGENTS.md
5. Verify action.yml still works (dynamic loading means no change needed)
6. Update VERSION if meaningful
