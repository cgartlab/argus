# Argus 商用产品战略计划（2026–2027）

> 文档版本：d1（2026-09） · 依据：v0.5.6 代码库实际状态 + 市场调研
> 本文档是产品方向的决策底稿，不是承诺清单。所有时间线均为方向性估算，随验证结果滚动调整。
>
> **版本号治理（所有者规则）**：Argus 的产品版本号**始终保持在 0.x.x**。任何升至 1.0 的提议都必须经所有者（你）明确批准；本文档中的"M1/M2"是里程碑代号，不是版本号承诺。日常演进走 0.x 的 patch/minor（如 0.5.6 → 0.6.0），遵循 `make bump-*` 流程。

---

## 1. 执行摘要

**Argus 的定位**：前端设计代码审查的**垂直专家 agent** —— 在"设计质量"这一个横切面上做到比任何通用审查工具都深，以"精确率/召回率可量化"建立信任，以 GitHub App + 复合 action 实现零摩擦分发，以"免费模型成本结构"实现可持续的 open-core 变现。

**战略判断（一句话）**：横向 AI 代码审查已是红海（Copilot Review、CodeRabbit、Greptile、Bito、CodeScene 等正面厮杀）；而"设计 token 违规 / a11y / dark mode / hardcoded values"这一垂直细分尚无垄断者，同时被两条宏观趋势推高：① 设计系统（Design Tokens, W3C DTCG）在企业前端团队中的普及率持续上升；② 无障碍合规从"可选项"变为"合规项"（EU 无障碍法案 2025 年 6 月生效、WCAG 2.2 AA 成为采购门槛）。Argus 的机会是**先占住"前端设计质量"这个心智词**，再横向扩展。

**当前资产盘点（v0.5.6）**：
- 成熟的发布管线：版本门禁（check_release / release-check / validate_versioning）、`make release` 一键发版、CI + fixture 回归全绿
- 独特的评估资产：`tests/fixtures/` 的 false-positives / should-flag **镜像对**（这是行业少见的"精确率基准"）
- 成本优势结构：`config/free-models.yml` 免费模型队列 + `model-scores.yml` 评分 + 每周 API 驱动刷新 → 单次审查边际成本≈0
- 零摩擦分发：复合 action `argus-review@main` 动态注入规则（规则更新即对所有消费者生效，无版本锁）+ argus-flash GitHub App
- 多渠道技能分发：SkillHub / ClawHub / skills.sh 三注册中心（PR #132）
- 生态协同：men 团队可选择性调用（增量、不 gate 核心）
- 营销站：site/（Astro + DigitalWater 视觉），部署至 GitHub Pages

**三大支柱**：**信任**（质量可量化）→ **分发**（接入成本趋近于零）→ **变现**（open-core 分层，免费模型压低边际成本）。

---

## 2. 愿景与使命

- **愿景**：让每一行前端代码都符合设计系统与无障碍规范 —— 成为"前端设计质量"的默认检查层，像 ESLint 之于代码风格、SonarQube 之于静态分析一样成为基础设施。
- **使命**：把资深设计审查专家的判断力，变成任何团队都可负担、可量化、可自动化的 PR 门禁。

---

## 3. 市场分析

### 3.1 宏观趋势（利好 Argus 的四条线）

| 趋势 | 影响 | 证据/参考 |
|---|---|---|
| AI 代码审查进入主流程 | 教育了市场：团队已接受"机器审 PR"，Argus 只需证明"设计这一维我更懂" | GitHub Copilot Review、CodeRabbit 等横向玩家 |
| 设计系统成熟度上升 | 更多团队有 token 体系，需要"token 违规"这种高级检查，而非基础 lint | W3C DTCG Design Tokens 规范、antd5/material3/polaris token 体系 |
| 无障碍合规法制化 | a11y 从 best-effort 变 mandatory；自动化检测是合规报告的必要组成 | EU 无障碍法案（2025.6 生效）、WCAG 2.2 AA 成为政府采购门槛；无障碍软件市场 CAGR 持续增长 |
| 开源 agent 生态爆发 | 技能分发生态（SkillHub/ClawHub/skills.sh）刚起步，先发者可占据生态位 | OpenCode / Claude Code / Codex 多框架共存 |

