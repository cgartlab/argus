# Argus × men Integration

> **Status:** Optional | **Applies to:** Argus v0.4.0+

This document describes how the **men agent team** (cgartlab/men) can invoke Argus as an optional frontend design review capability. Everything described here is **additive** — Argus runs standalone in any agent framework or as the argus-flash GitHub App with no men dependency.

---

## 1. Overview

Argus is a self-contained frontend design code review agent. men is an optional orchestrating team that may route frontend design review tasks to Argus as one of its capabilities.

### Relationship

- **Argus** — the review engine. Detects design issues (hardcoded values, token violations, a11y gaps, dark mode breaks, stack-aware API misuse) and returns copy-ready fixes.
- **men** — the orchestrator. May call Argus when a task requires frontend design review.

### Independence Statement

- Argus never requires men to run.
- men never modifies Argus core rules, severity, or output format.
- Integration is **opt-in**: it is activated only by explicit invocation from a men context.
- All men-facing behavior is injectable and reversible — it never gates, alters, or replaces standalone review.

---

## 2. Detecting men Context

Argus detects whether it is running inside a men pipeline through three signals, checked in order:

| Signal | How | Effect |
|--------|-----|--------|
| CLI flag | `--men-context` | Enables men-compatible summary framing |
| Environment | `MEN_CONTEXT=1` | Same as the flag |
| Invocation context | men passes an envelope with `source: men` | Argus may include men metadata in its report |

> ⚠️ **Prompt-layer convention, not a CLI feature.** `--men-context`, `MEN_CONTEXT=1`, and `--events-json` are prompt-layer conventions: the OpenCode CLI itself does not recognize these custom flags. They take effect through the rules injected into the LLM context (AGENTS.md / SKILL.md) — the LLM reads the flag wording and adjusts its framing. In frameworks that load the skill package without flag support, the equivalent is to state `respond in men-context format` directly in the prompt; the CLI invocation examples in §3 / §6 are illustrative only.

**Detection rules:**

1. If no signal is present, Argus runs in **standalone mode** — canonical output, no men framing.
2. The flag and env var are equivalent; if both are present, the flag wins.
3. Detection only changes *framing* — it never changes severity rules, review dimensions, or fixture regression guarantees.

---

## 3. Routing & Invocation

men routes a frontend review task to Argus through an explicit intent gate.

### Intent Gate

men first classifies the task. Only frontend design review tasks are routed to Argus:

| Task type | Routed to |
|-----------|-----------|
| Frontend design review (tokens, a11y, dark mode, hardcoded values, stack API) | **Argus** |
| General web search | men's search agent |
| Content planning / decomposition | men's planning agent |

### Invocation Parameters

> **Note on the flags below:** `--men-context` / `--events-json` are prompt-layer conventions (see §2) — the OpenCode CLI does not recognize custom flags. If the framework loading the skill package does not support them, write `respond in men-context format` directly in the prompt instead.

```bash
# Minimal invocation (standalone-compatible)
opencode run argus -- "review src/components/Button.jsx"

# men-context invocation
opencode run argus --men-context -- \
  "design review for men: src/components/Button.jsx"

# With event logging
opencode run argus --men-context --events-json /tmp/argus-events.jsonl -- \
  "review PR #123 changed files"
```

| Parameter | Type | Purpose |
|-----------|------|---------|
| target | path or PR scope | Files to review; unresolved scope is reported, not guessed |
| `--men-context` | flag | Enables men-compatible summary framing |
| `--events-json` | path | Best-effort event logging (see §6) |

---

## 4. Output Contract for men

Argus keeps its canonical output format **verbatim** in every context. For men's four-part summary template, Argus maps its standard output as follows:

| Men template slot | Argus output | Example |
|-------------------|--------------|---------|
| **conclusion** | Summary header (totals, stack, documentation) | `## Argus Design Review Summary — Total Issues: 3 (P0: 1 | P1: 2 ...)` |
| **key issues** | Issue blocks grouped by severity | `[P0] src/app.css:12 — bare oklch in component rule` |
| **evidence** | Found / Expected snippets + Reference links | `Found: background: oklch(...)` / `Expected: var(--ds-color-surface)` |
| **open questions** | Unresolved items (see Confidence rule) | `unresolved: stack not detected for src/legacy/` |

