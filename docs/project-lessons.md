# Project Lessons (`.argus/LESSON.md`)

Argus reviews are defined by `AGENTS.md` + `SKILL.md` (shipped with Argus).
Those rules are **static** — they cannot know the project-specific facts that
Argus keeps getting wrong in *your* codebase. `.argus/LESSON.md` is the
per-project feedback channel: Argus loads it into the review prompt whenever it
reviews that project, so the same mistake does not recur.

> **Trust, not noise.** This is the **external truth** input that the Argus
> quality engine lacks — real review errors discovered in consumer projects.
> See `tests/fixtures/README.md` for how the quality engine distinguishes the
> *static scanner regression lock* from the *LLM agent-quality signal*.

## Where it lives

- Default path: `.argus/LESSON.md` (next to `.argus.yml`).
- Override with `lessons-path:` in `.argus.yml` (relative to repo root).

## Loading

- **Cloud review** — the composite action reads `.argus/LESSON.md` from your
  repo (if it exists) and injects it under `## Project Lessons (do not repeat
  these mistakes)`, unconditionally. No file → no change in behavior.
- **Local review** — `tools/argus_review.py` auto-detects `.argus/LESSON.md`
  in the current directory, or pass `--lessons PATH`.

## Format

See `config/lessons.template.md` for a copy-paste starter. Each entry:

```markdown
## L-001 · <one-line title>
- kind: false-positive        # false-positive | false-negative | wrong-fix | missing-dimension | context
- trigger: <code/situation that triggers the mistake>
- do not: <what Argus incorrectly does>
- instead: <what Argus should do>
- recorded: 2026-01-01
- source: <repo#PR / issue / "local review">
```

`kind` values:

| kind | meaning |
|---|---|
| `false-positive` | Argus flagged code that is legal in this project |
| `false-negative` | Argus missed a real violation |
| `wrong-fix` | The fix Argus suggested is wrong for this project |
| `missing-dimension` | Argus omitted a check that matters here |
| `context` | A project fact Argus should assume (token naming, conventions) |

## Keeping it small

- `make validate-lessons FILE=.argus/LESSON.md` checks format, ID uniqueness,
  and a size budget (~6 KB / 20 entries). A runaway file bloats *this*
  project's prompt.
- **Delete resolved entries.** If a lesson is generic (Argus itself is wrong,
  not just this project), promote it: file it in the `cgartlab/argus` repo via
  `tools/add_fp_appeal.py` (false positives) or a new fixture, so it becomes a
  regression guard for *every* consumer — then remove it from this file.

## What belongs here vs. in the Argus repo

| Question | Put it in |
|---|---|
| "Argus is wrong about my project's pattern" | `.argus/LESSON.md` (here) |
| "Argus is wrong in general / for everyone" | Argus repo: fixture (+ maybe SKILL.md rule) |

The boundary keeps each project's prompt bounded and lets Argus-the-product
learn the generic cases once, for everyone.
