#!/usr/bin/env python3
"""
validate_severity_matrix.py - enforce the rule-id x severity matrix

Checks that the three places where rule severities are declared agree:

  1. config/severity-matrix.yml      - canonical rule-id -> severity (source of truth)
  2. SKILL.md "## Issue Severity"    - documented matrix table (prose contract)
  3. tools/load_config.py            - NON_DOWNGRADABLE_RULES enforcement (runtime)

Consistency rules enforced:
  - Every rule in the canonical matrix appears in the SKILL.md matrix table at
    the SAME severity (no silent drift between docs and config).
  - Every rule-id mentioned in the SKILL.md matrix table exists in the
    canonical matrix (new documented rules must be declared).
  - The set of P0/P1 rules in the canonical matrix EXACTLY equals
    load_config.NON_DOWNGRADABLE_RULES (enforcement matches the matrix).
  - Severity values are valid (P0-P3) and rule-ids are kebab-case.

Usage:
  python3 tools/validate_severity_matrix.py
  python3 tools/validate_severity_matrix.py --matrix config/severity-matrix.yml

Exit codes:
  0 - matrix consistent
  1 - inconsistency found
  2 - usage / config error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import load_config  # reuse YAML loading + NON_DOWNGRADABLE_RULES

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = REPO_ROOT / "config" / "severity-matrix.yml"
SKILL_MD = REPO_ROOT / "SKILL.md"

VALID_SEVERITIES = {"P0", "P1", "P2", "P3"}
RULE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_skill_matrix(skill_text: str) -> dict[str, str]:
    """Extract {rule-id: severity} from the SKILL.md '## Issue Severity' table."""
    section = re.search(r"^## Issue Severity\s*\n(.*?)(?=^## )", skill_text, re.MULTILINE | re.DOTALL)
    if not section:
        print("[error] SKILL.md has no '## Issue Severity' section", file=sys.stderr)
        sys.exit(2)

    matrix: dict[str, str] = {}
    for line in section.group(1).splitlines():
        m = re.match(r"^\|\s*\*\*(P[0-3])\*\*\s*\|", line)
        if not m:
            continue
        severity = m.group(1)
        for rule_id in re.findall(r"`([a-z0-9][a-z0-9-]+)`", line):
            matrix[rule_id] = severity
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce the rule-id x severity matrix")
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX), metavar="PATH",
                        help="Canonical matrix YAML (default: config/severity-matrix.yml)")
    args = parser.parse_args()

    matrix_path = Path(args.matrix)
    data = load_config.load_raw_yaml(matrix_path)
    rules = data.get("rules")
    if not isinstance(rules, dict) or not rules:
        print(f"[error] {matrix_path}: missing or empty 'rules' map", file=sys.stderr)
        return 2

    skill_matrix = parse_skill_matrix(SKILL_MD.read_text(encoding="utf-8"))

    errors: list[str] = []
    rows: list[tuple[str, str, str, str, str]] = []  # rule, sev, in_skill, in_code, non_downgradable

    # Validate canonical matrix entries + cross-check SKILL.md
    for rule_id, severity in sorted(rules.items()):
        if severity not in VALID_SEVERITIES:
            errors.append(f"{rule_id}: invalid severity {severity!r} (valid: {sorted(VALID_SEVERITIES)})")
        if not RULE_ID_RE.fullmatch(rule_id):
            errors.append(f"{rule_id}: not kebab-case rule-id")

        skill_sev = skill_matrix.get(rule_id)
        if skill_sev is None:
            errors.append(f"{rule_id}: declared {severity} in matrix but absent from SKILL.md matrix table")
        elif skill_sev != severity:
            errors.append(f"{rule_id}: SKILL.md matrix says {skill_sev}, canonical matrix says {severity}")
        rows.append((rule_id, severity, skill_sev or "n/a", "yes" if severity in ("P0", "P1") else "no"))

    # Every rule-id documented in SKILL.md must be declared in the canonical matrix
    for rule_id in sorted(skill_matrix):
        if rule_id not in rules:
            errors.append(f"{rule_id}: documented in SKILL.md matrix but missing from {matrix_path.name}")

    # Enforcement parity: P0/P1 in matrix == load_config.NON_DOWNGRADABLE_RULES
    matrix_non_downgradable = {rid for rid, sev in rules.items() if sev in ("P0", "P1")}
    code_non_downgradable = set(load_config.NON_DOWNGRADABLE_RULES)
    if matrix_non_downgradable != code_non_downgradable:
        errors.append(
            "load_config.NON_DOWNGRADABLE_RULES mismatch: "
            f"matrix P0/P1={sorted(matrix_non_downgradable)} vs code={sorted(code_non_downgradable)}"
        )

    # Report (ASCII-safe output for Windows/GBK consoles)
    print("== Severity Matrix ==")
    print(f"  {'rule-id':<22} {'sev':<4} {'SKILL.md':<9} {'load_config':<11} non-downgradable")
    for rule_id, sev, in_skill, nd in rows:
        print(f"  {rule_id:<22} {sev:<4} {in_skill:<9} {nd}")
    print(f"  ({len(rules)} rule(s) - {len(matrix_non_downgradable)} non-downgradable)")
    print()

    if errors:
        print("== Severity Matrix CHECK FAILED ==")
        for err in errors:
            print(f"  [FAIL] {err}")
        return 1

    print("OK: severity matrix consistent (config <-> SKILL.md <-> load_config)")
    return 0


if __name__ == "__main__":
    sys.exit(main())