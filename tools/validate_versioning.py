#!/usr/bin/env python3
"""
Validate versioning consistency across all 5 version locations.

VERSION is the single source of truth. The other 4 locations must match it:
  - VERSION           → source of truth
  - CHANGELOG.md      → latest section `## [x.y.z]` (content must be non-empty)
  - AGENTS.md         → header `**Version:** x.y.z`
  - SKILL.md          → frontmatter `version: x.y.z`
  - manifest.yaml     → `version: x.y.z`

Any mismatch exits non-zero with `FAIL: <file> version <found> != <expected>`.
Run from the repository root (Makefile and CI both call it that way).
"""

import re
import sys

VERSION_FILE = "VERSION"
CHANGELOG_FILE = "CHANGELOG.md"

# path → regex extracting the version number (group 1)
SYNCED_FILES = {
    "AGENTS.md": r"\*\*Version:\*\*\s*([0-9]+\.[0-9]+\.[0-9]+)",
    "SKILL.md": r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
    "manifest.yaml": r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)",
}


def read_version() -> str:
    with open(VERSION_FILE, encoding="utf-8") as f:
        return f.read().strip()


def check_changelog_header(version: str) -> None:
    with open(CHANGELOG_FILE, encoding="utf-8") as f:
        content = f.read()
    pattern = rf"^## \[{re.escape(version)}\]"
    if not re.search(pattern, content, re.MULTILINE):
        print(f"FAIL: CHANGELOG missing [{version}] section — run 'make bump-*' first")
        sys.exit(1)
    print(f"  CHANGELOG has [{version}] section")


def check_changelog_content(version: str) -> None:
    with open(CHANGELOG_FILE, encoding="utf-8") as f:
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


def check_file_version(path: str, pattern: str, expected: str) -> None:
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"FAIL: {path} not found")
        sys.exit(1)
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        print(f"FAIL: {path}: version pattern not found")
        sys.exit(1)
    found = m.group(1)
    if found != expected:
        print(f"FAIL: {path} version {found} != {expected}")
        sys.exit(1)
    print(f"  {path} version {found} ok")


def main() -> None:
    print("Versioning checks:")
    version = read_version()
    print(f"  VERSION = {version}")
    check_changelog_header(version)
    check_changelog_content(version)
    for path, pattern in SYNCED_FILES.items():
        check_file_version(path, pattern, version)
    print("")
    print("All versioning checks passed")


if __name__ == "__main__":
    main()