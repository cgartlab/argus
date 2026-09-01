# Argus Website Architecture — 蓝图 v1.0

> **状态**: si 规划定稿，ji 按本蓝图实现
> **目标站**: `https://argus.cgartlab.com`
> **仓库位置**: `argus/site/` 子目录
> **读者**: ji（实现）、chi（验收）、men（编排）
> **参考**: men.cgartlab.com（Astro ^7.1.3 静态站，已由 xun 逆向分析）

---

## 0. 决策总览（先看这张表）

| # | 决策点 | 结论 | 一句话理由 |
|---|--------|------|-----------|
| D1 | Astro 版本 | **^7.x** | 对齐 men（^7.1.3），纯静态 SSG 无 LTS 需求，2026-08 主线 |
| D2 | UnoCSS 集成方式 | **`@unocss/astro` integration**（integrations 数组），**不用** `@unocss/vite` 插件 | 官方文档指定集成方式，插件会走 vite.plugins 歧路 |
| D3 | 文档系统 | **Content Collections（Content Layer API）+ 纯 Markdown**，**不用 MDX，不用 men 式手写 pages** | 文档源全是 md，CC 免费给 schema 校验 + 自动路由 + 侧边栏自动化 |
| D4 | `@astrojs/sitemap` | **yes** | SEO 基线零成本 |
| D5 | `astro-icon` | **yes**（对齐 men） | 图标用 inline SVG 语义化渲染，a11y 可控 |
| D6 | `@astrojs/mdx` | **no** | 文档无需在 md 内嵌交互组件，保持 .md 简单 |
| D7 | UnoCSS presets | **presetUno + presetTypography**；**不用** presetIcons / presetWebFonts | Icons 交给 astro-icon，WebFonts 用系统字体栈，避免运行时加载 |
| D8 | prefetch | **yes**（astro.config `prefetch: true`） | 站内 docs 导航零成本提速 |
| D9 | 部署 | **GitHub Pages + actions/deploy-pages@v5 + Cloudflare DNS 前置**，**不用** @astrojs/cloudflare adapter | 对齐 men 模式，两站无 adapter 先例 |
| D10 | 404 | **`src/pages/404.astro`** | 两参考站缺失项，必须补 |
| D11 | 路由 | 无 .html 后缀、无 trailing slash（`trailingSlash: 'never'`） | 对齐 men |
| D12 | 语言 | 全站英文，`<html lang="en">` | 国际开源社区，与项目语言一致 |

---

## 1. 技术栈决策详情

### 1.1 Astro 版本：^7.x

- **结论**: `astro@^7`，Node 22（对齐 men workflow 的 node-version）
- **理由**:
  - men.cgartlab.com 用 ^7.1.3 跑通，Astro 7 是当前主线（官方文档存在 v7 upgrade guide）
  - 本项目纯静态 SSG + Content Layer API，无依赖 React/Svelte integration，风险低
  - 5.x LTS 已不是主线，新站点用 7.x 避免 1-2 年后被迫迁移
- **不锁定 exact**，package.json 用 `"astro": "^7.1.3"` 附近即可，ji 安装时取最新 7.x

### 1.2 UnoCSS 集成方式：`@unocss/astro` integration

官方文档（webfetch 已验证 unocss.dev/integrations/astro）：

```
pnpm add -D unocss @unocss/astro
```

- **必须用 integration**，放在 `astro.config.mjs` 的 `integrations: [UnoCSS()]`
- **不用 `@unocss/vite`**：虽然下钻到 Vite 插件，但 Astro 官方集成处理了 `.astro`/`.md` 文件提取 + dev HMR，插件方式需要手动配 transform 范围，是歧路
- **官方要点**:
  - 该插件**默认不注入任何 preset**（`presetUno` 等必须显式配置）
  - style reset 默认**不注入**，需装 `@unocss/reset`
  - 需要 `uno.config.ts` 文件

**uno.config.ts 骨架（ji 落地参考）**:

