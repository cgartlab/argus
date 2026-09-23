# Development Guide — Argus

Agent framework: OpenCode / Claude Code / Codex CLI / any agentskills.io-compatible runtime.

## Architecture

Argus has two operating modes:

### 1. Local Agent Mode

The agent's behavior is defined entirely by reading `AGENTS.md` and `SKILL.md` at startup. Pure documentation — no runtime code, no `npm install`, no build step.

### 2. Automated PR Review Mode (argus-flash App)

When a PR is opened in any repo that has the `argus-flash` GitHub App installed:

```
PR opened → GitHub Actions triggers review.yml
         → generate installation token via actions/create-github-app-token
         → call cgartlab/argus/.github/actions/argus-review@main
         → composite action:
             1. Configures git with the token
             2. Installs OpenCode CLI
             3. Reads AGENTS.md + SKILL.md at runtime, injects into PROMPT
             4. Runs `opencode github run`
             5. argus-flash bot comments review on the PR
```

The composite action dynamically loads rules from the argus repo at the referenced ref (`@main` or `@v0.4.1`). There is no hardcoded prompt — the review behavior is always driven by `AGENTS.md` + `SKILL.md`.

## AGENTS.md Structure

```
Identity
Core Capabilities
Hard Rules          <- invariants; severity and scope must not be weakened
Review Checklist    <- always run all checks
Output Format       <- format must be followed exactly
Version Management
Relationship with Kold
```

## SKILL.md Structure

```
YAML frontmatter (name, description, version)
Body:
  - Review Dimensions (with code examples of wrong/right)
  - Issue Severity Table
  - Output Format
  - Review Workflow
  - Non-Blocking Context
```

### Description Writing

The `description` field is a trigger mechanism, not a summary. It must contain 3+ real-world trigger phrases that a user would actually type.

```
description: "Use when reviewing frontend code for design quality,
  checking token usage, dark mode coverage, or accessibility.
  Trigger phrases: '帮我 review 这段代码'、'检查一下 hardcoded values'、'dark mode 有没有遗漏'"
```

## Severity Assignment

| Severity | When to use |
|---|---|
| P0 | Code will cause CI failure or silent runtime break |
| P1 | Accessibility violation or dark mode break |
| P2 | Hardcoded value, semantic violation, empty catch |
| P3 | Polish, cosmetic, code style |

Never downgrade a real P0 or P1 to P2/P3. False negatives damage trust more than false positives.

## Output Format

Each issue must report: severity, file:line, what was found, what was expected, which token should be used.

## Composite Action Maintenance

The composite action at `.github/actions/argus-review/action.yml` is the integration point for automated reviews. Key behaviors:

- **Dynamic rule injection**: `AGENTS.md` and `SKILL.md` are read via `cat ${{ github.action_path }}/../../../` and written to `$GITHUB_ENV` as `PROMPT`. This happens at runtime on every review run.
- **No hardcoded prompt**: The LLM prompt is entirely composed from the rule files. Updating AGENTS.md or SKILL.md changes review behavior for all consumer repos.
- **Token handling**: The `github-token` input is used for git operations and API calls. `actions/create-github-app-token@v1` is the recommended way to generate it.

### When to update action.yml

- Adding a new step (e.g., pre-processing files)
- Changing how PROMPT is constructed
- Updating the model name or CLI installation method
- Adding new inputs or changing defaults

### When NOT to update action.yml

- Adding/modifying review rules → edit `AGENTS.md` or `SKILL.md` only
- Adding trigger phrases → edit `SKILL.md` frontmatter only

## argus-flash App Integration

Any repo can use the composite action with the `argus-flash` GitHub App:

```yaml
- uses: cgartlab/argus/.github/actions/argus-review@main
  with:
    github-token: ${{ steps.app-token.outputs.token }}
```

Prerequisites:
1. Install `argus-flash` App at `github.com/apps/argus-flash` on the target repo
2. Add `ARGUS_FLASH_APP_ID` and `ARGUS_FLASH_PRIVATE_KEY` to repo Secrets
3. Create a minimal `review.yml` workflow

## Local Review CLI

Review files locally with the exact same rules as the GitHub App / composite
action — no GitHub, no workflow needed:

