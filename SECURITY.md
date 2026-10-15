# Security Policy

## Supported Versions

| Version | Status |
|---|---|
| Latest main | Actively maintained |
| Previous minor | Security updates |
| Older versions | Not supported |

## Scope

Argus is a docs-driven agent: its review behavior is defined by `AGENTS.md` + `SKILL.md`, which the composite action injects into an LLM prompt at runtime. It is **not** a documentation-only repository — it also ships a stdlib-only Python toolchain under `tools/`, a Node/Astro marketing site under `site/`, GitHub Actions workflows, and a `.gitlab/` runner script. There is no server-side service and no database.

Potential risk areas:

- **Prompt / rule injection** — malicious content in `AGENTS.md` / `SKILL.md` (or a consumer's `.argus/LESSON.md`) that could mislead the agent; reviewed before merging.
- **Supply chain** — the composite action installs the OpenCode CLI (`curl https://opencode.ai/install`); the site has third-party npm dependencies; Python tools make outbound HTTPS calls (OpenCode Zen model API).
- **Secrets** — `OPENCODE_API_KEY`, GitHub App credentials, and registry tokens are passed as Actions secrets; keys must never be committed (see README).
- **Untrusted consumer input** — `.argus.yml`, `.argus/LESSON.md`, and reviewed source code are consumer-controlled and fed to the model; treat them as untrusted data.

## Reporting

If you discover a security issue, open a private security advisory via GitHub's Security Advisories feature. Do not open a public issue for security concerns.

## Safe Use

- Only load SKILL.md files from sources you trust
- Review AGENTS.md content before enabling it in your agent runtime
- Keep your agent runtime updated