```ts
import { defineConfig, presetUno, presetTypography } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),          // 核心引擎，Tailwind/Wind 兼容语法
    presetTypography(),   // docs prose 排版（prose 类）
  ],
  content: {
    filesystem: ['src/**/*.{astro,md,ts,html}'],  // 扫描范围
  },
  shortcuts: {
    // 站内复用的组合类，ji 自定义
  },
})
```

**不用 presetIcons** — 图标走 `astro-icon`（D5），避免双图标体系：
- `presetIcons` 通过 CSS mask/inline background 渲染，a11y 语义弱
- `astro-icon` 渲染真实 `<svg>` 内联，可加 `alt`/`aria-hidden`，语义正确
- 对齐 men 已选 astro-icon，少一份调研/学习成本

**不用 presetWebFonts** — WebFonts 需要运行时/构建时加载自定义字体网络资源；静态站用系统字体栈（`-apple-system, 'Segoe UI', Roboto, sans-serif`）即可，零依赖、性能更好。

### 1.3 Content Collections vs 手写 pages：**用 CC**

**结论**: Content Layer API（build-time）+ 纯 Markdown，不用 MDX，不用 men 式 JSON+手写 pages。

**理由（权衡）**:
| 维度 | CC（采用） | men 式（放弃） |
|------|-----------|---------------|
| 内容源 | 天然 Markdown 匹配（AGENTS.md/SKILL.md/README.md 全是 md） | 需把 md 内容硬编码进 .astro 或 JSON，反直觉 |
| 校验 | frontmatter Zod schema 强校验（title/order 缺失即 build fail） | 无校验，缺失静默 |
| 路由 | `[...slug].astro` 单文件自动生成所有 docs 页 | 每章一个文件 + 手写 index 目录 |
| 侧边栏 | `getCollection('docs')` 按 order/sidebarGroup 自动渲染 | 手写 JSON 维护顺序 |
| 复杂度 | 一个 `content.config.ts`，官方一等公民 | 简单但全是手写，维护痛 |

**不用 MDX**：文档不需要在 markdown 内嵌 `<Component>`；纯 md + CC 足够。未来要交互再升 MDX 不晚（CC 兼容 .mdx）。

### 1.4 其他集成逐项

| 集成 | yes/no | 理由 |
|------|--------|------|
| `@astrojs/sitemap` | ✅ yes | 静态站免费 SEO，`build` 自动生成 sitemap-index.xml |
| `astro-icon` | ✅ yes | 对齐 men，inline SVG 语义化；配合 `@iconify-json/lucide` |
| `@astrojs/mdx` | ❌ no | D6：纯 md 够用，避免复杂度 |
| `@astrojs/cloudflare` adapter | ❌ no | D9：GH Pages 无 adapter，静态 output 即可 |
| `@astrojs/rss` | ❌ no | 无博客需求 |
| React/Vue/etc | ❌ no | 用户明确无 islands |

---

## 2. 目录结构（site/，文件级）

