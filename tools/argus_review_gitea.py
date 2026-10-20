#!/usr/bin/env python3
"""Argus review for Gitea pull requests — static scanner + Gitea API comment.

This is the disaster-recovery counterpart of the GitHub App review. The
GitHub version drives `opencode github run` (LLM) and posts through the
argus-flash GitHub App. This version:

  - runs the same heuristic scanner (tools/argus_review.py --mode static),
    which needs no API key and no network;
  - posts the findings as a pull-request comment through the Gitea REST API.

The output format is identical to the GitHub version: severity-grouped
issue blocks with Found / Expected / Fix, plus a summary header. Consumer
repositories keep their existing "read the comment -> fix -> push" loop
unchanged.

Known degradation: the static scanner is a heuristic. It finds mechanical
problems (hardcoded values, missing a11y attributes, token violations) but
not semantic ones ("this flow is confusing"). The GitHub version retains
full LLM review; this is the fallback for when GitHub is unavailable.

Usage (inside a Gitea Actions job):

    python3 tools/argus_review_gitea.py \
        --repo-owner cgartlab --repo-name inkard --pr 42 \
        --findings findings.json

Environment:
    GITEA_TOKEN   required, API token with write access to the repo
    GITEA_URL     optional, defaults to the instance's own URL
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Severity order and labels mirror the GitHub version exactly.
SEVERITY_ORDER = ["P0", "P1", "P2", "P3"]
SEVERITY_TITLES = {
    "P0": "Blocking Issues (must fix, CI will fail)",
    "P1": "High Priority (must fix before merge)",
    "P2": "Medium Priority (should fix)",
    "P3": "Low Priority (optional polish)",
}
SEPARATOR = "─" * 49


def gitea_url() -> str:
    return os.environ.get("GITEA_URL", "http://192.168.31.92:8418").rstrip("/")


def api_request(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"{gitea_url()}{path}"
    data = None
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            if not body.strip():
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"Gitea API {method} {path} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gitea API {method} {path} unreachable: {exc.reason}") from exc


def format_finding(finding: dict[str, Any]) -> str:
    """Render one finding as an Argus issue block.

    The shape matches the GitHub version: a separator, a [P#] header line
    with file:line, then Found / Expected / Fix.

    Field names follow what tools/argus_review.py --json actually writes:
    severity, file, line, description, found, expected, (optionally fix,
    token, reference, note).
    """
    severity = finding.get("severity", "P3")
    file_path = finding.get("file", "")
    line = finding.get("line", "")
    title = (
        finding.get("description")
        or finding.get("message")
        or finding.get("title")
        or ""
    )
    location = f"{file_path}:{line}" if line not in (None, "") else str(file_path)

    lines = [SEPARATOR, f"[{severity}] {location} — {title}".rstrip(" —"), ""]

    found = finding.get("found") or finding.get("snippet")
    if found:
        lines.append(f"  Found:    {found}")
    expected = finding.get("expected")
    if expected:
        lines.append(f"  Expected: {expected}")
    if finding.get("fix"):
        lines.append("  Fix:")
        lines.append("  ```")
        for fix_line in str(finding["fix"]).splitlines():
            lines.append(f"  {fix_line}")
        lines.append("  ```")
    if finding.get("token"):
        lines.append(f"  Token:    {finding['token']}")
    if finding.get("reference"):
        lines.append(f"  Reference: {finding['reference']}")
    if finding.get("note"):
        lines.append(f"  Note:     {finding['note']}")

    return "\n".join(lines)


def build_comment(report: dict[str, Any]) -> str:
    findings = report.get("findings", [])
    by_severity = report.get("by_severity", {})
    files_reviewed = report.get("files_reviewed", 0)
    stack = report.get("stack", "auto")

    counts = " | ".join(f"{s}: {by_severity.get(s, 0)}" for s in SEVERITY_ORDER)
    parts = [
        "## Argus Design Review Summary",
        f"- Total Issues: {report.get('total_issues', len(findings))} ({counts})",
        f"- Files Reviewed: {files_reviewed}",
        f"- Technology Stack: {stack}",
        "- Review Mode: **static scanner** (Gitea disaster-recovery fallback — "
        "no LLM). The GitHub review keeps full semantic coverage.",
        "",
    ]

    for severity in SEVERITY_ORDER:
        parts.append(f"## {severity} — {SEVERITY_TITLES[severity]}")
        parts.append("")
        group = [f for f in findings if f.get("severity") == severity]
        if not group:
            parts.append("✓ No issues found")
            parts.append("")
            continue
        for finding in group:
            parts.append(format_finding(finding))
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Post an Argus static review to a Gitea PR.")
    parser.add_argument("--repo-owner", required=True)
    parser.add_argument("--repo-name", required=True)
    parser.add_argument("--pr", required=True, type=int, help="pull request number")
    parser.add_argument("--findings", required=True, help="JSON report from argus_review.py --json")
    parser.add_argument("--dry-run", action="store_true", help="print the comment instead of posting it")
    args = parser.parse_args()

    report_path = Path(args.findings)
    if not report_path.is_file():
        print(f"[error] findings file not found: {report_path}", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))

    comment = build_comment(report)

    if args.dry_run:
        print(comment)
        return 0

    token = os.environ.get("GITEA_TOKEN", "").strip()
    if not token:
        print("[error] GITEA_TOKEN is not set", file=sys.stderr)
        return 1

    path = f"/api/v1/repos/{args.repo_owner}/{args.repo_name}/issues/{args.pr}/comments"
    try:
        result = api_request("POST", path, token, {"body": comment})
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    comment_id = result.get("id") if isinstance(result, dict) else "?"
    total = report.get("total_issues", 0)
    print(f"[argus] posted review to PR #{args.pr} (comment id={comment_id}, {total} issue(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
