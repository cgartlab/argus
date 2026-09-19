# Argus Site Web Quality Audit — 2026-09-19

**Repository:** github.com/cgartlab/argus (site/ subproject)  
**Base commit:** b912e7a  
**Audit date:** 2026-09-19  
**Auditor:** SenseNova agent (automated scan + manual review)  
**Severity scale:** P0 (critical flow broken, injectable, secrets in bundle) → P1 (critical flow blocked, severe unreadability) → P2 (secondary page/state defects, WCAG AA) → P3 (polish)

---

## ① Mechanical Gates

| Gate | Command | Exit | Notes |
|------|---------|------|-------|
| npm audit | `npm audit --audit-level=high` | 0 | 0 vulnerabilities |
| Site build | `npm run build` | 0 | 12 pages built in 1.33s |
| **Gap:** lint | No `lint` script in package.json | — | Not installed; no ESLint config |
| **Gap:** typecheck | No `typecheck`/`tsc` script in package.json | — | `tsconfig.json` exists (astro/tsconfigs/strict) but no script |
| **Gap:** test | No `test` script in package.json | — | No test framework |

**Note:** This site is a static Astro marketing site. The only automated gates are `npm audit` and `npm run build`. No lint, typecheck, or test infrastructure exists. Adding any would require new devDependencies.

---

## P0 — Blocking Issues

✓ **No issues found.**

---

## P1 — High Priority

✓ **No issues found.**

---

## P2 — Medium Priority

─────────────────────────────────────────────────

### [P2] [安全] site/src/components/Header.astro:30 — External nav links lack `target="_blank" rel="noopener noreferrer"`

  Found:    `<a href={item.href} ...>{item.label}</a>`
  Expected: `<a href={item.href} target="_blank" rel="noopener noreferrer" ...>{item.label}</a>`
  
  CWE-1021 (Improper Restriction of Rendered UI Layers or Frames)  
  Reference: https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/target  
  Basis: The Header.astro component detects external links (`item.href.startsWith('http')`) at line 22 but does not add `target="_blank" rel="noopener noreferrer"` for them. The GitHub link (`https://github.com/cgartlab/argus` from site.ts nav) navigates in the same tab without `rel="noopener"`, enabling reverse tabnabbing.
  
  Fix:
  ```html
  <a
    href={item.href}
    target={isExternal ? '_blank' : undefined}
    rel={isExternal ? 'noopener noreferrer' : undefined}
    aria-current={isActive ? 'page' : undefined}
    class:list={[...]}
  >
    {item.label}
  </a>
  ```
  Note: This fix requires modifying the `site.nav` rendering loop in Header.astro. The `isExternal` variable is already computed at line 22 — it just needs to be used to conditionally set `target` and `rel`.

─────────────────────────────────────────────────

### [P2] [安全] site/src/components/Footer.astro:27,30 — External links lack `target="_blank" rel="noopener noreferrer"`

  Found:    `<a href={site.github} ...>GitHub</a>` / `<a href={site.appUrl} ...>Install the App</a>`
  Expected: `<a href={site.github} target="_blank" rel="noopener noreferrer" ...>GitHub</a>` / `<a href={site.appUrl} target="_blank" rel="noopener noreferrer" ...>Install the App</a>`
  
  CWE-1021  
  Basis: Footer.astro has 3 external links (creatorUrl, github, appUrl) without `target` or `rel` attributes. Same reverse tabnabbing risk as Header.

─────────────────────────────────────────────────

### [P2] [安全] site/src/components/Hero.astro:15,28 — External links lack `target="_blank" rel="noopener noreferrer"`

  Found:    `<a href={site.creatorUrl} ...>CGArtLab</a>` / `<a href={site.appUrl} class="btn-primary no-underline">...`
  Expected: `<a href={site.creatorUrl} target="_blank" rel="noopener noreferrer" ...>CGArtLab</a>` / `<a href={site.appUrl} target="_blank" rel="noopener noreferrer" class="btn-primary no-underline">...`
  
  CWE-1021  
  Basis: Hero.astro has 2 external links (creatorUrl, appUrl) without `target` or `rel` attributes.

