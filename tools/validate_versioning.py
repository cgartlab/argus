#!/usr/bin/env python3
"""
Validate versioning consistency: VERSION ↔ CHANGELOG.
"""

import re
import sys

VERSION_FILE = "VERSION"
CHANGELOG_FILE = "CHANGELOG.md"


def read_version() -> str:
    with open(VERSION_FILE) as f:
        return f.read().strip()


def check_changelog_header(version: str) -> None:
    with open(CHANGELOG_FILE) as f:
        content = f.read()
    pattern = rf"^## \[{re.escape(version)}\]"
    if not re.search(pattern, content, re.MULTILINE):
        print(f"FAIL: CHANGELOG missing [{version}] section — run 'make bump-*' first")
        sys.exit(1)
    print(f"  CHANGELOG has [{version}] section")


def check_changelog_content(version: str) -> None:
    with open(CHANGELOG_FILE) as f:
        content = f.read()
    parts = re.split(r"^## ", content, flags=re.MULTILINE)
    body = ""
    for part in parts[1:]:
        if part.startswith(f"[{version}]"):
            lines = part.split("\n")[1:]
            body = "\n".join(lines)
            break
    if not body:
        print("FAIL: Could not find CHANGELOG section")
        sys.exit(1)
    cleaned = re.sub(r"^### \w+\s*$|^- ", "", body, flags=re.MULTILINE).strip()
    if not cleaned:
        print(f"FAIL: CHANGELOG entry for [{version}] is empty — add entries before releasing")
        sys.exit(1)
    print(f"  CHANGELOG entry has content")


def main() -> None:
    print("Versioning checks:")
    version = read_version()
    print(f"  VERSION = {version}")
    check_changelog_header(version)
    check_changelog_content(version)
    print("")
    print("All versioning checks passed")


if __name__ == "__main__":
    main()