```
site/
├── package.json              # astro@^7, unocss, @unocss/astro, @unocss/reset, @astrojs/sitemap, astro-icon, @iconify-json/lucide
├── astro.config.mjs          # 见 §7：output static, site, base '/', integrations, prefetch, trailingSlash
├── uno.config.ts             # §1.2 骨架
├── tsconfig.json             # extends astro/tsconfigs/strict
├── .gitignore                # 站内兜底（规格上也依赖仓库根忽略项，§5.3）
├── public/                   # 静态直拷文件（不进 Astro 处理）
│   ├── favicon.svg
│   ├── robots.txt            # Allow all + Sitemap: https://argus.cgartlab.com/sitemap-index.xml
│   └── CNAME                 # 内容: argus.cgartlab.com
└── src/
    ├── content.config.ts     # CC 定义（docs collection schema）
    ├── content/
    │   └── docs/             # 每章一个 .md（§4 页面清单）
    │       ├── index.md                 → /docs/ (overview，order: 0)
    │       ├── getting-started.md       → /docs/getting-started
    │       ├── capabilities.md          → /docs/capabilities
    │       ├── architecture.md          → /docs/architecture
    │       ├── configuration.md         → /docs/configuration
    │       ├── commands.md              → /docs/commands
    │       └── development.md           → /docs/development
    ├── data/
    │   ├── site.ts           # 站点元信息（version/GitHub URL/links/nav）
    │   └── content.ts        # landing 数据（capabilities/quickstart/architecture 节点）
    ├── layouts/
    │   ├── BaseLayout.astro  # 全局：head/Header/Footer/背景/skip-link/lang
    │   └── DocsLayout.astro  # docs 页布局：BaseLayout + DocsSidebar + prose 容器 + prev/next
    ├── components/           # 扁平组件（对齐 men 风格，全 .astro）
    │   ├── Header.astro
    │   ├── Footer.astro
    │   ├── Hero.astro
    │   ├── CapabilityList.astro
    │   ├── ArchitectureDiagram.astro
    │   ├── QuickStart.astro
    │   ├── CodeBlock.astro
    │   ├── DocsSidebar.astro
    │   └── NotFound.astro    # 404 专用布局内容
    ├── styles/
    │   └── global.css        # 手写全局样式：reset 之外的自定义（背景、focus-visible、字体栈、prose 微调）
    └── pages/
        ├── index.astro       # landing 单页（锚点区段）
        ├── 404.astro         # NotFound + BaseLayout
        └── docs/
            ├── index.astro   # docs 目录页（getCollection 渲染章节列表）
            └── [...slug].astro  # CC 动态路由：getStaticPaths 生成每章
```

### 目录职责

| 目录 | 职责 |
|------|------|
| `public/` | 原样拷贝静态资源：favicon、robots、CNAME（GH Pages 自定义域名探测依据） |
| `src/content/` | CC 内容仓库，docs 章节 md 源（唯一内容真源） |
| `src/content.config.ts` | collection 定义 + frontmatter schema（§5.2） |
| `src/data/` | 站点元信息 + landing 结构化数据（非文档内容的展示数据） |
| `src/layouts/` | 页面骨架：BaseLayout 全局，DocsLayout docs 专用 |
| `src/components/` | 复用 UI 组件，全部无状态无 interactions |
| `src/styles/` | UnoCSS 之外的全局手写 CSS（极小） |
| `src/pages/` | 路由入口：landing / 404 / docs 动态路由 |

---

## 3. 组件清单与职责

| 组件 | 文件 | 职责 | Props |
|------|------|------|-------|
| BaseLayout | `layouts/BaseLayout.astro` | head(meta/og/title)、`<html lang="en">`、skip-link、Header、Footer、背景容器、`<slot />`；导入 global.css | `title`, `description` |
| DocsLayout | `layouts/DocsLayout.astro` | 组合 BaseLayout + DocsSidebar + `<article class="prose">` + prev/next 导航；接收当前 entry 计算 sidebar 高亮与 prev/next | `entry`, `sidebar` |
| Header | `components/Header.astro` | 站名 logo 链接 + `<nav aria-label>`（Home / Docs / GitHub），`aria-current="page"` | 无 |
| Footer | `components/Footer.astro` | 版权、版本、GitHub 链接、许可证 | `version` |
| Hero | `components/Hero.astro` | landing Hero：一句话产品定位 + 主 CTA（Install App / Read Docs）+ argus 简介 | 无 |
| CapabilityList | `components/CapabilityList.astro` | 渲染 7 大审查维度卡片网格（数据来自 `data/content.ts`） | `capabilities` |
| ArchitectureDiagram | `components/ArchitectureDiagram.astro` | 架构图：App→workflow→composite action→rules→Review result。**SVG 或纯 HTML/CSS 框线图**（ji 自选），节点文案来自 `data/content.ts` | `nodes` |
| QuickStart | `components/QuickStart.astro` | 3 步接入 GitHub App（数据来自 `data/content.ts`） | `steps` |
| CodeBlock | `components/CodeBlock.astro` | 代码块包裹：语法高亮 + 复制按钮（复制按钮为增强，无 JS 也可显示） | `code`, `lang` |
| DocsSidebar | `components/DocsSidebar.astro` | docs 章节导航：`getCollection('docs')` 按 `order` 渲染，当前页 `aria-current="page"`，分组按 `sidebarGroup` | `entries`, `currentSlug` |
| NotFound | `components/NotFound.astro` | 404 内容：提示 + 回首页/Docs 链接 | 无 |