### 3.2 市场规模（量级估算，方向性）

- TAM：全球软件开发者 ~3000 万，其中前端/全栈开发者约 1/3；AI 代码审查工具付费渗透率参照横向玩家约 5–15%。
- SAM：专注"设计质量 + a11y 合规"的团队级场景，全球前端团队估算数万级；企业 a11y 合规预算属于独立采购项。
- SOM（12–18 个月现实目标）：GitHub App 安装数百个 → 活跃仓库数十个 → 付费团队个位数到两位数。
- 结论：**这不是一个靠"大渗透"赢的生意，而是靠"高转化 + 高客单 + 合规刚需"赢的垂直生意**。定价锚定"省下的一次设计师返工"与"合规审计成本"，而非"一个 dev tool 的订阅费"。

### 3.3 竞争格局

| 类别 | 代表 | 与 Argus 的关系 |
|---|---|---|
| 横向 AI 代码审查 | Copilot Review、CodeRabbit、Greptile、Bito、CodeScene | **友军兼对手**：教育市场，但检查维度通用（bug/安全/逻辑），设计质量只是附带项；Argus 以设计纵深差异化 |
| 设计交付/设计 QA | Zeplin、UXPin、Figma 插件生态、Buoy 等 | 偏设计稿侧，不做代码级 token/a11y 审查；可合作（从 Figma 设计稿导出 token 基线喂给 Argus） |
| a11y 自动化检测 | axe / Deque、IBM Equal Access、Storybook a11y addon、Lighthouse | 偏运行时/DOM 检测，Argus 偏**源码 PR 门禁**；可集成互补（Argus 在 PR 期拦截，运行时工具在 CI/E2E 期兜底） |
| 通用 lint 体系 | ESLint（含 jsx-a11y）、Stylelint | 规则确定性但覆盖面窄（无法理解"这个 hex 是否与 token 语义等价"）；Argus 是 LLM 判断的**语义级**审查，可与 lint 共存 |
| 大模型平台自带审查 | Codex / Claude 的通用 review | 通用性强、无产品化包装（无 config、无门禁、无量化）；Argus 提供**开箱即用的垂直规则 + 门禁 + 报告** |

### 3.4 差异化定位（一句话）

> **"通用审查工具告诉你代码有没有 bug；Argus 告诉你它有没有 '长对' —— 用没用心维护设计系统。"**

三个不可复制的护城河方向：
1. **规则资产**：AGENTS.md + SKILL.md 的审查维度（token 映射 antd5/material3/polaris/custom、dark mode、a11y AA、hardcoded values）+ fixture 镜像对，是多年打磨的领域知识。
2. **质量基准**：false-positives/should-flag 精确率基准 + 每版本回归门禁，直接对抗"AI 审查 = 噪音"的信任危机。
3. **成本结构**：免费模型队列路由（动态评分 + 每周刷新）→ 可承受"免费层永远免费"，把付费点放在团队/合规能力而非单次调用。

---

## 4. 目标用户与典型场景

| 画像 | 痛点 | Argus 价值主张 | 付费意愿 |
|---|---|---|---|
| 独立开发者 / 开源维护者 | 想守设计规范但没精力逐行 review | 免费安装、PR 自动审查、copy-ready 修复 | 低（贡献口碑与案例） |
| 前端团队（10–100 人） | 设计 token 被绕过、a11y 返工、新人不熟规范 | PR 门禁 + 团队 config + 历史趋势报告，把规范"钉"进流程 | 中高（Pro） |
| Design Ops / Platform 团队 | 跨多产品线维护 token 体系一致性 | 多仓库统一规则、token 映射扩展、合规报告导出 | 高（Pro/Enterprise） |
| 受合规约束的企业 | EU 无障碍法案、WCAG AA 采购要求 | 合规级 a11y 报告 + 审计留痕 + SSO/私有化 | 最高（Enterprise） |
| 代理商/外包团队 | 交付质量背书、验收成本 | 交付前自动审查报告作为质量证明 | 中（按项目） |

