#!/usr/bin/env python3
"""Validate the argus-review composite action's shell blocks.

Why this exists
---------------
``.github/workflows/review.yml`` consumes the composite action via
``cgartlab/argus/.github/actions/argus-review@main``. A PR that only changes
``action.yml`` therefore runs the *old* main version — the PR's own code is
never executed, so a regression introduced in a step (e.g. a PATH mistake)
cannot be caught by that workflow. See cgartlab/argus#174.

This tool closes that gap without needing a runner: it parses action.yml and
checks the invariants that matter, plus shell syntax via ``bash -n``.

Run::

    python3 tools/validate_action.py          # exit 0 = ok, 1 = problem

Exit codes: 0 ok, 1 validation error, 2 usage/environment error.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is present on CI runners
    yaml = None

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
ACTION_FILE = REPO_ROOT / ".github" / "actions" / "argus-review" / "action.yml"

# Steps that must exist for the action to be able to review at all.
REQUIRED_STEPS = (
    "Install OpenCode CLI",
    "Load consumer configuration",
    "Build review prompt from Argus rules",
    "Run OpenCode review",
)

# Steps that must survive failures / be skipped in the right situations.
ALWAYS_RESTORE_STEP = "Restore quarantined opencode config"
QUARANTINE_STEP = "Quarantine V2-only opencode config"
# Must sit between the quarantine step and the review, so a masking failure is
# caught before `opencode github run` can commit it.
WORKTREE_GATE_STEP = "Verify worktree is clean before review"

# Composite action steps accept only these keys (GitHub metadata syntax).
# A key outside this set is rejected by the runner at action-load time with
# "Unexpected value '<key>'" — the action then fails to load for EVERY
# consumer. Regression: timeout-minutes (a workflow job-step-only key) on a
# composite step, 2026-10-19 (argus 2a2ef567), which broke every consumer's
# argus-review until 02045919.
COMPOSITE_STEP_KEYS = frozenset({
    "name",
    "id",
    "if",
    "uses",
    "run",
    "env",
    "shell",
    "working-directory",
    "with",
    "continue-on-error",
})


def _load_action(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse action.yml")
    return yaml.safe_load(text)


def _steps(action: dict) -> list[dict]:
    return action.get("runs", {}).get("steps", []) or []


def _run_of(step: dict) -> str:
    value = step.get("run")
    return value if isinstance(value, str) else ""


def _python3_is_store_stub() -> bool:
    """True when `python3` on PATH is the Microsoft Store launcher stub.

    The stub ships on every Windows box, exits non-zero, and prints an install
    prompt instead of running code. Assuming it is a real interpreter turns
    every shell-out check into a permanent false red.
    """
    found = shutil.which("python3")
    if not found:
        return False
    return "WindowsApps" in pathlib.Path(found).as_posix().replace("/", "\\")


def _bash_available() -> str | None:
    """Return a *working* bash, or None.

    `shutil.which("bash")` on Windows resolves to the Microsoft Store stub
    (`WindowsApps\\bash.exe`), which exists but only prints a WSL install
    prompt and exits 1 — so every `bash -n` check reported a bogus failure
    and this validator's whole shell layer silently produced no signal.
    Try the real Git Bash first, and probe each candidate by running it.
    """
    candidates = [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]
    which = shutil.which("bash")
    if which:
        candidates.append(which)
    for candidate in candidates:
        if not pathlib.Path(candidate).exists():
            continue
        try:
            probe = subprocess.run(
                [candidate, "--noprofile", "--norc", "-c", "echo argus-bash-ok"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and "argus-bash-ok" in (probe.stdout or ""):
            return candidate
    return None


# `${{ inputs.model }}` may be written with or without inner spaces, so match
# the expression structurally instead of on an exact string.
#
# Only pass a `run:` body here. The correct pattern puts the expression in
# `env:`, which callers deliberately exclude via `_run_of()`.
_EXPR_RE = None


def _has_expression(script: str, context: str) -> bool:
    """True if `script` interpolates `${{ <context> }}` (any inner spacing).

    Matches the context exactly or as a property access, so `inputs.model-family`
    is not mistaken for `inputs.model`.
    """
    global _EXPR_RE
    if _EXPR_RE is None:
        import re

        _EXPR_RE = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")
    for expr in _EXPR_RE.findall(script):
        expr = expr.strip()
        # exact match, or a property access on the same context, so that
        # `inputs.model-family` is not mistaken for `inputs.model`
        if expr == context or expr.startswith(context + "."):
            return True
    return False


def check_shell_syntax(steps: list[dict], bash: str | None) -> list[str]:
    """Run `bash -n` over every shell step's script body."""
    problems: list[str] = []
    if bash is None:
        return ["SKIP: bash not found — shell syntax checks not run"]
    for step in steps:
        script = _run_of(step)
        if not script:
            continue
        name = step.get("name", "(unnamed)")
        proc = subprocess.run(
            [bash, "-n"],
            input=script,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            problems.append(f"{name}: bash -n failed: {proc.stderr.strip()[:300]}")
    return problems


def check_required_steps(steps: list[dict]) -> list[str]:
    problems = []
    names = [s.get("name", "") for s in steps]
    for required in REQUIRED_STEPS:
        if not any(required in n for n in names):
            problems.append(f"missing required step: {required}")
    return problems


def check_step_keys(steps: list[dict]) -> list[str]:
    """Composite action steps only accept a fixed set of keys.

    The runner rejects the whole action manifest when a step carries an
    unknown key ("Unexpected value '<key>'"), so the action fails to load
    for every consumer — the failure surfaces in the consumer's CI, not
    here. 2026-10-19: `timeout-minutes` (a job-step-only key) on a
    composite step broke every consumer's argus-review.
    """
    problems: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        for key in step:
            if key not in COMPOSITE_STEP_KEYS:
                name = step.get("name", "(unnamed)")
                problems.append(
                    f"step '{name}' has unsupported key '{key}' — composite action "
                    f"steps accept only: {', '.join(sorted(COMPOSITE_STEP_KEYS))}"
                )
    return problems


def check_version_pin(steps: list[dict]) -> list[str]:
    """The action must pin an OpenCode 1.x version and reject 2.x."""
    problems = []
    install = next(
        (s for s in steps if "Install OpenCode" in (s.get("name") or "")), None
    )
    if install is None:
        return ["missing 'Install OpenCode CLI' step"]
    script = _run_of(install)
    if "opencode-install.sh --version" not in script:
        problems.append("install step does not pass --version to the installer (unpinned CLI)")
    if "1.*" not in script:
        problems.append("install step does not guard against non-1.x versions")
    env = install.get("env", {}) or {}
    if not any("OPENCODE_CLI_VERSION" in k for k in env):
        problems.append("install step does not read the OPENCODE_CLI_VERSION env var")
    # The version check must not be able to fail an otherwise-good install.
    if "|| echo" not in script and "|| true" not in script:
        problems.append("install step's `opencode --version` check is fatal — a PATH quirk would fail the run")
    return problems


def check_path_export(steps: list[dict]) -> list[str]:
    """`$GITHUB_PATH` only affects later steps, so the install step must export PATH."""
    problems = []
    install = next(
        (s for s in steps if "Install OpenCode" in (s.get("name") or "")), None
    )
    if install is None:
        return ["missing 'Install OpenCode CLI' step"]
    if 'export PATH=' not in _run_of(install):
        problems.append(
            "install step does not `export PATH=...` — $GITHUB_PATH only applies to later steps, "
            "so an in-step version check fails with exit 127 (regression seen in #174)"
        )
    return problems


def check_quarantine_restore(steps: list[dict]) -> list[str]:
    """V2-config quarantine must hide from git, and must be restored."""
    problems = []
    restore = next(
        (s for s in steps if ALWAYS_RESTORE_STEP in (s.get("name") or "")), None
    )
    if restore is None:
        return [f"missing '{ALWAYS_RESTORE_STEP}' step — a neutralised config would be left in place on failure"]
    if restore.get("if") != "always()":
        problems.append(f"'{ALWAYS_RESTORE_STEP}' must use `if: always()` so a failed review still restores config")
    quarantine = next(
        (s for s in steps if QUARANTINE_STEP in (s.get("name") or "")), None
    )
    if quarantine is None:
        problems.append("missing quarantine step (restore exists but nothing quarantines)")
        return problems
    script = _run_of(quarantine)
    if 'echo "$rel" >> "$QUARANTINE_DIR/manifest"' not in script:
        problems.append("quarantine step does not record a manifest — restore has nothing to work from")
    if "cp -p" not in script:
        problems.append("quarantine step does not preserve a copy before rewriting the file")
    # The core of the cgartlab/men@a21a4c44 fix: quarantine must be invisible to git.
    # Deleting the file instead makes the worktree dirty, and `opencode github
    # run` (v1.19.3 pushToLocalBranch) would commit and push that deletion to
    # the consumer's PR branch.
    if "git update-index --skip-worktree" not in script:
        problems.append(
            "quarantine step does not hide rewritten paths with "
            "`git update-index --skip-worktree` — the worktree would stay dirty "
            "and the review would commit the quarantine to the consumer's branch (cgartlab/men@a21a4c44)"
        )
    for bad in ('rm -f "$rel"', 'rm -rf "$rel"', 'rm -f -- "$rel"'):
        if bad in script:
            problems.append(
                f"quarantine step removes a consumer file with `{bad}` — that "
                "deletion would be committed and pushed (cgartlab/men@a21a4c44)"
            )
    restore_script = _run_of(restore)
    if "git update-index --no-skip-worktree" not in restore_script:
        problems.append(
            "restore step does not clear `--skip-worktree` — the consumer's git "
            "would keep hiding real edits after the action finished"
        )
    if 'cp -p "$src" "$rel"' not in restore_script:
        problems.append("restore moves its backup instead of copying — a retried restore would find nothing")
    return problems


def check_worktree_gate(steps: list[dict]) -> list[str]:
    """The clean-worktree gate must run after quarantine and before the review.

    `opencode github run` commits whatever `git status --porcelain` reports, so
    the gate is the last line of defence against quarantines leaking into the
    consumer's PR branch (cgartlab/men@a21a4c44).
    """
    problems = []
    gate = next((s for s in steps if WORKTREE_GATE_STEP in (s.get("name") or "")), None)
    if gate is None:
        return [
            f"missing '{WORKTREE_GATE_STEP}' step — a dirty worktree would be "
            "committed and pushed to the consumer's PR branch (cgartlab/men@a21a4c44)"
        ]
    script = _run_of(gate)
    if "git status --porcelain" not in script:
        problems.append("gate step does not check `git status --porcelain`")
    if "exit 1" not in script:
        problems.append("gate step does not fail the run when the worktree is dirty")
    if "::error::" not in script:
        problems.append("gate step does not report the offending paths as GitHub Actions errors")
    # Ordering: quarantine < gate < review. Anything earlier hides its own
    # rewrites; anything later is already past the point of no return.
    def index_of(fragment: str) -> int:
        for i, s in enumerate(steps):
            if fragment in (s.get("name") or ""):
                return i
        return -1

    q, g, r = index_of(QUARANTINE_STEP), index_of(WORKTREE_GATE_STEP), index_of("Run OpenCode review")
    if not (0 <= q < g < r):
        problems.append(
            f"step order must be quarantine -> worktree gate -> review (got {q}, {g}, {r})"
        )
    return problems


def check_model_ids_callable(action: dict) -> list[str]:
    """Every hard-coded model ID in the action/manifest must still be callable.

    The review resolves its model from config/free-models.yml, but two places
    name a model *without* consulting that file: the action's last-resort
    ``PRIMARY_MODEL`` default, and ``manifest.yaml``'s ``preferred_models``.
    Those are exactly the paths that get exercised when config is broken, so a
    stale ID there is the worst case — and it silently rots as the Zen
    catalogue churns.

    Regression (PR #203, found by argus review): the action still defaulted to
    ``opencode/nemotron-3-ultra-free`` and the manifest still preferred
    ``opencode/deepseek-v4-flash-free``; both had been delisted, while the rest
    of the same PR was busy removing exactly this class of dead reference.

    A model is callable when config/model-scores.yml lists it and it carries
    neither ``deprecated: true`` nor ``regions: []``.
    """
    problems: list[str] = []

    scores_path = REPO_ROOT / "config" / "model-scores.yml"
    try:
        import yaml  # noqa: PLC0415 - optional at import time
    except ImportError:
        return ["SKIP: PyYAML not installed — model ID callability not checked"]
    if not scores_path.exists():
        return [f"{scores_path} not found — cannot validate hard-coded model IDs"]
    with scores_path.open(encoding="utf-8") as f:
        scores = (yaml.safe_load(f) or {}).get("models", {}) or {}

    def classify(model_id: str) -> str | None:
        entry = scores.get(model_id)
        if entry is None:
            return "not listed in config/model-scores.yml"
        if entry.get("deprecated"):
            return "marked deprecated in config/model-scores.yml"
        if entry.get("regions") == []:
            return "marked regions: [] (known unreachable) in config/model-scores.yml"
        return None

    model_re = re.compile(r"opencode/[A-Za-z0-9._-]*free")

    # 1. Every model ID appearing in any step body.
    for step in _steps(action):
        script = _run_of(step)
        if not script:
            continue
        name = step.get("name", "(unnamed)")
        for model_id in sorted(set(model_re.findall(script))):
            reason = classify(model_id)
            if reason:
                problems.append(f"step '{name}' references {model_id} — {reason}")

    # 2. manifest.yaml preferred_models.
    manifest_path = REPO_ROOT / "manifest.yaml"
    if manifest_path.exists():
        try:
            with manifest_path.open(encoding="utf-8") as f:
                manifest = yaml.safe_load(f) or {}
        except Exception as exc:  # noqa: BLE001 - report any parse failure
            problems.append(f"manifest.yaml is not valid YAML: {exc}")
            manifest = {}
        for model_id in manifest.get("preferred_models", []) or []:
            reason = classify(str(model_id))
            if reason:
                problems.append(f"manifest.yaml preferred_models references {model_id} — {reason}")

    # 3. The updater's own last-resort literal. It is named without consulting
    #    config, exactly like the action default above.
    updater_path = REPO_ROOT / "tools" / "update_free_models.py"
    if updater_path.exists():
        match = re.search(
            r'^BUILTIN_PRIMARY\s*=\s*"([^"]+)"',
            updater_path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
        if match:
            reason = classify(match.group(1))
            if reason:
                problems.append(
                    f"tools/update_free_models.py BUILTIN_PRIMARY is {match.group(1)} — {reason}"
                )
        else:
            # Fail closed: if the constant is renamed or reshaped the regex
            # stops matching, and a silent pass is worse than a false alarm —
            # this guard exists precisely to catch a dead last-resort model.
            problems.append(
                "tools/update_free_models.py: BUILTIN_PRIMARY not found — "
                "cannot validate the last-resort primary model"
            )

    return problems


def _find_keys(obj, key: str, prefix: str = "") -> list[str]:
    """Return every dotted path at which `key` occurs, recursively."""
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else k
            if k == key:
                hits.append(path)
            hits.extend(_find_keys(v, key, path))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_find_keys(v, key, f"{prefix}[{i}]"))
    return hits


def _run_script(script: str, cwd: pathlib.Path, bash: str | None, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    if bash is None:
        raise RuntimeError("bash not found")
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [bash, "-c", script],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def run_quarantine_roundtrip(steps: list[dict], bash: str | None) -> list[str]:
    """Actually execute the quarantine/restore scripts in a sandbox.

    Parsing the YAML proves the steps exist; running them proves they behave.
    This is what would have caught the frontmatter `---`-swallowing regex bug
    that shipped in the first version of the quarantine step.
    """
    if bash is None:
        return ["SKIP: bash not found — quarantine round-trip not run"]
    if _python3_is_store_stub():
        # The step shells out to `python3`; the Store stub exits non-zero with
        # an install prompt, which would otherwise look exactly like a real
        # regression. Report as a skip (see SKIP_OUTCOMES in main).
        return ["SKIP: python3 is a Microsoft Store stub on this host"]
    quarantine = next((s for s in steps if "Quarantine" in (s.get("name") or "")), None)
    restore = next((s for s in steps if ALWAYS_RESTORE_STEP in (s.get("name") or "")), None)
    if quarantine is None or restore is None:
        return ["quarantine/restore steps missing — nothing to round-trip"]

    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="argus-action-"))
    try:
        repo = sandbox / "repo"
        (repo / ".opencode" / "agent").mkdir(parents=True)

        # V2-format consumer config (the shape that got polluted in
        # cgartlab/men@a21a4c44).
        opencode_json = json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "default_agent": "men",
                "agent": {
                    "men": {
                        "model": "x/y",
                        "description": "orchestrator",
                        "permissions": [
                            {"action": "question", "resource": "*", "effect": "allow"}
                        ],
                    },
                    "ji": {"model": "x/z", "permissions": [{"action": "edit", "effect": "deny"}]},
                },
            }
        )
        (repo / "opencode.json").write_text(opencode_json, encoding="utf-8")
        # Agent markdown whose frontmatter carries a V2 permissions block.
        agent_md = repo / ".opencode" / "agent" / "men.md"
        agent_md_text = (
            "---\ndescription: t\nmode: primary\nmodel: x/y\n"
            "permissions:\n  - action: question\n    effect: allow\n"
            "---\n\n# men\n"
        )
        agent_md.write_text(agent_md_text, encoding="utf-8")
        # A V1-only consumer file that must be left completely alone.
        v1_file = repo / "v1only.json"
        v1_file.write_text('{"agent":{"a":{"permission":{"question":"allow"}}}}', encoding="utf-8")
        v1_before = v1_file.read_text(encoding="utf-8")
        # A file the V1 CLI rewrites itself (it adds @opencode-ai/plugin to it);
        # quarantine must mask it, not rewrite it.
        pkg = repo / ".opencode" / "package.json"
        pkg.write_text('{"name": "plugins", "dependencies": {"@opencode/plugin": "2.0.6"}}', encoding="utf-8")
        pkg_before = pkg.read_text(encoding="utf-8")

        gh_env = sandbox / "gh_env"
        gh_env.touch()

        problems: list[str] = []
        r = _run_script(_run_of(quarantine), repo, bash, {"GITHUB_ENV": str(gh_env)})
        if r.returncode != 0:
            detail = f"{r.stderr.strip()[:200]} {r.stdout.strip()[:200]}".strip()
            problems.append(f"quarantine script exited {r.returncode}: {detail}")
            return problems

        # The fix neutralises the file in place instead of deleting it, so the
        # V1 CLI still sees a working config and the worktree stays clean.
        if not (repo / "opencode.json").exists():
            problems.append("quarantine removed opencode.json instead of neutralising it in place")
        try:
            rewritten = json.loads((repo / "opencode.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"quarantine left opencode.json unparseable by the V1 CLI: {exc}")
            rewritten = None
        if rewritten is not None:
            if rewritten.get("default_agent") != "men":
                problems.append("quarantine dropped default_agent from opencode.json")
            if rewritten.get("agent", {}).get("men", {}).get("model") != "x/y":
                problems.append("quarantine dropped the agent model from opencode.json")
            if rewritten.get("agent", {}).get("ji", {}).get("model") != "x/z":
                problems.append("quarantine dropped the second agent from opencode.json")
            if _find_keys(rewritten, "permissions"):
                problems.append("quarantine left a `permissions` array in opencode.json")

        stripped = agent_md.read_text(encoding="utf-8")
        if "permissions:" in stripped:
            problems.append("quarantine did not strip the V2 permissions block from agent frontmatter")
        if not stripped.startswith("---\n") or "# men" not in stripped or stripped.count("---") < 2:
            problems.append("stripped frontmatter lost its closing '---' — opencode would fail to parse it")
        for keep in ("description:", "mode:", "model:"):
            if keep not in stripped:
                problems.append(f"quarantine dropped `{keep}` from the agent frontmatter")

        # Masked-only files must keep their original bytes.
        if pkg.read_text(encoding="utf-8") != pkg_before:
            problems.append("quarantine rewrote a file it was only supposed to mask")
        if v1_file.read_text(encoding="utf-8") != v1_before:
            problems.append("quarantine touched a V1-only config file")

        # Restore must put everything back byte-for-byte.
        qdir = ""
        for line in gh_env.read_text(encoding="utf-8").splitlines():
            if line.startswith("QUARANTINE_DIR="):
                qdir = line.split("=", 1)[1]
        if not qdir:
            problems.append("quarantine did not export QUARANTINE_DIR — restore cannot run")
            return problems

        r2 = _run_script(_run_of(restore), repo, bash, {"QUARANTINE_DIR": qdir})
        if r2.returncode != 0:
            problems.append(f"restore script exited {r2.returncode}: {r2.stderr.strip()[:200]}")
        if (repo / "opencode.json").read_text(encoding="utf-8") != opencode_json:
            problems.append("restore did not bring back opencode.json byte-for-byte")
        if agent_md.read_text(encoding="utf-8") != agent_md_text:
            problems.append("restore did not bring back the agent frontmatter permissions block")
        if pkg.read_text(encoding="utf-8") != pkg_before:
            problems.append("restore did not bring back the masked package.json byte-for-byte")
        if v1_file.read_text(encoding="utf-8") != v1_before:
            problems.append("restore touched a V1-only config file")
        # Restore must copy, not move. It also cleans up the quarantine dir, so a
        # post-run "backup still there" assertion cannot work — check the script
        # itself instead: moving is only safe if the dir is never reused, and a
        # retried restore would then find an empty backup.
        restore_script = _run_of(restore)
        if 'cp -p "$src" "$rel"' not in restore_script:
            problems.append("restore moves its backup instead of copying — a retried restore would find nothing")
        return problems
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)


def check_fixture_step(steps: list[dict]) -> list[str]:
    problems = []
    fixture = next(
        (s for s in steps if "fixture regression" in (s.get("name") or "").lower()), None
    )
    if fixture is None:
        return []  # optional step, not an error
    script = _run_of(fixture)
    if "run_fixture_tests.py" not in script:
        problems.append("fixture step does not call tools/run_fixture_tests.py")
    return problems


# Caller-controlled contexts. `secrets.*` is deliberately excluded: the runner
# masks those in logs, and the value is chosen by the repo owner, not by an
# untrusted PR author. `inputs.*` is the dangerous set — the calling repo passes
# them via `with:` and they are NOT masked, so interpolating them into a `run:`
# body is a script-injection vector (see cgartlab/argus#169, #170).
INJECTABLE_INPUT_CONTEXTS = (
    "inputs.api-key",
    "inputs.model",
    "inputs.fallback-models",
    "inputs.config-path",
    "inputs.github-token",
    "inputs.opencode-version",
    "inputs.fixture-mode",
)


def check_no_injection(steps: list[dict]) -> list[str]:
    """No caller-controlled value may appear inside any `run:` body.

    GitHub expands `${{ ... }}` into the script text before bash parses it, so
    an interpolated `inputs.*` value executes as code. Values must be passed
    via `env:` instead, where they arrive as inert strings.
    """
    problems = []
    for step in steps:
        name = step.get("name") or step.get("uses") or "(unnamed step)"
        script = _run_of(step)
        if not script:
            continue
        for ctx in INJECTABLE_INPUT_CONTEXTS:
            if _has_expression(script, ctx):
                problems.append(
                    f"{name}: '${{{{ {ctx} }}}}' interpolated into run: — "
                    "caller-controlled value executes as shell; pass it via env:"
                )
    return problems


def check_fixture_arg_array(steps: list[dict]) -> list[str]:
    """The fixture step must build argv from a quoted bash array.

    The pre-fix form used unquoted command substitution
    (`$([ -n ... ] && echo --model "$X")`), which word-splits and re-parses
    metacharacters. A quoted array keeps each value in exactly one argv element.
    """
    problems = []
    fixture = next(
        (s for s in steps if "fixture regression" in (s.get("name") or "").lower()), None
    )
    if fixture is None:
        return []  # optional step, not an error
    script = _run_of(fixture)
    if "EXTRA_ARGS=()" not in script:
        problems.append("fixture step does not initialise EXTRA_ARGS as an array")
    if '"${EXTRA_ARGS[@]}"' not in script:
        problems.append("fixture step does not expand EXTRA_ARGS with quotes")
    if "echo --model" in script or "echo --fallback-models" in script:
        problems.append(
            "fixture step still uses unquoted command substitution for CLI args"
        )
    return problems


def check_function_order(steps: list[dict]) -> list[str]:
    """A shell function must be defined in a script before it is called.

    Bash resolves function names at call time, so calling one that appears
    later in the same script fails with ``command not found`` (exit 127) —
    and under ``set -e`` that aborts the whole step. This is easy to
    introduce by moving a call during a refactor: the function still exists
    in the file, so review-by-reading looks fine.

    Regression (#189 / 2a2ef56, observed live on PR #203): the timeout branch
    called ``dismiss_stale_reviews`` three lines *above* its definition, so
    every primary-model timeout — the exact case #185's timeout guard exists
    for — died at exit 127 instead of falling through to the fallback queue.

    ``bash -n`` cannot catch this: it is valid syntax. Only ordering matters.
    """
    problems: list[str] = []
    # `name() {` / `function name {` at the start of a line (any indent).
    def_re = re.compile(r"^\s*(?:function\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*\{", re.MULTILINE)

    for step in steps:
        script = _run_of(step)
        if not script:
            continue
        name = step.get("name", "(unnamed)")

        definitions: dict[str, int] = {}
        for m in def_re.finditer(script):
            definitions.setdefault(m.group(1), script.count("\n", 0, m.start()) + 1)

        for func, def_line in definitions.items():
            # First line where the bare name is invoked as a command.
            call_re = re.compile(rf"^\s*{re.escape(func)}\s*(?:$|[^()\w])", re.MULTILINE)
            first_call = None
            for m in call_re.finditer(script):
                line = script.count("\n", 0, m.start()) + 1
                if line == def_line:
                    continue
                first_call = line
                break
            if first_call is not None and first_call < def_line:
                problems.append(
                    f"step '{name}': function '{func}' is called on line {first_call} "
                    f"but defined on line {def_line} — bash fails with exit 127 "
                    f"('command not found'); move the definition above its first call"
                )

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", dest="output_json", metavar="FILE", help="Write results to FILE")
    args = parser.parse_args(argv)

    if not ACTION_FILE.exists():
        print(f"action.yml not found at {ACTION_FILE}", file=sys.stderr)
        return 2

    try:
        action = _load_action(ACTION_FILE)
    except Exception as exc:  # noqa: BLE001 - report any parse failure
        print(f"action.yml is not valid YAML: {exc}", file=sys.stderr)
        return 2

    steps = _steps(action)
    bash = _bash_available()
    checks = {
        "shell_syntax": check_shell_syntax(steps, bash),
        "step_keys": check_step_keys(steps),
        "required_steps": check_required_steps(steps),
        "version_pin": check_version_pin(steps),
        "path_export": check_path_export(steps),
        "quarantine_restore": check_quarantine_restore(steps),
        "worktree_gate": check_worktree_gate(steps),
        "quarantine_roundtrip": run_quarantine_roundtrip(steps, bash),
        "fixture_step": check_fixture_step(steps),
        "no_injection": check_no_injection(steps),
        "fixture_arg_array": check_fixture_arg_array(steps),
        "model_ids_callable": check_model_ids_callable(action),
        "function_order": check_function_order(steps),
    }

    failed = {
        k: v
        for k, v in checks.items()
        if v and not all(str(p).startswith("SKIP: ") for p in v)
    }
    for name, problems in checks.items():
        if problems and name not in failed:
            print(f"[argus:action] {name}: {problems[0][len('SKIP: '):]}")
        elif problems:
            for p in problems:
                print(f"[argus:action] {name}: {p}", file=sys.stderr)
        else:
            print(f"[argus:action] {name}: ok")

    skipped = [k for k, v in checks.items() if v and k not in failed]
    print(
        f"[argus:action] {len(steps)} steps checked, {sum(len(v) for v in failed.values())} problem(s)"
        + (f", skipped: {', '.join(skipped)}" if skipped else "")
    )

    if args.output_json:
        pathlib.Path(args.output_json).write_text(
            '{"steps": %d, "problems": %s}\n'
            % (len(steps), json.dumps(failed)),
            encoding="utf-8",
        )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
