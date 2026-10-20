#!/usr/bin/env python3
"""
Validate versioning consistency across all 7 version locations.

VERSION is the single source of truth. The other 6 locations must match it:
  - VERSION                          → source of truth
  - CHANGELOG.md                     → latest section `## [x.y.z]` (content must be non-empty)
  - AGENTS.md                        → header `**Version:** x.y.z`
  - SKILL.md                         → frontmatter `version: x.y.z`
  - manifest.yaml                    → `version: x.y.z`
  - site/src/data/site.ts            → `version: 'x.y.z'`
  - site/src/content/docs/index.md   → `| Version | x.y.z |`

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
    "site/src/data/site.ts": r"version:\s*'([0-9]+\.[0-9]+\.[0-9]+)'",
    "site/src/content/docs/index.md": r"\| Version \| ([0-9]+\.[0-9]+\.[0-9]+) \|",
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
    print("  CHANGELOG entry has content")


def check_changelog_structure() -> None:
    """Every released version heading must be present, unique, and in order.

    ``check_changelog_header`` only looks for the *current* version, so a
    deleted heading for an older release passes silently — and then
    ``release.yml``'s awk extraction (``## [x.y.z]`` until the next ``## [``)
    folds that older release's body into the newer one's GitHub Release notes.

    Regression: #203 accidentally dropped the ``## [0.6.5]`` heading while
    prepending 0.6.6, so v0.6.6's notes would have republished the 0.6.5
    security fixes (#169/#170) as if they shipped in 0.6.6.

    A lost heading does *not* break ordering (0.6.6 → 0.6.4 is still
    descending), so ordering alone cannot detect it. The reliable signal is an
    **orphan body**: every ``> **一句话概括**`` summary line must sit directly
    under a ``## [x.y.z]`` heading. A body without its heading means the
    heading was deleted.
    """
    with open(CHANGELOG_FILE, encoding="utf-8") as f:
        lines = f.read().splitlines()

    headings = re.findall(r"^## \[(v?[0-9]+\.[0-9]+\.[0-9]+|Unreleased)\]", "\n".join(lines), re.MULTILINE)
    versions = [h.lstrip("v") for h in headings if h != "Unreleased"]

    if not versions:
        print("FAIL: CHANGELOG has no versioned sections")
        sys.exit(1)

    dupes = sorted({v for v in versions if versions.count(v) > 1})
    if dupes:
        print(f"FAIL: CHANGELOG has duplicate section(s): {', '.join(dupes)}")
        sys.exit(1)

    def key(v: str) -> tuple[int, ...]:
        return tuple(int(p) for p in v.split("."))

    for older, newer in zip(versions, versions[1:]):
        if key(older) <= key(newer):
            print(
                f"FAIL: CHANGELOG sections out of order: [{older}] appears above [{newer}] "
                f"— newest must come first"
            )
            sys.exit(1)

    # Orphan-body detection: within each released section, the summary line must
    # belong to a heading. The file preamble also mentions 「一句话概括」 in prose
    # ("每个版本的第一段必须是「一句话概括」"), so only consider lines that sit
    # *after* the first version heading.
    first_heading = None
    for idx, line in enumerate(lines):
        if re.match(r"^## \[(v?[0-9]+\.[0-9]+\.[0-9]+|Unreleased)\]", line):
            first_heading = idx
            break
    if first_heading is None:
        print("FAIL: CHANGELOG has no version headings")
        sys.exit(1)

    for idx in range(first_heading, len(lines)):
        line = lines[idx]
        if "**一句话概括**" not in line:
            continue
        back = idx - 1
        while back >= first_heading and not lines[back].strip():
            back -= 1
        owner = lines[back] if back >= first_heading else ""
        if not re.match(r"^## \[", owner):
            print(
                f"FAIL: CHANGELOG line {idx + 1}: summary block has no version heading "
                f"above it (nearest heading line is: {owner[:60]!r}) — a section "
                f"heading was probably deleted, which would merge two releases' "
                f"notes in release.yml"
            )
            sys.exit(1)

    print(f"  CHANGELOG has {len(versions)} ordered, unique version section(s) "
          f"with no orphaned bodies")


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
    check_changelog_structure()
    for path, pattern in SYNCED_FILES.items():
        check_file_version(path, pattern, version)
    print("")
    print("All versioning checks passed")


if __name__ == "__main__":
    main()