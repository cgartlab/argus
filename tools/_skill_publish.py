#!/usr/bin/env python3
"""
_skill_publish.py — shared helpers for skill-registry publish prep.

Common machinery for `publish_skillhub.py` / `publish_clawhub.py`: SKILL.md
frontmatter parsing, skill-zip extraction, VERSION resolution, and CHANGELOG
summary extraction. Registry-specific validation lives in each wrapper.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

# SemVer 2.0.0 (shared by both registries).
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def read_frontmatter(path: Path) -> dict[str, str]:
    """Parse the top-level YAML frontmatter fields from a SKILL.md file."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        fail("SKILL.md missing YAML frontmatter")

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        # Skip blank lines, comments, and nested keys (e.g. metadata.openclaw).
        if not line or line.startswith("#") or line.startswith(" "):
            continue
        if ":" not in line:
            fail(f"invalid SKILL.md frontmatter line: {line}")
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def extract_skill_zip(archive: Path, out_dir: Path) -> None:
    """Extract the skill package zip into out_dir and require a SKILL.md."""
    if not archive.is_file():
        fail(f"skill package not found: {archive}")

    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(out_dir)

    skill_md = out_dir / "SKILL.md"
    if not skill_md.is_file():
        fail("extracted skill package has no SKILL.md")


def resolve_version(repo_root: Path, explicit: str | None) -> str:
    """Return the explicit version, or read it from the repo VERSION file."""
    if explicit:
        return explicit
    version_file = repo_root / "VERSION"
    if not version_file.is_file():
        fail("VERSION file not found; pass --version")
    return version_file.read_text(encoding="utf-8").strip()


def changelog_summary(changelog_path: Path, version: str) -> str:
    """Return a one-line summary from the CHANGELOG section for `version`."""
    text = changelog_path.read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.MULTILINE)
    body = ""
    for part in parts[1:]:
        if part.startswith(f"[{version}]"):
            body = "\n".join(part.splitlines()[1:])
            break
    if not body:
        fail(f"CHANGELOG.md has no section for v{version}")

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            return re.sub(r"\s+", " ", stripped[2:]).strip()[:500]

    fail(f"CHANGELOG.md section for v{version} has no bullet summary")
