---
title: Capabilities
description: The seven review dimensions Argus audits on every frontend file.
order: 2
sidebarGroup: System
updated: 2026-08-31
---

# Capabilities

This page explains the seven things Argus checks on every frontend file — in plain language, with everyday examples. Read it to understand what a review comment means and why each check matters.

Think of Argus as **a tireless reviewer who only cares about frontend details** — it never gets tired, never skips a file, and always shows you the exact fix.

## First: how Argus reports problems (the severity model)

Argus groups every issue into four severity levels. Think of them like a traffic light — red means stop, yellow means fix soon, green means optional.

| Severity | Plain meaning | Examples | Must you fix it? |
|---|---|---|---|
| **P0** | Blocking — the change will break something or fail CI (automated checks) | Bare color value in a component, missing dark-mode override | Yes — it blocks merge |
| **P1** | High — must fix before merging | Missing button label, hardcoded spacing | Yes, before merge |
| **P2** | Medium — should fix when you can | Duplicate CSS rules, empty error handlers | Should, but not blocking |
| **P3** | Low — polish | Cosmetic / style issues | Optional |

One important rule: **Argus never downgrades a real P0 or P1 issue.** If it's genuinely blocking, it stays blocking — that's what keeps the review trustworthy.

## The seven review dimensions

### 1. Design token audit

**Plain language:** A design token is a reusable design variable — you give a color, spacing, or font size a name and reuse that name everywhere. It's like deciding the color palette before painting a room, instead of mixing a new shade every time.

**Rule:** Every color in a component must use a token reference (`var(--ds-*)`), not a raw color value.

```css
/* WRONG — a raw color typed directly in the component */
.ds-card {
  background: oklch(99% 0.005 80);
  color: oklch(20% 0.02 60);
}

/* RIGHT — a reference to the token */
.ds-card {
  background: var(--ds-color-surface);
  color: var(--ds-color-fg);
}
```

**Exception:** Token *definitions* (in `:root` or `@keyframes`) may use raw values — that's where tokens are created.

**Why it matters:** raw colors scattered through components turn "change the theme" into a hunt-and-replace nightmare. One central token change updates the whole app.

### 2. Hardcoded value detection

**Plain language:** "Magic numbers" are spacing, corner radius, or font sizes typed directly (like `16px`) instead of using your design scale. It's like writing "16" in the middle of a math problem without saying what it means.

**Rule:** Spacing, radii, and type scale values must use the design token scale.

```css
/* WRONG — magic numbers */
padding: 16px;
border-radius: 8px;

/* RIGHT — named scale values */
padding: var(--ds-space-4);
border-radius: var(--ds-radius-lg);
```

**Why it matters:** when every component uses the same scale, the design stays consistent, and adjusting the whole scale later is a one-line change.

### 3. Accessibility review

**Plain language:** Accessibility (a11y) means making sure everyone can use your site — including people using screen readers, keyboard-only navigation, or low vision. WCAG is the international standard for this; AA is the level most products target.

**Rule:** WCAG AA is the baseline — mandatory, never downgraded to a warning.

| Pattern | Requirement |
|---|---|
| Icon-only `<button>` | Must have an `aria-label` (text that screen readers announce) |
| `<img>` | Must have an `alt` attribute (text description) |
| `<a>` without `href` | Don't use it as a button — use a real `<button>` |
| Focusable elements | Must show a visible focus indicator (like a border when tabbing) |
| Color contrast | 4.5:1 for normal text, 3:1 for large text |

**Why it matters:** a missing label doesn't break the visual layout, so it ships unnoticed — but it locks out real users. Argus treats accessibility as non-negotiable.

### 4. Dark mode coverage

**Plain language:** A token defined in `:root` (light theme) also needs a `[data-theme="dark"]` override. Without it, the color stays light in dark mode.

**Rule:** Every color token declared in `:root` must have a dark-mode override.

```css
/* WRONG — the light value has no dark override */
:root {
  --ds-color-bg: oklch(97% 0.012 80);
}

/* RIGHT — a dark override exists */
[data-theme="dark"] {
  --ds-color-bg: oklch(15% 0.008 75);
}
```

**Why it matters:** a missing override is a silent break — the page doesn't error, it just looks wrong (or unreadable) in dark mode. Users will notice before you do.

### 5. CSS consistency

**Plain language:** Small CSS sloppiness that compounds — duplicate rules, empty error handlers, broken naming conventions.

**Rule:** No duplicate rules in the same selector block, no empty `catch {}` blocks, valid BEM naming (a naming convention for CSS classes), no duplicate HTML `id`s.

**Why it matters:** duplicate rules mean the last one silently wins (confusing), empty `catch` blocks swallow errors (bugs hide), and inconsistent naming makes the codebase harder to maintain.

### 6. HTML structure validation

**Plain language:** Use the right HTML element for the job — a `<button>` for actions, an `<a>` for links.

**Rule:** No `<a>` tags without `href` used as interactive elements; semantic elements used correctly.

**Why it matters:** wrong elements break keyboard navigation and screen reader behavior. It costs nothing to use the right tag, and it makes your site work for everyone.

### 7. Framework API usage (stack-aware)

**Plain language:** "Stack" = the set of technologies your project uses. Argus detects yours and checks API usage against official documentation — so it catches misuse that a generic linter wouldn't know about.

**Rule:** Use framework APIs correctly per official docs.

| Stack | How Argus detects it | Documentation it checks |
|---|---|---|
| React | `*.tsx`/`*.jsx` + `react` in package.json | react.dev |
| Vue | `*.vue` | vuejs.org/guide |
| Svelte | `*.svelte` | svelte.dev/docs |
| Angular | `angular.json` | angular.dev/api |
| Astro | `*.astro` | docs.astro.build |
| Lit | `lit-*.js` / lit imports | lit.dev/docs |
| Vanilla CSS | CSS/SCSS only | developer.mozilla.org |

Argus keeps a library of framework anti-patterns (for example, React hooks dependency arrays, Vue Composition API consistency, Angular subscription cleanup) — each with a detection rule and a copy-ready fix.

**Why it matters:** framework misuse often passes tests but breaks at runtime. Because Argus checks against official docs, its advice stays current with each framework's best practices.

## What a review comment looks like

Every finding includes the file and line, what was found, what was expected, and a copy-ready fix — you can paste the fix and move on.