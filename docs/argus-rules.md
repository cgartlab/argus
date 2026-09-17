# Argus Custom Rules (Rule DSL)

Team-defined review rules that complement the built-in design-review
dimensions. Teams can flag their own conventions — a bespoke brand color
that must use a token, a banned pattern, a legacy helper — with copy-ready
fixes, without touching `AGENTS.md` / `SKILL.md`.

## Format

A rules file is validated against
[`config/argus-rules.schema.json`](../config/argus-rules.schema.json)
(JSON Schema draft-07; `python3 tools/argus_rules.py --validate` uses the
repo's zero-dependency engine).

Portable form (parses identically with PyYAML and the minimal fallback):

```yaml
version: "1"
rules:
  - "<id>|<severity>|<match>|<message>|<token>|<file-filter(s)>"
```

| Field | Meaning |
|---|---|
| `id` | kebab-case rule id |
| `severity` | `P0` \| `P1` \| `P2` \| `P3` |
| `match` | case-insensitive substring scanned against each code line |
| `message` | finding description (shown verbatim) |
| `token` | design token the fix should use (optional; empty = none) |
| `files` | comma-separated filename filters (optional; empty = all files) |

## Example

See [`config/argus-rules.example.yml`](../config/argus-rules.example.yml):

```yaml
version: "1"
rules:
  - "brand-primary-bare|P2|#f43f5e|Bare brand color - use var(--brand-primary)|--brand-primary|"
  - "no-inline-style|P2|style=|Inline style attribute - move to a class with design tokens||.html"
  - "legacy-space-mixin|P3|px-|Legacy spacing helper - use the space token scale||"
```

## Usage

```bash
# Validate your rules file
python3 tools/argus_rules.py --validate --rules argus-rules.yml

# Apply to files/dirs
python3 tools/argus_rules.py apply src/ --rules argus-rules.yml
python3 tools/argus_rules.py apply src/ --rules argus-rules.yml --json findings.json
```

Output follows the standard Argus format (`[P#] file:line - message` with
`Found:` / `Expected:` / `Token:` lines), so it composes with the review CLI
and the HTML report generator (`tools/argus_report.py`).

## Design notes

- Rules are **additive** — they never downgrade the built-in P0/P1 core
  rules (see `config/severity-matrix.yml`).
- Prefer a `severity` override in `.argus.yml` for adjusting built-in rule
  severities; custom rules are for team-specific conventions the built-ins
  don't model.
- Matching is a substring scan for predictability (no regex foot-guns in the
  first iteration); a regex engine is a future extension.