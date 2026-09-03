#!/usr/bin/env python3
"""
run_fixture_tests.py — Argus Fixture Regression Test Runner

Validates that Argus review rules produce the expected findings for each
fixture in tests/fixtures/. Operates in heuristic mode: checks severity
counts and keyword presence, not exact line numbers.

Also reports a run-level FalsePositiveRate (FP / (FP + TP)) from
must-not-flag violations and matched expected findings — informational
output, not a gate (static mode enforces must-not-flag as errors, so a
passing static run always has FP = 0).

Usage:
  python3 tools/run_fixture_tests.py                             # all fixtures
  python3 tools/run_fixture_tests.py --category design-tokens   # one category
  python3 tools/run_fixture_tests.py --fixture tests/fixtures/design-tokens/bad-hardcoded-colors.css
  python3 tools/run_fixture_tests.py --verbose                   # show full detail
  python3 tools/run_fixture_tests.py --dry-run                   # parse only, no Argus invocation

Exit codes:
  0 — all fixtures passed
  1 — one or more fixtures failed
  2 — usage / configuration error
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
SKILL_MD = REPO_ROOT / "SKILL.md"

SEVERITY_ORDER = ["P0", "P1", "P2", "P3"]

# Colour codes (disabled when not a TTY)
_USE_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if not _USE_COLOUR:
        return text
    codes = {"green": "32", "red": "31", "yellow": "33", "cyan": "36", "bold": "1", "reset": "0"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FindingSpec:
    severity: str          # P0 / P1 / P2 / P3
    line_hint: str         # optional substring for file:line reference
    keyword: str           # substring in issue description (case-insensitive)


@dataclass
class ExpectedFile:
    path: Path
    fixture_path: Path
    description: str
    findings: list[FindingSpec]
    must_not_flag: list[str]
    counts: dict[str, int]   # {"P0": 5, "P1": 0, ...}


@dataclass
class FixtureResult:
    fixture: Path
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    argus_output: str = ""
    skipped: bool = False
    skip_reason: str = ""
    fp_count: int = 0        # must-not-flag items wrongly flagged (false positives)
    tp_count: int = 0        # expected finding keywords present in output (true positives)


# ── Parser for .expected files ────────────────────────────────────────────────

def parse_expected(expected_path: Path) -> ExpectedFile:
    """Parse a .expected file into an ExpectedFile dataclass."""
    text = expected_path.read_text(encoding="utf-8")

    # Strip comment lines for configparser sections, but keep them for context
    # We use a manual section parser to support our custom format.

    sections: dict[str, list[str]] = {}
    current: Optional[str] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    # [meta]
    meta: dict[str, str] = {}
    for entry in sections.get("meta", []):
        if "=" in entry:
            k, _, v = entry.partition("=")
            meta[k.strip()] = v.strip()

    fixture_rel = meta.get("fixture", "")
    description = meta.get("description", "")
    fixture_path = REPO_ROOT / "tests" / "fixtures" / fixture_rel if fixture_rel else expected_path.with_suffix("")

    # [findings]
    findings: list[FindingSpec] = []
    for entry in sections.get("findings", []):
        parts = [p.strip() for p in entry.split("|")]
        if len(parts) != 3:
            raise ValueError(f"Malformed finding line in {expected_path}: '{entry}' — expected 'SEVERITY | LINE_HINT | KEYWORD'")
        severity, line_hint, keyword = parts
        if severity not in SEVERITY_ORDER:
            raise ValueError(f"Unknown severity '{severity}' in {expected_path}")
        findings.append(FindingSpec(severity=severity, line_hint=line_hint, keyword=keyword))

    # [must-not-flag]
    must_not_flag = sections.get("must-not-flag", [])

    # [counts]
    counts: dict[str, int] = {}
    for entry in sections.get("counts", []):
        if "=" in entry:
            k, _, v = entry.partition("=")
            k, v = k.strip(), v.strip()
            if k in SEVERITY_ORDER:
                try:
                    counts[k] = int(v)
                except ValueError:
                    raise ValueError(f"Non-integer count for {k} in {expected_path}: '{v}'")

    return ExpectedFile(
        path=expected_path,
        fixture_path=fixture_path,
        description=description,
        findings=findings,
        must_not_flag=must_not_flag,
        counts=counts,
    )


# ── Argus invocation (heuristic/static mode) ──────────────────────────────────

# Fallback queue is read from config/free-models.yml (auto-refreshed weekly via reviewable PR
# by the update-free-models workflow). These are last-resort built-in defaults
# used only when the config file is missing or unparseable.
# Single source of truth for the built-in queue lives in
# tools/update_free_models.py (MODEL_SCORES, rank_models, _parse_config) —
# imported here to prevent drift between the two Python tools.
from update_free_models import MODEL_SCORES as _MODEL_SCORES
from update_free_models import rank_models as _rank_models
from update_free_models import _parse_config as _parse_free_models_config
from update_free_models import BUILTIN_PRIMARY as _BUILTIN_PRIMARY

# Last-resort built-in queue = known free models ranked by coding ability,
# excluding the built-in primary (the primary is never part of the fallback queue).
BUILTIN_FALLBACK_MODELS = ",".join(
    m for m in _rank_models(list(_MODEL_SCORES.keys())) if m != _BUILTIN_PRIMARY
)


def default_fallback_models() -> str:
    """Return the fallback queue from config/free-models.yml (or built-in defaults).

    Mirrors the composite action's runtime resolution so local LLM-mode
    fixture runs use exactly the same queue as cloud reviews.
    """
    config_path = REPO_ROOT / "config" / "free-models.yml"
    data = _parse_free_models_config(config_path)
    val = data.get("fallback_models", "")
    return val if val else BUILTIN_FALLBACK_MODELS


def default_primary_model() -> str:
    """Return the primary model from config/free-models.yml (or built-in default).

    Mirrors the composite action's runtime resolution so local LLM-mode
    fixture runs use the same primary as cloud reviews.
    """
    config_path = REPO_ROOT / "config" / "free-models.yml"
    data = _parse_free_models_config(config_path)
    val = data.get("primary", "")
    return val if val else _BUILTIN_PRIMARY

def _detect_design_system(package_json: Path) -> str:
    """Detect the design system from package.json (mirrors action.yml detect step).

    Returns one of: antd5 / antd4-unsupported / material3 / polaris / custom.
    Missing or invalid package.json yields 'custom'.
    """
    try:
        data = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "custom"
    deps = {}
    deps.update(data.get("dependencies", {}))
    deps.update(data.get("devDependencies", {}))
    if "antd" in deps:
        major = deps["antd"].lstrip("^~").split(".")[0]
        try:
            return "antd5" if int(major) >= 5 else "antd4-unsupported"
        except ValueError:
            return "antd5"
    elif "@mui/material" in deps:
        return "material3"
    elif "@shopify/polaris" in deps:
        return "polaris"
    return "custom"


def _load_token_section(token_system: str) -> str:
    """Return the design-token prompt section for a system, or '' when none.

    'auto' triggers package.json detection at REPO_ROOT. Missing/unreadable
    .github/tokens/<system>.json files silently yield '' (no injection),
    matching the composite action's degrade-without-error behavior.
    """
    system = token_system
    if system == "auto":
        system = _detect_design_system(REPO_ROOT / "package.json")

    if system == "antd4-unsupported":
        return (
            "## Design System: antd v4 (unsupported)\n"
            "antd v4 uses Less variables, not CSS custom properties.\n"
            "Configure design-system: custom in .argus.yml, or migrate to antd v5.\n"
        )
    if system == "custom":
        return ""

    token_file = REPO_ROOT / ".github" / "tokens" / f"{system}.json"
    if not token_file.exists():
        return ""
    try:
        tokens = token_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    if not tokens.strip():
        return ""
    return (
        f"## Design System: {system}\n"
        "Reference these design tokens when suggesting fixes:\n"
        f"{tokens.strip()}\n"
    )


def build_argus_prompt(fixture_path: Path, token_system: str = "auto") -> str:
    """Build the same prompt the composite action uses, injecting AGENTS.md + SKILL.md."""
    agents = AGENTS_MD.read_text(encoding="utf-8")
    skill = SKILL_MD.read_text(encoding="utf-8")
    code = fixture_path.read_text(encoding="utf-8")
    rel = fixture_path.relative_to(REPO_ROOT)

    token_section = _load_token_section(token_system)
    token_block = f"{token_section}\n" if token_section else ""

    return textwrap.dedent(f"""\
        You are Argus, a frontend design code review agent.

        ## Argus Hard Rules
        {agents}

        {token_block}## Review Dimensions
        {skill}

        ## File to Review
        File: {rel}

        ```
        {code}
        ```

        Review this file. Output findings grouped by severity P0 → P1 → P2 → P3.
        For every issue show: [P#] file:line — description / Found: / Expected:
        Only output findings. No preamble, no summary.
    """)


def _run_opencode(opencode: str, model: str, prompt_file: Path, verbose: bool) -> tuple[int, str]:
    """Run opencode CLI with a given model and prompt file.
    Returns (returncode, raw_output).

    ``opencode`` is the resolved CLI path; the caller owns the
    is-None check (see run_argus_on_fixture).

    The prompt is read from the file and passed as the positional
    ``message`` argument to ``opencode run`` (the CLI has no
    ``--prompt-file`` flag).
    """
    try:
        prompt_text = prompt_file.read_text(encoding="utf-8")
        result = subprocess.run(
            [opencode, "run", "--model", model, prompt_text],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        output = result.stdout + result.stderr
        if verbose:
            print(f"\n{_c('cyan', f'── Argus raw output (model: {model}) ──')}\n"
                  f"{output}\n{_c('cyan', '──────────────────────────────────────')}")
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 1, "[TIMEOUT] Argus did not respond within 120 seconds."
    except Exception as exc:
        return 1, f"[ERROR] Failed to run OpenCode: {exc}"


def run_argus_on_fixture(fixture_path: Path, model: str, verbose: bool,
                         fallback_models: str | None = None,
                         token_system: str = "auto") -> str:
    """
    Invoke Argus (via OpenCode CLI) on a single fixture file.
    Returns the raw text output.
    Falls back to a static heuristic scan if OpenCode is not installed.

    If fallback_models is provided (comma-separated list) and the primary
    model fails (non-zero exit code) AND the output indicates a rate-limit
    error, retries each fallback model in order until one succeeds or all
    are exhausted.
    """
    opencode = _find_opencode()
    if opencode is None:
        return _static_heuristic_scan(fixture_path)

    prompt = build_argus_prompt(fixture_path, token_system=token_system)
    prompt_file = fixture_path.parent / f".argus_prompt_{fixture_path.stem}.tmp"
    try:
        prompt_file.write_text(prompt, encoding="utf-8")

        # Try primary model
        exit_code, output = _run_opencode(opencode, model, prompt_file, verbose)
        primary_output = output  # preserve for fallback exhaustion

        def _is_retryable(text: str) -> bool:
            """Check if output indicates a retryable condition: rate limit or model unavailable."""
            return bool(re.search(
                r"429\s+(rate|too|exceeded|limit(?:ed|s)?)\b|rate\s*limit|too many requests|"
                r"model\s+not\s+found|no\s+such\s+model|model\s+does\s+not\s+exist|"
                r"upstream request failed|endpoint is unavailable|unavailable",
                text, re.IGNORECASE,
            ))

        # Retry with fallback queue: gate on non-zero exit code AND retryable text.
        # NOTE: verified that the opencode CLI exits non-zero (1) on model errors,
        # so a rate limit never produces exit 0 — the gate is reliable.
        if (fallback_models and exit_code != 0 and
                _is_retryable(output)):
            queue = [m.strip() for m in fallback_models.split(",") if m.strip()]
            for fb_model in queue:
                print(f"  {_c('yellow', '⚠')} Primary model '{model}' rate-limited or unavailable, "
                      f"retrying with fallback '{fb_model}' ...", flush=True)
                exit_code, output = _run_opencode(opencode, fb_model, prompt_file, verbose)
                if exit_code == 0:
                    return output  # success
                if _is_retryable(output):
                    print(f"  {_c('yellow', '⚠')} Fallback '{fb_model}' also retryable, "
                          f"trying next ...", flush=True)
                else:
                    print(f"  {_c('yellow', '⚠')} Fallback '{fb_model}' failed (non-retryable), "
                          f"trying next ...", flush=True)
            # All fallbacks exhausted — return primary output
            output = primary_output

        return output
    finally:
        if prompt_file.exists():
            prompt_file.unlink()


def _find_opencode() -> Optional[str]:
    """Return path to OpenCode CLI, or None if not installed."""
    for candidate in [os.path.expanduser("~/.opencode/bin/opencode"), "opencode"]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, timeout=5)
            return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def _auth_preflight(model: str) -> None:
    """Non-blocking hint when an opencode/ provider model is selected without
    an OPENCODE_API_KEY (local LLM mode only; static heuristic mode needs none)."""
    if not model.startswith("opencode/"):
        return
    if os.environ.get("OPENCODE_API_KEY"):
        return
    if _find_opencode() is None:
        return  # static heuristic mode — no auth required
    print(_c("yellow", "⚠ No OPENCODE_API_KEY set for opencode/ provider — runs may fail."))
    print(_c("yellow", "  Fix: run `opencode auth login` (local login) or set OPENCODE_API_KEY."))
    print(_c("yellow", "  Docs: https://opencode.ai/auth"))


def _static_heuristic_scan(fixture_path: Path) -> str:
    """
    Lightweight rule-based scan used when OpenCode is not available (CI without API keys).
    Detects the most common violations so fixture count assertions can still be verified.
    Returns output in the standard Argus format.
    """
    suffix = fixture_path.suffix.lower()
    text = fixture_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: list[str] = []

    def emit(severity: str, lineno: int, issue: str, found: str, expected: str) -> None:
        abs_fp = fixture_path.resolve()
        try:
            rel = abs_fp.relative_to(REPO_ROOT)
        except ValueError:
            rel = abs_fp
        findings.append(
            f"[{severity}] {rel}:{lineno} — {issue}\n"
            f"  Found:    {found}\n"
            f"  Expected: {expected}"
        )

    if suffix == ".css":
        # Track brace depth to detect :root scope reliably
        brace_depth = 0
        root_start_depth = -1   # brace depth when :root opened
        in_root = False
        selector_props: dict[str, int] = {}  # prop → first seen lineno
        current_selector = ""
        non_blocking_reset = False   # True inside a universal-selector (reset) block

        # Dark-mode coverage: collect :root color tokens and dark overrides
        root_color_tokens: set[str] = set()
        dark_override_tokens: set[str] = set()
        root_color_token_lines: dict[str, int] = {}  # token → first line
        in_dark_block = False
        dark_depth = -1

        for i, raw in enumerate(lines, start=1):
            stripped = raw.strip()

            # Skip pure comment lines for most checks
            is_comment = stripped.startswith("/*") or stripped.startswith("//")

            # Count brace opens/closes on this line
            opens = raw.count("{")
            closes = raw.count("}")

            # Detect :root opening
            if re.search(r":root\s*\{", raw) and not is_comment:
                root_start_depth = brace_depth
                in_root = True

            # Detect [data-theme="dark"] opening
            if re.search(r'\[data-theme=["\']dark["\']\]\s*\{', raw) and not is_comment:
                in_dark_block = True
                dark_depth = brace_depth

            brace_depth += opens - closes

            # Close :root when its brace depth returns to root_start_depth
            if in_root and brace_depth <= root_start_depth and root_start_depth >= 0:
                in_root = False
                root_start_depth = -1

            # Close dark block
            if in_dark_block and brace_depth <= dark_depth and dark_depth >= 0:
                in_dark_block = False
                dark_depth = -1

            # Collect :root color token declarations
            if in_root and not is_comment:
                m = re.match(r"^\s*(--[\w-]+)\s*:\s*(oklch|#[0-9a-fA-F]|rgb|rgba|hsl)", stripped)
                if m:
                    tok = m.group(1)
                    root_color_tokens.add(tok)
                    root_color_token_lines.setdefault(tok, i)

            # Collect dark-mode token overrides
            if in_dark_block and not is_comment:
                m = re.match(r"^\s*(--[\w-]+)\s*:", stripped)
                if m:
                    dark_override_tokens.add(m.group(1))

            # Selector detection (reset duplicate tracking per block).
            # `*` is included so universal-selector resets (`* { ... }`,
            # `*::before { ... }`, `.reset * { ... }`) reset tracking AND mark
            # a non-blocking context: third-party reset boilerplate must not be
            # flagged P2 (AGENTS.md: "don't flag boilerplate, third-party resets").
            if re.match(r"^[.#\w\[\]:,\s>~+*-]+\{", stripped) and not is_comment:
                if ":root" not in stripped and "data-theme" not in stripped:
                    current_selector = stripped
                    selector_props = {}
                    non_blocking_reset = "*" in current_selector

            # Bare color values in component rules (not :root, not dark-block)
            if not in_root and not in_dark_block and not is_comment:
                prop_name = stripped.split(":", 1)[0].strip()
                # Shadow colors (box-shadow / text-shadow) are legitimate values,
                # not color violations — skip them to avoid false positives.
                is_shadow_color = prop_name in ("box-shadow", "text-shadow")
                for pattern, label in [
                    (r"\boklch\(", "bare oklch"),
                    (r"(?<!['\"])#[0-9a-fA-F]{3,8}\b", "bare hex"),
                    (r"\brgb\(", "bare rgb"),
                    (r"\brgba\(", "bare rgba"),
                    (r"\bhsl\(", "bare hsl"),
                ]:
                    m = re.search(pattern, stripped)
                    if m and not is_shadow_color and "var(--" not in stripped and "--" not in stripped.split(":")[0]:
                        value = stripped.split(":", 1)[-1].strip().rstrip(";").split("/*")[0].strip()
                        emit("P0", i, f"Bare color value ({label}) — use a design token",
                             value, "var(--ds-color-*)")

            # Hardcoded spacing / radii / font-size (non-zero px values)
            if not in_root and not in_dark_block and not is_comment:
                # Match longhand and shorthand spacing properties
                for prop in [
                    "padding", "margin", "margin-top", "margin-right",
                    "margin-bottom", "margin-left", "padding-top", "padding-right",
                    "padding-bottom", "padding-left", "gap", "row-gap", "column-gap",
                    "border-radius", "font-size", "line-height",
                ]:
                    m = re.match(rf"^\s*{re.escape(prop)}\s*:\s*(\d+px)", stripped)
                    if m and m.group(1) != "0px":
                        emit("P1", i, f"Hardcoded {prop} — use a design token",
                             m.group(1), "var(--ds-*)")

            # Duplicate property detection (within same selector block).
            # Suppressed inside universal-selector (reset) blocks: resets are
            # non-blocking context and must not produce P2 noise.
            prop_match = re.match(r"^\s*([\w-]+)\s*:", stripped)
            if prop_match and not is_comment and "{" not in stripped and "}" not in stripped:
                prop = prop_match.group(1)
                if not prop.startswith("--"):  # ignore custom property declarations
                    if prop in selector_props and not non_blocking_reset:
                        emit("P2", i, f"Duplicate property '{prop}' in selector",
                             stripped.strip(), f"Remove duplicate; keep one '{prop}' declaration")
                    else:
                        selector_props[prop] = i

        # Post-pass: emit P0 for :root color tokens missing dark override
        missing_dark = root_color_tokens - dark_override_tokens
        for tok in sorted(missing_dark):
            line = root_color_token_lines.get(tok, 0)
            emit("P0", line,
                 f"Color token '{tok}' has no [data-theme=\"dark\"] override — silent dark mode break",
                 f"{tok}: <value>",
                 f'[data-theme="dark"] {{ {tok}: <dark-value>; }}')

    elif suffix in (".html", ".htm"):
        for i, raw in enumerate(lines, start=1):
            stripped = raw.strip()

            # Icon-only buttons (button tag with no aria-label and no visible text)
            if re.search(r"<button[^>]*>", stripped, re.I):
                if "aria-label" not in stripped.lower():
                    # Check if next few lines have SVG but no text
                    block = " ".join(lines[i-1:i+3])
                    if "<svg" in block.lower() and not re.search(r">\s*\w", stripped):
                        emit("P1", i, "Icon-only button missing aria-label",
                             stripped, '<button aria-label="Describe action">')

            # img without alt
            if re.search(r"<img\b[^>]*>", stripped, re.I):
                if "alt=" not in stripped.lower():
                    emit("P1", i, "img element missing alt attribute",
                         stripped, '<img src="..." alt="Describe image">')

            # <a> used as button (no href, has onclick)
            if re.search(r"<a\b[^>]*onclick", stripped, re.I):
                if "href=" not in stripped.lower():
                    emit("P1", i, "<a> without href used as interactive element — use <button> instead",
                         stripped, '<button class="...">...</button>')

    return "\n".join(findings) if findings else "(no findings)"


# ── Result validation ─────────────────────────────────────────────────────────

def validate_output(expected: ExpectedFile, argus_output: str, tolerance: int = 1) -> FixtureResult:
    """Compare Argus output against the .expected specification.

    ``tolerance`` is the allowed count deviation per severity: static
    heuristic mode is deterministic and passes ``tolerance=0`` (exact match),
    while LLM mode keeps the historical ±1 for model variance.
    """
    errors: list[str] = []
    warnings: list[str] = []
    output_lower = argus_output.lower()

    # 1. Count findings per severity in actual output
    actual_counts: dict[str, int] = {s: 0 for s in SEVERITY_ORDER}
    for line in argus_output.splitlines():
        for sev in SEVERITY_ORDER:
            if re.search(rf"\[{sev}\]", line):
                actual_counts[sev] += 1

    # 2. Verify severity counts (static heuristic mode → exact; LLM ±1)
    for sev, expected_count in expected.counts.items():
        actual = actual_counts.get(sev, 0)
        if abs(actual - expected_count) > tolerance:
            errors.append(
                f"Count mismatch [{sev}]: expected {expected_count}, got {actual} "
                f"(tolerance ±{tolerance})"
            )
        elif actual != expected_count:
            warnings.append(
                f"Count [{sev}]: expected {expected_count}, got {actual} (within tolerance)"
            )

    # 3. Check that each required keyword appears somewhere in the output
    for spec in expected.findings:
        if spec.keyword and spec.keyword.lower() not in output_lower:
            errors.append(
                f"Required keyword not found in [{spec.severity}] findings: '{spec.keyword}'"
            )

    # 3b. Verify line_hint substrings (README: "substring that must appear in
    #     the file:line reference"). Empty hints are skipped; a hint that
    #     matches no finding line of its severity is advisory-only (warn), since
    #     LLM output may reword the issue description.
    for spec in expected.findings:
        if not spec.line_hint:
            continue
        finding_lines = [
            l for l in argus_output.splitlines()
            if re.search(rf"\[{spec.severity}\]", l)
        ]
        if not any(spec.line_hint in l for l in finding_lines):
            warnings.append(
                f"line_hint '{spec.line_hint}' not found in any [{spec.severity}] finding line"
            )

    # 4. Check must-not-flag items — these should not appear as flagged tokens.
    #    Each violation counts as a false positive (fp_count) for the run-level
    #    FalsePositiveRate metric (informational, not a gate).
    flagged_lines = [l for l in argus_output.splitlines() if re.search(r"\[P\d\]", l)]
    flagged_text = "\n".join(flagged_lines).lower()
    fp_count = 0
    for forbidden in expected.must_not_flag:
        if forbidden.lower() in flagged_text:
            fp_count += 1
            errors.append(f"False positive: '{forbidden}' was flagged but must NOT be")

    # 5. True positives: how many expected finding keywords actually appeared.
    #    Paired with fp_count for the run-level FalsePositiveRate metric.
    tp_count = 0
    for spec in expected.findings:
        if spec.keyword and spec.keyword.lower() in output_lower:
            tp_count += 1

    passed = len(errors) == 0
    return FixtureResult(
        fixture=expected.fixture_path,
        passed=passed,
        errors=errors,
        warnings=warnings,
        argus_output=argus_output,
        fp_count=fp_count,
        tp_count=tp_count,
    )


# ── Discovery ────────────────────────────────────────────────────────────────

def discover_fixtures(
    category: Optional[str] = None,
    single_fixture: Optional[Path] = None,
) -> list[tuple[Path, Path]]:
    """
    Return list of (fixture_path, expected_path) pairs.
    """
    if single_fixture is not None:
        expected = single_fixture.with_suffix(single_fixture.suffix + ".expected")
        if not expected.exists():
            # Try <stem>.expected
            expected = single_fixture.with_name(single_fixture.stem + ".expected")
        if not expected.exists():
            print(f"[error] No .expected file found for {single_fixture}", file=sys.stderr)
            sys.exit(2)
        return [(single_fixture, expected)]

    base = FIXTURES_DIR
    if category:
        base = FIXTURES_DIR / category
        if not base.is_dir():
            print(f"[error] Category directory not found: {base}", file=sys.stderr)
            sys.exit(2)

    pairs: list[tuple[Path, Path]] = []
    for expected_path in sorted(base.rglob("*.expected")):
        # Derive fixture path: the stem of the .expected file is the fixture
        # base name, which may have any extension (e.g. .css, .html).
        # Strip the trailing ".expected" to get the bare name, then look for
        # any file in the same directory that matches <stem>.<any-ext>.
        bare_name = expected_path.name[: -len(".expected")]  # e.g. "missing-aria"

        # First try: exact name match (bare_name has its own extension already)
        exact = expected_path.parent / bare_name
        if exact.exists() and exact.is_file():
            pairs.append((exact, expected_path))
            continue

        # Second try: glob for <bare_name>.<ext> siblings
        candidates = [
            f for f in expected_path.parent.iterdir()
            if f.stem == bare_name and not f.name.endswith(".expected") and f.is_file()
        ]
        if len(candidates) == 1:
            pairs.append((candidates[0], expected_path))
        elif len(candidates) > 1:
            # Prefer .css > .html > first alphabetically
            preferred = sorted(candidates, key=lambda p: (p.suffix not in (".css", ".html"), p.name))
            pairs.append((preferred[0], expected_path))
            print(f"[warn] Multiple fixture candidates for {expected_path.name}, using {preferred[0].name}", file=sys.stderr)
        else:
            print(f"[warn] .expected file has no matching fixture: {expected_path}", file=sys.stderr)
    return pairs


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_summary(results: list[FixtureResult]) -> None:
    passed = [r for r in results if r.passed and not r.skipped]
    failed = [r for r in results if not r.passed and not r.skipped]
    skipped = [r for r in results if r.skipped]

    print()
    print(_c("bold", "── Fixture Test Summary ──────────────────────────────"))
    for r in results:
        rel = r.fixture.resolve().relative_to(REPO_ROOT) if r.fixture.resolve().is_relative_to(REPO_ROOT) else r.fixture
        if r.skipped:
            print(f"  {_c('yellow', 'SKIP')}  {rel}  ({r.skip_reason})")
        elif r.passed:
            warn_tag = f"  {_c('yellow', f'{len(r.warnings)} warning(s)')}" if r.warnings else ""
            print(f"  {_c('green', 'PASS')}  {rel}{warn_tag}")
        else:
            print(f"  {_c('red', 'FAIL')}  {rel}")
            for err in r.errors:
                print(f"        {_c('red', '✗')} {err}")
            for w in r.warnings:
                print(f"        {_c('yellow', '!')} {w}")

    total = len(results) - len(skipped)
    print()
    print(
        f"  {_c('bold', 'Results:')} "
        f"{_c('green', str(len(passed)))} passed, "
        f"{_c('red', str(len(failed)))} failed, "
        f"{_c('yellow', str(len(skipped)))} skipped "
        f"({total} total)"
    )
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Argus Fixture Regression Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--category", metavar="NAME", help="Run only fixtures in this category subdirectory")
    parser.add_argument("--fixture", metavar="PATH", type=Path, help="Run a single fixture file")
    parser.add_argument("--model", default=None, help="LLM model to use (default: primary from config/free-models.yml)")
    parser.add_argument("--token-system", default="auto", choices=["antd5", "material3", "polaris", "custom", "auto"], help="Design system whose token mapping (.github/tokens/<system>.json) is injected into the prompt; 'auto' detects from package.json (default: auto)")
    parser.add_argument("--fallback-models", default=None, help="Comma-separated fallback model queue (ordered by coding ability) when primary fails. Defaults to config/free-models.yml (auto-refreshed weekly via reviewable PR).")
    parser.add_argument("--verbose", action="store_true", help="Show full Argus output for each fixture")
    parser.add_argument("--dry-run", action="store_true", help="Parse fixtures and print plan, but do not invoke Argus")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write JSON results to FILE")
    args = parser.parse_args()

    # Resolve fallback queue: explicit --fallback-models wins; otherwise read
    # from config/free-models.yml (auto-refreshed weekly via reviewable PR).
    fallback_models = args.fallback_models or default_fallback_models()

    # Resolve primary model: explicit --model wins; otherwise read the primary
    # from config/free-models.yml; built-in default only if config is missing.
    model = args.model or default_primary_model()
    _auth_preflight(model)

    pairs = discover_fixtures(
        category=args.category,
        single_fixture=args.fixture.resolve() if args.fixture else None,
    )

    if not pairs:
        print("[warn] No fixtures found.", file=sys.stderr)
        return 0

    print(_c("bold", f"\nArgus Fixture Tests — {len(pairs)} fixture(s)\n"))

    results: list[FixtureResult] = []

    for fixture_path, expected_path in pairs:
        rel = fixture_path.relative_to(REPO_ROOT)
        print(f"  {_c('cyan', 'RUN')}   {rel} ...", end="", flush=True)

        try:
            expected = parse_expected(expected_path)
        except (ValueError, FileNotFoundError) as exc:
            result = FixtureResult(
                fixture=fixture_path,
                passed=False,
                errors=[f"Failed to parse .expected: {exc}"],
            )
            results.append(result)
            print(f" {_c('red', 'FAIL')}")
            continue

        if args.dry_run:
            result = FixtureResult(
                fixture=fixture_path,
                passed=True,
                skipped=True,
                skip_reason="dry-run",
            )
            results.append(result)
            print(f" {_c('yellow', 'SKIP')} (dry-run)")
            continue

        argus_output = run_argus_on_fixture(fixture_path, model=model, verbose=args.verbose,
                                            fallback_models=fallback_models,
                                            token_system=args.token_system)
        # Static heuristic scan is deterministic → exact counts (tolerance 0);
        # LLM output varies → keep the historical ±1 tolerance.
        static_mode = _find_opencode() is None
        result = validate_output(expected, argus_output, tolerance=0 if static_mode else 1)
        results.append(result)

        if result.passed:
            warn_tag = f" ({len(result.warnings)} warning)" if result.warnings else ""
            print(f" {_c('green', 'PASS')}{warn_tag}")
        else:
            print(f" {_c('red', 'FAIL')}")

    print_summary(results)

    # FalsePositiveRate — informational metric (not a gate). Aggregates
    # must-not-flag violations (FP) and matched expected findings (TP) across
    # all non-skipped fixtures. Meaningful in LLM mode; static heuristic mode
    # is deterministic and enforces must-not-flag as errors, so a passing
    # static run always yields FP = 0.
    active = [r for r in results if not r.skipped]
    fp_total = sum(r.fp_count for r in active)
    tp_total = sum(r.tp_count for r in active)
    fp_rate = (fp_total / (fp_total + tp_total) * 100) if (fp_total + tp_total) else 0.0
    if active:
        print(_c("bold", "── FalsePositiveRate ───────────────────────────────"))
        print(f"  {_c('bold', 'FalsePositiveRate:')} {fp_rate:.1f}% (target ≤5%)"
              f"  — {fp_total} FP / {tp_total} TP")
        print()

    if args.output_json:
        json_data = [
            {
                "fixture": str(r.fixture.resolve().relative_to(REPO_ROOT) if r.fixture.resolve().is_relative_to(REPO_ROOT) else r.fixture),
                "passed": r.passed,
                "skipped": r.skipped,
                "errors": r.errors,
                "warnings": r.warnings,
                "fp_count": r.fp_count,
                "tp_count": r.tp_count,
            }
            for r in results
        ]
        json_data.append({
            "fixture": "__summary__",
            "fp_count": fp_total,
            "tp_count": tp_total,
            "fp_rate": round(fp_rate, 2),
        })
        Path(args.output_json).write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        print(f"JSON results written to {args.output_json}")

    failed = [r for r in results if not r.passed and not r.skipped]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