**杀手场景（Killer Use Case）**：设计师在 Figma 定了 token → 前端在 PR 里写了 `#3b82f6` → Argus 在 CI 里拦截并给出 `Expected: var(--ds-color-blue-500)`。这个"从设计到代码的最后一公里"目前无人系统化解决。

---

## 5. 产品路线图

### 5.1 已完成（0.x 阶段）回顾

- ✅ 审查规则引擎：token / hardcoded / a11y / dark mode / CSS / HTML / 框架 API 七维
- ✅ 质量基座：fixture 回归 + 镜像对精确率基准
- ✅ 分发基座：argus-flash App + 复合 action 动态注入 + `.argus.yml` 消费者配置
- ✅ 成本基座：免费模型队列 + 模型评分 + 每周刷新 + LLM/静态双模式
- ✅ 工程基座：发布门禁、版本一致性、CI、多注册中心发布、营销站

### 5.2 里程碑 M1（产品成熟度门槛）

M1 不是"大版本号"，而是**信任与商业闭环的证明**（达成后是否升 1.0 需你单独批准）：
- [ ] **公开质量指标**：发布 precision/recall 仪表盘（基于 fixtures + 公开基准集）
- [ ] **报告能力**：PR 评论之外提供可分享的审查报告链接（团队/合规可引用）
- [ ] **配置体验**：`.argus.yml` 校验报错友好化 + 文档完善（已有 schema 文档，需可视化生成器）
- [ ] **首个付费档上线**：GitHub Marketplace 上架 Pro（见 §6）
- [ ] **GitLab/Bitbucket 至少一个第二平台验证**（证明"复合 action 模式可复制"，打开非 GitHub 市场）

### 5.3 12–18 个月主题（P1 优先 / P2 增强 / P3 探索）

**P1 — 信任与质量引擎（立身之本）**
- 建立**黄金评测集**：从真实 PR 中收集标注样本（found/expected 对），自动扩展 fixtures；每版本跑 precision/recall，设**回归门禁**（如 precision 不低于上版、recall 关键维度不降）
- 严重度校准：依据真实反馈分布校准 P0–P3 阈值；建立"误报申诉"回路（用户标记 → 进 FP 基准）
- 规则可追溯：每条 issue 带规则 ID + 参考文档链接（已有 Reference 字段，需结构化输出）

**P2 — 集成与团队矩阵**
- 平台：GitLab / Bitbucket / Azure DevOps 的自托管版 review 模板
- 形态：CLI（`argus review .` 本地扫描）+ IDE 插件（VS Code，增量诊断）
- 团队：多仓库规则中心、基线管理（已有 ignore paths，需"批准基线"工作流）、PR 摘要报告、历史趋势仪表盘
- 配置：`.argus.yml` 可视化编辑器 / JSON schema 校验友好化（已有 load_config 校验器，包装成 UX）

**P3 — 合规、平台化与生态**
- a11y 合规报告（WCAG 2.2 AA 逐条映射 + 证据截图位），对接合规审计
- 自定义规则 DSL / 插件：团队可写自己的 token 映射与规则（对标 ESLint 插件生态）
- 公开 API / webhook：审查结果可被下游流水线消费；与运行时 a11y 工具（axe）结果合并为全链路报告
- 模型战略升级：多模型路由（简单文件静态启发式、复杂语义走强模型）、私有化/自托管推理选项（企业数据不出域）、按严重度分级用模型
- men 生态深化：作为 men 团队的标准"前端设计审查"技能被编排调用，形成生态协同而非依赖

---

## 6. 商业模型与定价

### 6.1 模式：Open-core（免费审查引擎 + 付费团队/合规层）

| 档位 | 定价（方向性） | 内容 | 目标用户 |
|---|---|---|---|
| **Community（免费）** | $0 | GitHub App 基础审查（公开/小型私有仓库）、单一仓库 config、静态+免费模型模式 | 个人/开源 |
| **Pro** | $20–29/座位/月 或 $99/仓库/月 | 私有仓库规模审查、团队多仓库、审查报告链接、历史趋势、模型选择（含更强模型配额） | 前端团队 |
| **Enterprise** | 定制（$1k+/月起步） | SSO、自托管/私有化、合规报告（WCAG 映射 + 审计留痕）、SLA、专属 token 映射支持 | 受合规约束企业 |

