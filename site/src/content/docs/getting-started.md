---
title: Getting Started
description: Install argus-flash in three steps and run your first design review.
order: 1
sidebarGroup: Start
updated: 2026-08-31
---

# Getting Started

This guide gets Argus running on your code in about 10 minutes. By the end, every pull request in your repository will get an automated design review comment.

Argus has two ways to run — the **GitHub App** (automated reviews on every PR) and the **local agent** (you run it inside your own coding tool). Most people start with the GitHub App, so that's the focus here.

## Prerequisites

Before you start, make sure you have:

- A **GitHub account** with permission to install apps and edit repository settings (usually "Admin" access on the repo)
- A **repository with frontend code** — HTML, CSS, or JavaScript. It can be public or private.
- (Only for local mode) An agent framework like OpenCode, Claude Code, or Codex CLI

## Method A: Automated reviews with the GitHub App

The most common setup. Three steps.

### Step 1 — Install the app

**What to do:** Open [github.com/apps/argus-flash](https://github.com/apps/argus-flash) and click **Install**. Choose the repositories you want reviewed (all of them, or specific ones).

**Why:** A GitHub App is an official bot account. Installing it tells GitHub "this bot is allowed to read my code and comment on my PRs."

**What you'll see:** The app appears in your repository's Settings → Integrations list, and GitHub sends you a confirmation email.

### Step 2 — Add two secrets

**What to do:** Go to your repository → **Settings → Secrets and variables → Actions** → **New repository secret**, and add these two:

| Secret name | What it is |
|---|---|
| `ARGUS_FLASH_APP_ID` | The app's ID number (a long numeric string) |
| `ARGUS_FLASH_PRIVATE_KEY` | The app's private key — a long encrypted text block that proves the bot is really you |

**Where do these values come from?** When you install the app, GitHub shows you the **App ID** and lets you generate a **private key**. If you skipped it, find both on your app's settings page on GitHub.

**Why:** An Actions secret is an encrypted setting stored on GitHub — code can't read it directly, and it never appears in logs. The workflow uses these two secrets to generate a temporary "token" that lets the bot act on your behalf.

**What you'll see:** The secrets appear in the list on the Settings → Secrets page, shown as `••••••••`.

> **Important:** a private key is like a password — never commit it to your repository or paste it into a public issue.

### Step 3 — Create a workflow file

**What to do:** In your repository, create a file at `.github/workflows/argus-review.yml` with the content below.

**Why:** `.github/workflows/` is a special folder — GitHub treats every file in it as a "workflow," an automated task triggered by events (like a new pull request). This workflow tells GitHub: "when someone opens a PR, run Argus."

```yaml
name: Argus-Flash Review          # The workflow's name, shown in the Actions tab
on: [pull_request]                # Run whenever a PR is opened or updated
jobs:
  review:                         # A "job" = one thing this workflow does
    runs-on: ubuntu-latest        # Use a standard GitHub server (Linux)
    permissions:
      contents: read              # The bot may read your code
      pull-requests: write        # The bot may comment on PRs
    steps:
      - uses: actions/checkout@v4 # Step 1: download a copy of your code onto the server
        with: { persist-credentials: false }

      - name: Generate argus-flash token   # Step 2: create a short-lived bot token
        id: app-token
        uses: actions/create-github-app-token@v1
        with:
          app-id: ${{ secrets.ARGUS_FLASH_APP_ID }}            # Read the first secret you added
          private-key: ${{ secrets.ARGUS_FLASH_PRIVATE_KEY }}  # Read the second secret you added

      - uses: cgartlab/argus/.github/actions/argus-review@main # Step 3: run the Argus review
        with:
          github-token: ${{ steps.app-token.outputs.token }}   # Pass the bot token to Argus
```

**What you'll see:** A new workflow appears under your repository's **Actions** tab.

### Step 4 — Open a pull request and watch the magic

**What to do:** Open a pull request (PR) — that's the process of proposing code changes for review. Add any frontend change, even a tiny one.

**Why:** The workflow triggers on `pull_request` events, so opening a PR is what starts the review.

**What you'll see (expected result):** Within a few minutes, a comment from **argus-flash[bot]** appears on your PR with a summary like this:

```
## Argus Design Review Summary
- Total Issues: 2 (P0: 0 | P1: 1 | P2: 1 | P3: 0)
```

Each issue shows the file and line, what was found, what was expected, and a copy-ready fix you can paste.

## Method B: Local agent mode

If you don't use GitHub, or you prefer to review inside your own coding tool:

```bash
git clone https://github.com/cgartlab/argus.git   # download the Argus repository
cd argus                                          # go into it
```

**Why:** Argus is a pure documentation project — no installation, no build step. The "engine" is two files, `AGENTS.md` and `SKILL.md`, which define all review rules.

Point your agent framework (OpenCode, Claude Code, Codex CLI) at this folder, and the review behavior loads automatically.

## Pinning the action version

**What to do:** In the workflow, use a version tag instead of `@main`:

```yaml
- uses: cgartlab/argus/.github/actions/argus-review@v0.4.0
```

**Why:** `@main` always uses the latest Argus rules — great for development, but a rule change could alter your reviews at any time. A pinned tag (like `@v0.4.0`) keeps reviews stable for production repos.

## Troubleshooting

**Q: The bot didn't comment on my PR. What do I check?**
1. Open the **Actions** tab and click the "Argus-Flash Review" workflow run — if it failed, the error is there.
2. Confirm the workflow file is exactly at `.github/workflows/argus-review.yml` (not `.github/argus-review.yml`).
3. Confirm the app is installed on **this** repository (Settings → Integrations).
4. Confirm both secrets are spelled exactly `ARGUS_FLASH_APP_ID` and `ARGUS_FLASH_PRIVATE_KEY`.

**Q: The workflow fails with "secret not found" or "Permission denied."**
The secrets are missing or mistyped. Re-add them at Settings → Secrets and variables → Actions. A common mistake is a trailing space or a line break inside the private key — paste the key exactly as GitHub generated it.

**Q: I don't want to see a certain rule anymore.**
Argus supports a config file called `.argus.yml` where you can downgrade or ignore specific rules. See [Configuration](/docs/configuration).

**Q: `@main` changed my review behavior suddenly. How do I stop that?**
Switch the workflow to a pinned tag like `@v0.4.0` (see "Pinning the action version" above).