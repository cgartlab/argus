#!/usr/bin/env python3
"""
argus_webhook.py — forward a findings report to a webhook (public API surface)

POSTs a findings JSON report (from tools/argus_review.py --json,
tools/argus_rules.py --json, or tools/eval_quality.py --json) to a custom
endpoint — a Slack/Feishu incoming webhook, an internal dashboard, or any
HTTP service. This is the roadmap's "public API / webhook" item: teams wire
Argus reports into their own systems without waiting for a hosted API.

Usage:
  python3 tools/argus_review.py src/ --json review.json
  python3 tools/argus_webhook.py send review.json --url https://hooks.example.com/argus
  python3 tools/argus_webhook.py send review.json --url ... --token "$WEBHOOK_TOKEN"
  python3 tools/argus_webhook.py send review.json --url ... --dry-run   # print request

Options:
  send <report.json>  the findings JSON report (any JSON object is accepted)
  --url URL           webhook endpoint (required unless --dry-run)
  --token TOKEN       sent as an Authorization: Bearer header (optional)
  --timeout SECONDS   request timeout (default 15)
  --dry-run           print the request (method/url/headers/body) without sending

Exit codes:
  0 — sent (HTTP 2xx) or dry-run
  1 — send failure (HTTP error / network error / unreadable report)
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forward an Argus findings report to a webhook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", nargs="?", choices=["send"], help="send: POST a report to a webhook")
    parser.add_argument("report", nargs="?", metavar="REPORT.json", help="Findings JSON report")
    parser.add_argument("--url", default=None, metavar="URL", help="Webhook endpoint")
    parser.add_argument("--token", default=None, metavar="TOKEN", help="Bearer token (Authorization header)")
    parser.add_argument("--timeout", type=float, default=15.0, metavar="SECONDS", help="Request timeout (default 15)")
    parser.add_argument("--dry-run", action="store_true", help="Print the request without sending")
    args = parser.parse_args()

    if args.command != "send" or not args.report:
        parser.error("provide 'send <report.json>'")

    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"[error] report not found: {report_path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"[error] invalid JSON in {report_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print(f"[error] {report_path}: expected a JSON object report", file=sys.stderr)
        return 1

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Bearer {args.token}"
    url = args.url or ""

    if args.dry_run:
        print(f"POST {url}")
        for key, value in headers.items():
            print(f"  {key}: {value}")
        print(f"  body ({len(body)} bytes):")
        print(body.decode("utf-8", "replace"))
        return 0

    if not url:
        parser.error("--url is required (or use --dry-run)")

    req = urllib.request.Request(url, data=body, method="POST")
    for key, value in headers.items():
        req.add_header(key, value)

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            status = resp.status
            resp_body = resp.read(500).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", "replace")
        print(f"[error] webhook returned HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[error] webhook request failed: {exc}", file=sys.stderr)
        return 1

    print(f"ok: webhook responded {status} ({len(body)} bytes sent)")
    if resp_body:
        print(f"  response: {resp_body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())