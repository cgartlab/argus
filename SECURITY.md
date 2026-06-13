# Security Policy

## Supported Versions

| Version | Status |
|---|---|
| Latest main | Actively maintained |
| Previous minor | Security updates |
| Older versions | Not supported |

## Scope

Argus is a pure documentation repository. It contains only Markdown files that define agent review behavior. There is no server-side code, no database, no user input handling, and no third-party dependencies.

Potential risk areas:

- Malicious content in AGENTS.md / SKILL.md files that could mislead an agent (reviewed before merging)
- Third-party resources referenced in documentation (none currently)

## Reporting

If you discover a security issue, open a private security advisory via GitHub's Security Advisories feature. Do not open a public issue for security concerns.

## Safe Use

- Only load SKILL.md files from sources you trust
- Review AGENTS.md content before enabling it in your agent runtime
- Keep your agent runtime updated