对标参考：GitHub Marketplace 支持免费 + 多档付费（参考 GitHub Marketplace 定价文档）；横向竞品 CodeRabbit 等为按仓库/按座位订阅。Argus 的差异点是**免费层可持续**（免费模型成本≈0），付费点天然落在"团队协作与合规证据"。

### 6.2 成本结构与毛利

- 边际成本：单次审查的模型推理。当前免费队列 → ≈0；Pro 引入更强模型 → 用配额/计费对冲。
- 关键控制点：`model-scores.yml` 评分 + `free-models.yml` 路由 + 每周刷新，保证"免费层永远用得起、质量永远够用"。
- 收入杠杆：转化漏斗 Community → Pro（报告功能是钩子）；Enterprise 客单高但周期长，靠合规刚需驱动。

### 6.3 变现节奏

1. M1 阶段：先把**报告能力**做成 Pro 钩子（免费版无分享报告、无历史趋势）
2. M1 达成时：GitHub Marketplace 上架 Pro（最低可行付费）
3. M2 阶段：Enterprise（合规 + 私有化）作为毛利主力

---

## 7. 分发与增长（GTM）

### 7.1 分发渠道（按杠杆排序）

1. **复合 action 病毒式分发**（最高杠杆）：`cgartlab/argus/.github/actions/argus-review@main` 让任何仓库一行接入且**规则更新即时生效**——这是"安装即传播"的设计；需持续沉淀 consumer 案例。
2. **GitHub App + Marketplace 上架**：argus-flash 已可安装；上架 Marketplace 获得搜索流量与"安装量"社会证明。
3. **技能生态分发**：SkillHub / ClawHub / skills.sh 三注册中心（PR #132）→ OpenCode/Claude/Codex 生态用户可 `skills add` 即用；在生态早期占位（slug 已锁定 `argus-design-review` / `cgartlab-argus-design-review`）。
4. **men 团队协同**：作为 men 的可选"设计审查技能"被编排调用，借团队生态触达更多项目。
5. **内容与 SEO**：营销站（site/）承载文档 + 案例 + 对比页；产出"设计 token 违规 Top 10"、"dark mode 审查清单"等长尾 SEO 内容；GitHub README + Badge 是初始转化页。
6. **社区与案例**：开源榜单、DevRel 内容、与设计系统团队（antd/material/polaris 生态）合作背书。

### 7.2 增长漏斗与转化钩子

```
安装（Marketplace/action）→ 首次 PR 审查（激活：≤5 分钟）→ 发现真问题（Aha：设计师认可）→ 团队铺开（config 多仓库）→ 升级 Pro（报告/趋势钩子）
```

- 激活指标：安装后 7 天内完成首次成功审查的占比
- Aha 指标：首次审查产生 ≥1 个被接受的 P1+ 修复
- 转化钩子：免费版在"第 N 个仓库"或"报告分享"处提示升级，不打断核心审查

---

## 8. 工程与质量战略

### 8.1 评估体系（最优先投入）

- **三层测试**：静态启发式 fixture（无 API key，CI 快）+ LLM 模式 fixtures（真模型，发布前跑）+ 黄金评测集（真实 PR 标注，每版本门禁）
- **质量门禁**：`make test`（validate + test-fixtures）已存在；扩展为 **precision/recall 回归门禁**：新规则/模型变更必须不降基准
- **误报闭环**：用户"这不是问题"反馈 → 自动进入 FP 基准候选 → 人工确认后固化（防回归）

### 8.2 可靠性

- 发布门禁已成熟（check_release / release-check / validate_versioning / CI 全绿）
- 需补：**降级路径**（主模型不可用时 fallback 队列——已有；模型 API 全挂时优雅降级到静态启发式）、审查超时/速率限制、评论去重与幂等
- 版本策略：AGENTS.md/SKILL.md 规则变更走 minor/patch 语义化（消费者用 `@main` 即时生效 + `@vX.Y.Z` 钉版本两种模式，文档已声明）