### Machine-Readable Contract

- `[P#] file:line` prefixes are preserved **verbatim** — men parsers rely on this format.
- Copy-ready fix code blocks are **mandatory** for every issue.
- Token naming is always included.
- Empty severity groups output `✓ No issues found`.

### Confidence Rule

If the technology stack or target file is not clearly identifiable, Argus **does not guess**. The item is listed as **unresolved** in the open-questions section instead of being flagged with a fabricated severity. This mirrors the men team's "clarify before acting" rule.

---

## 5. Chi Judge Verification Interface

In a men pipeline, the chi judge agent may independently re-check Argus output before it is consumed.

### What chi verifies

| Check | Criterion |
|-------|-----------|
| Format compliance | `[P#] file:line` prefixes, severity groups P0 → P3, mandatory Fix blocks |
| Severity cross-check | No P0/P1 downgraded to P2/P3; a11y never demoted |
| Fix applicability | Fix code is copy-ready and references the correct token/API |
| Evidence quality | Found / Expected snippets match the reviewed files |

### Verdicts

| Verdict | Meaning |
|---------|---------|
| **PASS** | Output is format-compliant and severity-consistent |
| **REGRESSED** | Output deviates from the contract; routed back to Argus for correction |

Chi verification is **optional** — standalone runs skip it entirely.

---

## 6. Events & Learning

Argus supports best-effort event logging for men's learning loops.

### Usage

> Flags here are prompt-layer conventions (see §2 / §3): the CLI does not parse `--events-json`; it is recognized through the injected LLM rules, or equivalently by stating the request in the prompt.

```bash
opencode run argus --men-context --events-json /tmp/argus-events.jsonl -- \
  "design review: src/components/"
```

### Event shape

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `verify` |
| `subject` | string | `argus` |
| `outcome` | string | `PASS` / `FAIL` |
| `skill` | string | `argus-design-review` |
| `detail` | object | Severity totals, files reviewed, stack detected |

### Notes

- Event writing is **best-effort** — a write failure never blocks review delivery.
- Logged events can feed men's `learn.mjs` pipeline as training material for future review routing.
- No user code, tokens, or private content is sent to external systems.

---

## 7. Standalone vs Enhanced Behavior

| Behavior | Standalone (no men) | men-enhanced |
|----------|---------------------|--------------|
| Review dimensions | Full set | Full set (identical) |
| Severity rules | P0 → P3 unchanged | P0 → P3 unchanged |
| Output format | Canonical `[P#] file:line` | Canonical + four-part summary framing |
| Copy-ready fixes | Mandatory | Mandatory |
| Confidence rule | Applied | Applied |
| Chi judge re-check | Not run | Optional |
| Event logging | Off | Optional via `--events-json` |
| Dependencies | None | None added |

**The matrix is a strict superset** — men adds framing and logging, never removes or alters review behavior.

---

## 8. Versioning & Compatibility

### Protocol Version

men integrations should pin a **men-api-version** to prevent protocol drift:

| Element | Value |
|---------|-------|
| `men-api-version` | `1` |
| Applies to | Output contract (§4), detection signals (§2), event shape (§6) |
| Change policy | Breaking changes bump the version; additive changes do not |

### Compatibility Rules

- Argus core versions (e.g. v0.4.0) are independent of the men protocol version.
- A men integration that targets `men-api-version: 1` will keep working as long as Argus honors the contract in this document.
- If a future Argus release changes the men contract, the change is announced with a bumped `men-api-version` — consumers upgrade explicitly, never silently.
- The `--men-context` flag and `MEN_CONTEXT=1` env remain recognized across Argus releases unless the protocol version explicitly breaks them.

---

## Appendix: Quick Reference

| Topic | Section |
|-------|---------|
| Relationship & independence | §1 |
| Context detection | §2 |
| Routing & parameters | §3 |
| Output contract & Confidence rule | §4 |
| chi judge verification | §5 |
| Events & learning | §6 |
| Standalone vs enhanced | §7 |
| Versioning | §8 |