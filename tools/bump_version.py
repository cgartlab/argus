#!/usr/bin/env python3
"""
Bump the version in VERSION and optionally prepend a CHANGELOG entry.

Usage:
    python3 tools/bump_version.py patch   # 0.1.0 → 0.1.1
    python3 tools/bump_version.py minor   # 0.1.0 → 0.2.0
    python3 tools/bump_version.py major   # 0.1.0 → 1.0.0
"""

import re
import sys
from datetime import date


def read_version() -> str:
    with open("VERSION") as f:
        return f.read().strip()


def write_version(ver: str) -> None:
    with open("VERSION", "w") as f:
        f.write(ver + "\n")


def bump(ver: str, kind: str) -> str:
    major, minor, patch = ver.split(".")
    m, n, p = int(major), int(minor), int(patch)
    if kind == "major":
        return f"{m+1}.0.0"
    elif kind == "minor":
        return f"{m}.{n+1}.0"
    else:
        return f"{m}.{n}.{p+1}"


def prepend_changelog(ver: str) -> bool:
    today = date.today().isoformat()
    with open("CHANGELOG.md") as f:
        content = f.read()

    if re.search(rf"^## \[{re.escape(ver)}\]", content, re.MULTILINE):
        print(f"CHANGELOG already has [{ver}] section — skipping prepend")
        return False

    entry = (
        f"## [{ver}] — {today}\n\n"
        "### Added\n\n"
        "### Changed\n\n"
        "### Fixed\n\n"
        "### Removed\n\n"
        "---\n\n"
    )
    with open("CHANGELOG.md", "w") as f:
        f.write(entry + content)
    return True


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Usage: python3 tools/bump_version.py <patch|minor|major>")
        sys.exit(1)

    kind = sys.argv[1]
    old_ver = read_version()
    new_ver = bump(old_ver, kind)

    print(f"Bumping: {old_ver} → {new_ver}")

    if prepend_changelog(new_ver):
        print(f"CHANGELOG.md: added [{new_ver}] section")

    write_version(new_ver)
    print(f"VERSION: updated to {new_ver}")
    print(f"Run: git add VERSION CHANGELOG.md")


if __name__ == "__main__":
    main()
