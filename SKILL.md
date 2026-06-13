---
name: argus-design-review
description: "Use when reviewing frontend code for design quality — checking design token usage, hardcoded values, dark mode coverage, accessibility compliance, CSS consistency, or semantic HTML. Use when auditing a component, page, or design system for issues. Trigger phrases: '帮我 review 这段代码'、'检查一下这个组件的设计问题'、'看看有没有 hardcoded values'、'dark mode 有没有遗漏'、'无障碍有没有问题'、'帮我做个 design audit'"
version: 0.1.0
---

# Argus Design Review Skill

When this skill is active, every line of frontend code is audited against the same standards: design tokens used correctly, no hardcoded values, dark mode fully covered, accessibility baseline met.

## Review Dimensions

### 1. Design Tokens

**Rule:** Every color in component rules must be a `var(--ds-*)` reference. No bare `oklch()`, `#hex`, or `rgb()`.

```css
/* WRONG — bare oklch in component rule */
.ds-card {
  background: oklch(99% 0.005 80);
  color: oklch(20% 0.02 60);
}

/* RIGHT — token reference */
.ds-card {
  background: var(--ds-color-surface);
  color: var(--ds-color-fg);
}
```

**Exception:** Token declarations in `:root` and `@keyframes` may use bare oklch/hex.

**Flag:** Any occurrence of bare color value in component rules (CSS or inline `style=`).

### 2. Hardcoded Values

**Rule:** All spacing, radii, and type scale values must use design token scale. No magic numbers.

```css
/* WRONG */
padding: 16px;
border-radius: 8px;

/* RIGHT */
padding: var(--ds-space-4);
border-radius: var(--ds-radius-lg);
```

**Flag:** Any numeric value (not 0) that should be a design token but isn't.

### 3. Dark Mode Coverage

**Rule:** Every color token declared in `:root` must have a `[data-theme="dark"]` override.

```css
/* WRONG — no dark override */
:root {
  --ds-color-bg: oklch(97% 0.012 80);
}

/* RIGHT — override exists */
[data-theme="dark"] {
  --ds-color-bg: oklch(15% 0.008 75);
}
```

**Flag:** Any `:root` color token without a `[data-theme="dark"]` override. This is a silent dark mode break — colors may become unreadable.

### 4. Accessibility

**Rule:** WCAG AA baseline. Mandatory, never demoted to warning.

| Pattern | Requirement |
|---|---|
| Icon-only `<button>` | `aria-label` present |
| `<img>` | `alt` attribute present |
| `<a>` without href | Not used as a button; use `<button>` |
| Focusable elements | Visible focus indicator |
| Color contrast | 4.5:1 for normal text, 3:1 for large text |

**Flag:** Any violation is P1 minimum.

### 5. CSS Quality

- No duplicate rules in same selector block
- No empty `catch {}` blocks
- Valid BEM (no dangling modifiers like `.parent a--active`)
- No invalid HTML `id` duplicates

### 6. HTML Structure

- No `<a>` tags without `href` used as interactive elements
- Semantic elements used correctly (`<button>` for actions, `<a>` for links)

## Issue Severity

| Severity | Meaning | Examples |
|---|---|---|
| **P0** | Blocking — CI will fail | Bare oklch in component rule, broken dark mode override |
| **P1** | High — must fix | Missing aria-label, invalid BEM, hardcoded spacing |
| **P2** | Medium — should fix | Duplicate rules, empty catch blocks, semantic violations |
| **P3** | Low — polish | Code style, cosmetic issues |

## Output Format

For each issue found:

```
[P severity] <file>:<line> — <issue description>
  Found:   <what the code currently says>
  Expected: <what it should say>
  Token:    <the design token it should use, if applicable>
```

Group output by severity: P0 → P1 → P2 → P3.

## Review Workflow

1. Read the codebase — understand the design token system in use
2. Scan for bare color values (oklch/hex/rgb outside :root declarations)
3. Scan for magic numbers in spacing, radii, font sizes
4. Verify dark mode coverage for every color token
5. Check accessibility — buttons, images, semantic HTML
6. Check CSS quality — duplicates, BEM, empty catch blocks
7. Report findings grouped by severity

## Non-Blocking Context

Do NOT flag issues in:
- Third-party resets or normalize.css
- Generated boilerplate that will be replaced
- Test fixtures and mock data files
- `node_modules/` (ignore entirely)