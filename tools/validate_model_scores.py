#!/usr/bin/env python3
"""
validate_model_scores.py — schema validator for config/model-scores.yml.

Closes issue #101: model-scores.yml is the single source of truth for the
fallback-queue ranking, but a hand-edited entry with a bad `benchmark` value,
a `score` out of range, a missing `source`, or an unknown top-level field
silently breaks the ranking (composite_score() falls back to weight 0) or the
auto-refresher (unknown model → tail of queue, see #90). This tool makes those
mistakes a hard CI failure.

Zero-dependency: reuses _load_model_scores() from tools/update_free_models.py,
which transparently uses PyYAML or the built-in indentation parser. The validator
itself runs pure Python stdlib, so it works on CI runners without extra
pip installs.

Schema (per model entry under `models:`):

  Required fields:
    underlying  : str, non-empty  (human-readable description)
    score       : int or float in [0, 100]
    benchmark   : one of {swebench_verifiable, swebench_verified, swebench_pro,
                          intelligence_index, none}
    source      : str, non-empty URL
    confidence  : one of {high, medium, low}

  Optional fields:
    regions      : list[str]
    deprecated   : bool
    capabilities : list[str]

  Unknown fields are rejected (typo detection — the parser is indentation-based
  and would otherwise silently drop them).

Model id format (top-level key): `opencode/<id>-free`.

Usage:
  python3 tools/validate_model_scores.py            # validate, human-readable
  python3 tools/validate_model_scores.py --check    # alias for the default
  python3 tools/validate_model_scores.py --json     # machine-readable JSON

Exit codes:
  0 — schema valid
  1 — one or more schema violations
  2 — usage / runtime error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# Force UTF-8 so non-ASCII log glyphs (✓ ✗ ⚠) never crash on Windows GBK
# consoles; CI runners (UTF-8) are unaffected.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

MODEL_ID_RE = re.compile(r"^opencode/[A-Za-z0-9._-]+-free$")
SOURCE_RE = re.compile(r"^https?://\S+$")

REQUIRED_FIELDS = {"underlying", "score", "benchmark", "source", "confidence"}
OPTIONAL_FIELDS = {"regions", "deprecated", "capabilities"}
KNOWN_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

VALID_BENCHMARKS = {
    "swebench_verifiable",
    "swebench_verified",
    "swebench_pro",
    "intelligence_index",
    "none",
}
VALID_CONFIDENCE = {"high", "medium", "low"}

EXIT_OK = 0
EXIT_INVALID = 1
EXIT_USAGE = 2


def _load_raw_scores() -> dict[str, dict[str, Any]]:
    """Load scores via the shared loader. Import-time cache reset so each
    invocation reads a fresh copy of the file (the loader memoises on module
    import, which matters for tests).
    """
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    import update_free_models  # noqa: WPS433  (local repo module, by design)
    update_free_models._SCORES_CACHE = None  # bypass module-level memo
    return update_free_models._load_model_scores()


def _validate_entry(mid: str, fields: dict[str, Any]) -> list[str]:
    """Return a list of violation strings for a single model entry."""
    errs: list[str] = []

    if not isinstance(fields, dict):
        return [f"{mid}: entry must be a mapping, got {type(fields).__name__}"]

    # Top-level key format
    if not MODEL_ID_RE.fullmatch(mid):
        errs.append(
            f"{mid}: invalid model id — must match "
            f"'opencode/<id>-free' (e.g. 'opencode/deepseek-v4-flash-free')"
        )

    # Required fields: presence first
    for f in REQUIRED_FIELDS:
        if f not in fields:
            errs.append(f"{mid}: missing required field '{f}'")

    # Unknown fields: hard reject (typo detector)
    for f in fields:
        if f not in KNOWN_FIELDS:
            errs.append(
                f"{mid}: unknown field '{f}' "
                f"(known: {', '.join(sorted(KNOWN_FIELDS))})"
            )

    # Field-level type + range checks — only run if present
    underlying = fields.get("underlying")
    if "underlying" in fields:
        if not isinstance(underlying, str) or not underlying.strip():
            errs.append(f"{mid}: 'underlying' must be a non-empty string")

    score = fields.get("score")
    if "score" in fields:
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            errs.append(f"{mid}: 'score' must be a number")
        else:
            score_f = float(score)
            if not (0 <= score_f <= 100):
                errs.append(f"{mid}: 'score' must be in [0, 100], got {score_f}")

    benchmark = fields.get("benchmark")
    if "benchmark" in fields:
        if not isinstance(benchmark, str) or benchmark not in VALID_BENCHMARKS:
            errs.append(
                f"{mid}: 'benchmark' must be one of "
                f"{sorted(VALID_BENCHMARKS)}, got {benchmark!r}"
            )

    source = fields.get("source")
    if "source" in fields:
        if not isinstance(source, str) or not SOURCE_RE.match(source):
            errs.append(f"{mid}: 'source' must be an http(s) URL")

    confidence = fields.get("confidence")
    if "confidence" in fields:
        if not isinstance(confidence, str) or confidence not in VALID_CONFIDENCE:
            errs.append(
                f"{mid}: 'confidence' must be one of "
                f"{sorted(VALID_CONFIDENCE)}, got {confidence!r}"
            )

    # Optional field shape checks (only when present)
    regions = fields.get("regions")
    if "regions" in fields:
        if not isinstance(regions, list) or not all(
            isinstance(x, str) for x in regions
        ):
            errs.append(f"{mid}: 'regions' must be a list of strings")

    deprecated = fields.get("deprecated")
    if "deprecated" in fields:
        if not isinstance(deprecated, bool):
            errs.append(f"{mid}: 'deprecated' must be a boolean")

    capabilities = fields.get("capabilities")
    if "capabilities" in fields:
        if not isinstance(capabilities, list) or not all(
            isinstance(x, str) for x in capabilities
        ):
            errs.append(f"{mid}: 'capabilities' must be a list of strings")

    return errs


def validate() -> tuple[int, list[str], int]:
    """Validate config/model-scores.yml.

    Returns (exit_code, errors, model_count).
    """
    from update_free_models import MODEL_SCORES_PATH  # noqa: WPS433

    if not MODEL_SCORES_PATH.exists():
        return EXIT_INVALID, [
            f"{MODEL_SCORES_PATH.relative_to(REPO_ROOT)} missing — "
            f"required schema source"
        ], 0

    try:
        scores = _load_raw_scores()
    except Exception as exc:  # noqa: BLE001 — broad on purpose: report and exit 1
        return EXIT_INVALID, [f"failed to load scores: {exc!r}"], 0

    if not scores:
        return EXIT_INVALID, ["no models defined under 'models:' — file is empty"], 0

    errors: list[str] = []
    for mid, fields in scores.items():
        errors.extend(_validate_entry(mid, fields))

    if errors:
        return EXIT_INVALID, errors, len(scores)

    return EXIT_OK, [], len(scores)


def _print_human(exit_code: int, errors: list[str], count: int) -> None:
    rel = "config/model-scores.yml"
    if exit_code == EXIT_OK:
        print(f"[validate-model-scores] ✓ {rel}: {count} models valid")
        return
    print(f"[validate-model-scores] ✗ {rel}: {len(errors)} violation(s) "
          f"across {count} model(s):", file=sys.stderr)
    for e in errors:
        print(f"  ✗ {e}", file=sys.stderr)


def _print_json(exit_code: int, errors: list[str], count: int) -> None:
    print(json.dumps(
        {
            "ok": exit_code == EXIT_OK,
            "model_count": count,
            "error_count": len(errors),
            "errors": errors,
        },
        indent=2,
    ))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate config/model-scores.yml against the Argus schema."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="alias for the default behaviour (compat with --check convention)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print JSON output instead of human-readable",
    )
    args = parser.parse_args(argv)

    exit_code, errors, count = validate()

    if args.json:
        _print_json(exit_code, errors, count)
    else:
        _print_human(exit_code, errors, count)

    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(EXIT_USAGE)
    except Exception as exc:  # noqa: BLE001
        print(f"[validate-model-scores] ✗ runtime error: {exc!r}", file=sys.stderr)
        sys.exit(EXIT_USAGE)
