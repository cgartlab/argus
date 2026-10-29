#!/usr/bin/env python3
"""Probe ONE opencode free model for callability + a quality smoke.

Temporary diagnostic (PR B of the model-queue expansion): run the exact
Argus prompt (built from a golden fixture) through ``opencode run --model
<model>``, classify the outcome, and validate the review output against the
fixture's expected findings. Written as a per-model tool so the probe
workflow can fan out over the live free models in parallel (a matrix job
per model), each bounded by its own timeout.

The classification deliberately distinguishes:

  callable    exit 0 with a review body — the model genuinely runs
  unavailable exit != 0 with ``model unavailable`` / ``not available in
              your country`` / ``model not found`` — the exact Zen
              gateway/CLI errors (see config/model-scores.yml)
  auth_error  exit != 0 with a 401/403/auth phrase — the key path is broken
  hang        the process did not exit within --timeout seconds
  error       any other non-zero exit

For ``callable`` the review text is additionally validated against the
fixture's ``.expected`` (tolerance ±1, the same rule the LLM fixture path
uses) to give a quality signal: passed/tp/fp/errors.

Usage:
  python3 tools/probe_free_models.py \
      --model opencode/deepseek-v4.1-flash-free \
      --fixture tests/fixtures/golden/product-card.css \
      [--timeout 480] [--json out.json] [--verbose]

Exit codes:
  0 — probe ran; JSON written (callability may still be "unavailable")
  2 — usage/environment error (opencode missing, bad fixture/expected)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 so non-ASCII glyphs never crash on a GBK console (Windows).
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

# Reuse the fixture runner's prompt builder, expected parser, validator and
# opencode locator so the probe exercises the exact same review contract the
# action does (no second, drifting copy of the prompt).
from run_fixture_tests import (  # noqa: E402
    _auth_preflight,
    _find_opencode,
    build_argus_prompt,
    parse_expected,
    validate_output,
)

# Retryable/unavailable phrases — mirrors the action's retry_re. Only the
# phrases the Zen gateway/CLI actually emit; a bare `unavailable` is
# deliberately absent (line numbers and review prose match it).
_UNAVAILABLE_RE = re.compile(
    r"model\s+not\s+found|no\s+such\s+model|model\s+does\s+not\s+exist|"
    r"model\s+(?:is\s+)?unavailable|not\s+available\s+in\s+your\s+country",
    re.IGNORECASE,
)
_AUTH_RE = re.compile(
    r"401\s+(?:unauthorized|invalid)|403\s+(?:forbidden|invalid)|"
    r"unauthorized|authentication\s+(?:failed|error)|invalid\s+api\s+key",
    re.IGNORECASE,
)
# A real Argus review body carries the summary header and/or severity tags.
_REVIEW_BODY_RE = re.compile(r"Argus Design Review Summary|\[P[0-3]\]", re.IGNORECASE)


def _run_opencode(opencode: str, model: str, prompt: str, timeout: int,
                  verbose: bool) -> tuple[str, str, float]:
    """Run ``opencode run --model <model> <prompt>``.

    Returns (status, output, seconds). ``status`` is the classification:
    callable / unavailable / auth_error / hang / error.
    """
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [opencode, "run", "--model", model, prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or b"") + (exc.stderr or b"")
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return "hang", out, round(time.monotonic() - t0, 1)

    output = proc.stdout + proc.stderr
    elapsed = round(time.monotonic() - t0, 1)
    if verbose:
        print(f"\n── raw output (exit {proc.returncode}) ──\n{output}\n──────────", flush=True)

    if proc.returncode != 0:
        if _AUTH_RE.search(output):
            return "auth_error", output, elapsed
        if _UNAVAILABLE_RE.search(output):
            return "unavailable", output, elapsed
        return "error", output, elapsed

    # exit 0 — did it actually produce a review body?
    if _REVIEW_BODY_RE.search(output):
        return "callable", output, elapsed
    return "error", output, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe one opencode free model (callability + quality smoke)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--model", required=True, help="opencode model ID, e.g. opencode/x-free")
    parser.add_argument("--fixture", required=True, type=Path,
                        help="Fixture file whose Argus prompt is the probe input")
    parser.add_argument("--timeout", type=int, default=480,
                        help="Seconds before the attempt is classified a hang (default 480)")
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write result JSON to FILE")
    parser.add_argument("--verbose", action="store_true", help="Print the raw model output")
    args = parser.parse_args()

    opencode = _find_opencode()
    if opencode is None:
        print("[probe] ✗ opencode CLI not found — the probe job must install it first", file=sys.stderr)
        return 2

    # Fail loudly on auth misconfiguration rather than reporting 8 fake
    # "unavailable" results. The action treats the key as optional (free
    # models run without one), but a present-but-invalid key is a real error.
    try:
        _auth_preflight(args.model)
    except SystemExit as exc:
        print(f"[probe] ✗ auth preflight failed: {exc}", file=sys.stderr)
        return 2

    fixture = args.fixture.resolve()
    if not fixture.exists():
        print(f"[probe] ✗ fixture not found: {fixture}", file=sys.stderr)
        return 2
    try:
        expected_path = fixture.with_suffix(fixture.suffix + ".expected")
        if not expected_path.exists():
            expected_path = fixture.with_name(fixture.stem + ".expected")
        expected = parse_expected(expected_path)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[probe] ✗ could not load expected for {fixture}: {exc}", file=sys.stderr)
        return 2

    prompt = build_argus_prompt(fixture, token_system="auto", lessons_text="")
    status, output, seconds = _run_opencode(opencode, args.model, prompt, args.timeout, args.verbose)

    result: dict = {
        "model": args.model,
        "status": status,
        "exit_note": "timeout" if status == "hang" else "non-zero" if status in ("unavailable", "auth_error", "error") else "zero",
        "seconds": seconds,
        "output_tail": "\n".join(output.strip().splitlines()[-15:]),
        "quality": None,
    }
    if status == "callable":
        vres = validate_output(expected, output, tolerance=1)
        result["quality"] = {
            "passed": vres.passed,
            "tp_count": vres.tp_count,
            "fp_count": vres.fp_count,
            "errors": vres.errors,
            "warnings": vres.warnings,
        }

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[probe] {args.model} → {status} ({seconds}s) — JSON → {args.output_json}")
    else:
        print(f"[probe] {args.model} → {status} ({seconds}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
