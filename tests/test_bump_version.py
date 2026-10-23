#!/usr/bin/env python3
"""Regression test: bump_version.py must promote [Unreleased] into a real section.

Background
----------
The promote logic matched `^## [Unreleased]\\n`. The real heading carries a
compare link — `## [Unreleased](https://.../compare/v0.6.6...main)` — so the
pattern never matched. Every bump fell through to the "no Unreleased block"
branch, which prepended an *empty* template above `# Changelog`, leaving the
written notes stranded under `[Unreleased]` forever.

`make release` extracts release notes by reading the version section, so the
published notes would be an empty skeleton while the real content sat below it.

This test drives the real function against a fixture shaped like the actual
CHANGELOG and asserts the outcome.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_bump_module():
    spec = importlib.util.spec_from_file_location(
        "bump_version_under_test", REPO_ROOT / "tools" / "bump_version.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# Shaped like the real file: preamble, then [Unreleased] with a compare link
# and real notes, then the previous release.
FIXTURE = """# Changelog

本文件记录 argus 的所有显著变更。

## [Unreleased](https://github.com/example/compare/v1.0.0...main)

> **一句话概括**：这次修了某个东西。

### Fixed

- something important

---

## [1.0.0](https://github.com/example/compare/v0.9.0...v1.0.0) — 2026-01-01

> previous release
"""


class BumpPromotesUnreleasedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.changelog = Path(self.tmp.name) / "CHANGELOG.md"
        self.changelog.write_text(FIXTURE, encoding="utf-8")
        self.original_cwd = Path.cwd()
        import os

        os.chdir(self.tmp.name)
        self.addCleanup(lambda: os.chdir(self.original_cwd))
        self.mod = _load_bump_module()

    def test_promotes_in_place(self) -> None:
        promoted = self.mod.prepend_changelog("1.1.0")
        self.assertTrue(promoted, "prepend_changelog returned False")
        text = self.changelog.read_text(encoding="utf-8")

        # The new section exists and carries the real notes.
        self.assertRegex(text, r"(?m)^## \[1\.1\.0\]")
        self.assertIn("something important", text.split("## [1.0.0]")[0])

        # The file still starts with its preamble, not with a version heading.
        self.assertTrue(
            text.startswith("# Changelog"),
            "the version section must not be placed above `# Changelog`",
        )

        # No empty skeleton left behind.
        self.assertNotIn("## [Unreleased]", text)
        for empty_section in ("### Added\n\n### Changed", "### Removed\n\n---"):
            self.assertNotIn(empty_section, text)

    def test_preserves_previous_release(self) -> None:
        self.mod.prepend_changelog("1.1.0")
        text = self.changelog.read_text(encoding="utf-8")
        self.assertIn("## [1.0.0]", text)
        self.assertIn("previous release", text)

    def test_idempotent(self) -> None:
        self.assertTrue(self.mod.prepend_changelog("1.1.0"))
        self.assertFalse(
            self.mod.prepend_changelog("1.1.0"),
            "running the same bump twice must not add a second section",
        )
        text = self.changelog.read_text(encoding="utf-8")
        self.assertEqual(1, len(re.findall(r"(?m)^## \[1\.1\.0\]", text)))


class BumpWithoutUnreleasedTest(unittest.TestCase):
    """With no [Unreleased] block the new section goes below the preamble."""

    def test_inserts_after_preamble(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        changelog = Path(tmp.name) / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\nintro\n\n## [1.0.0] — 2026-01-01\n\nnotes\n",
            encoding="utf-8",
        )
        import os

        original = Path.cwd()
        os.chdir(tmp.name)
        self.addCleanup(lambda: os.chdir(original))
        mod = _load_bump_module()

        mod.prepend_changelog("1.1.0")
        text = changelog.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Changelog"))
        self.assertLess(text.index("intro"), text.index("## [1.1.0]"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
