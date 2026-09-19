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

## P3 — Low Priority

✓ **No issues found.** (Dimensions 6–12 not yet audited — see Progress. Dimensions 3–5: 0 findings — see Dimension table.)

---

## Dimension Audit Progress

| # | Dimension | Status | Findings |
|---|-----------|--------|----------|
| 1 | 断链 (broken links) | ✓ Done | 0 broken internal links; all 8 internal routes verified against page files and content collection. 16 external links verified for format. |
| 2 | 空实现 (empty href="#") | ✓ Done | 0 `href="#"` found. `#main` (BaseLayout.astro:41→43) and `/#capabilities` (site.ts→CapabilityList.astro:11) are valid in-page anchors. |
| 3 | !important | ✓ Done | 0 findings. 9 `!important` instances found: 3 in global.css:143-145 (inside `@media (prefers-reduced-motion: reduce)` — WCAG 2.3.3 best practice for accessibility) and 6 in CodeBlock.astro:86-91 (overriding Shiki's `.astro-code` third-party styles via `:global()` — documented exception). Both are legitimate, documented uses. |
| 4 | 裸色值 (bare color values) | ✓ Done | 0 findings. 29 matches for hex/rgb/rgba/hsl/hsla across all `.astro`, `.css`, `.ts`, `.mjs`, `.js` files in `site/src/` and `site/`. All matches are: (a) design token definitions in global.css `:root` (lines 3-19) and `[data-theme="dark"]` (lines 74-89) — excluded per constraint "不报令牌中的裸值定义"; (b) `rgba(var(--color-...-rgb), alpha)` pattern in Hero.astro (lines 53,54,68-70,76,86) — references design tokens with variable alpha, not bare values; (c) JS fallback constants in DigitalWater.astro (lines 158-160) — canvas rendering fallbacks, not CSS; (d) description string in content.ts:12 — text describing what Argus detects, not actual color values. |
| 5 | 标题层级 (heading hierarchy) | ✓ Done | 0 findings. 26 `<h[1-6]>` matches across 13 `.astro` files + 95 `^#{1,6}\s` matches across 8 `.md` content files. All 5 pages (index, docs/index, docs/[...slug], legal, 404) have exactly one `<h1>`. No heading level skips: hierarchy is always h1→h2→h3 (no h1→h3, no h2→h4, etc.). Code-block comments in configuration.md (lines 22,43,46,54,61,70,75,184,187) and skill.md (lines 46-47) are inside ``` fenced blocks, not actual headings. |
| 6 | 对比度 (contrast) | ⏳ Pending | — |
| 7 | 键盘焦点 (keyboard focus) | ⏳ Pending | — |
| 8 | 错误容错 (error handling) | ⏳ Pending | — |
| 9 | 核心网页指标 (Core Web Vitals) | ⏳ Pending | — |
| 10 | XSS | ⏳ Pending | — |
| 11 | 密钥泄露 (secret leakage) | ⏳ Pending | — |
| 12 | 交互态 (interaction states) | ⏳ Pending | — |

---

## Six Clusters — Status

| Cluster | Status | Scope checked |
|---------|--------|---------------|
| 样式代码 | ⏳ Partial | !important: 9 instances, all legitimate (reduced-motion + Shiki override). 裸色值: 29 matches, all token definitions or token references. Remaining: inline styles, dead code, breakpoint consistency, dark-mode token consistency, long-text layout. |
| 信息排版 | ⏳ Partial | 标题层级: all 5 pages have exactly one h1, no heading skips (h1→h2→h3). Remaining: body font ≥16px, line-height 1.4–1.7, line length 45–90 chars, spacing rhythm, body contrast ≥4.5:1. |
| 元素一致性 | ⏳ Pending | — |
| 交互体验 | ⏳ Pending | — |
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
