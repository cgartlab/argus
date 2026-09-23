#!/usr/bin/env python3
"""
argus_report.py — turn a findings JSON report into a shareable static HTML

Consumes the structured JSON emitted by `tools/argus_review.py --json` (or
any compatible `{"findings": [...]}` document) and produces a single
self-contained HTML file — no server, no external assets — ready to share in
a PR comment, team channel, or compliance handoff. This is the artifact a
future hosted report-link / Pro hook serves.

Usage:
  python3 tools/argus_review.py src/ --json review.json
  python3 tools/argus_report.py review.json                  # -> dist/argus-report.html
  python3 tools/argus_report.py review.json --out report.html --title "Checkout UI"
  python3 tools/argus_report.py review.json --wcag           # WCAG 2.2 compliance annotation

Options:
  --json FILE        findings JSON (from argus_review.py --json)
  --out FILE         output HTML path (default: dist/argus-report.html)
  --title TEXT       report title (default: "Argus Design Review")
  --wcag             annotate findings with WCAG 2.2 success criteria and add
                     a compliance summary (mapping: config/wcag-mapping.yml)
  --wcag-mapping F   WCAG mapping YAML (default: config/wcag-mapping.yml)

Exit codes:
  0 — report written
  1 — error (missing file, invalid JSON, no findings)
  2 — usage error
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import load_config  # YAML loading for config/wcag-mapping.yml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WCAG_MAPPING = REPO_ROOT / "config" / "wcag-mapping.yml"

SEVERITY_ORDER = ["P0", "P1", "P2", "P3"]
SEVERITY_META = {
    "P0": ("Blocking Issues", "#b42318", "#fef3f2"),
    "P1": ("High Priority", "#b54708", "#fffaeb"),
    "P2": ("Medium Priority", "#854d0e", "#fefce8"),
    "P3": ("Low Priority", "#475467", "#f2f4f7"),
}


def _esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def load_wcag_mapping(path: Path) -> list[dict]:
    """Load the pipe-delimited WCAG mapping (robust with or without PyYAML).

    Each entry: "<keyword>|<SC>|<level>|<name>".
    """
    data = load_config.load_raw_yaml(path)
    raw = data.get("criteria")
    if not isinstance(raw, list) or not raw:
        print(f"[error] {path}: missing or empty 'criteria' list", file=sys.stderr)
        sys.exit(1)
    criteria: list[dict] = []
    for entry in raw:
        parts = [p.strip() for p in str(entry).split("|")]
        if len(parts) < 4 or not parts[0]:
            print(f"[error] {path}: malformed criterion entry {entry!r} "
                  f"(expected '<keyword>|<SC>|<level>|<name>')", file=sys.stderr)
            sys.exit(1)
        criteria.append({"keyword": parts[0], "sc": parts[1],
                         "level": parts[2], "name": parts[3]})
    return criteria


def map_wcag(findings: list[dict], criteria: list[dict]) -> dict:
    """Annotate each finding with its WCAG success criterion (in place, key
    ``_wcag``) and return the compliance summary ``{"covered": {sc: ...}}``."""
    covered: dict[str, dict] = {}
    for finding in findings:
        text = str(finding.get("description", "")).lower()
        sc = None
        for entry in criteria:
            if entry.get("keyword", "").lower() in text:
                sc = entry
                break
        finding["_wcag"] = sc
        if sc is not None:
            key = str(sc.get("sc", ""))
            covered.setdefault(key, {"name": sc.get("name", ""), "level": sc.get("level", ""), "count": 0})
            covered[key]["count"] += 1
    return {"covered": covered}


def build_html(report: dict, title: str, wcag: dict | None = None) -> str:
    findings = report.get("findings") or []
    by_severity = report.get("by_severity") or {}
    meta = {
        "generated_at": report.get("generated_at", ""),
        "stack": report.get("stack", ""),
        "model": report.get("model", ""),
        "files_reviewed": report.get("files_reviewed", 0),
        "total_issues": report.get("total_issues", len(findings)),
    }

    groups: dict[str, list[dict]] = {s: [] for s in SEVERITY_ORDER}
    for finding in findings:
        groups.setdefault(finding.get("severity", "P3"), []).append(finding)

    counts = " | ".join(f"{s}: {by_severity.get(s, 0)}" for s in SEVERITY_ORDER)

    compliance_html = ""
    if wcag is not None:
        covered = wcag.get("covered", {})
        if not covered:
            compliance_html = ""
        else:
            a_count = sum(1 for c in covered.values() if c["level"] == "A")
            aa_count = sum(1 for c in covered.values() if c["level"] == "AA")
            rows = "".join(
                f'<tr><td style="text-align:left;padding:6px 10px;border-bottom:1px solid #eaecf0">'
                f'<strong>WCAG 2.2 {_esc(sc)}</strong> ({_esc(c.get("level", ""))}) — {_esc(c.get("name", ""))}</td>'
                f'<td style="text-align:center;padding:6px 10px;border-bottom:1px solid #eaecf0">{c["count"]}</td></tr>'
                for sc, c in sorted(covered.items())
            )
            compliance_html = (
                '<section style="margin-bottom:28px;background:#fff;border:1px solid #eaecf0;'
                'border-radius:8px;padding:16px 18px">'
                '<h2 style="margin:0 0 4px;font-size:18px">WCAG 2.2 Compliance Summary</h2>'
                f'<p style="margin:0 0 10px;color:#667085;font-size:13px">'
                f'{len(covered)} unique success criteria covered ({a_count} A / {aa_count} AA)</p>'
                f'<table style="border-collapse:collapse;width:100%;font-size:13px">'
                '<tr><th style="text-align:left;padding:6px 10px;border-bottom:2px solid #d0d5dd">Criterion</th>'
                '<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #d0d5dd">Findings</th></tr>'
                f'{rows}</table></section>'
            )

    sections = []
    for severity in SEVERITY_ORDER:
        label, fg, bg = SEVERITY_META[severity]
        items = groups.get(severity, [])
        badge = f'<span style="background:{bg};color:{fg};font-weight:700;padding:2px 10px;border-radius:999px;font-size:12px">{severity}</span>'
        if not items:
            sections.append(
                f'<section style="margin-bottom:28px"><h2 style="margin:0 0 8px">{badge} {_esc(label)}</h2>'
                f'<p style="margin:0;color:#667085">No issues found.</p></section>'
            )
            continue
        cards = []
        for item in items:
            wcag_sc = item.get("_wcag")
            sc_badge = ""
            if wcag_sc is not None:
                sc_badge = (
                    f'<span style="background:#eef4ff;color:#3538cd;border:1px solid #c7d7fe;'
                    f'border-radius:6px;padding:2px 8px;font-size:11px;margin-left:8px;white-space:nowrap">'
                    f'WCAG {_esc(wcag_sc.get("sc", ""))} ({_esc(wcag_sc.get("level", ""))})</span>'
                )
            cards.append(
                f'<article style="border:1px solid #eaecf0;border-left:4px solid {fg};'
                f'border-radius:8px;padding:14px 16px;margin:10px 0;background:#fff">'
                f'<code style="color:{fg};font-weight:600">{_esc(item.get("severity", ""))}</code> '
                f'<code style="color:#344054">{_esc(item.get("file", ""))}:{_esc(item.get("line", ""))}</code>{sc_badge}'
                f'<p style="margin:8px 0 6px;font-weight:600;color:#101828">{_esc(item.get("description", ""))}</p>'
                f'<pre style="background:#f9fafb;border:1px solid #eaecf0;border-radius:6px;'
                f'padding:8px 10px;margin:4px 0;font-size:12px;white-space:pre-wrap;color:#344054">'
                f'Found:    {_esc(item.get("found", ""))}\n'
                f'Expected: {_esc(item.get("expected", ""))}</pre>'
                f'</article>'
            )
        sections.append(
            f'<section style="margin-bottom:28px"><h2 style="margin:0 0 8px">{badge} {_esc(label)} '
            f'({len(items)})</h2>{"".join(cards)}</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(title)}</title>
</head>
<body style="margin:0;background:#fcfcfd;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#101828">
<div style="max-width:860px;margin:0 auto;padding:32px 20px 64px">
  <header style="border-bottom:1px solid #eaecf0;padding-bottom:16px;margin-bottom:24px">
    <h1 style="margin:0 0 4px;font-size:24px">&#128065; {_esc(title)}</h1>
    <p style="margin:0;color:#667085;font-size:13px">
      Total Issues: <strong>{meta['total_issues']}</strong> ({_esc(counts)}) &middot;
      Files Reviewed: {meta['files_reviewed']}
    </p>
    <p style="margin:6px 0 0;color:#98a2b3;font-size:12px">
      {_esc(meta['generated_at'])} &middot; stack={_esc(meta['stack'])} &middot; model={_esc(meta['model'])}
    </p>
  </header>
  {compliance_html}
  {"".join(sections)}
  <footer style="margin-top:32px;padding-top:12px;border-top:1px solid #eaecf0;color:#98a2b3;font-size:12px">
    Generated by Argus — frontend design code review agent.
  </footer>
</div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Turn a findings JSON report into a shareable static HTML file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", required=True, metavar="FILE", help="Findings JSON (from argus_review.py --json)")
    parser.add_argument("--out", default=None, metavar="FILE", help="Output HTML path (default: dist/argus-report.html)")
    parser.add_argument("--title", default="Argus Design Review", help="Report title")
    parser.add_argument("--wcag", action="store_true",
                        help="Annotate findings with WCAG 2.2 success criteria and add a compliance summary")
    parser.add_argument("--wcag-mapping", default=str(DEFAULT_WCAG_MAPPING), metavar="FILE",
                        help="WCAG mapping YAML (default: config/wcag-mapping.yml)")
    args = parser.parse_args()

    json_path = Path(args.json)
    if not json_path.is_file():
        print(f"[error] findings JSON not found: {json_path}", file=sys.stderr)
        return 1
    try:
        report = json.loads(json_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"[error] invalid JSON in {json_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(report, dict) or "findings" not in report:
        print(f"[error] {json_path} has no 'findings' list — expected argus_review.py --json output", file=sys.stderr)
        return 1

    out_path = Path(args.out) if args.out else Path("dist") / "argus-report.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wcag = None
    if args.wcag:
        criteria = load_wcag_mapping(Path(args.wcag_mapping))
        wcag = map_wcag(report.get("findings") or [], criteria)
    out_path.write_text(build_html(report, args.title, wcag=wcag), encoding="utf-8")
    print(f"Report written to {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())