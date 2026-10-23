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

### bash 函数必须先定义后调用
- 失误：重构超时分支时，把 `dismiss_stale_reviews` 的**调用**挪到了定义之前。bash 在调用时解析函数名，于是 primary 超时 → `command not found`（exit 127）→ `set -e` 崩掉整个 step，**fallback 队列一次都没跑**。#185 的超时保护因此只生效了一半，潜伏数月才在 PR #203 暴露（只有超时才触发）→ 规则：函数定义一律放在 step 脚本开头；`validate_action.py` 的 `check_function_order` 会校验「首次调用行号 > 定义行号」。注意 `bash -n` 抓不到这个——语法完全合法（PR #203）

### 超时不要靠输出文本判断可重试
- 失误：超时分支之后又走 `grep retry_re` 门禁，但 `timeout` 杀掉挂住的进程时输出为空串，任何模式都匹配不上，于是 `return 124` 直接放弃、fallback 循环永远进不去 → 规则：exit 124 **本身就是可重试信号**，用标志位短路文本判定，不要让它参与 grep（PR #203）。回归测试：`tests/action/test_timeout_fallback.sh`

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

### 「目录里有」不等于「能调用」
- 失误：队列按 `GET /zen/v1/models` 是否列出模型来生成，于是推荐了 8 个实际不可用的模型（地区封锁、API 列出但 CLI 无法解析）→ 规则：三种状态必须分开表达——`deprecated: true`（已下架/改名，无恢复预期）、`regions: []`（仍在目录但本账号调用必失败）、无标记（可用）。每个条目的注释写明判定依据与核对日期，否则下一个人只能重新实测一遍（PR #187/#188/#199/#201，2026-10-20）

### 兜底值也是要维护的代码
- 失误：`BUILTIN_PRIMARY` 兜底指向一个早已 deprecated 的模型——「配置文件缺 primary 时」用它，等于配置一出问题就静默塞进死模型 → 规则：兜底常量必须有和主路径同等的可用性验证，并在注释里写明「这个值必须保持可调用」（PR #203）

## 发布与文档

### 删掉旧版本标题会让 Release Notes 串版
- 失误：改 CHANGELOG 时 prepend 新版本，把 `## [0.6.5]` 标题行一并替换掉，0.6.5 的正文变成悬空内容被算进 0.6.6。`release.yml` 用 awk 从 `## [x.y.z]` 截到下一个 `## [`，所以 v0.6.6 的 GitHub Release Notes 会把 0.6.5 的安全修复当成这一版的内容发布出去 → 规则：`validate_versioning.py` 现在校验标题唯一、严格降序、且每个「一句话概括」摘要行上方必须紧邻版本标题（孤立正文 = 标题被删）。**顺序检查单独不够**——删标题不会破坏降序（0.6.6 → 0.6.4 仍降序），必须查孤立正文（PR #203）


### Markdown 标题行不会以换行结尾
- 失误：`bump_version.py` 用 `^## \[Unreleased\]\n` 匹配「待发布块」，但真实标题带 compare 链接（`## [Unreleased](.../compare/...)`），`]` 后不是换行——正则**从未匹配过**，每次都走「没有 Unreleased」分支，把空模板插到文件最顶部（`# Changelog` 之上），已写好的说明留在原地永不提升；`make release` 抽出的发布说明是空骨架 → 规则：匹配 Markdown 标题**只锚定前缀**，不要假设标题行以 `\n` 结尾（标题常带链接/日期后缀）；改这类提取逻辑必须配 fixture 测试，样本要用真实文件形状（带 compare URL）（issue #208）

### 插入位置要用「原来那块在哪」，不是「文件开头」
- 失误：同一函数把新版本块拼到 `content` 最前面，假设 `[Unreleased]` 在文件顶部；实际开头是 `# Changelog` 前言，版本节跑到前言之上，`validate_versioning.py` 报 `summary block has no version heading above it` → 规则：移动章节时按原位置替换，不按文件头拼接

### 「没跑成」与「跑了但有问题」必须在数据层区分
- 失误：校验器在依赖缺失时返回 `"bash not found — skipped ..."`，文字写着 skipped 但没有 `SKIP: ` 前缀，而分类器只认前缀——「本机少个工具」被报成「代码有错」，退出码 1，日志指向 action.yml → 规则：用机器可判的标记（前缀/枚举）表达「跳过」，不要靠自然语言里的 "skipped"；并加断言锁住（`tests/action/test_skip_contract.py`）

### 不要依赖 runner 镜像的预装包
- 失误：`tools/` 有 5 个脚本 `import yaml`，`release.yml` 显式装了 PyYAML，但 `ci.yml` 没装也没声明 `requirements.txt`——CI 靠 `ubuntu-latest` 恰好预装才绿；换自托管 runner / slim 镜像就静默降级 → 规则：第三方依赖必须在仓库里有声明文件，CI 显式安装；CI 与 release 用同一个 `actions/setup-python` 版本常量（issue #208）

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
