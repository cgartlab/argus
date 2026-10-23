#!/usr/bin/env python3
"""
Bump the version in VERSION, prepend a CHANGELOG entry, and sync all version locations.

VERSION is the single source of truth. After a bump the following are synced:
  - VERSION                          → written with the new version
  - CHANGELOG.md                     → existing `## [Unreleased]` block is promoted in
                                       place to the new `## [x.y.z]` section, so
                                       unreleased notes are never orphaned; if no
                                       [Unreleased] block exists, an empty section is
                                       inserted after the file's preamble
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

    # Promote an existing [Unreleased] block into the new version section, in
    # place. Without this, a fresh empty section would be inserted elsewhere and
    # the notes would end up orphaned under the wrong version.
    #
    # The heading carries a compare link — `## [Unreleased](.../compare/...)` —
    # so a pattern anchored with `\n` right after `]` never matched, and every
    # bump took the else branch below: an empty section appeared at the very top
    # of the file, above `# Changelog`. Match the heading prefix only, then skip
    # to the end of that line.
    m = re.search(r"^## \[Unreleased\]", content, re.MULTILINE)
    if m:
        start = m.start()
        eol = content.find("\n", m.end())
        if eol == -1:
            eol = len(content)
        tail = content[eol:]
        nxt = re.search(r"^## \[", tail, re.MULTILINE)
        end = eol + (nxt.start() if nxt else len(tail))
        header, _, body = content[start:end].partition("\n")
        # Drop a trailing "---" separator that already closes the block, if any.
        body = re.sub(r"\n---\s*\n?$", "", body)
        # Preserve the compare link: the real heading looks like
        # `## [Unreleased](https://.../compare/vX.Y.Z...main)`. Dropping it
        # would make every released heading differ from the rest of the file
        # and require a manual fix (0.6.7 needed one).
        heading = f"## [{ver}] — {today}"
        link = re.search(r"\((https?://[^)]+)\)", header)
        if link:
            url = re.sub(r"\.\.\.main$", f"...v{ver}", link.group(1))
            url = re.sub(r"\.\.\.v[0-9][^)]*$", f"...v{ver}", url)
            heading = f"## [{ver}]({url}) — {today}"
        new_block = f"{heading}\n{body}".rstrip() + "\n\n---\n\n"
        # Insert where [Unreleased] was, NOT at the top of the file: the file
        # opens with `# Changelog` and an explanation, and a version section
        # above that preamble leaves the summary block with no heading above it
        # (validate_versioning.py flags exactly that).
        content = content[:start] + new_block + content[end:]
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
        # Insert after the file's preamble (the `# Changelog` header and its
        # explanation), never above it.
        anchor = re.search(r"^## \[", content, re.MULTILINE)
        if anchor:
            content = content[:anchor.start()] + entry + content[anchor.start():]
        else:
            content = content.rstrip() + "\n\n" + entry
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
