# LESSONS — argus

> 前端设计代码审查 AI Agent（docs-driven：`AGENTS.md` + `SKILL.md` 运行时注入；stdlib-only Python 工具链；argus-flash GitHub App + composite action；MIT）。
> 本仓库从真实失误沉淀的「教训→规则」清单。**会话开始先全文阅读并遵循其中所有规则**；出现新失误按 §维护 追加。
> 权威依据：Anthropic Claude Code memory/best practices（<200 行、具体可验证、第二次犯同样错即写入）；社区 lessons.md 惯例（Boris Cherny，Anthropic）。
> 来源：本仓库 AGENTS.md + 已验证 fix 提交（2026-10 密集期，多为消费方实际故障反馈）。
>
> **注意区分两种 LESSONS**：本文件是 argus 自身的开发教训；`.argus/LESSONS.md` 是**给消费仓库用的**反馈通道（见 `docs/project-lessons.md`），两者不可混淆。

## 维护
- **触发**：用户纠正 / Agent 自查到的失误 / 非显而易见的 gotcha。
- **格式**：`### <主题>` 下，每条 = 失误（具体场景）→ 规则（最小可执行指令），一行可验证。
- **只记项目特有、不可从代码推断的**；通用最佳实践不写；含糊措辞（"小心""注意"）删掉。
- **重复出现** → 升级进 `AGENTS.md` 硬规则；**月度审阅**裁剪过期项；目标 < 200 行。

## Composite action（消费方故障最大来源）

### 步骤级 `timeout-minutes` 会让所有消费方失败
- 失误：在 composite action 的 step 上加 `timeout-minutes` —— composite-action manifest **不接受**该键，导致每个消费仓库的 review job 直接报错 → 规则：超时只能写在 **job 级**（消费方 workflow 的 job），action 内部用 GNU `timeout` 包命令（commit 0204591）

### `uses:` 不支持 `env` 表达式
- 失误：`uses: xxx@${{ env.REF }}` → `env` 上下文在 `uses` 键上不可用 → 规则：`uses` 只能用字面量或 `github.*`/`inputs.*` 上下文（commit 0e445d4）

### 安装后要显式 export PATH
- 失误：同一 step 内安装 CLI 后立刻调用，报 command not found → 规则：安装后显式 `export PATH=...`，不依赖 shell 重新加载（commit fb8da3b）

### 长任务必须硬超时
- 失误：评审完成后 opencode 进程挂住，job 一直跑到 6 小时默认上限 → 规则：用 `timeout` 包裹长命令，job 级再设 15 分钟兜底（commit 2a2ef56）

### V2-only 配置会让 V1 CLI 崩溃
- 失误：消费仓库的 `opencode.json` 含 V2 专属字段，固定的 V1 CLI 解析崩溃 → 规则：action 内隔离 V2-only 配置，CLI 版本固定到 1.x（commit e830943、8e1cee4）

## 安全（评审 agent 会拿到消费方写权限）

### 禁止评审 agent 推代码到消费仓库
- 失误：composite action 里写入 remote 凭据，评审 agent 得以向消费方分支推送 → 规则：**绝不**给评审进程配置 push 凭据；用 pre-push hook 兜底拦截（commit 362eb2c、67f47ac）

### 临时文件不能落到消费方分支
- 失误：quarantine 机制把临时产物写进工作树并推到消费方分支 → 规则：临时产物用原地改写 + `--skip-worktree`，绝不进入提交（commit 8c9ad2f）

### PR 分支名是注入向量
- 失误：把 PR 分支名直接插进 shell 命令（脚本注入）→ 规则：任何来自 PR 的字符串（分支名、标题、body）进入 shell 前必须转义或用 env 变量传递（commit 7a6379c、a3f8063、66ab7c2）

## 模型与队列

### 队列里不能有已弃用/不可达模型
- 失误：`free-models.yml` 保留已弃用与地区封锁模型，回退队列整条失效 → 规则：刷新后必须过滤 deprecated，并用网关实测可用性再生成（commit 66922f5、349cf04、be2de8d）

### primary 必须真实可用
- 失误：primary 指向不可用模型，全部请求走回退 → 规则：改 primary 前用真实凭据跑一次调用验证（commit 349cf04）

## 规则与质量门禁

### 改规则必须配 fixture
- 失误：改了检测规则但没动 fixture，回归无保护 → 规则：任何规则变更同 PR 增改 `tests/fixtures/`（见 AGENTS.md ANTI-PATTERNS）

### 基线只能因真实改进而刷新
- 失误：为了变绿刷新 `quality-baseline.json` → 规则：只在验证过的改进后 `make eval-baseline`；不得为通过而放宽（`make eval-gate` 在 CI 拦）

### 两类质量指标不可混谈
- 失误：把静态扫描指标当成 LLM agent 质量 → 规则：fixture 回归锁（gating）与 agent 质量（tracked）分开报告，见 AGENTS.md「Quality engine」

## 消费方配置

### 硬规则不可被 `.argus.yml` 关掉
- 失误：消费方通过配置完全屏蔽 P0 颜色/无障碍检查 → 规则：`.argus.yml` 只能调优（token 前缀、忽略路径、阈值），**P0 与 a11y 不可关闭**
