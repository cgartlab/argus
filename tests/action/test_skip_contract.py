#!/usr/bin/env python3
"""Regression test: a missing dependency must be reported as SKIP, not a failure.

Background (issue #208)
-----------------------
`validate_action.main()` decides a check failed with:

    failed = {k: v for k, v in checks.items()
              if v and not all(str(p).startswith("SKIP: ") for p in v)}

So the literal prefix `SKIP: ` is the *only* signal that distinguishes
"could not run" from "ran and found problems". Three checks used to say
"skipped" in prose without the prefix, which meant running the validator
without bash (or without PyYAML) reported a bogus failure and exited 1 —
sending the reader to inspect action.yml for a bug that was actually a
missing tool on their machine.

This test locks the contract so it cannot regress.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import validate_action as va  # noqa: E402


def classify(checks: dict[str, list[str]]) -> dict[str, list[str]]:
    """Mirror main()'s failure classification exactly."""
    return {
        k: v
        for k, v in checks.items()
        if v and not all(str(p).startswith("SKIP: ") for p in v)
    }


class SkipContractTest(unittest.TestCase):
    """Every 'could not run' path must be classified as a skip."""

    @classmethod
    def setUpClass(cls) -> None:
        action = va._load_action(va.ACTION_FILE)
        cls.steps = va._steps(action)

    def test_shell_syntax_skips_without_bash(self) -> None:
        result = va.check_shell_syntax(self.steps, None)
        self.assertTrue(result, "expected an explanatory message, got no output")
        self.assertTrue(
            all(str(p).startswith("SKIP: ") for p in result),
            f"missing bash must be a SKIP, got: {result}",
        )
        self.assertEqual({}, classify({"shell_syntax": result}))

    def test_quarantine_roundtrip_skips_without_bash(self) -> None:
        result = va.run_quarantine_roundtrip(self.steps, None)
        self.assertTrue(result, "expected an explanatory message, got no output")
        self.assertTrue(
            all(str(p).startswith("SKIP: ") for p in result),
            f"missing bash must be a SKIP, got: {result}",
        )
        self.assertEqual({}, classify({"quarantine_roundtrip": result}))

    def test_no_bash_run_exits_zero(self) -> None:
        """The whole validator must succeed when bash is unavailable.

        `_bash_available` is patched to return None, which is what a machine
        without bash (or with only the Microsoft Store stub) sees.
        """
        original = va._bash_available
        try:
            va._bash_available = lambda: None  # type: ignore[assignment]
            exit_code = va.main([])
        finally:
            va._bash_available = original
        self.assertEqual(
            0,
            exit_code,
            "validate_action.py must exit 0 when bash is missing "
            "(the checks are skipped, not failed)",
        )

    def test_real_failures_still_fail(self) -> None:
        """Guard against 'fix it by making everything a skip'."""
        bogus = {"shell_syntax": ["step 'x' has a syntax error"]}
        self.assertEqual(bogus, classify(bogus))


if __name__ == "__main__":
    unittest.main(verbosity=2)
