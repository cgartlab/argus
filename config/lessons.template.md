<!--
  .argus/LESSONS.md — Project Lessons for Argus

  Argus loads this file into its review prompt whenever it reviews THIS repo.
  Put facts Argus keeps getting wrong about THIS project here (a legitimate
  pattern, a token-naming convention, a known exemption).

  Generic Argus bugs do NOT belong here — file those in the Argus repo so they
  become a fixture/rule everyone benefits from. This file is per-project.

  Keep it small. `python3 tools/validate_lessons.py --file .argus/LESSONS.md`
  (or `make validate-lessons FILE=.argus/LESSONS.md`) caps the file at ~6 KB /
  20 entries. Delete resolved entries — promoted ones live in the Argus repo.

  Copy this file to your repo at `.argus/LESSONS.md` and edit. Then delete
  this comment block.
-->

# Project Lessons

## L-001 · <one-line title — what Argus gets wrong>
- kind: false-positive            # false-positive | false-negative | wrong-fix | missing-dimension | context
- trigger: `box-shadow: 0 2px 4px rgba(0,0,0,.2)`
- do not: report P0 bare-color
- instead: ignore — shadow colors are legitimate values in this project
- recorded: 2026-01-01
- source: local review            # repo#PR / issue / "local review"
