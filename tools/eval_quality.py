#!/usr/bin/env python3
"""
eval_quality.py — Argus Quality Engine V1 (precision / recall / F1 + gates)

Computes suite-level quality metrics from the fixture regression suite and
enforces regression gates against a committed baseline:

    Precision = TP / (TP + FP)
    Recall    = TP / (TP + FN)
    F1        = 2 * P * R / (P + R)

where, aggregated over all active fixtures:

    TP  = expected [findings] keywords matched in Argus output
    FN  = expected [findings] keywords NOT matched
    FP  = must-not-flag violations, plus every finding in a zero-expectation
          fixture (false-positives/ fixtures declare all-zero counts, so any
          finding there is a false positive)

Modes:
  (default)        run fixtures and print the quality report
  --gate           like default, then FAIL (exit 1) if any metric regressed vs
                   the committed baseline (config/quality-baseline.json) or if
                   the fixture suite itself failed
  --update-baseline  write current metrics to config/quality-baseline.json
                   (use only after intentional, verified improvements)
  --category NAME  limit to one fixture category
  --json FILE      write the full quality report to FILE

Usage:
  python3 tools/eval_quality.py
  python3 tools/eval_quality.py --gate
  python3 tools/eval_quality.py --update-baseline
  python3 tools/eval_quality.py --category design-tokens --json dist/quality-report.json

Exit codes:
  0 — pass (or baseline updated)
  1 — gate failure / fixture failure
  2 — usage / configuration error (no fixtures, missing baseline, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Reuse the fixture runner's discovery / parse / invoke / validate machinery
# so the quality metrics are computed over exactly what CI validates.
import run_fixture_tests as rft

REPO_ROOT = rft.REPO_ROOT
BASELINE_PATH = REPO_ROOT / "config" / "quality-baseline.json"

# Allowed degradation vs baseline before the gate fails. Static heuristic mode
# is deterministic; the epsilon absorbs only rounding / benign LLM variance.
GATE_EPSILON = 0.01


def _c(code: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    codes = {"green": "32", "red": "31", "yellow": "33", "bold": "1"}
    return f"\033[{codes.get(code, '0')}m{text}\033[0m"


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_metrics(results: list[rft.FixtureResult],
                    expected_map: dict[Path, rft.ExpectedFile]) -> dict:
    """Aggregate TP / FP / FN and derive precision / recall / F1.

    ``expected_map`` maps fixture path -> parsed ExpectedFile so FN can be
    derived (unmatched expected findings). A fixture is "zero-expectation"
    when it declares no [findings] and all-zero [counts]; any finding there
    counts as a false positive.
    """
    tp = fp = fn = 0
    by_category: dict[str, dict] = {}
    fixture_details: list[dict] = []

    for result in results:
        if result.skipped:
            continue
        expected = expected_map.get(result.fixture)
        if expected is None:
            continue

        actual_findings = sum(
            1 for line in result.argus_output.splitlines()
            if any(f"[{s}]" in line for s in rft.SEVERITY_ORDER)
        )

        zero_expectation = (sum(expected.counts.values()) == 0) and not expected.findings

        # FP: must-not-flag violations + every finding in zero-expectation fixtures.
        fp_fixture = result.fp_count + (actual_findings if zero_expectation else 0)
        # TP / FN: matched vs unmatched expected [findings] keywords.
        tp_fixture = result.tp_count
        fn_fixture = max(0, len(expected.findings) - tp_fixture)

        tp += tp_fixture
        fp += fp_fixture
        fn += fn_fixture

        cat = expected.fixture_path.parent.name
        cat_agg = by_category.setdefault(cat, {"tp": 0, "fp": 0, "fn": 0})
        cat_agg["tp"] += tp_fixture
        cat_agg["fp"] += fp_fixture
        cat_agg["fn"] += fn_fixture

        fixture_details.append({
            "fixture": str(expected.fixture_path.relative_to(REPO_ROOT)
                           if expected.fixture_path.resolve().is_relative_to(REPO_ROOT)
                           else expected.fixture_path),
            "category": cat,
            "tp": tp_fixture, "fp": fp_fixture, "fn": fn_fixture,
            "passed": result.passed,
        })

    def _rates(t: int, p: int, n: int) -> dict:
        precision = (t / (t + p)) if (t + p) else 1.0
        recall = (t / (t + n)) if (t + n) else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        return {"tp": t, "fp": p, "fn": n,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4)}

    return {
        "fixture_count": len([r for r in results if not r.skipped]),
        "overall": _rates(tp, fp, fn),
        "by_category": {cat: _rates(a["tp"], a["fp"], a["fn"]) for cat, a in sorted(by_category.items())},
        "fixtures": fixture_details,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        print(f"[error] baseline not found: {BASELINE_PATH} — run "
              f"'python3 tools/eval_quality.py --update-baseline' first", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[error] cannot read baseline {BASELINE_PATH}: {exc}", file=sys.stderr)
        sys.exit(2)


def write_baseline(metrics: dict) -> None:
    data = {
        "precision": metrics["overall"]["precision"],
        "recall": metrics["overall"]["recall"],
        "f1": metrics["overall"]["f1"],
        "tp": metrics["overall"]["tp"],
        "fp": metrics["overall"]["fp"],
        "fn": metrics["overall"]["fn"],
        "fixture_count": metrics["fixture_count"],
        "generated_at": metrics["generated_at"],
    }
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Baseline updated: {BASELINE_PATH}")


def gate_check(metrics: dict) -> list[str]:
    """Return a list of gate failures (empty = pass)."""
    base = load_baseline()
    cur = metrics["overall"]
    failures: list[str] = []

    if cur["precision"] < base["precision"] - GATE_EPSILON:
        failures.append(
            f"precision {cur['precision']:.4f} < baseline {base['precision']:.4f} "
            f"(epsilon {GATE_EPSILON})"
        )
    if cur["recall"] < base["recall"] - GATE_EPSILON:
        failures.append(
            f"recall {cur['recall']:.4f} < baseline {base['recall']:.4f} "
            f"(epsilon {GATE_EPSILON})"
        )
    if cur["f1"] < base["f1"] - GATE_EPSILON:
        failures.append(
            f"f1 {cur['f1']:.4f} < baseline {base['f1']:.4f} "
            f"(epsilon {GATE_EPSILON})"
        )
    if cur["fp"] > base["fp"]:
        failures.append(
            f"false positives {cur['fp']} > baseline {base['fp']} (FP must never increase)"
        )
    return failures


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_report(metrics: dict, baseline: dict | None = None) -> None:
    o = metrics["overall"]
    prec = f"{o['precision']:.4f}"
    rec = f"{o['recall']:.4f}"
    f1 = f"{o['f1']:.4f}"
    print(_c("bold", "── Quality Report ───────────────────────────────────────"))
    print(f"  Fixtures: {metrics['fixture_count']}")
    print(f"  Precision: {_c('green', prec)}  ({o['tp']} TP / {o['tp'] + o['fp']} flagged)")
    print(f"  Recall:    {_c('green', rec)}  ({o['tp']} TP / {o['tp'] + o['fn']} expected)")
    print(f"  F1:        {_c('green', f1)}")
    if baseline is not None:
        bp = baseline.get("precision", 0)
        br = baseline.get("recall", 0)
        bf = baseline.get("f1", 0)
        bfp = baseline.get("fp", 0)
        print(_c("bold", "  ── vs baseline ──"))
        print(f"  precision Δ {o['precision'] - bp:+.4f}  "
              f"recall Δ {o['recall'] - br:+.4f}  "
              f"f1 Δ {o['f1'] - bf:+.4f}  "
              f"fp Δ {o['fp'] - bfp:+d}")
    print(_c("bold", "  ── by category ──"))
    for cat, m in metrics["by_category"].items():
        cprec = f"{m['precision']:.4f}"
        crec = f"{m['recall']:.4f}"
        print(f"  {cat:<18} precision {cprec}  recall {crec}  "
              f"({m['tp']}TP/{m['fp']}FP/{m['fn']}FN)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Argus Quality Engine — precision/recall/F1 + regression gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--gate", action="store_true", help="Enforce regression gates vs baseline")
    parser.add_argument("--update-baseline", action="store_true", help="Write current metrics as the new baseline")
    parser.add_argument("--category", default=None, help="Restrict to one fixture category")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write quality report JSON to FILE")
    parser.add_argument("--model", default=None, help="LLM model (default: primary from config/free-models.yml)")
    parser.add_argument("--fallback-models", default=None, help="Comma-separated fallback queue")
    args = parser.parse_args()

    model = args.model or rft.default_primary_model()
    fallback = args.fallback_models or rft.default_fallback_models()

    pairs = rft.discover_fixtures(category=args.category)
    if not pairs:
        print("[error] no fixtures found", file=sys.stderr)
        return 2

    expected_map: dict[Path, rft.ExpectedFile] = {}
    results: list[rft.FixtureResult] = []
    fixture_failures = 0

    for fixture_path, expected_path in pairs:
        try:
            expected = rft.parse_expected(expected_path)
        except (ValueError, FileNotFoundError) as exc:
            results.append(rft.FixtureResult(fixture=fixture_path, passed=False,
                                             errors=[f"Failed to parse .expected: {exc}"]))
            fixture_failures += 1
            continue
        expected_map[fixture_path] = expected

        argus_output = rft.run_argus_on_fixture(
            fixture_path, model=model, verbose=False,
            fallback_models=fallback, token_system="auto",
        )
        static_mode = rft._find_opencode() is None
        result = rft.validate_output(expected, argus_output, tolerance=0 if static_mode else 1)
        results.append(result)
        if not result.passed:
            fixture_failures += 1

    metrics = compute_metrics(results, expected_map)

    baseline = None
    if args.gate:
        baseline = load_baseline()
    elif args.update_baseline and BASELINE_PATH.exists():
        baseline = load_baseline()
    print_report(metrics, baseline)

    if args.output_json:
        out = {"metrics": metrics, "fixture_failures": fixture_failures}
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"JSON report written to {args.output_json}")

    if args.update_baseline:
        write_baseline(metrics)
        return 0

    if fixture_failures:
        print(_c("red", f"✗ {fixture_failures} fixture(s) failed — quality metrics unreliable"))
        return 1

    if args.gate:
        failures = gate_check(metrics)
        if failures:
            print(_c("red", "── Quality GATE FAILED ──"))
            for f in failures:
                print(_c("red", f"  ✗ {f}"))
            print(_c("red", "  If the change intentionally improves quality, run: make eval-baseline"))
            return 1
        print(_c("green", "✓ Quality gates passed"))

    return 0


if __name__ == "__main__":
    sys.exit(main())