#!/usr/bin/env python3
"""
add_fp_appeal.py — turn a false-positive appeal into a regression fixture

When Argus flags code that is actually legal ("this isn't a bug"), the appeal
is captured as a regression guard in tests/fixtures/false-positives/: a
zero-expectation fixture that MUST produce no findings, plus [must-not-flag]
entries naming the construct that must never appear on a flagged line.

This tool does the boilerplate:
  1. copies the offending code snippet into tests/fixtures/false-positives/<name>.<ext>
  2. writes the matching <name>.expected (zero counts + must-not-flag list)
  3. runs the static heuristic scanner on the new fixture and reports whether
     it currently flags the appeal — a red run means a REAL false positive
     that must be fixed before merging (see SKILL.md non-blocking context)

Usage:
  python3 tools/add_fp_appeal.py --name drop-shadow-color \
      --file /tmp/drop-shadow.css \
      --reason "Shadow colors are legitimate values, not token violations" \
      --forbidden "drop-shadow" --forbidden "rgba(0, 0, 0, 0.2)"

Options:
  --name NAME        fixture base name (kebab-case)
  --file PATH        code snippet that was wrongly flagged (.css/.html)
  --reason TEXT      why this code is legal (goes into the .expected description)
  --forbidden TEXT   substring that must never appear on a flagged line (repeatable)
  --dry-run          print what would be created without writing files

Exit codes:
  0 — fixture created and the static scanner is clean (no false positive)
  1 — fixture created but the static scanner still flags it — real FP to fix
  2 — usage / validation error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import run_fixture_tests as rft

REPO_ROOT = rft.REPO_ROOT
FP_DIR = REPO_ROOT / "tests" / "fixtures" / "false-positives"
ALLOWED_EXTS = {".css", ".html"}
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$|^[a-z0-9]$")


def build_fixture(name: str, snippet: str, ext: str) -> str:
    header = (
        f"/*\n"
        f" * FIXTURE: false-positives/{name}{ext} (false-positive appeal)\n"
        f" * Status: LEGAL code — must produce ZERO findings.\n"
        f" * Filed via: python3 tools/add_fp_appeal.py\n"
        f" * If the scanner or LLM flags this file, the finding is a false\n"
        f" * positive and the responsible rule/exemption must be fixed.\n"
        f" */\n\n"
    )
    return header + snippet.rstrip() + "\n"


def build_expected(name: str, ext: str, reason: str, forbidden: list[str]) -> str:
    lines = [
        "[meta]",
        f"fixture = false-positives/{name}{ext}",
        f"description = FP appeal: {reason}",
        "",
        "[findings]",
        "",
        "[must-not-flag]",
    ]
    lines.extend(f"# {item}" for item in forbidden)
    lines.extend(forbidden)
    lines += [
        "",
        "[counts]",
        "P0 = 0",
        "P1 = 0",
        "P2 = 0",
        "P3 = 0",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn a false-positive appeal into a regression fixture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--name", required=True, help="Fixture base name (kebab-case)")
    parser.add_argument("--file", required=True, metavar="PATH", help="Code snippet that was wrongly flagged")
    parser.add_argument("--reason", required=True, help="Why this code is legal")
    parser.add_argument("--forbidden", action="append", default=[], metavar="TEXT",
                        help="Substring that must never be flagged (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created, write nothing")
    args = parser.parse_args()

    if not NAME_RE.fullmatch(args.name):
        print(f"[error] --name must be kebab-case, got {args.name!r}", file=sys.stderr)
        return 2

    snippet_path = Path(args.file).resolve()
    if not snippet_path.is_file():
        print(f"[error] snippet file not found: {snippet_path}", file=sys.stderr)
        return 2
    ext = snippet_path.suffix.lower()
    if ext not in ALLOWED_EXTS:
        print(f"[error] snippet extension {ext!r} not supported (allowed: {sorted(ALLOWED_EXTS)})", file=sys.stderr)
        return 2
    if not args.forbidden:
        print("[warn] no --forbidden entries given — the fixture guards nothing; add at least one", file=sys.stderr)

    snippet = snippet_path.read_text(encoding="utf-8")
    fixture_content = build_fixture(args.name, snippet, ext)
    expected_content = build_expected(args.name, ext, args.reason, args.forbidden)

    fixture_path = FP_DIR / f"{args.name}{ext}"
    expected_path = FP_DIR / f"{args.name}.expected"

    if args.dry_run:
        print(f"[dry-run] would create:\n  {fixture_path}\n  {expected_path}")
        return 0

    if fixture_path.exists() or expected_path.exists():
        print(f"[error] fixture already exists: {fixture_path} or {expected_path}", file=sys.stderr)
        return 2

    FP_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(fixture_content, encoding="utf-8")
    expected_path.write_text(expected_content, encoding="utf-8")
    print(f"created: {fixture_path}")
    print(f"created: {expected_path}")

    # Static scan check: does the scanner still flag the appeal?
    scan_output = rft._static_heuristic_scan(fixture_path)
    flagged = [line for line in scan_output.splitlines() if re.search(r"\[P\d\]", line)]
    if flagged:
        print("[FAIL] static scanner still flags this appeal — a real false positive to fix:")
        for line in flagged:
            print(f"  {line}")
        print("Fix the responsible rule/exemption (see SKILL.md non-blocking context), then re-run:")
        print(f"  python3 tools/run_fixture_tests.py --fixture {fixture_path}")
        return 1
    print("[ok] static scanner is clean for this appeal")
    return 0


if __name__ == "__main__":
    sys.exit(main())