# Argus

**代号 Argus** — 全视之眼，洞察每一个设计细节。

Code review agent for frontend design. Works in any agent framework.

---

## What is Argus?

Argus is a cross-platform AI coding agent specialized in **frontend design code review**. It runs independently in any agent framework (OpenClaw, Claude Code, OpenCode, Codex CLI, etc.) and can also be invoked by other agents as a sub-task specialist.

Argus's core strength: it sees what others miss — hardcoded color values that should use design tokens, spacing that breaks on mobile, missing accessibility attributes, semantic HTML violations, dark mode gaps.

---

## Core Capabilities

- **Design Token Audit** — detect bare `oklch()`, `#hex`, `rgb()` values that should be using CSS custom properties
- **Hardcoded Value Detection** — find magic numbers in spacing, font sizes, and radii that bypass the design system
- **Accessibility Review** — check for missing `aria-label`, `alt`, semantic tag violations, keyboard focus issues
- **Dark Mode Coverage** — verify that every color token has a corresponding dark mode override
- **CSS Consistency** — detect duplicate rules, invalid BEM, incorrect token declarations
- **Self-Evolving** — learns from every codebase it reviews; continuously refines its checklist based on real-world patterns

---

## How to Use

### Clone & Go

```bash
git clone https://github.com/cgartlab/argus.git
cd argus
```

Argus is framework-agnostic. Drop it into your agent's workspace and it will read `AGENTS.md` and load its skills on startup. No installation, no build step.

### For OpenClaw / Claude Code / OpenCode / Codex CLI

The repository contains a complete `AGENTS.md` and `skills/` directory. Your agent reads them automatically on every session start. You don't need to configure anything.

### For Other Frameworks

Reference `AGENTS.md` as your agent's behavioral foundation. Copy the `skills/` directory into your agent's equivalent skill directory. The SKILL.md format follows the [agentskills.io](https://agentskills.io) open standard and works across all major agent frameworks.

---

## Project Structure

```
argus/
├── AGENTS.md              # Core identity, rules, and working agreements
├── SKILL.md               # Primary skill: design code review
├── skills/
│   └── design-review/     # Code review skill with checklists
│       ├── SKILL.md
│       └── references/
│           ├── a11y-checklist.md
│           ├── darkmode-checklist.md
│           └── token-audit-guide.md
├── references/            # Extended review references
└── README.md
```

---

## Argus's Review Checklist

Every review covers these dimensions:

| Category | What to Check |
|---|---|
| **Design Tokens** | No bare oklch/hex/rgb; all colors/spacing via CSS custom properties |
| **Hardcoding** | No magic numbers; spacing and radii from design token scale |
| **Accessibility** | aria-label on icon buttons, alt on images, semantic HTML |
| **Dark Mode** | Every color token has `[data-theme="dark"]` override |
| **CSS Quality** | No duplicate rules, valid BEM, no empty catch blocks |
| **HTML Structure** | No anchor tags without href, no invalid id duplicates |

---

## Relationship with Kold

Argus and Kold are companion agents:

- **Kold** produces frontend code — components, pages, design systems
- **Argus** reviews frontend code — catches style issues, hardcoded values, a11y problems, design token violations

They share the same design principles and can work together in a Kold → Argus workflow, or independently.

---

## Version

`VERSION` file = source of truth. Increment after meaningful changes.

---

## License

MIT