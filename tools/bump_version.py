#!/usr/bin/env python3
"""
Bump the version in VERSION, prepend a CHANGELOG entry, and sync all version locations.

VERSION is the single source of truth. After a bump the following are synced:
  - VERSION                          → written with the new version
  - CHANGELOG.md                     → existing `## [Unreleased]` block is promoted to the
                                       new `## [x.y.z]` section and moved to the top, so
                                       unreleased notes are never orphaned; if no
                                       [Unreleased] block exists, an empty section is
                                       prepended instead
  - AGENTS.md                        → header `**Version:** x.y.z`
  - SKILL.md                         → frontmatter `version: x.y.z`
  - manifest.yaml                    → `version: x.y.z`
  - site/src/data/site.ts            → `version: 'x.y.z'` (website "current version")
  - site/src/content/docs/index.md   → `| Version | x.y.z |` table row (docs site)

If an old version number is not found in a synced file, a warning is printed and
the tool continues (the file may be drifted — fix it manually before release).

Usage:
    python3 tools/bump_version.py patch   # 0.1.0 → 0.1.1
    python3 tools/bump_version.py minor   # 0.1.0 → 0.2.0
    python3 tools/bump_version.py major   # 0.1.0 → 1.0.0
"""

import re
import subprocess
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

    # Promote an existing [Unreleased] block into the new version section and
    # move it to the top. Without this, a fresh empty section would be prepended
    # above the [Unreleased] block and its notes would end up orphaned under the
    # wrong version during the next release.
    m = re.search(r"^## \[Unreleased\]\n", content, re.MULTILINE)
    if m:
        start = m.start()
        tail = content[m.end():]
        nxt = re.search(r"^## \[", tail, re.MULTILINE)
        end = m.end() + (nxt.start() if nxt else len(tail))
        header, _, body = content[start:end].partition("\n")
        # Drop a trailing "---" separator that already closes the block, if any.
        body = re.sub(r"\n---\s*\n?$", "", body)
        new_block = f"## [{ver}] — {today}\n{body}".rstrip() + "\n\n---\n\n"
        content = new_block + content[:start] + content[end:]
        print(f"CHANGELOG.md: promoted [Unreleased] → [{ver}] ({today})")
    else:
        entry = (
            f"## [{ver}] — {today}\n\n"
            "### Added\n\n"
            "### Changed\n\n"
            "### Fixed\n\n"
            "### Removed\n\n"
            "---\n\n"
        )
        content = entry + content
        print(f"CHANGELOG.md: added [{ver}] section")

    with open("CHANGELOG.md", "w", encoding="utf-8") as f:
        f.write(content)
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
        ("site/src/data/site.ts", rf"version:\s*'{re.escape(old_ver)}'", f"version: '{new_ver}'"),
        ("site/src/content/docs/index.md", rf"\| Version \| {re.escape(old_ver)} \|", f"| Version | {new_ver} |"),
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
        print(f"CHANGELOG.md: updated for [{new_ver}] section")

    write_version(new_ver)
    print(f"VERSION: updated to {new_ver}")

    synced = sync_version_files(old_ver, new_ver)
    if synced:
        print(f"Synced {len(synced)} files: {', '.join(synced)}")
    else:
        print("WARNING: no synced files updated (all skipped — check for drift)")

    # Stage the version files so the Makefile's "Files staged" message is
    # truthful and `make release` operates on a committed state.
    files = ["VERSION", "CHANGELOG.md", *synced]
    try:
        subprocess.run(
            ["git", "add", "--", *files],
            check=True, capture_output=True, text=True,
        )
        print(f"Staged {len(files)} file(s): {', '.join(files)}")
    except Exception as e:
        print(
            f"WARNING: could not stage files ({e}) — "
            f"run 'git add {' '.join(files)}' manually"
        )

    print(f"Next: write CHANGELOG entries for [{new_ver}], review, then commit:")
    print(f"  git commit -m \"chore(release): prepare v{new_ver}\"")
    print("Then: make test && make release")


if __name__ == "__main__":
    main()