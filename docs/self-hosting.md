# Argus Self-Hosting & Private Deployment

> For teams whose policy requires code and review traffic to stay inside their
> own infrastructure (regulated industries, proprietary codebases). Argus
> supports two self-hosting surfaces; use one or both.

## What "self-hosted" means for Argus

Argus is a **documentation-defined agent** (behavior lives in `AGENTS.md` +
`SKILL.md`) driven by an LLM. There is no Argus-owned server that code passes
through in the default setup — reviews run inside your CI (GitHub Actions or
GitLab) and call a model endpoint. "Self-hosting" therefore means:

1. **Run the review on your own runner** — code never leaves your infrastructure.
2. **Point inference at a private model endpoint** — review content never
   leaves your network.

## Surface 1 — Self-hosted runner

### GitHub Actions self-hosted runner

1. Add a self-hosted runner to the repo/org (Settings → Actions → Runners).
2. Target it from `review.yml`:

   ```yaml
   name: Review
   on: [pull_request]

   jobs:
     argus-review:
       runs-on: [self-hosted, linux, x64]
       steps:
         - uses: actions/create-github-app-token@v1
           id: app-token
           with:
             app-id: ${{ secrets.ARGUS_FLASH_APP_ID }}
             private-key: ${{ secrets.ARGUS_FLASH_PRIVATE_KEY }}
         - uses: cgartlab/argus/.github/actions/argus-review@main
           with:
             github-token: ${{ steps.app-token.outputs.token }}
             api-key: ${{ secrets.OPENCODE_API_KEY }}   # or a private endpoint key
   ```

   The composite action (rule injection + OpenCode CLI + config loading) runs
   entirely on the runner. The token pattern is the same as the cloud setup.

### GitLab self-hosted runner

Use the GitLab template (`.gitlab/argus-review.yml`) on a self-hosted GitLab
runner; the runner script (`.gitlab/argus-review.sh`) runs
`tools/argus_review.py` locally and posts the MR note via the GitLab API.

## Surface 2 — Private model endpoint

By default the action uses the free-model queue from
`config/free-models.yml` against the OpenCode Zen API. To keep inference
in-network, point Argus at a private OpenAI-compatible endpoint (e.g. vLLM,
Ollama, an internal gateway):

```yaml
# review.yml — private endpoint
- uses: cgartlab/argus/.github/actions/argus-review@main
  with:
    github-token: ${{ steps.app-token.outputs.token }}
    model: "my-internal-llama-70b"          # model name your endpoint exposes
    api-key: ${{ secrets.INTERNAL_MODEL_KEY }}
```

Environment / CLI equivalents:

```bash
# local CLI against a private endpoint
OPENCODE_API_KEY=... python3 tools/argus_review.py src/ --model my-internal-llama-70b
```

> **Note:** the free-model queue (`config/free-models.yml`) is a public list —
> self-hosted deployments usually configure an explicit private model instead.

## Data handling summary

| Data | Default (cloud) | Self-hosted |
|---|---|---|
| Reviewed code | Sent to the chosen model endpoint | Stays on your runner / network |
| Rules (`AGENTS.md` + `SKILL.md`) | Injected at runtime | Same — read from the Argus checkout |
| Findings | Written back to the PR | Same — written back to the PR |
| Training | Code is never used for training (no data retention) | N/A — nothing leaves your network |

## Security notes

- **Least-privilege tokens**: the app token has only the permissions the action
  needs (`contents: read`, `pull_requests: write`, `issues: write`, `checks: write`).
- **No secrets in `.argus.yml`**: the config file is committed; keys go in CI
  secrets / env only.
- **Private runner hygiene**: keep the runner patched; scope it to the repos
  that need Argus.
- **Model endpoint access**: prefer mTLS or a network-isolated endpoint for the
  inference traffic.

## Limitations

- Self-hosting does **not** change the review rules themselves — the same
  fixture/quality gates (`make test`, `make eval-gate`) apply.
- WCAG compliance reports (`argus_report.py --wcag`) and the quality engine run
  locally, so they work fully offline once a model endpoint is configured.
- The GitHub App installation token is still minted by GitHub (identity), but
  review traffic and inference stay in-network.