**依赖关系**：

```
pages/index.astro ──> BaseLayout ──> Header, Footer
                    ├──> Hero, CapabilityList, ArchitectureDiagram, QuickStart, CodeBlock
pages/docs/[...slug].astro ──> DocsLayout ──> BaseLayout, DocsSidebar
pages/404.astro ──> BaseLayout ──> NotFound
```

组件总数：**8 个 components + 2 个 layouts = 10 个 .astro 复用组件**。无 JS 运行时（纯 SSG 静态 HTML）。

---

## 4. 页面与路由结构

路由约定：**无 .html 后缀、无 trailing slash**（`trailingSlash: 'never'`，对齐 men）。

| 路由 | 文件 | 内容 | 来源（argus 仓库） |
|------|------|------|-------------------|
| `/` | `pages/index.astro` | landing：Hero（产品定位）/ Capabilities（7 维度）/ Architecture / QuickStart（3 步）/ GitHub 链接区段，锚点导航 | README.md + AGENTS.md |
| `/404` | `pages/404.astro` | 404 页 | — |
| `/docs` | `pages/docs/index.astro` | docs 目录页（章节列表） | CC 查询 |
| `/docs/overview` | `content/docs/index.md` | 项目概览 | README.md Overview + AGENTS.md OVERVIEW |
| `/docs/getting-started` | `content/docs/getting-started.md` | 3 步接入 GitHub App + 本地 clone | README.md Quick Start |
| `/docs/capabilities` | `content/docs/capabilities.md` | 7 大审查维度详细 | AGENTS.md review dimensions + README Capabilities |
| `/docs/architecture` | `content/docs/architecture.md` | 架构：App→workflow→action→rules→result + 三形态交付 | README Architecture + AGENTS.md STRUCTURE |
| `/docs/configuration` | `content/docs/configuration.md` | `.argus.yml` 全字段参考（token-prefix/severity/ignore/fail-on/output） | docs/argus-config-schema.md |
| `/docs/commands` | `content/docs/commands.md` | Makefile 命令 + GitHub App 用法 | Makefile + AGENTS.md COMMANDS |
| `/docs/development` | `content/docs/development.md` | 本地开发、fixture 测试、发布流程 | CONTRIBUTING.md + CHANGELOG.md + tools/ |

docs 页面数：**1 目录页 + 7 内容页 = 8 个 docs 页面**，全站 10 个 URL。

landing 区段锚点：`#hero` `#capabilities` `#architecture` `#quickstart` `#links`（Header 导航指向各锚点）。

---

## 5. 内容数据组织

### 5.1 `src/data/site.ts`（对齐 men）

```ts
export const site = {
  name: 'Argus',
  title: 'Argus — Frontend Design Code Review Agent',
  description: 'Cross-platform AI coding agent specialized in frontend design review: hardcoded values, design tokens, a11y, dark mode, framework API misuse.',
  version: '0.4.0',            // 同步 argus 根 VERSION（当前 0.4.0）
  url: 'https://argus.cgartlab.com',
  github: 'https://github.com/cgartlab/argus',
  appUrl: 'https://github.com/apps/argus-flash',
  docsPrefix: '/docs',
  license: 'MIT',
  nav: [
    { label: 'Features', href: '/#capabilities' },
    { label: 'Docs', href: '/docs' },
    { label: 'GitHub', href: 'https://github.com/cgartlab/argus' },
  ],
}
```

### 5.2 `src/content.config.ts` — docs collection schema

