#!/usr/bin/env python3
"""
Prepare and validate an Argus skill package for ClawHub publishing.

ClawHub (the OpenClaw skill registry) publishes from a skill *directory*
containing a valid SKILL.md — not a zip. This helper does the repo-specific
work before CI runs `clawhub skill publish`:
  1. extract dist/argus-skill-v{VERSION}.zip into a clean directory
  2. validate required ClawHub frontmatter (name, description, version)
  3. ensure SKILL.md version matches the VERSION file

It does not contact ClawHub and does not need the API token. CI still runs
`clawhub login`, `clawhub whoami`, and `clawhub skill publish`.

Shared machinery lives in tools/_skill_publish.py.

Note: ClawHub uses the portable `name` field as the routable slug
(@owner/name). The SkillHub-specific `slug` field (cgartlab-argus-design-review)
is intentionally ignored here — ClawHub publishes as @<owner>/argus-design-review.

Usage:
    python3 tools/publish_clawhub.py prepare dist/argus-skill-v0.5.7.zip \
        --out dist/clawhub-argus
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _skill_publish import (
    SEMVER_RE,
    extract_skill_zip,
    fail,
    read_frontmatter,
    resolve_version,
)

# ClawHub requires a portable `name`: 1-64 lowercase letters, digits, or hyphens.
# Must start and end with an alphanumeric (no leading/trailing hyphen).
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$|^[a-z0-9]$")


def validate_frontmatter(fields: dict[str, str]) -> str:
    """Validate ClawHub-required frontmatter and return the ClawHub slug (= name)."""
    required = ("name", "description", "version")
    missing = [field for field in required if not fields.get(field)]
    if missing:
        fail(f"SKILL.md missing required ClawHub field(s): {', '.join(missing)}")

    name = fields["name"]
    if not (1 <= len(name) <= 64):
        fail(f"name must be 1-64 chars, got {len(name)}")
    if not NAME_RE.fullmatch(name):
        fail(f"name must be lowercase kebab-case [a-z0-9-], got {name!r}")

    version = fields["version"]
    if not SEMVER_RE.fullmatch(version):
        fail(f"version must be valid SemVer, got {version!r}")

    description = fields["description"]
    if len(description) < 10:
        fail(
            f"description too short ({len(description)} chars) — "
            "ClawHub uses it as the search summary"
        )

    print(f"ClawHub metadata ok: {name} ({name}@{version})")
    return name


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Argus for ClawHub publish")
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("skill_zip", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Directory to publish from")
    parser.add_argument("--version", help="Expected version; defaults to VERSION file")
    args = parser.parse_args()

    repo_root = Path.cwd()
    version = resolve_version(repo_root, args.version)

    extract_skill_zip(args.skill_zip.resolve(), args.out.resolve())
    fields = read_frontmatter(args.out.resolve() / "SKILL.md")
    slug = validate_frontmatter(fields)

    if fields["version"] != version:
        fail(f"SKILL.md version {fields['version']} != VERSION {version}")

    print(f"Publish directory: {args.out.resolve()}")
    print(f"ClawHub slug: {slug}  (publish as @<owner>/{slug})")


if __name__ == "__main__":
    main()