─────────────────────────────────────────────────

### [P2] [安全] site/src/pages/index.astro:84,103 — External links in links section lack `target="_blank" rel="noopener noreferrer"`

  Found:    `<a href={site.github} class="mt-4 inline-block text-sm font-medium text-accent no-underline hover:text-accent-strong">...` / `<a href={site.appUrl} class="mt-4 inline-block text-sm font-medium text-accent no-underline hover:text-accent-strong">...`
  Expected: `<a href={site.github} target="_blank" rel="noopener noreferrer" class="...">...` / `<a href={site.appUrl} target="_blank" rel="noopener noreferrer" class="...">...`
  
  CWE-1021  
  Basis: index.astro links section has 2 external links (site.github, site.appUrl) without `target` or `rel` attributes.

─────────────────────────────────────────────────

### [P2] [安全] site/src/pages/legal.astro:25,26,45,51,53,55,56 — External links lack `target="_blank" rel="noopener noreferrer"`

  Found:    Multiple external links: site.creatorUrl, site.github, https://github.com, https://anoma.ly, https://github.com/anomalyco/opencode, https://opencode.ai/brand, https://opencode.ai/legal/terms-of-service
  Expected: Each external link should have `target="_blank" rel="noopener noreferrer"`
  
  CWE-1021  
  Basis: legal.astro has 7 external links without `target` or `rel` attributes. These are legal/trademark reference links — users would expect them to open in a new tab so the legal page remains visible.

─────────────────────────────────────────────────

### [P2] [安全] site/src/layouts/DocsLayout.astro:44 — External link in docs footer lacks `target="_blank" rel="noopener noreferrer"`

  Found:    `<a href={site.creatorUrl} class="no-underline text-fg-muted hover:text-fg">CGArtLab</a>`
  Expected: `<a href={site.creatorUrl} target="_blank" rel="noopener noreferrer" class="...">CGArtLab</a>`
  
  CWE-1021  
  Basis: DocsLayout.astro has 1 external link (creatorUrl) without `target` or `rel` attributes.

─────────────────────────────────────────────────

