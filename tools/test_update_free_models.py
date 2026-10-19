#!/usr/bin/env python3
"""
test_update_free_models.py — prove refresh() filters out deprecated models.

Regression pinned by task: argus-refresh-skip-deprecated

Bug
---
The OpenCode Zen API lists models that are dead at the gateway (e.g. disabled
or renamed). Before this fix, refresh() would still propose those dead models
in the fallback queue, and check() would reject the generated config. The
weekly update-free-models workflow's --check step therefore failed before the
create-pull-request step, and the workflow never pushed.

The fix moves the deprecated filter earlier: refresh() drops models marked
deprecated in config/model-scores.yml before computing primary and fallback.
check() still validates the generated config (defense in depth), but it no
longer has to reject a deprecated model — refresh() never proposes one.

Test scenarios
--------------
1. Deprecated models in live_free are excluded from primary and fallback.
2. Non-deprecated models in live_free are preserved.
3. If the current primary is deprecated, refresh() re-selects a non-deprecated
   primary.

No LLM, no network: stdlib only (unittest + unittest.mock).

Run:
    python tools/test_update_free_models.py

Exit codes:
    0 — all tests passed
    1 — one or more tests failed
"""

from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from update_free_models import refresh  # noqa: E402


# Model IDs used across the scenarios. The deprecated set mirrors what
# config/model-scores.yml flags as deprecated in PR #181.
BEAM = "opencode/beam-free"
DEEPSEEK = "opencode/deepseek-v4-flash-free"
JEVER = "opencode/jev-1.13-free"
NEMO = "opencode/nemotron-3.5-lightning-free"


def _entry(score: float, benchmark: str, deprecated: bool = False) -> dict:
    """Build a minimal model-scores entry (enough for composite_score + filter)."""
    return {
        "score": score,
        "benchmark": benchmark,
        "source": "test://",
        "confidence": "low" if deprecated else "high",
        "deprecated": deprecated,
    }


def _run_refresh(live_free: set[str], current_config: dict, scores: dict):
    """Run refresh(dry_run=False) with all I/O mocked.

    Returns (return_code, write_call_args). write_call_args is None when
    refresh() short-circuits with no changes (_write_config was not called).
    """
    with mock.patch(
        "update_free_models._fetch_live_free_models", return_value=live_free
    ), mock.patch(
        "update_free_models._find_opencode", return_value=None
    ), mock.patch(
        "update_free_models._parse_config", return_value=current_config
    ), mock.patch(
        "update_free_models._load_model_scores", return_value=scores
    ), mock.patch(
        "update_free_models._write_config"
    ) as write_mock:
        rc = refresh(dry_run=False)
    return rc, write_mock.call_args


class RefreshDeprecatedFilterTest(unittest.TestCase):
    """refresh() drops deprecated models from live_free before primary/fallback."""

    # ---- 1. deprecated models in live_free are excluded -----------------------
    def test_deprecated_models_excluded_from_primary_and_fallback(self):
        """Deprecated models (nemotron, jev) must not appear in primary or fallback."""
        live_free = {BEAM, DEEPSEEK, NEMO, JEVER}
        current_config = {"primary": BEAM, "fallback_models": ""}
        scores = {
            BEAM: _entry(70.7, "swebench_verified"),
            DEEPSEEK: _entry(79.0, "swebench_verified"),
            NEMO: _entry(51.6, "swebench_verifiable", deprecated=True),
            JEVER: _entry(0.0, "none", deprecated=True),
        }
        rc, call = _run_refresh(live_free, current_config, scores)
        self.assertIn(rc, (0, 1), f"refresh() should succeed (0 or 1), got {rc!r}")
        self.assertIsNotNone(call, "refresh() should have written the config")
        written_primary = call.args[1]
        written_fallback = list(call.args[2])
        for deprecated_mid in (NEMO, JEVER):
            self.assertNotIn(
                deprecated_mid, [written_primary] + written_fallback,
                f"deprecated model {deprecated_mid} must not be in primary or fallback",
            )
        self.assertEqual(written_primary, BEAM,
                         "current non-deprecated primary should be preserved")
        self.assertEqual(written_fallback, [DEEPSEEK],
                         "non-deprecated fallback should be preserved")

    # ---- 2. non-deprecated models in live_free are preserved ------------------
    def test_non_deprecated_models_preserved(self):
        """When no models are deprecated, all live models survive the filter."""
        live_free = {BEAM, DEEPSEEK}
        current_config = {"primary": BEAM, "fallback_models": ""}
        scores = {
            BEAM: _entry(70.7, "swebench_verified"),
            DEEPSEEK: _entry(79.0, "swebench_verified"),
        }
        rc, call = _run_refresh(live_free, current_config, scores)
        self.assertIn(rc, (0, 1), f"refresh() should succeed (0 or 1), got {rc!r}")
        self.assertIsNotNone(call, "refresh() should have written the config")
        written_primary = call.args[1]
        written_fallback = list(call.args[2])
        self.assertEqual(written_primary, BEAM,
                         "non-deprecated primary should be preserved")
        self.assertIn(DEEPSEEK, written_fallback,
                      "non-deprecated model should appear in fallback")
        self.assertEqual(written_fallback, [DEEPSEEK])

    # ---- 3. current primary is deprecated → re-selected -----------------------
    def test_primary_reselected_when_deprecated(self):
        """If the current primary is deprecated, refresh() picks a non-deprecated one."""
        live_free = {BEAM, DEEPSEEK}
        current_config = {"primary": BEAM, "fallback_models": DEEPSEEK}
        scores = {
            BEAM: _entry(70.7, "swebench_verified", deprecated=True),
            DEEPSEEK: _entry(79.0, "swebench_verified"),
        }
        rc, call = _run_refresh(live_free, current_config, scores)
        self.assertIn(rc, (0, 1), f"refresh() should succeed (0 or 1), got {rc!r}")
        self.assertIsNotNone(call, "refresh() should have written the config")
        written_primary = call.args[1]
        written_fallback = list(call.args[2])
        self.assertNotEqual(written_primary, BEAM,
                            "deprecated primary must be re-selected")
        self.assertEqual(written_primary, DEEPSEEK,
                         "re-selected primary should be the non-deprecated model")
        self.assertNotIn(BEAM, written_fallback,
                         "deprecated model must not be in fallback")


if __name__ == "__main__":
    unittest.main()