### 8.3 成本控制

- 免费队列路由 + 评分（已实现）→ 增加**按复杂度路由**（小 diff 静态/轻模型、大 diff 强模型）
- 缓存与去重：同文件未变不重复审查；PR 增量审查（只审 diff）已是天然降本
- 配额：免费层限速，Pro 给配额，Enterprise 按量计费

### 8.4 安全与隐私（Enterprise 的入场券）

- 数据原则：**代码不进训练集、不持久化**；审查即时执行，结果仅回写 PR
- 私有化选项：自托管 runner / 自托管模型端点（企业数据不出域）
- 供应链：dependabot + CodeQL 已启用；App token 最小权限（已做：权限加固、token 不入 git config）

---

## 9. 指标与北极星

- **北极星（North Star）**：每周被接受的设计审查问题数（= 每周被采纳的 P1+ 修复数）——衡量"真实价值交付"而非虚荣安装量
- **增长**：安装数、激活率（7 天首审）、仓库数/安装、PR 审查数
- **质量**：precision（FP 率）、关键维度 recall、误报申诉率、严重度校准偏差
- **商业**：Community→Pro 转化率、付费 MRR、企业 Pipeline、续费率
- **工程**：发布频率、CI 绿率、fixture 覆盖率、模型切换成功率

---

## 10. 风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| 免费模型质量波动 / 队列不稳定 | 高 | model-scores 评分 + 每周刷新（已实现）；多模型投票/路由；必要时 Pro 档引入付费强模型隔离 |
| 横向玩家下沉做设计维度 | 中 | 垂直深度（token 语义、镜像对基准）+ 先发心智（"前端设计质量"词）+ 社区案例护城河 |
| 误报率高 → 信任崩塌 | 高 | precision 门禁 + 误报申诉闭环 + 语境豁免（boilerplate/第三方代码不误报，已是规则） |
| LLM 成本失控 | 中 | 免费队列 + 复杂度路由 + 配额；成本是设计出来的不是事后补的 |
| GitHub Marketplace 政策/平台依赖 | 中 | 多平台（GitLab 等）+ 本地 CLI/IDE + 自托管，降低单平台锁定 |
| 开源项目商业化的社区反弹 | 低 | open-core 边界清晰：审查引擎永远免费开源，付费只买团队/合规层 |

---

## 11. 90 天行动计划 + 12 个月里程碑

### 90 天（M1 前半段，版本保持 0.x）

| 周 | 动作 | 产出 |
|---|---|---|
| 1–2 | 建立黄金评测集 V1（从 fixtures + 真实 PR 标注 50–100 例） | eval/ 数据集 + 评分脚本 |
| 3–4 | precision/recall 回归门禁接入 CI | 每版本质量报告（可发布） |
| 5–6 | 审查报告链接（PR 评论 → 可分享报告页） | Pro 钩子 V1 |
| 7–8 | `.argus.yml` 可视化生成器 / 校验错误友好化 | 配置体验闭环 |
| 9–10 | GitLab 模板验证（复合 action 模式复制到第二平台） | 第二平台 beta |
| 11–12 | GitHub Marketplace 上架 Pro（最低可行付费） | 首个付费档 + 计费闭环 |

### 12 个月（M1 后半段 → M2）

- M1 发布（质量指标公开 + 付费档 + 第二平台）
- 团队层：多仓库规则中心、历史趋势仪表盘、基线批准工作流
- 合规层：WCAG 2.2 AA 逐条报告 V1、审计留痕
- 集成层：VS Code 插件、CLI 本地扫描、axe 结果合并
- 模型层：复杂度路由、自托管选项（Enterprise POC）
- 生态：3 个 consumer 案例 + 1 个设计系统合作背书 + skills.sh 索引完成

---

## 12. 组织与执行（务实版）

