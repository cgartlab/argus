---
title: Argus Skill
description: Download the Argus skill package and use it inside OpenCode, Claude Code, or Codex CLI.
order: 2
sidebarGroup: Start
updated: 2026-09-03
---

# Argus Skill

Argus ships as a **skill package** — a single downloadable zip that turns any agent framework into a frontend design reviewer. This page explains what the skill is, how to download it, and how to use it inside your agent.

If you already use the GitHub App ([Getting Started](/docs/getting-started)), you don't need the skill — the App automates everything. The skill is for teams that want the same review power inside their own coding tool.

## What's in the skill package

The archive `argus-skill-v{VERSION}.zip` contains three files:

| File | What it is |
|---|---|
| `AGENTS.md` | Identity and hard rules — the non-negotiables (severity, a11y baseline, output format) |
| `SKILL.md` | The review skill — trigger phrases, seven review dimensions, per-framework rules, output contract |
| `manifest.yaml` | Agent manifest — name, version, capabilities, inputs/outputs |

**Why it matters:** Argus is a *pure documentation* project — no runtime code, no build step, no dependencies. The "engine" is the rules in these files. Any agent that reads Markdown can apply them.

## Download

Get the latest skill package from the [GitHub Releases page](https://github.com/cgartlab/argus/releases) — look for the asset named `argus-skill-v{VERSION}.zip` on the newest release.

Direct download link — replace `{VERSION}` with the actual version number from the [Releases page](https://github.com/cgartlab/argus/releases):

```
https://github.com/cgartlab/argus/releases/latest/download/argus-skill-v{VERSION}.zip
```

> **Version tip:** the `{VERSION}` in the asset name matches the release tag. If you want a specific version, download the asset from that release's page instead of the latest one.

## How to use it

### Option 1 — Install as a skill in your agent

Each agent framework has a `skills/` directory where skill packages live. Unzip the archive into that folder and name the top folder after the skill.

```bash
# Generic example — check your framework's docs for the exact path
# Replace {VERSION} with the version you downloaded from the Releases page
mkdir -p ~/.config/<agent>/skills/argus-design-review
unzip argus-skill-v{VERSION}.zip -d ~/.config/<agent>/skills/argus-design-review
```

Common locations:

| Framework | Skills directory |
|---|---|
| OpenCode | `~/.config/opencode/skills/` (user), or `<project>/.opencode/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` |

### Option 2 — Point your agent at the repository

Clone the repo and let your agent load rules from it — no unzipping needed:

```bash
git clone https://github.com/cgartlab/argus.git
cd argus
```

Point your agent framework at this folder; `AGENTS.md` + `SKILL.md` load automatically.

### Option 3 — Invoke by skill name

If your framework discovers skills by name (like OpenCode), you can also invoke the registered skill directly:

```text
argus-design-review: review src/components/Button.jsx
```

## What to say to trigger a review

Once the skill is loaded, ask for a design review in plain language. Trigger phrases include:

- "帮我 review 这段代码"
- "检查一下这个组件的设计问题"
- "看看有没有 hardcoded values"
- "dark mode 有没有遗漏"
- "帮我做个 design audit"

Argus then audits the target code and returns findings with the standard `[P#] file:line` format plus a copy-ready fix for every issue.

## Before you run a review

Argus reviews run on the **OpenCode Zen free model** (IDs end in `-free`). Authenticate once:

```bash
opencode auth login
```

Choose **OpenCode** and paste your key from [opencode.ai/auth](https://opencode.ai/auth) — or set the `OPENCODE_API_KEY` environment variable. The free model costs 0 USD per token, but the API still authenticates every call.

## Skill vs GitHub App

| | Skill package | GitHub App (argus-flash) |
|---|---|---|
| Where it runs | Inside your agent (OpenCode, Claude Code, Codex CLI) | GitHub Actions, automatically on every PR |
| Setup | Download + unzip (or clone) | Install App + add 2 secrets + 1 workflow |
| Trigger | You ask, in your agent | Opening a PR |
| Best for | Manual reviews, local development, private tools | Automated review gate on every merge |

Both use the **same rules** — `AGENTS.md` + `SKILL.md` — so a review looks identical either way.

## Key facts

| | |
|---|---|
| Package name | `argus-design-review` |
| Archive | `argus-skill-v{VERSION}.zip` |
| License | MIT |
| Repository | [github.com/cgartlab/argus](https://github.com/cgartlab/argus) |
| Releases | [github.com/cgartlab/argus/releases](https://github.com/cgartlab/argus/releases) |