### [P2] [对比度] site/src/styles/global.css:14 (light) — `--color-accent` on `--color-bg` fails WCAG AA (3.19:1 < 4.5:1)

  Found:    `--color-accent: #d97706;` on `--color-bg: #ffffff;` → contrast ratio 3.19:1
  Expected: Contrast ratio ≥ 4.5:1 for normal text (WCAG AA) or ≥ 3:1 for large text (≥18px or ≥14px bold)
  
  WCAG 1.4.3 (Contrast Minimum)  
  Reference: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
  
  Affected usages (light theme only — dark theme passes at 10.69:1):
  - `text-accent` links at 14px font-medium (10.5pt normal): index.astro:75,84,94,103 — FAILS AA 4.5:1
  - `text-accent` on `bg-accent-soft` at 14px font-medium: DocsSidebar.astro:45, Header.astro:35 — contrast 2.86:1, FAILS even AA Large 3:1
  - `btn-primary` button text (text-fg-invert #ffffff on bg-accent #d97706 = 3.19:1): Hero.astro:28, NotFound.astro:12, index.astro:54 — 14px font-medium (10.5pt normal) FAILS AA 4.5:1
  - QuickStart.astro:23 step number badge (text-fg-invert on bg-accent, 14px font-bold = 10.5pt bold < 14pt threshold) — FAILS AA 4.5:1
  
  Note: The accent color #d97706 is a brand color (amber/flash). Darkening it to meet 4.5:1 would require #a16207 (contrast 4.73:1) or #b45309 (accent-strong, contrast 5.02:1). The fix requires a design decision: either darken the accent token or change the text color to fg/accent-strong for these specific usages. Not fixing without confirmation per hard constraint.

─────────────────────────────────────────────────

### [P2] [对比度] site/src/styles/global.css:79 (dark) — `--color-fg-muted` on `--color-surface-2` fails WCAG AA (4.04:1 < 4.5:1)

  Found:    `--color-fg-muted: #94a3b8;` on `--color-surface-2: #334155;` → contrast ratio 4.04:1
  Expected: Contrast ratio ≥ 4.5:1 for normal text (WCAG AA)
  
  WCAG 1.4.3 (Contrast Minimum)  
  Reference: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html
  
  Affected usages (dark theme only — light theme passes at 6.92:1):
  - CodeBlock.astro:30 — `text-[10px] font-semibold` file label on bg-surface-2 — 10px normal text FAILS AA 4.5:1
  - CodeBlock.astro:41 — `text-xs font-medium` copy button text on bg-surface/90 (≈surface-2) — 12px normal text FAILS AA 4.5:1
  
  Note: 4.04:1 is close to 4.5:1 but fails. Fix requires darkening fg-muted to #84a3b8 (4.63:1) or lightening surface-2 to #2d3d52 (4.55:1). Not fixing without confirmation per hard constraint.

─────────────────────────────────────────────────

### [P2] [键盘焦点] site/src/components/CodeBlock.astro:41 — Copy button `opacity-60` reduces `:focus-visible` outline visibility

  Found:    `class="copy-btn ... opacity-60 ... hover:opacity-100 ..."` — no `focus:opacity-100`
  Expected: `class="copy-btn ... opacity-60 ... hover:opacity-100 focus:opacity-100 ..."`
  
  WCAG 1.4.11 (Non-text Contrast)  
  Reference: https://www.w3.org/WAI/WCAG21/Understanding/non-text-contrast.html
  
  Basis: The copy button has `opacity: 0.6` which applies to the entire element including its `:focus-visible` outline (2px solid var(--color-accent)). At 60% opacity on the light theme, the effective outline color blends with the background, reducing contrast below the 3:1 threshold for non-text UI components. The button does have `hover:opacity-100` but no `focus:opacity-100`, so keyboard focus does not restore full opacity.
  
  Fix:
  ```html
  <button
    type="button"
    class="copy-btn absolute right-3 top-3 z-10 inline-flex items-center gap-1.5 rounded-md border border-border bg-surface/90 px-2 py-1 font-mono text-xs font-medium text-fg-muted opacity-60 backdrop-blur transition-all hover:opacity-100 focus:opacity-100 hover:text-fg"
    aria-label="Copy code to clipboard"
    data-copy-target
  >
  ```
  Note: This is a 1-class fix. Applying it would restore full opacity on keyboard focus. Not applied yet — recorded for batch fix.

─────────────────────────────────────────────────

### [P2] [错误容错] site/src/components/CodeBlock.astro:120 — Copy button `writeText()` promise has no `.catch()` handler

  Found:    `navigator.clipboard.writeText(text).then(() => { ... })` — no error handler
  Expected: `navigator.clipboard.writeText(text).then(() => { ... }).catch(() => { /* show error feedback */ })`
  
  Basis: The `navigator.clipboard.writeText()` call can fail in insecure contexts (HTTP, non-localhost), when clipboard permission is denied, or when the browser does not support the API. Without a `.catch()` handler, the rejected promise becomes an unhandled rejection in the browser console. The user receives no feedback that the copy failed.
  
  Fix:
  ```javascript
  navigator.clipboard.writeText(text).then(() => {
    const copyIcon = btn.querySelector('.copy-icon')
    const checkIcon = btn.querySelector('.check-icon')
    const label = btn.querySelector('.copy-label')
    copyIcon?.classList.add('hidden')
    checkIcon?.classList.remove('hidden')
    if (label) label.textContent = 'Copied'
    setTimeout(() => {
      copyIcon?.classList.remove('hidden')
      checkIcon?.classList.add('hidden')
      if (label) label.textContent = 'Copy'
    }, 1500)
  }).catch(() => {
    const label = btn.querySelector('.copy-label')
    if (label) label.textContent = 'Failed'
    setTimeout(() => { if (label) label.textContent = 'Copy' }, 1500)
  })
  ```
  Note: Simple fix — add `.catch()` to the promise chain. Not applied yet — recorded for batch fix.

─────────────────────────────────────────────────

## P3 — Low Priority

✓ **No issues found.** (Dimensions 9–12 not yet audited — see Progress. Dimensions 3–5: 0 findings. Dimension 6: 2 P2. Dimension 7: 1 P2. Dimension 8: 1 P2.)

---

## Dimension Audit Progress

| # | Dimension | Status | Findings |
|---|-----------|--------|----------|
| 1 | 断链 (broken links) | ✓ Done | 0 broken internal links; all 8 internal routes verified against page files and content collection. 16 external links verified for format. |
| 2 | 空实现 (empty href="#") | ✓ Done | 0 `href="#"` found. `#main` (BaseLayout.astro:41→43) and `/#capabilities` (site.ts→CapabilityList.astro:11) are valid in-page anchors. |
| 3 | !important | ✓ Done | 0 findings. 9 `!important` instances found: 3 in global.css:143-145 (inside `@media (prefers-reduced-motion: reduce)` — WCAG 2.3.3 best practice for accessibility) and 6 in CodeBlock.astro:86-91 (overriding Shiki's `.astro-code` third-party styles via `:global()` — documented exception). Both are legitimate, documented uses. |
| 4 | 裸色值 (bare color values) | ✓ Done | 0 findings. 29 matches for hex/rgb/rgba/hsl/hsla across all `.astro`, `.css`, `.ts`, `.mjs`, `.js` files in `site/src/` and `site/`. All matches are: (a) design token definitions in global.css `:root` (lines 3-19) and `[data-theme="dark"]` (lines 74-89) — excluded per constraint "不报令牌中的裸值定义"; (b) `rgba(var(--color-...-rgb), alpha)` pattern in Hero.astro (lines 53,54,68-70,76,86) — references design tokens with variable alpha, not bare values; (c) JS fallback constants in DigitalWater.astro (lines 158-160) — canvas rendering fallbacks, not CSS; (d) description string in content.ts:12 — text describing what Argus detects, not actual color values. |
| 5 | 标题层级 (heading hierarchy) | ✓ Done | 0 findings. 26 `<h[1-6]>` matches across 13 `.astro` files + 95 `^#{1,6}\s` matches across 8 `.md` content files. All 5 pages (index, docs/index, docs/[...slug], legal, 404) have exactly one `<h1>`. No heading level skips: hierarchy is always h1→h2→h3 (no h1→h3, no h2→h4, etc.). Code-block comments in configuration.md (lines 22,43,46,54,61,70,75,184,187) and skill.md (lines 46-47) are inside ``` fenced blocks, not actual headings. |
| 6 | 对比度 (contrast) | ✓ Done | 2 P2 findings. Light theme: --color-accent #d97706 on --color-bg #ffffff = 3.19:1 (FAILS AA 4.5:1); --color-accent on --color-accent-soft = 2.86:1 (FAILS even AA Large 3:1); btn-primary text-fg-invert on bg-accent = 3.19:1 (FAILS AA). Dark theme: --color-fg-muted #94a3b8 on --color-surface-2 #334155 = 4.04:1 (FAILS AA 4.5:1). All other pairs pass AA. Contrast ratios computed via WCAG relative luminance formula. |
| 7 | 键盘焦点 (keyboard focus) | ✓ Done | 1 P2 finding. Global `:focus-visible` style present (outline: 2px solid var(--color-accent), offset 2px, border-radius 4px). Skip link present in BaseLayout.astro (hidden at left:-9999px, visible on :focus). No `outline: none` found. No `tabindex` attributes — natural DOM focus order. All nav elements have `aria-label`. P2: CodeBlock.astro:41 copy button has `opacity-60` which reduces `:focus-visible` outline visibility below WCAG 1.4.11 3:1 threshold — needs `focus:opacity-100`. |
| 8 | 错误容错 (error handling) | ✓ Done | 1 P2 finding. 404 page present (pages/404.astro → NotFound.astro with helpful messaging + navigation). DigitalWater.astro WebGL init has try/catch with Canvas2D fallback (lines 669-681, 687-698). Shader compilation errors throw and are caught by createRenderer(). P2: CodeBlock.astro:120 `navigator.clipboard.writeText()` promise has no `.catch()` — unhandled rejection on clipboard failure. Static site — no runtime error boundary needed (build-time errors fail the build). No empty/loading states needed (static content). |
| 9 | 核心网页指标 (Core Web Vitals) | ⏳ Pending | — |
| 10 | XSS | ⏳ Pending | — |
| 11 | 密钥泄露 (secret leakage) | ⏳ Pending | — |
| 12 | 交互态 (interaction states) | ⏳ Pending | — |

---

## Six Clusters — Status

| Cluster | Status | Scope checked |
|---------|--------|---------------|
| 样式代码 | ⏳ Partial | !important: 9 instances, all legitimate (reduced-motion + Shiki override). 裸色值: 29 matches, all token definitions or token references. Remaining: inline styles, dead code, breakpoint consistency, dark-mode token consistency, long-text layout. |
| 信息排版 | ⏳ Partial | 标题层级: all 5 pages have exactly one h1, no heading skips. 对比度: 2 P2 findings — light accent on bg fails AA (3.19:1), dark fg-muted on surface-2 fails AA (4.04:1). Remaining: body font ≥16px, line-height 1.4–1.7, line length 45–90 chars, spacing rhythm. |
| 元素一致性 | ⏳ Partial | 键盘焦点: global :focus-visible style present, skip link functional, no outline suppression, natural focus order. 1 P2: CodeBlock copy button opacity-60 reduces focus indicator visibility. Remaining: seven-state coverage (hover/focus/active/disabled/loading/empty/error), target size ≥24×24px, alt text and width/height on images. |
| 交互体验 | ⏳ Partial | 错误容错: 404 page present, WebGL fallback working. 1 P2: CodeBlock copy button unhandled promise rejection. Remaining: >300ms feedback, destructive action confirmation, error text with fix instructions, Tab reachability, modal focus return, prefers-reduced-motion, zoom not disabled. |
| 功能稳定 | ⏳ Pending | — |
| 前端安全 | ⏳ Partial | External link noopener (15 links found, no `target`/`rel`). Remaining: CSP/headers (covered by site/public/_headers), XSS APIs, postMessage, secret leakage, CVE. |

---

## Visual Documentation

**Status:** ⏳ Pending  
**Required:** Screenshots at 375/768/1440 × light/dark themes  
**Pages to sample:** index (homepage), docs (list), docs/getting-started (detail), legal (form-like), 404 (error)  
**Tools needed:** Browser screenshot tool (not available in this session)  
**UNKNOWN:** Cannot capture screenshots without a browser. This is a tool limitation, not a site defect.

---

## Auto-Review Status

| Check | Status | Tool | Notes |
|-------|--------|------|-------|
| Accessibility (axe/pa11y) | ⏳ Pending | Not installed | Tool gap — would require new devDependency |
| HTML validity | ⏳ Pending | — | Astro build validates syntax; no HTML validator run |
| Style rules | ⏳ Pending | — | No style lint config |
| Broken links | ✓ Done | grep + manual | All internal links verified against file system |

---

## Commits

| SHA | Message | Scope |
|-----|---------|-------|
| b912e7a | `docs(reports): add race/TOCTOU and DoS/ReDoS scope-checked audit` | Base |
| [to follow] | `docs(reports): add web-quality-2026-09-19.md` | This report (initial) |
