#!/usr/bin/env python3
"""
Prepare and validate an Argus skill package for SkillHub publishing.

The SkillHub CLI expects a Skill directory with a valid SKILL.md. This helper
does the repo-specific work before CI runs `skillhub publish`:
  1. extract dist/argus-skill-v{VERSION}.zip into a clean directory
  2. validate required SkillHub frontmatter fields
  3. write a one-line changelog from the current CHANGELOG section

It does not contact SkillHub and does not need the API key. CI still runs
`skillhub login`, `skillhub publish --dry-run`, and `skillhub publish`.

Shared machinery lives in tools/_skill_publish.py.

Usage:
    python3 tools/publish_skillhub.py prepare dist/argus-skill-v0.5.3.zip \
        --out dist/skillhub-argus --changelog-out /tmp/argus-changelog.txt
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _skill_publish import (
    SEMVER_RE,
    changelog_summary,
    extract_skill_zip,
    fail,
    read_frontmatter,
    resolve_version,
)

REQUIRED_FRONTMATTER = ("slug", "displayName", "version", "description")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,126}[a-z0-9])?$")


def validate_frontmatter(fields: dict[str, str]) -> None:
    missing = [field for field in REQUIRED_FRONTMATTER if not fields.get(field)]
    if missing:
        fail(f"SKILL.md missing required SkillHub field(s): {', '.join(missing)}")

    slug = fields["slug"]
    version = fields["version"]
    if len(slug) < 2 or len(slug) > 128:
        fail(f"slug must be 2-128 chars, got {len(slug)}")
    if not SLUG_RE.fullmatch(slug):
        fail(f"slug must be kebab-case, got {slug!r}")
    if not SEMVER_RE.fullmatch(version):
        fail(f"version must be valid SemVer, got {version!r}")

    print(f"SkillHub metadata ok: {fields['displayName']} ({slug}@{version})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Argus for SkillHub publish")
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("skill_zip", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Directory to publish from")
    parser.add_argument("--changelog-out", type=Path, help="Optional file for publish --changelog")
    parser.add_argument("--version", help="Expected version; defaults to VERSION file")
    args = parser.parse_args()

    repo_root = Path.cwd()
    version = resolve_version(repo_root, args.version)

    extract_skill_zip(args.skill_zip.resolve(), args.out.resolve())
    fields = read_frontmatter(args.out.resolve() / "SKILL.md")
    validate_frontmatter(fields)

    if fields["version"] != version:
        fail(f"SKILL.md version {fields['version']} != VERSION {version}")

    if args.changelog_out:
        summary = changelog_summary(repo_root / "CHANGELOG.md", version)
        args.changelog_out.parent.mkdir(parents=True, exist_ok=True)
        args.changelog_out.write_text(summary + "\n", encoding="utf-8")

    print(f"Publish directory: {args.out.resolve()}")
    if args.changelog_out:
        print(f"Changelog file: {args.changelog_out.resolve()}")


if __name__ == "__main__":
    main()