```ts
import { defineCollection } from 'astro:content'
import { glob } from 'astro/loaders'
import { z } from 'astro/zod'

const docs = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/docs' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    order: z.number(),                      // 侧边栏/目录排序，0 起
    sidebarGroup: z.enum(['Start', 'System', 'Reference']), // DocsSidebar 分组
    updated: z.string().optional(),         // ISO 日期，可选
  }),
})
export const collections = { docs }
```

**实现约定**：`getCollection('docs')` 后必须显式 `.sort((a,b) => a.data.order - b.data.order)`（CC 结果顺序非确定）。

### 5.3 `src/data/content.ts` — landing 展示数据

结论：**抽到 `content.ts`（TS 模块），不用 JSON**。理由：类型自校验、可 import 类型推导、比 JSON 少一层解析、men 参考站也已用 TS 数据文件。

```ts
export const capabilities: { title: string; desc: string; icon: string }[] = [
  // 7 大维度（icon = lucide 图标名，供 astro-icon 使用）
]
export const quickstartSteps: { title: string; desc: string; code?: string }[] = []
export const architectureNodes: { id: string; label: string; desc: string }[] = []
```

### 5.4 docs frontmatter 约定（每章 md 都必须有）

```yaml
---
title: Getting Started
description: Install argus-flash in three steps.
order: 1
sidebarGroup: Start
---
```

---

## 6. 部署方案

### 6.1 模式：GitHub Pages 托管 + Cloudflare DNS 前置（对齐 men）

- **不用** `@astrojs/cloudflare` adapter：静态站 SSG 产物直接喂 GitHub Pages，CF 只在 DNS 层
- 构建产物：`site/dist/`

### 6.2 `.github/workflows/deploy-site.yml`（新文件，不动现有 ci/review/release）

```yaml
name: Deploy Site

on:
  push:
    branches: [main]
    paths:
      - 'site/**'
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: site/package-lock.json
      - name: Install & Build
        working-directory: site
        run: |
          npm ci
          npm run build
      - name: Upload Pages Artifact
        uses: actions/upload-pages-artifact@v5
        with:
          path: site/dist
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
```

要点：
- `paths: ['site/**']` 过滤：只有 site/ 变更才触发，不干扰其余 CI
- Node 22（对齐 men）
- `working-directory: site` + `npm ci`（需提交 `package-lock.json`）
- artifact path `site/dist`（Astro `outDir` 默认 `dist`，相对 site/ 即为 `site/dist`）
- sequel 用 `actions/deploy-pages@v5` + 标准 concurrency group `pages`

### 6.3 自定义域名（GH Pages 侧 + Cloudflare DNS 侧）

**GH Pages 侧（仓库内自动化）**：`site/public/CNAME` 存在且内容为 `argus.cgartlab.com`。
- Astro 构建时 public/ 原样拷入 dist/，GH Pages 识别根 CNAME 即配置 custom domain
- 旁注：GH Pages 部署工作流要求 Settings → Pages → Source 选 "GitHub Actions"（与 artifact 方式配合）；Custom domain 首次也可在 Settings 手填 `argus.cgartlab.com`

**Cloudflare DNS 侧（用户自己操作，规划只说明）**：
- 在 CF 对 `argus.cgartlab.com` 添加记录，指向 GH Pages 域名（`cgartlab.github.io`）：
  - 推荐 **CNAME** `argus.cgartlab.com` → `cgartlab.github.io`（代理灰度/橙云可选）
  - 或 A 记录指向 GH Pages 当前 IP（`185.199.108.153 / 185.199.109.153 / 185.199.110.153 / 185.199.111.153`）
- `Public/robots.txt` 已声明 sitemap，保证 SEO 链路完整

---

## 7. astro.config.mjs 规格（ji 落地核对）

```js
import { defineConfig } from 'astro/config'
import UnoCSS from 'unocss/astro'
import sitemap from '@astrojs/sitemap'
import icon from 'astro-icon'

export default defineConfig({
  site: 'https://argus.cgartlab.com',
  base: '/',
  output: 'static',             // 默认亦为 static，显式声明
  trailingSlash: 'never',       // D11
  prefetch: true,               // D8
  integrations: [
    UnoCSS(),                   // D2：@unocss/astro integration
    sitemap(),                  // D4
    icon(),                     // D5：astro-icon（默认 lucide 可用）
  ],
})
```