```bash
# Review a single file (uses the OpenCode CLI if installed, else the static
# heuristic scanner — no API key required for static mode)
python3 tools/argus_review.py src/components/Card.css

# Batch + stack-aware
python3 tools/argus_review.py --dir src/ --ignore '*.test.*' --stack antd5

# Structured report (feeds the future report-link / CI-comment service)
python3 tools/argus_review.py src/App.tsx --json review.json

# Or via make
make review FILE=src/components/Card.css
```

The CLI reuses the same prompt builder, model queue (config/free-models.yml),
and static scanner as the fixture runner, so local output matches what the
GitHub App produces. `--json` emits a structured findings report
(`total_issues`, `by_severity`, per-finding `severity`/`file`/`line`/
`description`/`found`/`expected`) ready for any consumer.

`tools/argus_report.py` turns that JSON into a single self-contained,
shareable HTML file (no server, no external assets):

```bash
python3 tools/argus_review.py src/ --json review.json
python3 tools/argus_report.py review.json --out report.html --title "Checkout UI"
# or: make report JSON=review.json
```

This is the artifact a future hosted report-link / Pro hook will serve.

### WCAG 2.2 Compliance Reports

`argus_report.py --wcag` annotates each a11y finding with its governing WCAG
2.2 success criterion (mapping: `config/wcag-mapping.yml`) and adds a
**WCAG 2.2 Compliance Summary** to the report — unique criteria covered,
A/AA counts, and per-criterion finding counts — for compliance handoff:

```bash
python3 tools/argus_review.py src/ --json review.json
python3 tools/argus_report.py review.json --wcag --out compliance.html
```

Findings that don't map to a criterion (e.g. bare colors) get no badge and no
summary section, so reports stay focused.

## GitLab Integration (Second Platform)

GitLab MRs get the same review via an include template — proving the
composite-action pattern is replicable outside GitHub:

```yaml
# .gitlab-ci.yml
include:
  - remote: https://raw.githubusercontent.com/cgartlab/argus/main/.gitlab/argus-review.yml
```

The job (`.gitlab/argus-review.yml`) clones `cgartlab/argus`, runs
`tools/argus_review.py --mode auto` on the MR's changed frontend files, and
posts the review as an MR note via the GitLab API. The runner logic lives in
`.gitlab/argus-review.sh` (testable with `ARGUS_DRY_RUN=1`).

Optional variables: `ARGUS_MR_TOKEN` (api-scope token for MR notes; falls
back to `CI_JOB_TOKEN` for same-project MRs), `ARGUS_MODE` (auto|static|llm —
complexity routing), `ARGUS_STACK`, `ARGUS_REF`. No API key is required in
auto/static mode (built-in heuristic scanner).

### Complexity Routing (cost control)

`tools/argus_review.py --mode auto` (default) routes each file by size:
files ≤ `--min-lines` (default 200) are reviewed by the static heuristic
scanner (fast, free), larger files by the LLM. `--mode static` / `--mode llm`
force either path. This is the roadmap's model-cost-routing control: small
diffs never pay model tokens.

## Branch Strategy for Composite Action

| Ref | Behavior | Recommendation |
|---|---|---|
| `@main` | Latest rules at time of review run | Development / internal repos |
| `@v0.4.1` | Pinned to a release | Production / external consumer repos |

## Cross-Platform Compatibility

Argus runs in any framework that reads Markdown instructions:

| Platform | Instruction File | Notes |
|---|---|---|
| OpenCode | `AGENTS.md` | Also loads `SKILL.md` via config |
| Claude Code | `CLAUDE.md`->`@AGENTS.md` | Bridge file |
| Codex CLI | `AGENTS.md` | Read automatically |
| GitHub Actions | `action.yml` + `opencode github run` | Automated mode |

## Version Bumping

```bash
make bump-patch   # e.g. 0.4.0 → 0.4.1
make test         # validate + fixture tests
make release      # release-gate → tag → push → triggers release workflow
```

The release workflow (`.github/workflows/release.yml`) automatically:
- Validates versioning consistency
- Builds `dist/argus-v{VERSION}.tar.gz` and `.zip` (full archive)
- Builds `dist/argus-skill-v{VERSION}.zip` (skill package)
- Creates a GitHub Release with all artifacts
- Publishes the skill package to SkillHub when `SKILLHUB_API_KEY` is configured
- Publishes the skill package to ClawHub when `CLAWHUB_TOKEN` secret + `CLAWHUB_OWNER` variable are set

