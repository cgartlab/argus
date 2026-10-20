# Changelog

本文件记录 argus 的所有显著变更。

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)。

> `0.x` 阶段：接口与行为仍可能发生破坏性变更，升级前请阅读对应版本的**一句话概括**中的「你需要做什么」。

## 条目模板

每个版本的第一段必须是「一句话概括」；随后按 Keep a Changelog 六类分节。
条目应先说明对使用者的影响，再写实现细节；涉及 issue 的一律写成可点击链接。

## [Unreleased](https://github.com/cgartlab/argus/compare/v0.6.6...main)

## [0.6.6](https://github.com/cgartlab/argus/compare/v0.6.5...v0.6.6) — 2026-10-20

> **一句话概括**：这是一次**免费模型队列的可靠性**更新。修掉了「会自动挑一个用不了的模型」这条链上的五个缺陷，并给 composite action 加了一道防止它把**所有下游仓库**一起弄挂的语法门槛。**你不需要做任何事**——`@main` 使用者自动生效；如果你自己 pin 了模型，可以考虑去掉（见下）。

### Fixed

- **自动刷新的免费模型队列会挑到用不了的模型**（[#187](https://github.com/cgartlab/argus/pull/187), [#188](https://github.com/cgartlab/argus/pull/188), [#199](https://github.com/cgartlab/argus/pull/199), [#201](https://github.com/cgartlab/argus/pull/201)）

  队列是按「模型是否出现在 Zen 的 `/models` 目录」生成的，但**目录里存在 ≠ 能调用**。于是队列一度推荐了 8 个实际不可用的模型，下游仓库的审查全都红灯。现在有两道过滤：

  - `deprecated: true` —— 模型已下架或已改名，跳过
  - `regions: []` —— 模型还在目录里，但本账号调用必失败（地区封锁，或 API 列出而 CLI 无法解析），跳过

  同时给 `config/model-scores.yml` 的每个不可用条目补上了**判定依据与验核日期**——此前只有一句 `deprecated: true`，没人知道为什么。

- **composite action 上的一个非法字段会让所有下游仓库的审查全部中断**（[#189](https://github.com/cgartlab/argus/pull/189), [#202](https://github.com/cgartlab/argus/pull/202)）

  [`2a2ef567`](https://github.com/cgartlab/argus/commit/2a2ef567) 给 action 的一个 step 加了 `timeout-minutes`。这个字段只在 **workflow 的 job step** 上合法，在 composite action 的 step 上是非法的——runner 在**加载 action.yml 时**就直接拒绝整个清单，于是**每一个**使用 `cgartlab/argus/.github/actions/argus-review@main` 的仓库，审查全部失败。故障持续 33 分钟。

  修掉字段只是止血；真正的修复是让这类错误**在 argus 自己的 CI 里就被拦住**：`tools/validate_action.py` 现在会校验每个 step 的键名是否在白名单内，非法键直接报错并指名是哪个 step、哪个键。

  > 此前拦不住的原因：CI 里的 YAML 检查只做 `safe_load`（语法层，`timeout-minutes: 12` 是合法 YAML），而原有的 9 项语义检查都在看 step 的**内容**，没有人看 step 的**键名**。

- **兜底主模型是个早已下架的模型**（[`tools/update_free_models.py`](https://github.com/cgartlab/argus/blob/main/tools/update_free_models.py)）

  `BUILTIN_PRIMARY` 是一个「配置文件缺 primary 时」的兜底值，但它指向 `opencode/deepseek-v4-flash-free`——早已 deprecated 并被排除。也就是说配置文件一旦出问题，兜底反而会静默塞进一个死模型。已改为当前实测可调的 `opencode/deepseek-v4.1-flash-free`，并在注释里写明这个值必须保持可调用。

### Changed

- **`config/free-models.yml` 现在精确等于「实际能调用」的集合**

  当前结论：Zen 目录 9 个免费模型中，只有 `deepseek-v4.1-flash-free`（primary）和 `nemotron-3.5-super-vl-free`（fallback）可以真正调用。

  > **如果你在自己的仓库里 pin 了模型**：可以考虑去掉 pin，直接用 argus 的自动队列——队列现在每周自动刷新，且带上述两道过滤。pin 与队列是两份要各自维护的清单，容易漂移（`cgartlab/men` 已因此移除 pin）。

## [0.6.5](https://github.com/cgartlab/argus/compare/v0.6.4...v0.6.5) — 2026-10-18

> **一句话概括**：这是一次**安全与稳定性**更新。修复了两个可以让别人在你的仓库里偷偷执行命令的漏洞，并让审查在模型服务商临时故障时不再直接失败。**你不需要做任何事**——如果你是 argus-flash App 或 composite action 的使用者，升级后自动生效。

### Fixed

- **两个安全漏洞：别人可以通过 PR 在你的仓库里执行命令** ([#169](https://github.com/cgartlab/argus/issues/169), [#170](https://github.com/cgartlab/argus/issues/170))

  这是本版最重要的修复。GitHub Actions 有一个容易踩的坑：当你把 `${{ ... }}` 表达式直接写进 `run:` 脚本时，GitHub 会在 shell 解析之前就把值**当成代码拼进去**。如果那个值来自用户（比如 PR 的分支名、或者调用方传入的参数），里面夹带的 `;` `"` `$()` 就会被当成命令执行。

  - **漏洞一（[#169](https://github.com/cgartlab/argus/issues/169)）**：`pr-automation.yml` 直接把 PR 分支名拼进脚本。**任何能开 PR 的人**都可以给自己的分支起个带命令的名字，在你的仓库里执行任意操作。现在分支名改为通过 `env:` 传入，只会被当成普通文本。
  - **漏洞二（[#170](https://github.com/cgartlab/argus/issues/170)）**：`argus-review` composite action 有 10 处把调用方传入的参数（`api-key`、`model`、`config-path` 等）直接拼进脚本。这个 action 被多个仓库复用，**影响面是所有使用它的仓库**。现在全部改为 `env:` 传值。

  > **如果你在自己的仓库里调用 `cgartlab/argus/.github/actions/argus-review@main`**：不需要改任何配置，拉取最新版本即可自动获得修复。action 的输入参数名和用法完全没变。

- **模型服务商临时故障时，审查不再直接失败** ([#162](https://github.com/cgartlab/argus/issues/162))

  之前只有遇到限流（429）或模型不存在时才会切换到备用模型，但**服务商临时过载**（返回 503 "Service temporarily overloaded"）不在这份清单里，于是审查直接中断——尽管配置里明明准备了 7 个备用模型。现在这类临时故障也会触发切换。

  > 实际遇到的问题：`Streaming response failed: [503] Upstream error from Nvidia: Service temporarily overloaded` → 以前会导致 PR 拿不到审查结果 → 现在会自动换下一个模型继续。

- **ClawHub 发布到了错误的 slug** ([#161](https://github.com/cgartlab/argus/issues/161))

  发布脚本里把 slug 写死成 `argus-design-review`，但包内 `SKILL.md` 的 `name` 是 `argus-flash` ——于是发布出来的路径和预期不符。现在改为从包内文件派生，两边不会再漂移。

### Changed

- **站点依赖升级：sharp 0.35.5（修复 RCE 漏洞）** ([#165](https://github.com/cgartlab/argus/issues/165))

  `sharp` 图像处理库的 `librsvg` 依赖存在**远程代码执行**漏洞（[GHSA-wq5f-xc86-pv6w](https://github.com/advisories/GHSA-wq5f-xc86-pv6w) / CVE-2026-96889，高危）。站点的 lockfile 原本通过 Astro 的可选依赖锁在 0.35.4。

  修复方式是把 `sharp` 提升为直接依赖并锁定 0.35.5，`npm install` 后确认 `found 0 vulnerabilities`。**仅影响文档站点的构建依赖，不影响审查功能。**

- **PR 自动标签规则重写** ([#166](https://github.com/cgartlab/argus/issues/166))

  原来的标签配置是从一个通用站点模板照搬的，与 argus 的实际目录结构对不上，导致两个问题：① 改任何 `.md` 文件都会被误标成 `type:bug`；② 有些标签的路径规则指向了本仓库不存在的目录，永远不会生效。

  现在按真实结构重写，并新增 4 个标签：`🧩 area:action`（Composite Action）、`📖 area:site`（文档站点）、`🐍 area:tools`（工具链）、`🧪 tests`（测试）。

  > **`type:bug` 不再由文件路径自动推断**——改了什么文件并不能说明这次是修 bug 还是加功能。现在 `type:bug` 由 issue 模板承载，人工标注的标签也不会被自动清除。

### Added

- **PR / Issue 模板与自动分配** (#0fa9398)

  新增了 Bug 报告、功能请求、任务三种 Issue 表单，以及 PR 模板；PR 打开后会自动分配作者、按分支名前缀打标签（`feat/` → enhancement，`fix/` → bug，`docs/` → documentation）。

---

## [0.6.4](https://github.com/cgartlab/argus/compare/v0.6.3...v0.6.4) — 2026-10-16

> **一句话概括**：这是一次**发布架构与稳定性**更新。`SKILL.md` 与注册表耦合的字段（summary / homepage / metadata.openclaw）移到 `config/skill-platforms.yml`；备用模型切换逻辑补上了「服务商临时过载（503）」等失败模式，临时故障不再中断审查。**你不需要做任何事——消费端配置无需改动。**

### Changed

- **`SKILL.md` frontmatter de-coupled from registries where possible** ([#153](https://github.com/cgartlab/argus/issues/153)) — `summary`, `homepage`, and the `metadata.openclaw` block were non-standard, registry-coupled fields in the core skill file. They moved to the new `config/skill-platforms.yml` (`platforms.skillhub` / `platforms.clawhub`), so `SKILL.md` now carries only standard portable fields plus the two the SkillHub CLI requires.
  - `slug` and `displayName` **stay** in `SKILL.md`: the SkillHub CLI reads them directly from the file and fails with `SKILL.md 缺少 slug` when they are absent. Moving them to config broke the `skillhub` release job on v0.6.4 — that contract is now documented in both files so it is not "simplified" away again.
  - `tools/publish_skillhub.py` reads non-required display metadata from the platform config; `tools/publish_clawhub.py` reuses that loader for the ClawHub emoji.

### Fixed

- **action.yml Retry: transient 5xx upstream failures now fall back** — `retry_re` matched rate limits, missing models, and a few fixed phrases, but not a provider overload, so the review aborted instead of walking the fallback queue. Observed failure: `UnknownError: {"message":"Streaming response failed: [503] Upstream error from Nvidia: Service temporarily overloaded","type":"server_error"}` → no pattern matched → fail-fast, even though `config/free-models.yml` ships 7 fallback models and the first (`opencode/deepseek-v4-flash-free`) is not NVIDIA-served. Added phrase-specific patterns: `upstream error`, `service temporarily overloaded`, `temporarily overloaded`, `service unavailable`, `server_error`, `bad gateway`, `gateway timeout`. Bare `5xx` digits and bare `unavailable` are deliberately **not** matched — they hit ordinary line numbers and review prose (the same reason bare `unavailable` was dropped previously). The duplicated `_is_retryable()` regex in `tools/run_fixture_tests.py` was updated in the same change.

### Removed

---

## [0.6.3](https://github.com/cgartlab/argus/compare/v0.6.2...v0.6.3) — 2026-10-16

> **一句话概括**：这是一次**静态扫描器校准**。`hardcoded-spacing` 规则从 P1 降为 P2（与文档契约一致），此前每个硬编码间距都会阻塞合并；severity matrix 校验扩展到扫描器的 `emit()` 调用点。**你不需要做任何事——规则行为与既有文档对齐，合并阻塞减少。**

### Added

- **Severity matrix: static scanner is now a checked source** — `validate_severity_matrix.py` parses the `emit()` sites in `tools/run_fixture_tests.py` and enforces that each scanner rule emits at the severity the canonical matrix declares (previously only `config/severity-matrix.yml` ↔ `SKILL.md` ↔ `load_config.NON_DOWNGRADABLE_RULES` were compared). New scanner rules must be registered in `SCANNER_RULE_MAP`; an unmapped `emit()` site fails the check, so a new rule can no longer silently bypass the matrix.

### Changed

- **`hardcoded-spacing` is now P2, not P1** — the static scanner emitted hardcoded spacing/radii/font-size as **P1** while `config/severity-matrix.yml`, `SKILL.md`, and `docs/argus-config-schema.md` all declared it **P2** (and documented it as downgradable to P3). Since P1 means "must fix before merge" and P1 rules cannot be downgraded, every hardcoded `padding: 16px` blocked merges and consumers were forbidden from downgrading a rule the docs called P2. The scanner now matches the documented contract.
  - Fixture baselines updated accordingly: `hardcoded-values/bad-magic-numbers` (4 findings P1→P2), `golden/product-card` (3 findings P1→P2), `golden/theme-system` (1 finding P1→P2).
  - Aggregate detection is unchanged: 38 TP, 0 FP, precision/recall/F1 = 1.0 vs baseline.

### Fixed

- **`validate_severity_matrix.py` scanner column always showed `n/a`** — the scanner severities were computed before the row loop but then re-initialised to an empty dict immediately before it, so the report column and the drift check both saw nothing. Now computed once and shared.

### Removed

---

## [0.6.2](https://github.com/cgartlab/argus/compare/v0.6.1...v0.6.2) — 2026-10-15

> **一句话概括**：这是一次**小型 CI 修复**：扩展覆盖检查此前只字面匹配 `*.htm`，含 `.html` fixture 的 PR 会一直失败，现在两者等价。**你不需要做任何事。**

### Added

### Changed

- **CI: fixture extension-coverage step fixed** — `.htm` and `.html` share one static-scanner branch, but the check only counted `*.htm` literally (and there are no `.htm` fixtures, only `.html`). It now also accepts `.html` fixtures as coverage for `.htm` instead of failing every PR.

### Fixed

### Removed

## [0.6.1](https://github.com/cgartlab/argus/compare/v0.6.0...v0.6.1) — 2026-10-15

> **一句话概括**：这是一次**命名约定统一**：项目教训文件从单数 `.argus/LESSON.md` 统一为复数 `.argus/LESSONS.md`，行为不变。**使用 `.argus/LESSONS.md`（复数）的仓库不受影响；若你配置了单数旧路径，改名为复数即可。**

### Added

### Changed

- **Standardized the per-project lesson filename to `.argus/LESSONS.md`** (plural) — the v0.6.0 feature used the singular `.argus/LESSON.md`; the plural form matches Markdown/documentation convention. Renamed consistently across the `.argus.yml` `lessons-path` default (schema + example), `tools/load_config.py`, `tools/argus_review.py` (`--lessons` auto-detect + `--lessons` help), the composite action (`action.yml`), `tools/validate_lessons.py`, `config/lessons.template.md`, `docs/project-lessons.md`, `docs/argus-config-schema.md`, `AGENTS.md`, `README.md`, `SECURITY.md`, the `Makefile`, and the `site/` docs (commands / configuration / overview). Behavior is unchanged — only the filename convention moved; consumers using `.argus/LESSONS.md` are unaffected.

### Fixed

### Removed

---

## [0.6.0](https://github.com/cgartlab/argus/compare/v0.5.8...v0.6.0) — 2026-10-15

> **一句话概括**：这是一次**能力扩展与诚实性修正**：新增每项目教训通道（`.argus/LESSONS.md`，每次审查自动加载）；JS/TS 文件不再静默返回「无发现」，而是明确提示改用 LLM 模式；质量测量区分静态回归锁与 LLM 代理质量（tracked，不 gated）。**你不需要做任何事；审查 `.js/.ts` 时按提示用 `--mode llm` 即可。**

### Added

- **Project lessons channel (`.argus/LESSONS.md`)** — Argus now loads a per-project lesson file into every review it runs on that repo, so project-specific mistakes (a legitimate pattern, a token convention, a known exemption) do not recur. Absent file = no behavior change. Default path `.argus/LESSONS.md` (configurable via `.argus.yml` `lessons-path`). Cloud (`action.yml`) and local (`argus_review.py`) both load it; `--lessons PATH` overrides locally. See `docs/project-lessons.md` + starter `config/lessons.template.md`; validate with `make validate-lessons FILE=...`. Generic Argus bugs are promoted to the Argus repo as fixtures, not hoarded here.
- **`validate_lessons.py`** — validates a project lesson file (ID uniqueness, required fields, ~6 KB / 20-entry budget); runs in CI against the template.
- **Honest quality measurement (`eval_quality.py --mode`)** — explicit `--mode static|llm|auto` (was inferred from CLI presence). Static mode is labelled a *fixture regression lock* (not the LLM agent); `--mode llm` measures the real review path and, with `--history FILE`, appends `{ts, mode, model, metrics}` to `config/quality-llm-history.jsonl`. The scheduled `llm-fixture-tests` CI job is now **tracked, not gated** (free-model output varies run to run); a hard floor is deferred until variance is known.
- **`make eval-llm`** and **`make validate-lessons`** convenience targets.
- **CI: extension-coverage check** — every reviewable extension must be either static-supported (with ≥1 fixture) or declared LLM-only; catches an unclassified extension.
- **CI: toolchain end-to-end** — `argus_review --json → argus_report --wcag → argus_webhook --dry-run` runs every CI, so the report/webhook surfaces are never unexercised.
- **`_skill_publish.py`** — shared skill-publish helpers (frontmatter parsing, zip extraction, SemVer, CHANGELOG summary) now used by both `publish_skillhub.py` and `publish_clawhub.py` (de-duplicated two byte-identical frontmatter parsers).

### Changed

- **No more silent false-clean on JS/TS** — the static heuristic scanner (CSS/HTML-only) now raises `UnsupportedExtensionError` for `.js/.ts/.jsx/.tsx` instead of returning `"(no findings)"`. `argus_review.py --mode static` exits non-zero with a clear "use --mode llm" message on those files (the GitLab MR path inherits this); `--mode auto` routes LLM-only extensions to the LLM unconditionally.
- **Honesty pass** — `AGENTS.md`/`README.md`/`SECURITY.md`/`tests/fixtures/README.md` no longer imply the scanner gate measures the agent; the "pure documentation repository / no runtime code" claim in `SECURITY.md` is corrected to describe the actual Python toolchain + Astro site + supply-chain surface; "roadmap complete" wording now distinguishes the delivered engineering roadmap from the unmet commercial M1 gate.
- **`action.yml`** injects the consumer's `.argus/LESSONS.md` into the review prompt (after SKILL.md) and logs whether lessons were loaded. Consumers via `@main` pick this up automatically; no file = no change.
- **Website & docs synced** — `site/` docs (commands, configuration, index, getting-started, architecture, development, skill) now document `lessons-path`, `eval-llm`/`validate-lessons`, and the two-level quality measurement; stale version pins (`@v0.4.1` → `@v0.6.0`) and the false "pure documentation / no runtime code" claims corrected across site + root; the unreferenced stale `site/ARCHITECTURE.md` blueprint removed.

### Fixed

### Removed

- **`docs/reports/`** — the two dated one-shot audit snapshots (`code-quality-2026-09-19.md`, `web-quality-2026-09-19.md`) were unreferenced living docs that described already-merged fixes; deleted to stop misleading readers.
- **`.omo/`** entry removed from `AGENTS.md` STRUCTURE (empty gitignored runtime dir).

---

## [0.5.8](https://github.com/cgartlab/argus/compare/v0.5.7...v0.5.8) — 2026-09-23

> **一句话概括**：这是一次**大型能力发布**：本地审查 CLI（无需 API key 的静态模式）、GitLab MR 审查、HTML/WCAG 报告、自定义规则 DSL、webhook 转发、质量引擎与 golden 评测集、`.argus.yml` JSON Schema、自托管指南等。**你不需要做任何事——全部为新增能力；想在本机体验可运行 `make review FILE=...`。**

### Added

- **Local review CLI** — `tools/argus_review.py` reviews frontend files with the exact same rules as the GitHub App / composite action, anywhere Python runs: OpenCode CLI when installed, static heuristic scanner otherwise (no API key needed). `make review FILE=...` convenience target; `--stack` / `--model` / `--dir` / `--ignore`; `--json` emits a structured findings report (the payload a future report-link / CI-comment service consumes).
- **GitLab MR review (second platform)** — `.gitlab/argus-review.yml` is an include template any `.gitlab-ci.yml` can pull: it clones cgartlab/argus, runs `tools/argus_review.py` on the MR's changed frontend files, and posts the review as an MR note (runner: `.gitlab/argus-review.sh`, testable with `ARGUS_DRY_RUN=1`).
- **Complexity routing (cost control)** — `tools/argus_review.py --mode auto` routes each file by size: ≤ `--min-lines` (default 200) → static heuristic scanner (free), larger → LLM; `--mode static|llm` force either path.
- **Shareable HTML report** — `tools/argus_report.py` turns a findings JSON report (from `argus_review.py --json`) into a single self-contained HTML file (no server, no external assets) grouped by severity P0→P3, with escaped code snippets; `make report JSON=...`. This is the artifact a future hosted report-link / Pro hook serves.
- **WCAG 2.2 compliance reports** — `tools/argus_report.py --wcag` annotates a11y findings with their governing success criterion (`config/wcag-mapping.yml`: 1.1.1, 1.3.1, 1.4.3, 2.4.7, 2.5.8, 3.1.1, 4.1.2) and adds a compliance summary (unique criteria, A/AA counts) for audit handoff.
- **`.argus.yml` JSON Schema** — `config/argus-config.schema.json` (draft-07) for editor autocomplete and CI validation; `tools/validate_argus_schema.py` is a zero-dependency subset validator. `make validate-schema` checks the schema file and validates `config/argus.example.yml`.
- **Config parser hardening** — the `tools/load_config.py` minimal YAML fallback (used when PyYAML is unavailable) now handles arbitrary-depth nesting, inline lists (`[a, b]`), and bool/int scalar coercion; config `version` `"0.4"` is accepted (and is the new default), aligning docs with code.
- **Custom rules (rule DSL)** — `config/argus-rules.schema.json` (draft-07) + `tools/argus_rules.py`: teams define their own review rules (custom token mappings, banned patterns) as `"<id>|<severity>|<match>|<message>|<token>|<files>"` entries, validate them (`--validate`, zero-dep engine) and apply them to files (`apply`, standard Argus output + `--json`). Reference: `docs/argus-rules.md`; example: `config/argus-rules.example.yml`.
- **Webhook forwarding (public API)** — `tools/argus_webhook.py` POSTs a findings report to any HTTP endpoint (`POST application/json`, optional `Authorization: Bearer`); `--dry-run` prints the request without sending; `make webhook-send REPORT=... URL=...`.
- **Quality Engine V1** — `tools/eval_quality.py` computes suite-level precision / recall / F1 from the fixture regression suite and enforces regression gates against a committed baseline (`config/quality-baseline.json`). `make eval` reports quality, `make eval-gate` enforces the gates (runs in CI after fixture tests), `make eval-baseline` refreshes the baseline after verified improvements.
- **AGENTS.md next-phase conventions** — "Quality never regresses" (CONVENTIONS) and "Merging without quality gates" (ANTI-PATTERNS); quality engine entries in STRUCTURE / WHERE TO LOOK / COMMANDS / NOTES.
- **Golden Eval Set V1** — new `tests/fixtures/golden/` category with realistic multi-violation fixtures (product-card CSS, checkout page HTML, theme-system CSS); the quality engine now reports and gates over 14 fixtures (38 TP / 0 FP / 0 FN) and CI uploads `quality-report.json` as an artifact.
- **Severity matrix calibration** — `config/severity-matrix.yml` is now the canonical rule-id × severity matrix; `tools/validate_severity_matrix.py` (`make validate-severity`, runs in CI) enforces that it never drifts from the SKILL.md "## Issue Severity" table or `load_config.NON_DOWNGRADABLE_RULES`. Negative check verified: downgrading `bare-color` to P2 is caught on both the docs and enforcement axes.
- **False-positive appeal loop** — `tools/add_fp_appeal.py` turns a "this isn't a bug" report into a permanent zero-expectation regression fixture under `tests/fixtures/false-positives/` (with `[must-not-flag]` guards) and runs the static scanner to detect real false positives.
- **Fixed a real false positive found by the appeal loop** — the static scanner no longer flags `filter: drop-shadow(... rgba ...)` as a bare color; shadow colors (`box-shadow` / `text-shadow` / `filter: drop-shadow`) are exempt. Guarded by the new `drop-shadow-color` appeal fixture.
- **Marketplace listing prep** — `docs/marketplace-listing.md`: the full checklist to list argus-flash on the GitHub Marketplace (App permissions, listing content, Community/Pro/Enterprise pricing plans, submission + go-live), grounded in the commercial strategy plan's §6 pricing.
- **Self-hosting guide** — `docs/self-hosting.md`: private deployment — self-hosted runners (GitHub Actions / GitLab) and a private model endpoint, with a data-handling summary and security notes for regulated/enterprise use.
- **Roadmap completion** — all P1/P2/P3 items from `docs/strategic-plan.md` delivered (quality engine + gates, severity matrix, FP appeal loop, `.argus.yml` schema, local CLI, GitLab template, HTML/WCAG reports, custom rules DSL, webhook API); `docs/strategic-plan.md` §14 carries the delivery table and the roadmap is consolidated in the core docs (README toolchain/status, DEVELOPMENT-GUIDE).

### Changed

### Fixed

- **SkillHub publish slug corrected to `argus-flash`** — `SKILL.md` frontmatter `slug`/`name` were `argus-design-review`, so the v0.5.7 release published (or updated) a stray SkillHub entry instead of overwriting the existing skill whose unique ID is `argus-flash`. Frontmatter now uses `argus-flash`, so subsequent `skillhub publish` runs overwrite-update the correct skill. (The stray `argus-design-review` entry created by v0.5.7 must be removed manually on the SkillHub platform.)

### Removed

---

## [0.5.7](https://github.com/cgartlab/argus/compare/v0.5.6...v0.5.7) — 2026-09-12

> **一句话概括**：这是一次**发布修复**：SkillHub 发布恢复使用既有手工 slug `argus-design-review`，release 流程会更新原始 Argus skill。**你不需要做任何事。**

### Added

### Changed

- **SkillHub Slug Reuse** — `SKILL.md` now publishes to SkillHub with the existing manual release slug `argus-design-review`, so the release workflow updates the original Argus skill.

### Fixed

### Removed

---

## [0.5.6](https://github.com/cgartlab/argus/compare/v0.5.5...v0.5.6) — 2026-09-12

> **一句话概括**：这是一次**发布配置调整**：改用全局唯一 slug `cgartlab-argus-design-review`，避免与公开 slug `argus-design-review` 冲突。**你不需要做任何事。**

### Added

### Changed

- **Unique SkillHub Slug** — `SKILL.md` now publishes to SkillHub with the globally unique slug `cgartlab-argus-design-review`, avoiding a conflict with the existing public slug `argus-design-review`.

### Fixed

### Removed

---

## [0.5.5](https://github.com/cgartlab/argus/compare/v0.5.4...v0.5.5) — 2026-09-12

> **一句话概括**：这是一次**发布脚本修复**：`publish_skillhub.py` 现在能正确提取带 `### Added` / `### Changed` 等子标题的 CHANGELOG 段落的首条内容。**你不需要做任何事。**

### Added

### Changed

### Fixed

- **SkillHub Changelog Parsing** — `tools/publish_skillhub.py` now correctly extracts the first bullet from CHANGELOG sections that use `### Added`, `### Changed`, or other subheadings.

### Removed

---

## [0.5.4](https://github.com/cgartlab/argus/compare/v0.5.3...v0.5.4) — 2026-09-12

> **一句话概括**：这是一次**发布自动化扩展**：GitHub Release 成功后自动把 skill 包发布到 SkillHub（需配置 `SKILLHUB_API_KEY`）。**你不需要做任何事——仅仓库维护者需配置 secret。**

### Added

- **SkillHub Auto Publish** — `release.yml` now publishes the Argus skill package to SkillHub after the GitHub Release job succeeds, using the repository `SKILLHUB_API_KEY` secret.
- **SkillHub Publish Prep** — `tools/publish_skillhub.py` validates SkillHub frontmatter, extracts the skill package into a publishable directory, and writes the current changelog summary.
- **SkillHub Frontmatter** — `SKILL.md` now includes the required `slug`, `displayName`, `summary`, `license`, and `homepage` metadata for SkillHub publishing.

### Changed

- **Release Docs** — Release and development docs now document the SkillHub publishing step and the `make prepare-skillhub` maintainer check.

### Fixed

### Removed

---

## [0.5.3](https://github.com/cgartlab/argus/compare/v0.5.2...v0.5.3) — 2026-09-12

> **一句话概括**：这是一次**构建修复**：用 npm 10.9.8 重新生成 `site/package-lock.json`，修复 GitHub Pages 工作流 `npm ci` 失败。**你不需要做任何事。**

### Fixed

- **Site Lockfile for npm 10** — Regenerated `site/package-lock.json` with npm `10.9.8` so the GitHub Pages workflow can run `npm ci` successfully and include the expected `crossws@0.4.12` lockfile entry.

---

## [0.5.2](https://github.com/cgartlab/argus/compare/v0.5.1...v0.5.2) — 2026-09-12

> **一句话概括**：这是一次**发布安全加固**：`make release` 现在校验 tag/VERSION 一致性、拒绝重复或过期发布、要求版本文件已提交且本地 main 不落后；PR 审查与 bot 分配改用仓库 token。**你不需要做任何事——发版命令会先自我校验。**

### Added

- **Release Gate** — `tools/check_release.py` now verifies whether the current `VERSION` has a matching `vX.Y.Z` tag on `origin`; `make release` uses it to refuse duplicate or older releases, and CI can use `--expect-released` to catch phantom version bumps.
- **Daily Release Check** — `.github/workflows/release-check.yml` fails when `VERSION` is ahead of the latest release tag, making unreleased version bumps visible without waiting for a release attempt.

### Changed

- **Safer Release Flow** — `make release` now validates release state, requires version files to be committed at `HEAD`, refuses to run when local `main` is behind `origin/main`, creates an annotated tag, verifies the tag's `VERSION`, then pushes `main` and the tag.
- **Expanded Version Sync** — `make bump-*` and version validation now keep `site/src/data/site.ts` and `site/src/content/docs/index.md` in sync with `VERSION`, alongside `CHANGELOG.md`, `AGENTS.md`, `SKILL.md`, and `manifest.yaml`.
- **CI Release Coverage** — CI now validates `tools/check_release.py`, compiles it, includes `release-check.yml` in workflow YAML validation, and reports release status from `VERSION` vs origin tags.

### Fixed

- **Review Workflow Permissions** — `Argus-Flash Review` now uses the repository `GITHUB_TOKEN` for PR comments, avoiding installation-token permission failures on bot-created PRs.
- **PR Automation Bot Assignment** — PR automation no longer attempts to assign `argus-flash[bot]`, avoiding GitHub App installation-token assignee failures.
- **Model Refresh PR Creation** — The scheduled model refresh workflow creates its PR with an argus-flash installation token, preventing `GITHUB_TOKEN` PR-creation permission failures.
- **Dependabot Check Context** — Dependabot auto-merge explicitly runs `gh pr checks -R "${{ github.repository }}"` so the check wait uses the correct repository context.

---

## [0.5.1](https://github.com/cgartlab/argus/compare/v0.4.1...v0.5.1) — 2026-09-06

> **一句话概括**：这是一次**模型配置与鉴权体验更新**：默认主模型回到 `opencode/deepseek-v4-flash-free`（`hy3-free` 已下线）；新增 `api-key` 输入与 5 步修复指引；免费模型列表改为从公开 Zen API 实时刷新。**使用 composite action 需自行配置 `OPENCODE_API_KEY`（不内置 key）；已弃用模型会自动从队列移除。**

### Added

- **Zen API Key Guidance** — The composite action accepts a new `api-key` input. When the review fails with an auth-class error (401/403/unauthorized/invalid key), it fails fast instead of walking the fallback queue (every zen model shares the same key, so retries would 401 identically) and prints a copy-ready 5-step fix guide: register at opencode.ai → create a key at opencode.ai/auth → add an `OPENCODE_API_KEY` Actions secret → the workflow passes it via `api-key: ${{ secrets.OPENCODE_API_KEY }}` → re-run. Guidance goes to stdout and, best-effort, as a PR comment.
- **API-First Model Refresh** — `update_free_models.py` now fetches the live free model list from the public OpenCode Zen API (`GET https://opencode.ai/zen/v1/models`, no auth, stdlib `urllib` only). The opencode CLI is retained solely as a degradation path when the API is unreachable; the scheduled workflow no longer installs the CLI, and the cron is offset to `23 */12 * * *`.

### Changed

- **Dynamic Primary Selection** — `refresh()` re-selects the primary on every run: the current primary is kept while it is still live, otherwise the highest-ranked live `-free` model is promoted (composite score desc, ties alphabetical) with a `↻ Primary re-selected: X → Y` log. Default primary moved to `opencode/deepseek-v4-flash-free` (last-known-good); the action's `model` input now defaults to empty and is resolved at runtime from `config/free-models.yml` primary, with the same built-in default as final fallback. `run_fixture_tests.py` and `make test-fixtures-llm` no longer hardcode a model — they read the config primary too.

  > **Why deepseek is back:** [0.4.0] moved the default to `opencode/hy3-free` (deepseek was deprecated at that time). `hy3-free` was subsequently delisted from the live model list (see *Delisted Models Dropped* below), so the default reverts to `opencode/deepseek-v4-flash-free` as the last-known-good model. The "[0.4.0] deepseek deprecated" note is historical context for that release, not a statement about the current default.
- **User-Decided Constraints** — Only `-free`-suffixed model IDs qualify for the fallback queue (big-pickle stays excluded); consumers must configure their own OpenCode Zen API key (`OPENCODE_API_KEY`, provider=opencode) — no bundled key; GitHub's `GITHUB_TOKEN` with `contents: write` is sufficient for the auto-push, and the push does not re-trigger the workflow (accepted behavior).
- **Delisted Models Dropped** — Removed `opencode/hy3-free` and `opencode/x-preview-f-free` from `MODEL_SCORES`; regenerated `config/free-models.yml` contains only currently-live `-free` models.
- **Auth Preflight (local)** — `run_fixture_tests.py` prints a non-blocking hint when running an `opencode/` provider model without `OPENCODE_API_KEY` (`opencode auth login` or set the env var; see https://opencode.ai/auth).

---

## [0.5.0] — 2026-09-03 _(无 tag)_

> **一句话概括**：这是一次**审查规则与误报控制升级**：审查提示改用真实设计系统 token 名（Ant Design v5 / Material 3 / Polaris），支持 `design-system: auto` 自动探测；新增误报基准与 P0/P1 不可降级规则矩阵。**你不需要做任何事——默认自动探测；可在 `.argus.yml` 显式指定 `design-system`。**

### Added

- **Design-Token System Mapping** — The review prompt now references real design-system token names (`--ant-color-*` / `--md-sys-*` / `--p-color-*`) instead of generic `var(--ds-*)` placeholders, via built-in token mappings for Ant Design v5, Material Design 3, and Shopify Polaris
- **Auto Detection** — `design-system: auto` (default) detects the token mapping from `package.json` dependencies (antd ≥ 5 → antd5, `@mui/material` → material3, `@shopify/polaris` → polaris, otherwise custom); consumers can pin `design-system` explicitly in `.argus.yml`
- **False-Positive Benchmarks** — New `tests/fixtures/false-positives/` baseline so non-blocking bare values (e.g. a `box-shadow` rgba literal) are classified as P2 instead of over-flagged as P0; fixtures run as part of the static heuristic suite
- **FalsePositiveRate** — `run_fixture_tests.py` reports the false-positive rate against the expected baseline, keeping over-flagging visible in CI
- **Severity Matrix** — SKILL.md replaces the free-form severity table with a strict rule-id × severity matrix (`dark-mode-coverage`/`bare-color` → P0, `missing-alt`/`button-aria-label` → P1, `hardcoded-spacing`/`bem-naming`/`raw-px-breakpoint` → P2, polish → P3); P0/P1 core rules are non-downgradable, enforced by `load_config.py` (`Rule 'x' is P0 and cannot be downgraded`)
- **Design-System Config** — `.argus.yml` gains the `design-system` field (`auto` | `antd5` | `material3` | `polaris` | `custom`); `overrides.severity` accepts upgrades and non-core downgrades, rejects P0/P1 core downgrades

### Changed

- **Scoped Static Fixes** — `run_fixture_tests.py` static-heuristic fixes are scoped to the offending rule instead of the whole file, aligning with the false-positives baseline (Phase 1, [#18](https://github.com/cgartlab/argus/issues/18))

### Fixed

### Removed

> **Note:** Phase 1 of [#18](https://github.com/cgartlab/argus/issues/18) — Severity calibration. The 42 framework anti-pattern rules keep their existing inline P1/P2/P3 annotations unchanged.

---

## [0.4.1](https://github.com/cgartlab/argus/compare/v0.4.0...v0.4.1) — 2026-09-03

> **一句话概括**：这是一次**规则扩充与准确性修正**：新增 CSS-in-JS / 响应式设计模式（44px 触控目标等），并移除/修正多处编造或过时的框架示例（Angular `destroyRegistry()`、Vue 2 时代规则等）。**你不需要做任何事。**

### Added

- **CSS-in-JS / Responsive Design Patterns** — New SKILL.md section covering hardcoded values in styled-components / CSS Modules, media-query breakpoint tokens, and the 44px touch target

### Changed

- **SKILL.md Stack Detection Expanded** — Detection table adds UnoCSS and Tailwind CSS rows; the detection workflow adds an atomic-CSS check step

### Fixed

- **SKILL.md Anti-Patterns Accuracy** — Removed the fabricated Angular API `destroyRegistry()` in favor of the official `takeUntilDestroyed()` / `inject(DestroyRef)`; fixed the unclosed `new FormControl(')` string (Angular #2), the mistyped `onClick={{ handle }}` (React #3), the dead link (Svelte #2), and the invented `userStore.incrementAge()` (Svelte #5); rewrote Astro #1 and General JS/TS #4 so WRONG/RIGHT examples are unambiguous
- **SKILL.md Vue Rules Modernized** — Rewrote the doc-contradicting Vue #4 (reactive over ref) into a real anti-pattern: destructuring `reactive()` drops reactivity → use `ref()` / `toRefs()`; rewrote the Vue 2-era Vue #8 (push not reactive) into the Vue 3 rule: direct prop assignment → `defineModel()` / `emit`
- **action.yml Auth/Retry Tightening** — `auth_re` no longer matches bare `401|403|api key` (ordinary review prose and line numbers no longer trigger false auth failures or mislead users into configuring a key); `retry_re` drops bare `unavailable`; exhausted fallbacks with no primary output now emit explicit diagnostics (timeout / network / model hang)
- **action.yml Stale-Review Cleanup** — The fallback loop calls `dismiss_stale_reviews` between failed attempts to avoid duplicate review comments; last-resort fallback queue literal synced with `config/free-models.yml` (4 → 6 models)
- **Fixture Runner Verification** — `run_fixture_tests.py` now actually validates `line_hint` (previously parsed but never checked); static heuristic mode uses tolerance=0 for exact matching (LLM mode keeps ±1)
- **Model Refresh CLI Fallback** — `update_free_models.py` CLI fallback path accepts bare model IDs (no `opencode/` prefix); the `[`-prefixed line skip is narrowed to log-level lines only
- **Makefile Validate Hardening** — `make validate` no longer swallows SKILL.md trigger-phrase check failures (python3 present → fail on fail; missing → warn without blocking); added the `validate_versioning.py` consistency check; required-files list aligned with ci.yml (14 → 18)
- **Manifest & Docs Accuracy** — Removed the non-existent `skills: [accessibility]` reference from `manifest.yaml` (name difference annotated); cleaned duplicate COMMANDS lines in `AGENTS.md`; `docs/men-integration.md` clarifies that `--men-context` / `--events-json` are prompt-layer conventions, not CLI features; `docs/argus-config-schema.md` aligns the max-findings promise with actual behavior (dropped the unsubstantiated "N more findings suppressed" claim)

---

## [0.4.0](https://github.com/cgartlab/argus/compare/v0.3.3...v0.4.0) — 2026-09-02

> **一句话概括**：新增**营销官网**（`site/`，Astro 7，部署至 argus.cgartlab.com）与免费模型排名机制；默认审查模型切换为 `opencode/hy3-free`（该决定后来在 0.5.1 回退）。**你不需要做任何事——如需固定模型可在调用时显式指定。**

### Added

- **Marketing Site** — New `site/` (Astro 7 + UnoCSS) with a 60fps digital-water hero, frosted-glass header, 7 beginner-friendly docs, `/legal` pages, and a custom 404 page
- **Site Deployment** — New `.github/workflows/deploy-site.yml` builds and deploys `site/` to GitHub Pages on push to `main` (path-filtered on `site/**`); `site/public/CNAME` points to `argus.cgartlab.com`
- **Third-Party Notices** — Added `NOTICE` declaring OpenCode, GitHub, and other third-party trademarks; Argus remains independent and unaffiliated
- **Model Ranking** — `update_free_models.py` now ranks free models by composite coding ability (SWE-bench et al.) via `MODEL_SCORES` + `rank_models()`, replacing the hardcoded `BUILTIN_FALLBACK` constant

### Changed

- **Primary Model** — Default review model switched from `opencode/deepseek-v4-flash-free` to `opencode/hy3-free` (deepseek deprecated; see the Unreleased *Dynamic Primary Selection* entry for the subsequent revert)
- **Fallback Refresh** — `config/free-models.yml` fallback queue is now auto-refreshed every 12h, ordered by the coding-ability ranking
- **Release Notes Extraction** — `release.yml` now extracts the current version's CHANGELOG section with `index()` instead of a regex, making version-header matching more robust

### Fixed

- **Fixture CI ImportError** — `run_fixture_tests.py` imports aligned with `update_free_models.py`'s new API (`MODEL_SCORES`, `rank_models`, `_parse_config`), fixing the `ImportError` in the `fixture-tests` CI job

### Removed

---

## [0.3.3](https://github.com/cgartlab/argus/compare/v0.3.2...v0.3.3) — 2026-08-21

> **一句话概括**：这是一次**CI 与可靠性修复**：fixture 测试接入 `ci.yml`（静态扫描器，无需 API key）、PR 自动化修复 checkout 顺序、修复 fallback 模型漂移与重复审查。**你不需要做任何事。**

### Changed

- **CI Fixture Tests** — Added static heuristic scanner run to `fixture-tests` job in `ci.yml`, validating actual review logic against expected finding counts (no API key required)
- **Release Notes** — `release.yml` now extracts only the current version's section from CHANGELOG instead of dumping the entire file
- **PR Automation** — `pr-automation.yml` now checks out the repo before running `gh` commands, fixing `fatal: not a git repository` error on every PR; `add-to-project` step made resilient with `continue-on-error`
- **AGENTS.md** — Updated STRUCTURE with manifest.yaml, CLAUDE.md, src/, config/, and new workflows; WHERE TO LOOK with free model config/updater/PR automation; COMMANDS with bump/test-fixtures-llm/package-skill

### Fixed

- **Fixture runner LLM mode** — Replaced invalid `--prompt-file` flag (non-existent in OpenCode CLI) with positional `message` argument in `run_fixture_tests.py`
- **Version sync** — Updated version references in AGENTS.md, SKILL.md, and manifest.yaml to match VERSION=0.3.3
- **Fallback model drift** — Synced hardcoded fallback queue in `action.yml` and `BUILTIN_FALLBACK` in `update_free_models.py` with `config/free-models.yml` (replaced delisted `laguna-s-2.1-free` with `muse-spark-1.2-contributor-free`)
- **SKILL.md syntax** — Fixed unclosed string literal in React `useState` example (`useState(')` → `useState('')`)
- **Review trigger** — Added `reopened` to `pull_request` trigger types in `review.yml` so reopened PRs get reviewed
- **Duplicate PR reviews** — Added stale review dismissal via GitHub API before fallback model retry in `action.yml`, preventing conflicting reviews on the same PR

---

## [0.3.2](https://github.com/cgartlab/argus/compare/v0.3.1...v0.3.2) — 2026-08-06

> **一句话概括**：这是一次**降级可靠性升级**：主模型限流/不可用时按能力排序自动重试降级队列（`fallback-models` 可自定义）；修复 PR 审查 6 小时超时（`@main` 引用旧 action 所致）。**你不需要做任何事——升级后自动生效。**

### Added

- **Fallback Model Queue** — When the primary model (`opencode/deepseek-v4-flash-free`) hits a 429 rate limit or is unavailable, the review automatically retries a fallback queue ordered by coding ability: `hy3-free` → `nemotron-3-ultra-free` → `laguna-s-2.1-free` → `nemotron-3.5-lightning-free` → `mimo-v2.5-free`. Configurable via `fallback-models` input in the composite action; the default queue is auto-refreshed from the live opencode model list every 12 hours (see `config/free-models.yml`).
- **Exit-Code Gate** — Fallback only triggers on non-zero exit code AND rate-limit text, preventing false fallback on successful runs whose output happens to contain line numbers like `:429`.

### Changed

- **Primary Model** — Reverted to `opencode/deepseek-v4-flash-free` (best coding ability). Fallback queue replaces the previous single-fallback design.
- **`_is_rate_limited` Regex** — Tightened to `429\s+(rate|too|exceeded|limit(?:ed|s)?)\b` with word-boundary anchors, eliminating false matches on ordinary prose (e.g. "limited to 50 findings") and review line numbers (e.g. `file.css:429`).
- **`_run_opencode`** — Now accepts the resolved `opencode` path as a parameter, removing redundant `_find_opencode()` probes during fallback queue iteration.
- **Composite Action** — `run_with_fallback_queue` bash function replaces the old `run_with_fallback`; `fallback-models` (comma-separated list) replaces `fallback-model` (single model).

### Fixed

- **PR Review Timeout (6h)** — Root cause: `review.yml` references the composite action at `@main`, so the review used the old action (no fallback queue) until the PR was merged. After merge, the fallback queue is active and prevents future 6-hour cancellations.
- **PR Description Drift** — Title and body updated to match the final design (deepseek primary + ordered fallback queue).
- **`.pyc` Leak** — `tools/__pycache__/run_fixture_tests.cpython-312.pyc` removed from VCS; `__pycache__/` and `*.pyc` added to `.gitignore`.
- **Verbose f-string** — `--verbose` output now correctly interpolates the model name instead of printing literal `(model: {model})`.
- **Fallback Exhaustion** — When all fallbacks are rate-limited, the primary model's output (and exit code) is preserved instead of returning the weakest fallback's result.
- **Dead Code** — Removed `__STATIC_FALLBACK__` sentinel in `_run_opencode`; redundant `opencode is None` guard returns `(1, "")` instead of `(0, "")` for consistency.

### Removed

---

## [0.3.1](https://github.com/cgartlab/argus/compare/v0.1.1...v0.3.1) — 2026-08-02

> **一句话概括**：这是一次**审查输出标准化与发布自动化**更新：固定反馈格式（summary + P0-P3 分组）、栈感知 API 审查、框架反模式库、自动 GitHub Release 与 skill 打包。**你不需要做任何事。**

### Added

- **Fixed Output Format** — Added standardized, readable feedback format with summary header, severity groups (P0-P3), and consistent issue block structure
- **Stack-Aware API Review** — New framework detection (React, Vue, Angular, Svelte, Astro) with official documentation references for accurate syntax validation
- **Framework Anti-Patterns Library** — Comprehensive pattern catalog (React, Vue, Svelte, Angular, Astro, JS/TS) with detection rules, examples, and copy-ready fixes
- **Release Automation** — New `.github/workflows/release.yml` triggered by `v*` tag pushes: validates versioning, builds packages, and publishes a GitHub Release with full archive and skill package
- **Skill Package** — New `make package-skill` target creates `dist/argus-skill-v{VERSION}.zip` containing `SKILL.md`, `AGENTS.md`, and `manifest.yaml` for agent skill distribution
- **GitHub Release Workflow** — Automated release publishing via `softprops/action-gh-release` with CHANGELOG body and artifact uploads

### Changed

- **SKILL.md** — Added Technology Stack Detection section, expanded Review Dimensions with 7th dimension (Framework API Usage), added Framework Anti-Patterns Library, updated Output Format with new fields
- **AGENTS.md** — Added OUTPUT FORMAT section; updated STRUCTURE with release workflow, WHERE TO LOOK with release automation entry, COMMANDS with `package-skill` target, and NOTES with release workflow documentation
- **README.md** — Updated project structure, version references, and added skill package documentation
- **CONTRIBUTING.md** — Updated version management section with bump-patch workflow and release process
- **DEVELOPMENT-GUIDE.md** — Updated version references, added release workflow documentation, and branch strategy for composite action
- **manifest.yaml** — New skill metadata file (name, version 0.3.1, capabilities, inputs/outputs)
- **Makefile** — Added `package-skill` target, updated `package` to depend on it, updated `clean`, and refreshed version comments
- **.gitignore** — Added `dist/` exclusion pattern

### Fixed

- **Version consistency** — All stale 0.2.0 references in documentation updated to 0.3.0/0.3.1
- **SKILL.md corruption** — Repaired escaped code fences and bash-quoting artifacts that broke YAML frontmatter and Markdown rendering

## [0.3.0] — 2026-06-25 _(无 tag)_

> **一句话概括**：这是一次**消费端可配置化 + 回归测试**更新：新增 `.argus.yml` 配置层（`docs/argus-config-schema.md`、`tools/load_config.py`）与 fixture 回归套件（8 组输入/期望对），CI 重构为 3 个 job。**现有消费者无需任何操作——未配置 `.argus.yml` 时行为不变，新字段均有安全默认值。**

### Added

#### Direction 2 — Consumer Configuration Layer
- `docs/argus-config-schema.md` — Full `.argus.yml` field reference with schema, examples, and migration guide
- `tools/load_config.py` — Consumer config loader: reads `.argus.yml` from consumer repo, deep-merges with built-in defaults, validates all fields, emits `GITHUB_ENV` variables for use in subsequent Action steps
- `.argus.yml` support in `action.yml` — new `config-path` input (default: `.argus.yml`); `load-config` step runs before prompt build; consumer token-prefix, ignore rules/paths, fail-on thresholds, and max-findings are all injected into the LLM prompt at review time

#### Direction 3 — Fixture-Based Regression Testing
- `tests/fixtures/` — Regression test suite with 4 categories and 8 fixture pairs (input + `.expected`):
  - `design-tokens/bad-hardcoded-colors.css` — bare `oklch`/`hex`/`rgb` in component rules → 5 P0 findings expected
  - `design-tokens/missing-dark-mode.css` — `:root` color tokens without `[data-theme="dark"]` override → 3 P0 findings expected
  - `accessibility/missing-aria.html` — icon buttons, missing `alt`, `<a>`-as-button → 4 P1 findings expected
  - `hardcoded-values/bad-magic-numbers.css` — magic `px` spacing/radii/font-size → 4 P1 findings expected
  - `css-quality/duplicate-rules.css` — duplicate property declarations in same selector → 2 P2 findings expected
- `tests/fixtures/README.md` — `.expected` format spec, how to add fixtures, CI integration notes
- `tools/run_fixture_tests.py` — Fixture runner: parses `.expected` files, invokes Argus (OpenCode CLI) or falls back to built-in static heuristic scanner (no API key required), validates severity counts (±1 tolerance), checks `must-not-flag` rules, supports `--verbose`, `--dry-run`, `--json`, `--category`, `--fixture` flags

#### CI & Tooling
- `ci.yml` — Restructured into 3 jobs:
  - `lint` — YAML syntax validation (now includes `action.yml`) + 14 required file checks
  - `validate-tools` — Python syntax check for all 4 tools + `load_config` default and example config validation
  - `fixture-tests` — `.expected` dry-run parse, fixture directory structure verification, artifact upload
- `action.yml` — New `fixture-mode` input; when `"true"` runs `run_fixture_tests.py` instead of `opencode github run` (for Argus repo's own CI)

### Changed
- `AGENTS.md` — Updated to v0.3.0; expanded `STRUCTURE` tree (added `docs/`, `tests/`, full `tools/` listing); updated `WHERE TO LOOK` table (+6 rows); added fixture anti-pattern; updated `COMMANDS` section
- `Makefile` — New targets: `test-fixtures` (static heuristic mode), `test-fixtures-llm` (full LLM mode), `test` (= validate + test-fixtures); `validate` expanded to 7 checks (now includes Python syntax and `load_config` validation); `bump-*` completion hint updated to `make test && make release`
- `VERSION` — 0.2.0 → 0.3.0

### Notes
- **Backwards compatible** — existing consumers with no `.argus.yml` continue to work unchanged; all new config fields use safe defaults
- **No API key required for CI** — `run_fixture_tests.py` falls back to static heuristic mode when OpenCode CLI is not installed, allowing fixture structure validation to run in any CI environment
- **Fixture count tolerance** — severity count assertions allow ±1 variance to keep the suite stable across minor LLM updates
- **Consumer config is additive** — hard rules (P0 color violations, a11y baseline) cannot be fully disabled via `.argus.yml`; severity can be downgraded but not silenced entirely for critical rules

---

## [0.2.0] — 2026-06-17 _(无 tag)_

> **一句话概括**：这是一次**架构升级**：引入可复用 composite action（`.github/actions/argus-review`）与 `argus-flash` GitHub App，规则改为运行时动态注入——argus 仓库的规则更新会自动同步到所有消费仓库。**你不需要做任何事；任意仓库安装 argus-flash App 并加一个 26 行 review.yml 即可获得自动设计审查。**

### Added
- `.github/actions/argus-review/action.yml` — Reusable composite action wrapping OpenCode CLI + dynamic rule injection
- Dynamic runtime rule loading: `action.yml` reads `AGENTS.md` + `SKILL.md` from the argus repo at review time and injects their contents into the LLM prompt
- `argus-flash` GitHub App (`github.com/apps/argus-flash`) — replaces the default OpenCode Agent App for PR review authentication
- Workflow `use_github_token: true` support — enables custom GitHub App token usage instead of OIDC exchange
- `ci.yml` — Rewritten with proper YAML syntax validation and required file checks
- `review.yml` — Simplified to call the composite action; token generation via `actions/create-github-app-token@v1`

### Changed
- `AGENTS.md` — Updated structure, added composite action and `argus-flash` App to WHERE TO LOOK, added dynamic rule injection convention
- `SKILL.md` — Updated to v0.2.0, added automated PR review workflow section
- `README.md` — Full rewrite with architecture diagram, cross-repo usage guide, and rule auto-sync explanation
- `DEVELOPMENT-GUIDE.md` — Updated for new architecture (composite action, argus-flash App, GitHub Actions integration)
- `CONTRIBUTING.md` — Added action.yml to pull request checklist
- `Makefile` — Added `.github/actions/argus-review/action.yml` existence check to validate target
- `VERSION` — 0.1.1-test-2 → 0.2.0

### Removed
- `opencode.jsonc` — No longer needed; permissions are managed via GitHub App token
- `.github/workflows/release.yml` — Release process moved to local `make release`
- Old workflow files: `argus-test.yml`, `flash-review.yml`, `opencode.yml`

### Notes
- Any repo can install `argus-flash` GitHub App and add a minimal 26-line review.yml to get automated design reviews
- Rules are auto-synced via the composite action's `@main` ref — update AGENTS.md/SKILL.md in the argus repo and all consumers pick up changes at the next review run
- For pinned version usage, use `@v0.2.0` instead of `@main`

## [0.1.1] — 2026-06-17

> **一句话概括**：这是一次**早期能力补充**：新增 `opencode.jsonc` 与 GitHub App PR 审查工作流；许可证从 MIT 迁移为 BSL 1.1（5 年后自动转 Apache 2.0）。**你不需要做任何事；若计划商业生产使用，请注意 BSL 1.1 条款。**

### Added
- `opencode.jsonc` — Argus agent configuration for OpenCode, auto-loads AGENTS.md + SKILL.md
- `.github/workflows/argus-review.yml` — GitHub App PR review workflow (triggers on PR open/sync/reopen)

### Changed
- `AGENTS.md` — refreshed format with init-deep template (STRUCTURE, WHERE TO LOOK, CONVENTIONS, ANTI-PATTERNS sections)
- `LICENSE` — migrated from MIT to BSL 1.1 for commercial readiness
- `VERSION` — 0.1.1

### Notes
- Argus-flash GitHub App (https://github.com/apps/argus-flash) now integrated for PR review
- BSL 1.1 allows research/fork but prohibits commercial production use; auto-converts to Apache 2.0 after 5 years

## [0.1.0] — 2026-06-13 _(无 tag)_

> **一句话概括**：**首个版本**：Argus 以文档驱动的设计审查 Agent 形态发布（AGENTS.md 硬规则 + SKILL.md 审查技能 + CI/发布工作流 + Makefile）。**这是初始发布，按 README/AGENTS.md 配置即可使用。**

### Added
- `AGENTS.md` — identity, hard rules, Kold-Argus workflow, review dimensions, severity guide
- `SKILL.md` — design review skill with issue format, workflow, non-blocking context
- `README.md` — project overview, usage, project structure
- `VERSION` — 0.1.0
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `DEVELOPMENT-GUIDE.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `LICENSE` — MIT (upgraded to BSL 1.1 in v0.1.1)
- `CLAUDE.md` — Claude Code compatibility bridge
- `Makefile` — check-version, validate, release, package
- `.github/workflows/ci.yml`
- `.github/workflows/release.yml`

### Changed
- AGENTS.md: Kold-Argus workflow formally documented; Argus connects to GitHub Argus App
- AGENTS.md: review dimensions table added
- SKILL.md: non-blocking context clarified

### Notes
- Kold and Argus are companion agents sharing the same design principles
- Argus is the review gate; Kold never bypasses the review
- All merge operations require human approval