package.json scripts：

```json
{
  "scripts": {
    "dev": "astro dev",
    "build": "astro build",
    "preview": "astro preview",
    "astro": "astro"
  }
}
```

---

## 8. a11y / SEO / 性能基线

### a11y（WCAG AA，硬性）

| 项 | 实现点 |
|----|--------|
| skip-link | BaseLayout 首个元素 `<a href="#main">Skip to content</a>` + focusable 样式 |
| `aria-current="page"` | Header 当前导航项、DocsSidebar 当前章节 |
| 语义化 nav | `<nav aria-label="Main">` / `<nav aria-label="Docs">` |
| focus visible | 全局 `:focus-visible` 显式 outline（global.css） |
| 对比度 AA | 正文/链接/边框色满足 4.5:1 / 3:1（UnoCSS 色板灰阶可查） |
| `prefers-reduced-motion` | 动画/过渡在 reduced-motion 下禁用或最小化 |
| 图标语义 | 装饰性 icon `aria-hidden="true"`，功能性图标带 `alt`/`title` |

### SEO

- `@astrojs/sitemap`：自动生成 `sitemap-index.xml`（依赖 `site` 配置正确）
- `public/robots.txt`：`User-agent: *` + `Allow: /` + `Sitemap: https://argus.cgartlab.com/sitemap-index.xml`
- BaseLayout head：`<title>`、`<meta name="description">`、`og:title / og:description / og:type=website / og:url`、`<link rel="canonical">`
- 每 docs 页 title/description 来自 CC frontmatter 注入
- `<html lang="en">`（D12）

### 性能

- `prefetch: true`（astr 内置，hover/intent 预取站内链接）
- 系统字体栈 + 无 web font 网络请求
- 全静态 HTML，无 JS 运行时（除可选 CodeBlock 复制按钮）

---

## 5.3 CI 影响评估（读取现有文件后结论）⚠️ 关键

已读：`ci.yml` / `review.yml` / `release.yml` / `.gitignore` / `Makefile` / `tools/validate_versioning.py`。

### 5.3.1 `ci.yml` — 不受干扰 ✅

