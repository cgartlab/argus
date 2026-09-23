#!/usr/bin/env python3
"""
argus_review.py — local Argus review CLI

Reviews frontend files locally with the same rules as the GitHub App /
composite action. Uses the OpenCode CLI when installed; falls back to the
static heuristic scanner when it is not (no API key needed).

The CLI is the foundation for other roadmap surfaces: the structured --json
report is the payload a future report-link / CI-comment service consumes.

Usage:
  python3 tools/argus_review.py path/to/file.css
  python3 tools/argus_review.py src/components/*.css --stack antd5
  python3 tools/argus_review.py --dir src/ --ignore '*.test.*' --json review.json
  python3 tools/argus_review.py src/App.tsx --model opencode/deepseek-v4-flash-free

Options:
  --stack NAME            design system: auto | antd5 | material3 | polaris | custom (default: auto)
  --model NAME            LLM model (default: primary from config/free-models.yml)
  --fallback-models LIST  comma-separated fallback queue when the primary fails
  --json FILE             write a structured findings report (JSON) to FILE
  --dir PATH              review every .css/.html/.js/.ts/.jsx/.tsx file under PATH
  --ignore GLOB           skip files matching GLOB (repeatable; default excludes
                          node_modules / dist / .git)

Exit codes:
  0 — review completed (findings may exist)
  1 — error (missing path, no files to review)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import run_fixture_tests as rft

REPO_ROOT = rft.REPO_ROOT
REVIEW_EXTENSIONS = {".css", ".html", ".htm", ".js", ".ts", ".jsx", ".tsx"}
DEFAULT_IGNORES = ("node_modules/", "dist/", ".git/")


def collect_files(paths: list[Path], directory: str | None,
                  ignores: list[str]) -> list[Path]:
    """Resolve explicit paths + --dir globbing into a deduped file list."""
    files: list[Path] = []
    if directory:
        base = Path(directory)
        if not base.is_dir():
            print(f"[error] --dir path not found: {base}", file=sys.stderr)
            sys.exit(1)
        for p in base.rglob("*"):
            if p.is_file() and p.suffix.lower() in REVIEW_EXTENSIONS:
                files.append(p)
    for p in paths:
        if p.is_dir():
            files.extend(f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in REVIEW_EXTENSIONS)
        elif p.is_file():
            files.append(p)
        else:
            print(f"[error] path not found: {p}", file=sys.stderr)
            sys.exit(1)

    def ignored(p: Path) -> bool:
        rel = str(p).replace("\\", "/")
        if any(part in rel for part in DEFAULT_IGNORES):
            return True
        return any(part in rel for part in ignores)

    seen: set[Path] = set()
    result: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen or ignored(p):
            continue
        seen.add(rp)
        result.append(p)
    return sorted(result)


def parse_findings(output: str, default_file: str) -> list[dict]:
    """Parse the standard Argus output format into structured findings."""
    findings: list[dict] = []
    current: dict | None = None
    for line in output.splitlines():
        m = re.match(r"\[(P[0-3])\]\s+(\S+):(\d+)\s+—\s+(.+)", line)
        if m:
            current = {
                "severity": m.group(1),
                "file": m.group(2) or default_file,
                "line": int(m.group(3)),
                "description": m.group(4),
                "found": "",
                "expected": "",
            }
            findings.append(current)
            continue
        mf = re.match(r"\s*Found:\s*(.*)", line)
        if mf and current is not None:
            current["found"] = mf.group(1)
        me = re.match(r"\s*Expected:\s*(.*)", line)
        if me and current is not None:
            current["expected"] = me.group(1)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Argus local review CLI — same rules as the GitHub App, run anywhere",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="*", metavar="PATH", help="Files or directories to review")
    parser.add_argument("--stack", default="auto", choices=["auto", "antd5", "material3", "polaris", "custom"],
                        help="Design system token mapping (default: auto)")
    parser.add_argument("--model", default=None, help="LLM model (default: primary from config/free-models.yml)")
    parser.add_argument("--fallback-models", default=None, help="Comma-separated fallback queue")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write structured findings report to FILE")
    parser.add_argument("--dir", default=None, metavar="PATH", help="Review every frontend file under PATH")
    parser.add_argument("--ignore", action="append", default=[], metavar="GLOB",
                        help="Skip files whose path contains GLOB (repeatable)")
    parser.add_argument("--mode", default="auto", choices=["auto", "static", "llm"],
                        help="Review mode: auto (complexity routing — small files static, "
                             "large files LLM), static (heuristic scanner only), "
                             "llm (OpenCode CLI, falls back to static if absent) (default: auto)")
    parser.add_argument("--min-lines", type=int, default=200, metavar="N",
                        help="In auto mode, files with <= N lines are reviewed statically (default: 200)")
    args = parser.parse_args()

    if not args.paths and not args.dir:
        parser.error("provide at least one PATH or --dir")

    files = collect_files([Path(p) for p in args.paths], args.dir, args.ignore)
    if not files:
        print("[error] no reviewable files found", file=sys.stderr)
        return 1

    model = args.model or rft.default_primary_model()
    fallback = args.fallback_models or rft.default_fallback_models()

    all_findings: list[dict] = []
    print(f"Argus review — {len(files)} file(s), stack={args.stack}, model={model}\n")
    opencode_ok = rft._find_opencode() is not None

    def _run_llm(f: Path) -> str:
        return rft.run_argus_on_fixture(f, model=model, verbose=False,
                                        fallback_models=fallback,
                                        token_system=args.stack)

    for f in files:
        try:
            rel = f.resolve().relative_to(REPO_ROOT)
        except ValueError:
            rel = f
        print(f"── {rel} ──")
        try:
            if args.mode == "static":
                output = rft._static_heuristic_scan(f)
                routed = "static (forced)"
            elif not opencode_ok:
                output = rft._static_heuristic_scan(f)
                routed = "static (no opencode CLI)"
            elif args.mode == "llm":
                output = _run_llm(f)
                routed = "llm (forced)"
            else:  # auto — complexity routing (small files static, large files LLM)
                line_count = len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
                if line_count > args.min_lines:
                    output = _run_llm(f)
                    routed = f"llm (complexity: {line_count} lines > {args.min_lines})"
                else:
                    output = rft._static_heuristic_scan(f)
                    routed = f"static (complexity: {line_count} lines <= {args.min_lines})"
        except Exception as exc:  # never let one file abort the run
            print(f"  [error] {exc}")
            continue
        print(f"  [{routed}]")
        print(output)
        print()
        all_findings.extend(parse_findings(output, str(rel)))

    by_severity = {s: 0 for s in rft.SEVERITY_ORDER}
    for finding in all_findings:
        by_severity[finding["severity"]] += 1

    summary = (
        f"Total Issues: {len(all_findings)} "
        f"(P0: {by_severity['P0']} | P1: {by_severity['P1']} | "
        f"P2: {by_severity['P2']} | P3: {by_severity['P3']})"
    )
    print("── Summary ─────────────────────────────────────────")
    print(f"  {summary}")
    print(f"  Files Reviewed: {len(files)}")

    if args.output_json:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "stack": args.stack,
            "model": model,
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