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


def _bash_available() -> str | None:
    for candidate in ("bash", r"C:\Program Files\Git\bin\bash.exe"):
        found = shutil.which(candidate) or candidate
        if pathlib.Path(found).exists():
            return found
    return None


def check_shell_syntax(steps: list[dict], bash: str | None) -> list[str]:
    """Run `bash -n` over every shell step's script body."""
    problems: list[str] = []
    if bash is None:
        return ["bash not found — skipped shell syntax checks"]
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
    """V2-config quarantine must be paired with an always-on restore."""
    problems = []
    restore = next(
        (s for s in steps if ALWAYS_RESTORE_STEP in (s.get("name") or "")), None
    )
    if restore is None:
        return [f"missing '{ALWAYS_RESTORE_STEP}' step — a quarantined config would be lost on failure"]
    if restore.get("if") != "always()":
        problems.append(f"'{ALWAYS_RESTORE_STEP}' must use `if: always()` so a failed review still restores config")
    quarantine = next(
        (s for s in steps if "Quarantine" in (s.get("name") or "")), None
    )
    if quarantine is None:
        problems.append("missing quarantine step (restore exists but nothing quarantines)")
    else:
        script = _run_of(quarantine)
        if 'echo "$rel" >> "$QUARANTINE_DIR/manifest"' not in script:
            problems.append("quarantine step does not record a manifest — restore has nothing to work from")
        if "cp -p" not in script:
            problems.append("quarantine step does not preserve a copy before removing the file")
    return problems


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
        return ["bash not found — skipped quarantine round-trip"]
    quarantine = next((s for s in steps if "Quarantine" in (s.get("name") or "")), None)
    restore = next((s for s in steps if ALWAYS_RESTORE_STEP in (s.get("name") or "")), None)
    if quarantine is None or restore is None:
        return ["quarantine/restore steps missing — nothing to round-trip"]

    sandbox = pathlib.Path(tempfile.mkdtemp(prefix="argus-action-"))
    try:
        repo = sandbox / "repo"
        (repo / ".opencode" / "agent").mkdir(parents=True)

        # V2-format consumer config (the failing case from men#164).
        (repo / "opencode.json").write_text(
            json.dumps(
                {
                    "$schema": "https://opencode.ai/config.json",
                    "agent": {
                        "men": {
                            "model": "x/y",
                            "permissions": [
                                {"action": "question", "resource": "*", "effect": "allow"}
                            ],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        # Agent markdown whose frontmatter carries a V2 permissions block.
        agent_md = repo / ".opencode" / "agent" / "men.md"
        agent_md.write_text(
            "---\ndescription: t\nmode: primary\nmodel: x/y\n"
            "permissions:\n  - action: question\n    effect: allow\n"
            "---\n\n# men\n",
            encoding="utf-8",
        )
        # A V1-only consumer file that must be left completely alone.
        v1_file = repo / "v1only.json"
        v1_file.write_text('{"agent":{"a":{"permission":{"question":"allow"}}}}', encoding="utf-8")
        v1_before = v1_file.read_text(encoding="utf-8")

        gh_env = sandbox / "gh_env"
        gh_env.touch()

        problems: list[str] = []
        r = _run_script(_run_of(quarantine), repo, bash, {"GITHUB_ENV": str(gh_env)})
        if r.returncode != 0:
            problems.append(f"quarantine script exited {r.returncode}: {r.stderr.strip()[:200]}")
            return problems

        # After quarantine the V2 files must be gone and the frontmatter closed.
        if (repo / "opencode.json").exists():
            problems.append("quarantine did not remove opencode.json")
        if "permissions:" in agent_md.read_text(encoding="utf-8"):
            problems.append("quarantine did not strip the V2 permissions block from agent frontmatter")
        stripped = agent_md.read_text(encoding="utf-8")
        if not stripped.rstrip().endswith("# men") or stripped.count("---") < 2:
            problems.append("stripped frontmatter lost its closing '---' — opencode would fail to parse it")
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
        restored_json = json.loads((repo / "opencode.json").read_text(encoding="utf-8"))
        if "permissions" not in restored_json.get("agent", {}).get("men", {}):
            problems.append("restore did not bring back the V2 permissions array")
        if "permissions:" not in agent_md.read_text(encoding="utf-8"):
            problems.append("restore did not bring back the agent frontmatter permissions block")
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
        "required_steps": check_required_steps(steps),
        "version_pin": check_version_pin(steps),
        "path_export": check_path_export(steps),
        "quarantine_restore": check_quarantine_restore(steps),
        "quarantine_roundtrip": run_quarantine_roundtrip(steps, bash),
        "fixture_step": check_fixture_step(steps),
    }

    failed = {k: v for k, v in checks.items() if v}
    for name, problems in checks.items():
        if problems:
            for p in problems:
                print(f"[argus:action] {name}: {p}", file=sys.stderr)
        else:
            print(f"[argus:action] {name}: ok")

    print(f"[argus:action] {len(steps)} steps checked, {sum(len(v) for v in failed.values())} problem(s)")

    if args.output_json:
        pathlib.Path(args.output_json).write_text(
            '{"steps": %d, "problems": %s}\n'
            % (len(steps), json.dumps(failed)),
            encoding="utf-8",
        )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
