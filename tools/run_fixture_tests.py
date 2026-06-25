#!/usr/bin/env python3
"""
run_fixture_tests.py — Argus Fixture Regression Test Runner

Validates that Argus review rules produce the expected findings for each
fixture in tests/fixtures/. Operates in heuristic mode: checks severity
counts and keyword presence, not exact line numbers.

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

def build_argus_prompt(fixture_path: Path) -> str:
    """Build the same prompt the composite action uses, injecting AGENTS.md + SKILL.md."""
    agents = AGENTS_MD.read_text(encoding="utf-8")
    skill = SKILL_MD.read_text(encoding="utf-8")
    code = fixture_path.read_text(encoding="utf-8")
    rel = fixture_path.relative_to(REPO_ROOT)

    return textwrap.dedent(f"""\
        You are Argus, a frontend design code review agent.

        ## Argus Hard Rules
        {agents}

        ## Review Dimensions
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


def run_argus_on_fixture(fixture_path: Path, model: str, verbose: bool) -> str:
    """
    Invoke Argus (via OpenCode CLI) on a single fixture file.
    Returns the raw text output.
    Falls back to a static heuristic scan if OpenCode is not installed.
    """
    opencode = _find_opencode()
    if opencode is None:
        return _static_heuristic_scan(fixture_path)

    prompt = build_argus_prompt(fixture_path)
    prompt_file = fixture_path.parent / f".argus_prompt_{fixture_path.stem}.tmp"
    try:
        prompt_file.write_text(prompt, encoding="utf-8")
        result = subprocess.run(
            [opencode, "run", "--model", model, "--prompt-file", str(prompt_file)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        output = result.stdout + result.stderr
        if verbose:
            print(f"\n{_c('cyan', '── Argus raw output ──')}\n{output}\n{_c('cyan', '──────────────────────')}")
        return output
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] Argus did not respond within 120 seconds."
    except Exception as exc:
        return f"[ERROR] Failed to run OpenCode: {exc}"
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

            # Selector detection (reset duplicate tracking per block)
            if re.match(r"^[.#\w\[\]:,\s>~+-]+\{", stripped) and not is_comment:
                if ":root" not in stripped and "data-theme" not in stripped:
                    current_selector = stripped
                    selector_props = {}

            # Bare color values in component rules (not :root, not dark-block)
            if not in_root and not in_dark_block and not is_comment:
                for pattern, label in [
                    (r"\boklch\(", "bare oklch"),
                    (r"(?<!['\"])#[0-9a-fA-F]{3,8}\b", "bare hex"),
                    (r"\brgb\(", "bare rgb"),
                    (r"\brgba\(", "bare rgba"),
                    (r"\bhsl\(", "bare hsl"),
                ]:
                    m = re.search(pattern, stripped)
                    if m and "var(--" not in stripped and "--" not in stripped.split(":")[0]:
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

            # Duplicate property detection (within same selector block)
            prop_match = re.match(r"^\s*([\w-]+)\s*:", stripped)
            if prop_match and not is_comment and "{" not in stripped and "}" not in stripped:
                prop = prop_match.group(1)
                if not prop.startswith("--"):  # ignore custom property declarations
                    if prop in selector_props:
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

def validate_output(expected: ExpectedFile, argus_output: str) -> FixtureResult:
    """Compare Argus output against the .expected specification."""
    errors: list[str] = []
    warnings: list[str] = []
    output_lower = argus_output.lower()

    # 1. Count findings per severity in actual output
    actual_counts: dict[str, int] = {s: 0 for s in SEVERITY_ORDER}
    for line in argus_output.splitlines():
        for sev in SEVERITY_ORDER:
            if re.search(rf"\[{sev}\]", line):
                actual_counts[sev] += 1

    # 2. Verify severity counts (allow ±1 tolerance for LLM variance)
    TOLERANCE = 1
    for sev, expected_count in expected.counts.items():
        actual = actual_counts.get(sev, 0)
        if abs(actual - expected_count) > TOLERANCE:
            errors.append(
                f"Count mismatch [{sev}]: expected {expected_count}, got {actual} "
                f"(tolerance ±{TOLERANCE})"
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

    # 4. Check must-not-flag items — these should not appear as flagged tokens
    #    We check they don't appear on a [P*] finding line
    flagged_lines = [l for l in argus_output.splitlines() if re.search(r"\[P\d\]", l)]
    flagged_text = "\n".join(flagged_lines).lower()
    for forbidden in expected.must_not_flag:
        if forbidden.lower() in flagged_text:
            errors.append(f"False positive: '{forbidden}' was flagged but must NOT be")

    passed = len(errors) == 0
    return FixtureResult(
        fixture=expected.fixture_path,
        passed=passed,
        errors=errors,
        warnings=warnings,
        argus_output=argus_output,
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
    parser.add_argument("--model", default="opencode/deepseek-v4-flash-free", help="LLM model to use (default: deepseek-v4-flash-free)")
    parser.add_argument("--verbose", action="store_true", help="Show full Argus output for each fixture")
    parser.add_argument("--dry-run", action="store_true", help="Parse fixtures and print plan, but do not invoke Argus")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write JSON results to FILE")
    args = parser.parse_args()

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

        argus_output = run_argus_on_fixture(fixture_path, model=args.model, verbose=args.verbose)
        result = validate_output(expected, argus_output)
        results.append(result)

        if result.passed:
            warn_tag = f" ({len(result.warnings)} warning)" if result.warnings else ""
            print(f" {_c('green', 'PASS')}{warn_tag}")
        else:
            print(f" {_c('red', 'FAIL')}")

    print_summary(results)

    if args.output_json:
        json_data = [
            {
                "fixture": str(r.fixture.resolve().relative_to(REPO_ROOT) if r.fixture.resolve().is_relative_to(REPO_ROOT) else r.fixture),
                "passed": r.passed,
                "skipped": r.skipped,
                "errors": r.errors,
                "warnings": r.warnings,
            }
            for r in results
        ]
        Path(args.output_json).write_text(json.dumps(json_data, indent=2), encoding="utf-8")
        print(f"JSON results written to {args.output_json}")

    failed = [r for r in results if not r.passed and not r.skipped]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
