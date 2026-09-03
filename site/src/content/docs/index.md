---
title: Overview
description: What Argus is and how it reviews frontend code.
order: 0
sidebarGroup: Start
updated: 2026-08-31
---

# Overview

Argus is an AI reviewer for frontend code — it reads your HTML, CSS, and JavaScript and points out design problems before they ship. If you've ever merged a hardcoded color, a broken dark mode, or a button that screen readers can't find, Argus is built to catch exactly those mistakes.

This page explains what Argus does, the problems it solves, and who should use it. It's the best starting point — the other docs build on these basics.

## What is Argus, in one sentence

**Argus is a cross-platform AI coding agent that reviews frontend code for design quality and hands you copy-ready fixes.**

"Cross-platform" means it runs wherever you already work — inside coding agents like OpenCode, Claude Code, or Codex CLI, or as an automated reviewer on GitHub.

## What problem does it solve?

Frontend projects slowly accumulate "design debt" — small visual mistakes that pile up:

| Problem | What it looks like | Example |
|---|---|---|
| **Hardcoded values** | "Magic numbers" typed directly into CSS instead of reused variables | `padding: 16px` with no shared spacing scale |
| **Token drift** | The design system changes, but some components keep the old values | A color updated in one place, forgotten in another |
| **Accessibility gaps** | Some people can't use your site — no labels, no alt text, poor contrast | An icon button with no `aria-label` |
| **Dark mode breaks** | A color has no dark-mode override, so dark mode looks broken | A light background that stays light at night |

Argus reads every line of frontend code, flags issues with a severity level (P0 = blocking, down to P3 = optional polish), and gives a ready-to-paste fix for each one.

## Who is Argus for?

- **Frontend teams** that want a consistent design review on every pull request
- **Individual developers** who want a second pair of eyes on their UI code
- **Design system maintainers** who need to enforce token usage across many components

## How is it different from other linters and review tools?

| Other tools | Argus |
|---|---|
| Linters flag problems; you figure out the fix | Argus gives **copy-ready fixes** — paste and go |
| One-size-fits-all rules | **Stack-aware** — it detects React, Vue, Svelte, Angular, Astro, etc. and checks against official docs |
| Need installation, configuration, build steps | **Pure documentation** — no runtime code, no build step, just rules it reads at review time |

## Three ways to use it

- **Automated (GitHub App)** — install **argus-flash**, add a small workflow, and every pull request gets a design review comment automatically. See [Getting Started](/docs/getting-started).
- **Standalone (local agent)** — point any agent framework at `AGENTS.md` and `SKILL.md`; the review behavior loads automatically.
- **Skill package** — download `argus-skill-v{VERSION}.zip` from the [GitHub Releases](https://github.com/cgartlab/argus/releases) page and install it into your agent (OpenCode, Claude Code, Codex CLI). See [Argus Skill](/docs/skill).

**Why this matters:** the automated mode is what most teams use — it turns "remember to check the design" into "the bot checks it on every PR, every time." The skill package gives you the same rules inside your own tool.

## Key facts

| | |
|---|---|
| License | MIT |
| Version | 0.5.0 |
| Made by | [CGArtLab](https://github.com/cgartlab) |
| Repository | [github.com/cgartlab/argus](https://github.com/cgartlab/argus) |
| GitHub App | [github.com/apps/argus-flash](https://github.com/apps/argus-flash) |
| Runs in | OpenCode, Claude Code, Codex CLI, GitHub Actions |