- 现状：纯文档/配置仓库 + 一人/小团队维护，工程杠杆极高（无构建、无运维面）。
- 建议：保持"规则即代码、测试即门禁"的极简架构；商业化部分（报告服务、计费、仪表盘）单独作为一个轻量服务，与审查引擎解耦。
- 外包/自动化优先：合规报告、Marketplace 上架、SEO 内容可用 AI 流水线加速；核心的规则资产与评测集必须人审。
- 里程碑评审节奏：每 90 天按 §9 指标复盘一次，未达标的主题降级/砍掉（避免在低杠杆方向投入）。

---

## 13. 附录：当前资产 → 战略映射

| 现有资产 | 战略作用 | 下一步 |
|---|---|---|
| fixture 镜像对（false-positives/should-flag） | 精确率基准，信任立身之本 | 扩展为黄金评测集 + 公开指标 |
| free-models.yml / model-scores.yml / 每周刷新 | 成本结构护城河 | 复杂度路由、自托管 |
| 复合 action 动态注入 | 病毒式分发 | consumer 案例沉淀 |
| argus-flash App + review.yml | 产品形态（PR 门禁） | Marketplace 上架、多平台 |
| 多注册中心发布（SkillHub/ClawHub/skills.sh） | 生态分发占位 | 生态内容 + 索引完成 |
| `.argus.yml` schema + load_config | 配置入口 | 可视化、错误友好化 |
| token 映射（antd5/material3/polaris/custom） | 垂直深度 | 更多设计系统 + 自定义 DSL |
| 发布管线（check_release 等） | 工程可信度 | precision 门禁并入 CI |
| men 集成 | 生态协同（可选） | 保持增量、不 gate 核心 |
| 营销站 site/ | GTM 落地页 | SEO + 案例 + 对比页 |

---

## 14. 路线图执行状态（2026-09 回填）

下表按 §5 路线图章节回填实际交付（PR 编号为 cgartlab/argus 合并候选）。

| 路线图项 | 优先级 | 状态 | 交付 |
|---|---|---|---|
| 黄金评测集 + precision/recall 门禁 | P1 | ✅ 完成 | `tools/eval_quality.py` + `config/quality-baseline.json` + CI gate（PR #133） |
| 严重度校准（规则 × 严重度矩阵） | P1 | ✅ 完成 | `config/severity-matrix.yml` + `tools/validate_severity_matrix.py`（PR #135） |
| 误报申诉闭环 | P1 | ✅ 完成 | `tools/add_fp_appeal.py` + 修复 drop-shadow 真实误报（PR #136） |
| `.argus.yml` JSON Schema + 配置体验 | P2 | ✅ 完成 | `config/argus-config.schema.json` + 零依赖校验器 + 解析器加固（PR #134） |
| 本地 CLI | P2 | ✅ 完成 | `tools/argus_review.py` + `--mode` 复杂度路由（PR #137/#138） |
| 第二平台（GitLab MR 门禁） | P1(1.0 门槛) | ✅ 完成 | `.gitlab/argus-review.yml` + runner（PR #138） |
| 审查报告链接（Pro 钩子地基） | P2 | ✅ 完成 | `tools/argus_report.py` 静态 HTML 报告（PR #139） |
| WCAG 2.2 合规报告 | P3 | ✅ 完成 | `config/wcag-mapping.yml` + `argus_report.py --wcag`（PR #140） |
| 多注册中心发布（SkillHub/ClawHub/skills.sh） | — | ✅ 完成 | release.yml clawhub job + skills.sh submit（PR #132） |
| Marketplace 上架准备 + 自托管指南 | GTM | ✅ 完成 | `docs/marketplace-listing.md` + `docs/self-hosting.md`（PR #141） |
| 自定义规则 DSL | P3 | ✅ 完成 | `config/argus-rules.schema.json` + `tools/argus_rules.py`（PR #142） |
| 公开 API / webhook | P3 | ✅ 完成 | `tools/argus_webhook.py`（PR #143） |

**M1 门槛状态**：质量指标公开（precision/recall 门禁）、报告能力、第二平台均已具备；GitHub Marketplace 上架为 GTM 待办（见 `docs/marketplace-listing.md`），按 §6 定价执行。

---

*战略计划结束。下一次 90 天评审：按 §9 指标重估优先级，更新本文档版本号（产品版本仍保持 0.x，未经所有者批准不升 1.0）。*
