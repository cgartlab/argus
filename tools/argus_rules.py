#!/usr/bin/env python3
"""
argus_rules.py — team-defined custom review rules (rule DSL)

Applies a team's custom rules (config/argus-rules.schema.json format) to
frontend files and emits findings in the standard Argus output format. Rules
are case-insensitive substring matches against code lines, with a severity,
message, and an optional design-token suggestion.

Usage:
  python3 tools/argus_rules.py apply <file|dir> [--rules FILE] [--json FILE]
  python3 tools/argus_rules.py --validate [--rules FILE]

Commands:
  apply          run custom rules on files (dirs are scanned for frontend files)
  --validate     validate a rules file against config/argus-rules.schema.json
                 plus semantic checks (kebab-case id, non-empty message/match)

Options:
  --rules FILE   custom rules YAML (default: ./argus-rules.yml, else the repo example)
  --json FILE    write structured findings JSON to FILE (apply only)

Exit codes:
  0 — ok (validate passed / apply completed, findings may exist)
  1 — validation failed / rules file error
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import load_config
import validate_argus_schema

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "config" / "argus-rules.schema.json"
EXAMPLE_RULES = REPO_ROOT / "config" / "argus-rules.example.yml"
FILE_EXTENSIONS = {".css", ".html", ".htm", ".js", ".ts", ".jsx", ".tsx"}
RULE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def resolve_rules_file(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit).resolve()
        if not p.is_file():
            print(f"[error] rules file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p
    cwd_rules = Path("argus-rules.yml").resolve()
    return cwd_rules if cwd_rules.is_file() else EXAMPLE_RULES


def validate_rules(data: dict, schema_path: Path) -> list[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    validate_argus_schema.validate(data, schema, "", errors)
    for rule in data.get("rules", []) if isinstance(data, dict) else []:
        rid = rule.get("id", "")
        if not RULE_ID_RE.fullmatch(rid):
            errors.append(f"rules[{rid!r}].id must be kebab-case")
        if not str(rule.get("match", "")).strip():
            errors.append(f"rules[{rid}].match must be non-empty")
        if not str(rule.get("message", "")).strip():
            errors.append(f"rules[{rid}].message must be non-empty")
    return errors


def normalize_rules(raw_rules) -> list[dict]:
    """Accept structured dict rules (PyYAML) or pipe-delimited string rules
    (minimal fallback parser) and normalize to dicts.

    Pipe format: "<id>|<severity>|<match>|<message>|<token>|<file-filter(s)>"
    """
    out: list[dict] = []
    for entry in raw_rules or []:
        if isinstance(entry, dict):
            out.append(entry)
            continue
        parts = [p.strip() for p in str(entry).split("|")]
        if len(parts) < 4 or not parts[0]:
            print(f"[error] malformed rule entry {entry!r} "
                  f"(expected '<id>|<severity>|<match>|<message>|<token>|<files>')", file=sys.stderr)
            sys.exit(1)
        rule = {"id": parts[0], "severity": parts[1], "match": parts[2],
                "message": parts[3], "token": parts[4] if len(parts) > 4 else ""}
        if len(parts) > 5 and parts[5]:
            rule["files"] = [f2.strip() for f2 in parts[5].split(",") if f2.strip()]
        out.append(rule)
    return out

def collect_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(f for f in p.rglob("*")
                         if f.is_file() and f.suffix.lower() in FILE_EXTENSIONS)
        elif p.is_file():
            files.append(p)
        else:
            print(f"[error] path not found: {p}", file=sys.stderr)
            sys.exit(2)
    return sorted({f.resolve() for f in files})


def apply_rules(rules: list[dict], file_path: Path, rel: str) -> list[dict]:
    findings: list[dict] = []
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        print(f"  [error] cannot read {rel}: {exc}")
        return findings
    rel_lower = rel.lower()
    for rule in rules:
        filters = rule.get("files") or []
        if filters and not any(f.lower() in rel_lower for f in filters):
            continue
        match = str(rule.get("match", "")).lower()
        for i, line in enumerate(lines, start=1):
            if match in line.lower():
                token = rule.get("token", "")
                expected = f"use var({token})" if token else "remove or refactor"
                findings.append({
                    "severity": rule.get("severity", "P2"),
                    "file": rel,
                    "line": i,
                    "rule_id": rule.get("id", ""),
                    "description": rule.get("message", ""),
                    "found": line.strip(),
                    "expected": expected,
                    "token": token,
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply team-defined custom review rules (rule DSL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", nargs="?", choices=["apply"], help="apply: run custom rules on files")
    parser.add_argument("paths", nargs="*", metavar="PATH", help="Files/dirs to review (apply)")
    parser.add_argument("--rules", default=None, metavar="FILE", help="Custom rules YAML")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write findings JSON (apply)")
    parser.add_argument("--validate", action="store_true", help="Validate the rules file and exit")
    args = parser.parse_args()

    rules_file = resolve_rules_file(args.rules)
    data = load_config.load_raw_yaml(rules_file)
    if not isinstance(data, dict) or "rules" not in data:
        print(f"[error] {rules_file}: missing 'rules' list", file=sys.stderr)
        return 1

    rules = normalize_rules(data.get("rules"))

    if args.validate:
        errors = validate_rules({"rules": rules}, DEFAULT_SCHEMA)
        if errors:
            print(f"[argus:rules] FAIL: {rules_file} does not conform to {DEFAULT_SCHEMA.name}:")
            for err in errors:
                print(f"  [FAIL] {err}")
            return 1
        print(f"[argus:rules] ok: {rules_file} conforms to {DEFAULT_SCHEMA.name}")
        return 0

    if args.command != "apply" or not args.paths:
        parser.error("provide 'apply <path>' or --validate")

    files = collect_files([Path(p) for p in args.paths])
    if not files:
        print("[error] no reviewable files found", file=sys.stderr)
        return 1

    all_findings: list[dict] = []
    print(f"Argus custom rules - {len(rules)} rule(s), {len(files)} file(s)\n")
    for f in files:
        try:
            rel = f.relative_to(REPO_ROOT)
        except ValueError:
            rel = f
        print(f"-- {rel} --")
        findings = apply_rules(rules, f, str(rel))
        if not findings:
            print("  (no custom-rule findings)")
        for item in findings:
            token_line = f"\n  Token:    {item['token']}" if item["token"] else ""
            print(f"[{item['severity']}] {item['file']}:{item['line']} - {item['description']}")
            print(f"  Found:    {item['found']}")
            print(f"  Expected: {item['expected']}{token_line}")
        all_findings.extend(findings)
        print()

    by_severity = {s: 0 for s in ("P0", "P1", "P2", "P3")}
    for item in all_findings:
        by_severity[item["severity"]] += 1
    print(f"Total custom-rule findings: {len(all_findings)} "
          f"(P0: {by_severity['P0']} | P1: {by_severity['P1']} | "
          f"P2: {by_severity['P2']} | P3: {by_severity['P3']})")

    if args.output_json:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rules_file": str(rules_file),
            "rule_count": len(rules),
            "files_reviewed": len(files),
            "total_issues": len(all_findings),
            "by_severity": by_severity,
            "findings": all_findings,
        }
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nJSON report written to {args.output_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())