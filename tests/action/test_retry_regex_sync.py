#!/usr/bin/env python3
"""Keep the two retryable-error regexes in sync.

``.github/actions/argus-review/action.yml`` classifies a failed model attempt
as retryable with a bash ERE (``retry_re``), and ``tools/run_fixture_tests.py``
mirrors it in ``_is_retryable()``. They drifted once: the fixture regex still
had a bare ``unavailable`` alternative that the action had deliberately dropped
(because line numbers and review prose matched it), while the action in turn
was missing the exact ``model unavailable`` phrase the Zen gateway emits.

This test extracts both patterns and asserts they classify the same probe
corpus, and that neither carries a bare ``unavailable`` alternative.

Run: python3 tests/action/test_retry_regex_sync.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github" / "actions" / "argus-review" / "action.yml"
FIXTURE = ROOT / "tools" / "run_fixture_tests.py"


def action_retry_re() -> str:
    text = ACTION.read_text(encoding="utf-8")
    m = re.search(r'local retry_re="([^"]*)"', text)
    if not m:
        raise SystemExit("FAIL: could not extract retry_re from action.yml")
    # bash ERE [[:space:]] -> python \s
    return m.group(1).replace("[[:space:]]", r"\s")


def fixture_retry_re() -> str:
    text = FIXTURE.read_text(encoding="utf-8")
    start = text.index("def _is_retryable")
    window = text[start : start + 4000]
    m = re.search(r"re\.search\(\s*((?:r\"[^\"]*\"\s*)+)", window)
    if not m:
        raise SystemExit("FAIL: could not extract _is_retryable pattern")
    literals = re.findall(r'r"([^"]*)"', m.group(1))
    if not literals:
        raise SystemExit("FAIL: no r'' literals found in _is_retryable")
    return "".join(literals)


def has_bare_unavailable(pattern: str) -> bool:
    """True if the pattern has an alternative that is exactly `unavailable`."""
    return any(alt.strip().rstrip("\\") == "unavailable" for alt in pattern.split("|"))


def count_alternatives(pattern: str) -> int:
    """Count top-level `|` alternatives (not inside parentheses)."""
    depth = 0
    count = 1
    for ch in pattern:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            count += 1
    return count


def main() -> int:
    action = action_retry_re()
    fixture = fixture_retry_re()

    failures = []
    for name, pat in (("action", action), ("fixture", fixture)):
        if has_bare_unavailable(pat):
            failures.append(f"{name}: bare `unavailable` alternative present")
        try:
            re.compile(pat)
        except re.error as exc:
            failures.append(f"{name}: invalid regex after normalisation: {exc}")

    # Both patterns must describe the same decision procedure. The action uses
    # a bash ERE (`[[:space:]]`, `\b`) and the fixture a Python re; a
    # structural difference that changes behaviour (e.g. a trailing-space
    # requirement vs a `\b` boundary after the 429 keyword) must not slip
    # through. The counts must match AND every probe must agree.
    if count_alternatives(action) != count_alternatives(fixture):
        failures.append(
            f"alternative count differs: action={count_alternatives(action)} "
            f"fixture={count_alternatives(fixture)}"
        )

    # Probe corpus: phrases that ARE retryable vs prose that must NOT match,
    # including boundary cases (429 + hyphen/word-boundary, punctuation).
    positive = [
        "Model unavailable",
        "model is unavailable for this region",
        "This model is not available in your country",
        "429 Too Many Requests",
        "429 rate-limit exceeded",
        "429 rate limit exceeded",
        "429 too many requests",
        "Model not found: opencode/x",
        "no such model: opencode/x",
        "model does not exist",
        "upstream request failed: 503",
        "upstream error from Nvidia",
        "endpoint is unavailable",
        "service temporarily overloaded",
        "service unavailable",
        "bad gateway 502",
        "gateway timeout",
        "server_error",
    ]
    negative = [
        "This change makes the endpoint unavailable in dark mode",
        "line 42: color unavailable",
        "The CSS variable does not exist on this element",
        "no issues found; all checks passed",
        "429 requests were processed successfully",
        "the service was available throughout",
    ]

    for probe in positive:
        a = re.search(action, probe, re.IGNORECASE)
        f = re.search(fixture, probe, re.IGNORECASE)
        if not a:
            failures.append(f"action does NOT match positive probe: {probe!r}")
        if not f:
            failures.append(f"fixture does NOT match positive probe: {probe!r}")
    for probe in negative:
        a = re.search(action, probe, re.IGNORECASE)
        f = re.search(fixture, probe, re.IGNORECASE)
        if a:
            failures.append(f"action MATCHES negative probe: {probe!r}")
        if f:
            failures.append(f"fixture MATCHES negative probe: {probe!r}")

    # The two must AGREE on every probe — this is the actual sync guarantee.
    for probe in positive + negative:
        if bool(re.search(action, probe, re.IGNORECASE)) != bool(
            re.search(fixture, probe, re.IGNORECASE)
        ):
            failures.append(f"action and fixture DISAGREE on probe: {probe!r}")

    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        print(f"{len(failures)} FAILURE(S)")
        return 1
    print("PASS retry regexes in sync (action <-> fixture)")
    print(f"  action : {len(action)} chars, {count_alternatives(action)} alternatives")
    print(f"  fixture: {len(fixture)} chars, {count_alternatives(fixture)} alternatives")
    print(f"  probes : {len(positive)} positive / {len(negative)} negative (all agree)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
