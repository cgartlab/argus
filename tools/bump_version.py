#!/usr/bin/env python3
"""
Bump the version in VERSION, prepend a CHANGELOG entry, and sync all version locations.

VERSION is the single source of truth. After a bump the following are synced:
  - VERSION          → written with the new version
  - CHANGELOG.md     → new `## [x.y.z]` section prepended
  - AGENTS.md        → header `**Version:** x.y.z`
  - SKILL.md         → frontmatter `version: x.y.z`
  - manifest.yaml    → `version: x.y.z`

If an old version number is not found in a synced file, a warning is printed and
the tool continues (the file may be drifted — fix it manually before release).

Usage:
    python3 tools/bump_version.py patch   # 0.1.0 → 0.1.1
    python3 tools/bump_version.py minor   # 0.1.0 → 0.2.0
    python3 tools/bump_version.py major   # 0.1.0 → 1.0.0
"""

import re
import sys
from datetime import date


def read_version() -> str:
    with open("VERSION", encoding="utf-8") as f:
        return f.read().strip()


def write_version(ver: str) -> None:
    with open("VERSION", "w", encoding="utf-8") as f:
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
    with open("CHANGELOG.md", encoding="utf-8") as f:
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
    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(entry + content)
    return True


def sync_version_files(old_ver: str, new_ver: str) -> list[str]:
    """Sync version across AGENTS.md, SKILL.md, manifest.yaml.

    Returns the list of files that were successfully synced.
    A file whose old version number is not found is skipped with a warning.
    """
    synced = []
    targets = [
        ("AGENTS.md", rf"\*\*Version:\*\*\s*{re.escape(old_ver)}", f"**Version:** {new_ver}"),
        ("SKILL.md", rf"^version:\s*{re.escape(old_ver)}", f"version: {new_ver}"),
        ("manifest.yaml", rf"^version:\s*{re.escape(old_ver)}", f"version: {new_ver}"),
    ]
    for path, pattern, replacement in targets:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            print(f"WARNING: {path} not found — skipping")
            continue
        if not re.search(pattern, content, re.MULTILINE):
            print(f"WARNING: {path}: version {old_ver} not found — skipping (check for drift)")
            continue
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{path}: version synced to {new_ver}")
        synced.append(path)
    return synced


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

    synced = sync_version_files(old_ver, new_ver)
    if synced:
        print(f"Synced {len(synced)} files: {', '.join(synced)}")
    else:
        print("WARNING: no synced files updated (all skipped — check for drift)")

    print(f"Run: git add VERSION CHANGELOG.md AGENTS.md SKILL.md manifest.yaml")


if __name__ == "__main__":
    main()