- 触发：`push: main` + `pull_request: main`，**无 paths 过滤** → site/ 变更也会跑三个 job
- job 内容全部只查仓库根文件（YAML targets 硬编码、required files 清单、tools/*.py、tests/fixtures/*）**均不含 site/**，全部通过，不破坏
- ⚠️ 注意：ci.yml 的 YAML lint targets 是硬编码列表，**不会自动覆盖新加的 deploy-site.yml**。deploy-site.yml 语法由它自己运行时验证，如果 YAML 写错会导致 workflow 静默不触发。**对策：deploy-site.yml 必须用简单标准 YAML，ji 落地后本地 `python -c "import yaml; yaml.safe_load(...)"` 验证**。可选优化（不做，遵守"不动现有 ci.yml"约束）：后续可把 deploy-site.yml 加进 ci.yml targets

### 5.3.2 `review.yml` — 无冲突，反而受益 ✅

- 触发 PR 时 argus-flash 会审查整个 PR，包括 site/ 代码 → **dogfooding**：argus 自己的网站被 argus 审查，符合"自身代码符合自身规范"
- 对我们的站点代码是好约束：ji 写 site/ 前端代码时应保持 P0/P1 干净

### 5.3.3 `release.yml` + `Makefile` — **必须修改 Makefile** ⚠️

- release.yml 触发 tag `v*` → `make package-skill && make package`
- `Makefile package` 实测逻辑：
  - tar：`tar --exclude='.git' --exclude='dist' -czf dist/argus-v$(VERSION).tar.gz .` → **打包整个仓库**，site/node_modules、site/dist 会被打进去！
  - zip：`zip ... -x '.git/*' -x 'dist/*'` → **同样包含 site/node_modules**
- validate_versioning.py 只看 VERSION/CHANGELOG，无影响

**必须改动（Makefile.package 规则新增 exclude）**：

```make
package: package-skill
	@mkdir -p dist
	@tar --exclude='.git' --exclude='dist' \
	     --exclude='site/node_modules' --exclude='site/dist' --exclude='site/.astro' \
	     -czf dist/argus-v$(VERSION).tar.gz .
	@zip -q dist/argus-v$(VERSION).zip . -r \
	     -x '.git/*' -x 'dist/*' \
	     -x 'site/node_modules/*' -x 'site/dist/*' -x 'site/.astro/*'
```

### 5.3.4 根 `.gitignore` — 必须补充 ⚠️

现有根 `.gitignore`：`dist/`（全局匹配，已覆盖 site/dist）+ `__pycache__/` 等，**缺 node_modules 忽略**。

**必须新增（argus 根 .gitignore）**：

```gitignore
# 网站构建产物（site/）
site/node_modules/
site/dist/
site/.astro/
```

理由：若无此忽略，`git status` 会追踪 site/node_modules（海量文件）+ site/.astro 缓存，污染 PR diff；`site/dist/` 虽被全局 `dist/` 覆盖，仍显式列出防误读。

### 5.3.5 绝对不动清单 ✋

- `ci.yml`、`review.yml`、`release.yml`：原样保留
- `tools/`、`VERSION`、`CHANGELOG.md`：不动
- 根 Makefile 除 `package` 规则加 exclude 外不动

---

## 9. 实施 TODO（Wave 分解，供 men 分发 ji）

### Wave 1 — 脚手架（可并行于 Wave 2 的数据准备）

- [ ] T1: 创建 site/package.json + tsconfig.json + astro.config.mjs + uno.config.ts（Category: code | Skills: npm, astro | QA: V1-V4）
- [ ] T2: 安装依赖 `npm install` 并生成 package-lock.json（Category: code | Skills: npm | QA: V13）
- [ ] T3: 根 .gitignore 追加 3 行 + Makefile package 规则加 exclude（Category: code | Skills: git, make | QA: V11-V12）

### Wave 2 — 骨架与数据（依赖 Wave 1）

- [ ] T4: src/data/site.ts + src/data/content.ts 数据落地（Category: write | Skills: typescript | QA: V21）
- [ ] T5: BaseLayout + Header + Footer + global.css（Category: code | Skills: astro, unocss, a11y | QA: V6, V17）
- [ ] T6: content.config.ts + 7 个 docs md（先写 frontmatter + 章节标题占位，正文 T8 补全）（Category: write | Skills: markdown | QA: V5, V9）

### Wave 3 — 页面（依赖 Wave 2）

- [ ] T7: landing：Hero + CapabilityList + ArchitectureDiagram + QuickStart + CodeBlock + index.astro（Category: code | Skills: astro, unocss, a11y | QA: V7, V16, V18）
- [ ] T8: docs 内容正文补全（源码转写：AGENTS/SKILL/README/config-schema/Makefile）（Category: write | Skills: markdown, editorial | QA: V9-V10）
- [ ] T9: DocsLayout + DocsSidebar + docs/[...slug].astro + docs/index.astro（Category: code | Skills: astro, cc | QA: V5, V15）

### Wave 4 — 收尾（依赖 Wave 3）

- [ ] T10: 404.astro + NotFound + public/{favicon,robots,CNAME}（Category: code | Skills: astro | QA: V8, V20）
- [ ] T11: deploy-site.yml（Category: code | Skills: github-actions, yaml | QA: V19）
- [ ] T12: 构建验证：`cd site && npm install && npm run build` 退出码 0；根目录 `make validate` 通过（Category: review | Skills: npm, make | QA: V13-V15）

---

## 10. 验收标准表（chi judge 消费，全部机械可验证）

| ID | 描述 | 验证方式 | PASS 条件 |
|----|------|----------|-----------|
| V1 | site/package.json 存在且含 astro | `Test-Path site/package.json` + grep | 文件存在；dependencies/devDependencies 含 `astro` |
| V2 | site 依赖含 UnoCSS 全家 | grep site/package.json | 含 `unocss` 或 `@unocss/astro`，且含 `@unocss/reset` |
| V3 | astro.config.mjs 配置正确 | grep site/astro.config.mjs | 含 `output: 'static'`、`site: 'https://argus.cgartlab.com'`、`UnoCSS(`、`trailingSlash: 'never'`、`prefetch: true` |
| V4 | uno.config.ts 存在且含 presetUno | Test-Path + grep | 存在；含 `presetUno` |
| V5 | content.config.ts 定义 docs collection | Test-Path + grep | 存在；含 `defineCollection`、`glob`、`docs` |
| V6 | BaseLayout.astro 存在 | Test-Path | `site/src/layouts/BaseLayout.astro` 存在 |
| V7 | index.astro（landing）存在 | Test-Path | `site/src/pages/index.astro` 存在 |
| V8 | 404.astro 存在 | Test-Path | `site/src/pages/404.astro` 存在 |
| V9 | docs 内容页 ≥ 6 | `Get-ChildItem site/src/content/docs/*.md | Measure` | `.md` 文件 ≥ 6（index + ≥5 章节），各含 frontmatter 四字段 |
| V10 | docs 页面路由文件存在 | Test-Path | `site/src/pages/docs/[...slug].astro` 存在 |
| V11 | 根 .gitignore 补忽略项 | grep argus/.gitignore | 含 `site/node_modules/`、`site/dist/`、`site/.astro/` 三行 |
| V12 | Makefile package 排除 site | grep argus/Makefile | `package:` 规则含 `site/node_modules` 和 `site/dist` 的 exclude |
| V13 | site 构建成功 | `cd site && npm install && npm run build; $LASTEXITCODE` | 退出码 0 |
| V14 | dist/index.html 产出 | Test-Path | `site/dist/index.html` 存在 |
| V15 | docs 静态页产出 | Test-Path（取 1 章验证） | 如 `site/dist/docs/getting-started/index.html` 存在 |
| V16 | landing 板块关键词 | grep site/dist/index.html | 含 Hero 定位词（如 "frontend design"）、capabilities、architecture、quickstart、github 链接区（任一代表性词各 ≥1） |
| V17 | 语言英文 | grep site/dist/index.html | 含 `<html lang="en"` |
| V18 | 现有 CI 校验不破坏 | 根目录 `make validate` | 退出码 0 |
| V19 | deploy-site.yml 语法合法 | `python -c "import yaml; yaml.safe_load(open('.github/workflows/deploy-site.yml'))"` | 退出码 0 |
| V20 | CNAME 正确 | Get-Content site/public/CNAME | 内容恰为 `argus.cgartlab.com` |
| V21 | site.ts 元信息存在 | grep site/src/data/site.ts | 含 `version`、`github: 'https://github.com/cgartlab/argus'` |

**验收总数：21 项**（V1-V21）。

---

## 11. 风险与未决问题

### 低风险（方案内已消解）

1. UnoCSS 扫描范围：content.filesystem 已显式覆盖 `.astro/.md/.ts`，防漏扫
2. Astro 7 + CC 版本细节：`getCollection` 排序需显式 sort（集合顺序非确定）——已写入实现约定
3. GH Pages custom domain 首次配置：CNAME 文件 + Settings 手填二选一，文档已覆盖

### 未决问题（需 men/用户一次性确认，不阻塞 ji 开工）

| # | 问题 | 建议默认 |
|---|------|----------|
| Q1 | Cloudflare DNS 记录类型（CNAME 橙云 / A 记录直连） | CNAME → `cgartlab.github.io` |
| Q2 | 是否接受"Makefile.package 加 exclude 是对现有文件的唯一改动" | 是（不这么改 release 会打包 site 依赖进 release artifact） |
| Q3 | doc 内容转写版权口径：docs/configuration.md 基本照抄 argus-config-schema.md（同一仓库 MIT，无版权问题，仅确认） | 全量转写，保留示例 YAML |