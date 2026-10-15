#!/usr/bin/env python3
"""
validate_lessons.py — validate a project lesson file (.argus/LESSON.md)

Ensures the file Argus injects into its review prompt is well-formed and
bounded (a runaway file bloats that project's prompt).

Checks:
  - file parses as a LESSON.md
  - each entry has a unique L-NNN id and the required fields
  - total size <= 6144 bytes (~6 KB) and <= 20 active entries

Usage:
  python3 tools/validate_lessons.py                       # default .argus/LESSON.md
  python3 tools/validate_lessons.py --file .argus/LESSON.md

Exit codes:
  0 — valid (or file absent: treated as valid — no lesson file is the default)
  1 — validation errors
  2 — usage error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MAX_BYTES = 6144
MAX_ENTRIES = 20

ID_RE = re.compile(r"^##\s+(L-\d{3,})\b", re.IGNORECASE)
REQUIRED_FIELDS = ("kind", "trigger", "do not", "instead", "recorded")
VALID_KINDS = {"false-positive", "false-negative", "wrong-fix",
               "missing-dimension", "context"}


def parse_entries(text: str) -> list[dict]:
    """Return a list of {id, title, fields} dicts parsed from the lesson file."""
    entries: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        m = ID_RE.match(raw)
        if m:
            if current is not None:
                entries.append(current)
            current = {"id": m.group(1).upper(), "title": raw[m.end():].strip(" ·\t"),
                       "fields": {}}
            continue
        if current is not None:
            fm = re.match(r"^\s*-\s*([A-Za-z ]+?)\s*:", raw)
            if fm:
                key = fm.group(1).strip().lower()
                # strip trailing inline comment: `value  # explanation`
                value = raw[fm.end():].split("#", 1)[0].strip()
                current["fields"][key] = value
    if current is not None:
        entries.append(current)
    return entries


def validate(path: Path) -> list[str]:
    """Return a list of error messages. Empty list means valid."""
    errors: list[str] = []
    if not path.is_file():
        return []  # absent file is the default — valid

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []  # empty file is valid

    size = len(text.encode("utf-8"))
    if size > MAX_BYTES:
        errors.append(f"file is {size} bytes — exceeds {MAX_BYTES} byte budget; "
                      "promote or delete resolved entries")

    entries = parse_entries(text)
    if len(entries) > MAX_ENTRIES:
        errors.append(f"{len(entries)} entries — exceeds {MAX_ENTRIES} entry budget; "
                      "promote or delete resolved entries")

    if not entries:
        errors.append("no `## L-NNN` entries found — file is not a valid lesson file")

    seen_ids: set[str] = set()
    for e in entries:
        if e["id"] in seen_ids:
            errors.append(f"duplicate lesson id: {e['id']}")
        seen_ids.add(e["id"])
        missing = [f for f in REQUIRED_FIELDS if f not in e["fields"]]
        if missing:
            errors.append(f"{e['id']}: missing field(s): {', '.join(missing)}")
        kind = e["fields"].get("kind", "").strip()
        if kind and kind not in VALID_KINDS:
            errors.append(f"{e['id']}: invalid kind '{kind}' "
                          f"(valid: {sorted(VALID_KINDS)})")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a project lesson file (.argus/LESSON.md)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--file", default=".argus/LESSON.md", metavar="PATH",
                        help="Path to the lesson file (default: .argus/LESSON.md)")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        # absent file is the default — report success, no lesson loaded
        print(f"[argus:lessons] no lesson file at {path} (default — OK)")
        return 0

    errors = validate(path)
    if errors:
        print(f"[argus:lessons] {path}: validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  x {err}", file=sys.stderr)
        return 1

    entries = parse_entries(path.read_text(encoding="utf-8"))
    print(f"[argus:lessons] {path}: valid ({len(entries)} entry/ies, "
          f"{len(path.read_text(encoding='utf-8').encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
