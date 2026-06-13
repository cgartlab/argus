# Kold

Code review agent for frontend design. Works in any agent framework.

## What is Argus?

Argus is a cross-platform AI coding agent specialized in frontend design code review. It runs independently in any agent framework — OpenClaw, Claude Code, OpenCode, Codex CLI, or any other — and can be invoked by other agents as a sub-task specialist.

Core strength: catches what others miss — hardcoded values, design token violations, a11y issues, dark mode gaps.

## Capabilities

- Design token audit (detect bare oklch/hex/rgb)
- Hardcoded value detection (magic numbers in spacing, radii)
- Accessibility review (aria-label, alt, semantic HTML)
- Dark mode coverage verification
- CSS consistency (duplicate rules, invalid BEM, empty catch blocks)
- HTML structure validation

## Quick Start

Clone and the agent reads AGENTS.md and SKILL.md automatically on startup:

```bash
git clone https://github.com/cgartlab/argus.git
cd argus
```

No installation, no build step.

## Project Structure

```
argus/
├── AGENTS.md              # Identity, hard rules, review checklist
├── SKILL.md               # Design review skill with severity guide
├── skills/                # Supplementary skills (TBD)
├── references/            # Deep reference docs (TBD)
├── README.md
├── VERSION                # Semantic version
├── LICENSE                # MIT
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── DEVELOPMENT-GUIDE.md
├── CHANGELOG.md
└── SECURITY.md
```

## Relationship with Kold

Argus and Kold are companion agents:

- **Kold** — produces frontend code
- **Argus** — reviews frontend code

They share design principles and can work in a Kold -> Argus workflow, or independently.

## License

MIT