## Multi-Registry Skill Publishing

Argus publishes the skill package to three registries. Each is opt-in and gated on its own secret/variable, so a missing registry never blocks a release.

| Registry | Trigger | Prep tool | Enable by |
|----------|---------|-----------|-----------|
| SkillHub | `release.yml` `skillhub` job (every `v*` tag) | `make prepare-skillhub` (`tools/publish_skillhub.py`) | `SKILLHUB_API_KEY` secret |
| ClawHub | `release.yml` `clawhub` job (every `v*` tag) | `make prepare-clawhub` (`tools/publish_clawhub.py`) | `CLAWHUB_TOKEN` secret (`clh_...`) + `CLAWHUB_OWNER` variable |
| skills.sh | `skills-sh-submit.yml` (manual dispatch, one-time) | — | `SKILLS_SH_GH_TOKEN` PAT (for the cross-org `vercel-labs/skills` issue) |

### ClawHub

- Publishes the skill **directory** (not the zip) via `clawhub skill publish dist/clawhub-argus --slug argus-design-review --name "Argus Design Review" --owner "$CLAWHUB_OWNER" --version "$VERSION"`.
- The ClawHub slug is the portable `name` frontmatter field (`argus-design-review`), distinct from the SkillHub-specific `slug` (`cgartlab-argus-design-review`). Final listing: `@<owner>/argus-design-review`.
- `clawhub login --token "$CLAWHUB_TOKEN"` is the headless/CI login; `clawhub whoami` verifies it.
- CLI ≥ 0.7.1 is required (v0.7.0 omitted `acceptLicenseTerms` and failed publish); the workflow installs `clawhub@latest`.

### skills.sh

- skills.sh does **not** auto-index. Run **skills.sh Index Request** from the Actions tab once after a release is public: it adds discovery topics to this repo and files an index-request issue in `vercel-labs/skills`.
- Filing an issue in another org needs a PAT (`SKILLS_SH_GH_TOKEN`, `repo` scope); the default `GITHUB_TOKEN` only covers same-repo topic edits. The workflow is idempotent — a re-run skips issue creation if one already exists.
- `npx skills add cgartlab/argus` works immediately (clones from GitHub); only `npx skills search` discovery requires the index.

## Webhook Forwarding (public API surface)

`tools/argus_webhook.py` POSTs a findings report (from the review CLI, custom
rules, or the quality engine) to any HTTP endpoint — Slack/Feishu incoming
webhooks, internal dashboards, or a future hosted API:

```bash
python3 tools/argus_review.py src/ --json review.json
python3 tools/argus_webhook.py send review.json --url https://hooks.example.com/argus \
  --token "$WEBHOOK_TOKEN"
# or: make webhook-send REPORT=review.json URL=... TOKEN=...
# --dry-run prints the request without sending (for testing)
```

Requests are `POST application/json` with an optional `Authorization: Bearer`
header. This is the roadmap's "public API / webhook" item — teams wire Argus
reports into their own systems without waiting for a hosted API.

## Quality Engine (precision / recall / F1 + gates)

The quality engine (`tools/eval_quality.py`) turns the fixture suite into
machine-readable quality metrics and a regression gate:

- **TP** = matched expected `[findings]` keywords across fixtures
- **FN** = unmatched expected `[findings]` keywords
- **FP** = `must-not-flag` violations plus every finding in a zero-expectation
  fixture (false-positives/ fixtures declare all-zero counts)
- **Precision** = TP / (TP + FP) · **Recall** = TP / (TP + FN) · **F1** = 2·P·R / (P + R)

```bash
make eval            # print the quality report (static heuristic mode)
make eval-gate       # enforce gates vs config/quality-baseline.json (CI)
make eval-baseline   # refresh the baseline after verified improvements
```

Gate policy: precision / recall / F1 must not drop more than 0.01 vs the
committed baseline (`config/quality-baseline.json`), and FP must never
increase. The gate runs in CI right after the fixture tests. Raise the
baseline only after an intentional, verified improvement.

## Adding a New Review Rule

1. Identify the review dimension (token, a11y, dark mode, etc.)
2. Assign severity with rationale
3. Add to SKILL.md under the correct dimension with wrong/right code examples
4. Add to review checklist in AGENTS.md
5. Verify action.yml still works (dynamic loading means no change needed)
6. Update VERSION if meaningful
