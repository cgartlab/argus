# Argus Fixture Tests

Fixture-based regression tests for Argus review rules. Each fixture is a **deliberately broken** code file paired with a `.expected` file that declares exactly what Argus should find.

## Directory Layout

```
tests/fixtures/
  design-tokens/
    bad-hardcoded-colors.css        ← bare oklch/hex/rgb in component rules
    bad-hardcoded-colors.expected
    missing-dark-mode.css           ← :root tokens without dark override
    missing-dark-mode.expected
  accessibility/
    missing-aria.html               ← icon buttons, img, <a>-as-button violations
    missing-aria.expected
  hardcoded-values/
    bad-magic-numbers.css           ← px spacing/radii/font-size bypassing tokens
    bad-magic-numbers.expected
  css-quality/
    duplicate-rules.css             ← duplicate properties in same selector
    duplicate-rules.expected
  false-positives/                  ← legal code that must NOT be flagged
    root-tokens.css                 ← :root token declarations (in_root exemption)
    box-shadow.css                  ← rgba() inside box-shadow/text-shadow
    third-party-reset.css           ← universal-selector reset blocks
    *.expected                      ← [counts] all 0 + [must-not-flag] list
  should-flag/                      ← mirror pairs proving exemptions are scoped
    hardcoded-colors.css            ← component bare colors (must flag P0)
    missing-alt.html                ← img without alt (must flag P1)
    no-dark-mode.css                ← missing dark overrides (must flag P0)
    *.expected                      ← [counts] > 0 + required [findings]
```

## Category Semantics

- **`false-positives/`** — files that are **legally correct** and must produce **zero**
  findings. Each `.expected` declares `P0 = 0 / P1 = 0 / P2 = 0 / P3 = 0` plus a
  `[must-not-flag]` list naming the tokens/constructs that must never appear on a
  flagged line. These lock in exemption logic (e.g. `:root` token source, shadow
  colors, reset boilerplate) as regression guards.
- **`should-flag/`** — mirror pairs that prove the exemptions are **scoped, not
  blind**: the same construct outside its exempted context *must* be flagged
  (e.g. bare rgba in a component rule vs. inside `box-shadow`). `.expected`
  files carry `[counts]` > 0 and the required `[findings]`.
- **FalsePositiveRate** = FP / (FP + TP), where FP is the number of
  `[must-not-flag]` items that appeared on a flagged line and TP is the number of
  expected `[findings]` keywords that appeared in the output. Reported by the
  runner after every run (target ≤ 5%). The metric is meaningful in LLM mode;
  static heuristic mode is deterministic and enforces `must-not-flag` as errors,
  so a passing static run always has FP = 0.

## .expected File Format

```ini
[meta]
fixture = <relative path to input file>
description = <human-readable description of what is being tested>

[findings]
# One line per required finding: SEVERITY | LINE_HINT | KEYWORD
# SEVERITY  — P0, P1, P2, or P3
# LINE_HINT — optional substring that must appear in the file:line reference
# KEYWORD   — substring that must appear in the issue description (case-insensitive)
P0 | | oklch
P1 | 23 | aria-label

[must-not-flag]
# Substrings that must NOT appear as flagged tokens in the output
:root
var(--ds-color-surface)

[counts]
# Exact count of findings per severity
P0 = 5
P1 = 0
P2 = 0
P3 = 0
```

## Running Tests

```bash
# Run all fixture tests
make test-fixtures

# Run a specific fixture category
python3 tools/run_fixture_tests.py --category design-tokens

# Run a single fixture
python3 tools/run_fixture_tests.py --fixture tests/fixtures/design-tokens/bad-hardcoded-colors.css

# Verbose output (show full Argus output for each fixture)
python3 tools/run_fixture_tests.py --verbose
```

## Adding a New Fixture

1. Create `tests/fixtures/<category>/your-fixture.<ext>` with intentional violations.
2. Create `tests/fixtures/<category>/your-fixture.expected` following the format above.
3. Run `make test-fixtures` to confirm the fixture passes.
4. If Argus output diverges from expected, update either the fixture or the `.expected` file
   and document the change in `CHANGELOG.md`.

## CI Integration

The fixture test suite runs as the `fixture-test` job in `.github/workflows/ci.yml`.
A fixture failure blocks merge just like a YAML lint failure.

> **Note:** Because Argus is an LLM-based agent, fixture tests run in **heuristic mode**:
> they check that the *count* and *severity* of findings fall within acceptable ranges,
> not that exact line numbers match. This makes the suite stable across minor model updates.
