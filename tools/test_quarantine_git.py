#!/usr/bin/env python3
"""
test_quarantine_git.py — prove the V1-compatibility quarantine stays invisible to git

Bug pinned here (cgartlab/men#164, polluting commit a21a4c44)
--------------------------------------------------------------
The old quarantine step *deleted* the consumer's V2 opencode config to satisfy
the pinned OpenCode 1 CLI. OpenCode v1.19.3's github/index.ts commits whatever
the worktree reports:

    branchIsDirty()      -> `git status --porcelain` non-empty
    pushToLocalBranch()  -> `git add .` -> `git commit -m <summary>` -> `git push`

So a dirty worktree during the review is *always* committed and pushed onto
the consumer's PR branch. The pollution found in men#164 was exactly this:

    opencode.json              deleted (V2 permissions: [...] lost)
    .opencode/agent/men.md     permissions: block stripped
    .opencode/package.json     + @opencode-ai/plugin: 1.19.3 (written by the CLI)

Restoring afterwards is too late — the CLI has already pushed by then.

The fix neutralises the V2 keys in place and hides each touched path with
`git update-index --skip-worktree` (plus .git/info/exclude for paths that did
not exist yet), so the worktree stays clean from the CLI's point of view.

Why this test extracts the step body instead of re-implementing it
-------------------------------------------------------------------
A Python re-implementation of the quarantine would be a second copy of the
logic and could silently drift from action.yml, passing while the action is
broken. Instead this test pulls the `run:` body of the real step out of
.github/actions/argus-review/action.yml and executes it verbatim with bash
against a throw-away consumer repo. If the action changes, the test changes.

No LLM, no network, no GitHub runner: git + bash + stdlib only.

Run:
    python tools/test_quarantine_git.py

Exit codes:
    0 — all assertions passed
    1 — assertion failure (the fix regressed)
    2 — environment problem (missing git/bash/PyYAML)
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from validate_action import (  # noqa: E402  - local module, must follow sys.path insert
    _bash_available,
    _find_keys,
    _load_action,
    _run_of,
    _run_script,
    _steps,
)

ACTION_FILE = pathlib.Path(__file__).resolve().parent.parent / ".github" / "actions" / "argus-review" / "action.yml"

# ---------------------------------------------------------------------------
# A synthetic consumer repo in the exact shape men#164 had when it got burned:
# two V2 JSON configs, one agent file with a permissions block, the plugin
# package the V1 CLI rewrites, and one legitimate source file a review agent
# might legitimately edit.
# ---------------------------------------------------------------------------
OPENCODE_JSON = """{\n  \"$schema\": \"https://opencode.ai/config.json\",\n  \"default_agent\": \"men\",\n  \"agent\": {\n    \"men\": {\n      \"model\": \"deepseek-v4-flash\",\n      \"description\": \"orchestrator\",\n      \"permissions\": [\n        {\"action\": \"question\", \"resource\": \"*\", \"effect\": \"allow\"},\n        {\"action\": \"edit\", \"resource\": \"**/*.md\", \"effect\": \"deny\"}\n      ]\n    },\n    \"ji\": {\n      \"model\": \"senseNova-6.8-flash-lite\",\n      \"permissions\": [{\"action\": \"bash\", \"resource\": \"npm test\", \"effect\": \"allow\"}]\n    }\n  }\n}\n"""

OPENCODE_JSON_ALT = """{\n  \"agent\": {\"men\": {\"model\": \"deepseek-v4-flash\", \"permissions\": [{\"action\": \"edit\", \"effect\": \"deny\"}]}}\n}\n"""

AGENT_MD = """---
description: orchestrator
mode: primary
model: deepseek-v4-flash
permissions:
  - action: question
    resource: "*"
    effect: allow
  - action: edit
    effect: deny
---

# men

## Role
Orchestrates the review.
"""

PACKAGE_JSON = """{\n  "name": "men",\n  "dependencies": {\n    "@opencode/plugin": "2.0.6"\n  }\n}\n"""

# An agent file the consumer gitignores: untracked, so `--skip-worktree` cannot
# apply. It is hidden by the .git/info/exclude block instead, which proves that
# second mechanism works for pre-existing untracked files as well.
UNTRACKED_AGENT = """---
description: local scratch agent
mode: subagent
model: deepseek-v4-flash
permissions:
  - action: bash
    effect: deny
---

# scratch
"""

APP_CSS = "/* review me */\n.card { color: #fff; }\n"

# Paths that must never leave the repo's index while the review runs.
QUARANTINED = ("opencode.json", ".opencode/opencode.json", ".opencode/agent/men.md")
# The three files from the defect report: two V2 configs plus the plugin
# package the V1 CLI rewrites.
MASKED = QUARANTINED + (".opencode/package.json",)


def git(repo: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )


def build_consumer_repo(root: pathlib.Path) -> dict[str, bytes]:
    """Create a committed consumer repo and return each file's original bytes."""
    repo = root / "consumer"
    (repo / ".opencode" / "agent").mkdir(parents=True)
    (repo / "src").mkdir()
    originals: dict[str, bytes] = {}
    layout = {
        "opencode.json": OPENCODE_JSON,
        ".opencode/opencode.json": OPENCODE_JSON_ALT,
        ".opencode/agent/men.md": AGENT_MD,
        ".opencode/package.json": PACKAGE_JSON,
        "src/app.css": APP_CSS,
        ".gitignore": ".opencode/agent/scratch.md\n",
    }
    for rel, body in layout.items():
        p = repo / rel
        p.write_text(body, encoding="utf-8")
        originals[rel] = p.read_bytes()
    # Untracked because the consumer gitignores local agent definitions -- a
    # common pattern. `--skip-worktree` cannot apply to untracked paths, so
    # this exercises the branch where the quarantine only has .gitignore and
    # .git/info/exclude to hide behind. It must still be neutralised and
    # restored byte-for-byte.
    scratch = repo / ".opencode/agent/scratch.md"
    scratch.write_text(UNTRACKED_AGENT, encoding="utf-8")
    originals[".opencode/agent/scratch.md"] = scratch.read_bytes()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "argus-test@example.invalid")
    git(repo, "config", "user.name", "argus test")
    # CI runs on Linux; local runs may be Windows, where git would translate
    # LF -> CRLF and break every byte-for-byte comparison below.
    git(repo, "config", "core.autocrlf", "false")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: V2 consumer config")
    assert git(repo, "status", "--porcelain").stdout == ""
    return originals


def step_body(action: dict, fragment: str) -> str:
    for step in _steps(action):
        if fragment in (step.get("name") or ""):
            return _run_of(step)
    raise AssertionError(f"step not found in action.yml: {fragment!r}")


def read_quarantine_dir(gh_env: pathlib.Path) -> str:
    for line in gh_env.read_text(encoding="utf-8").splitlines():
        if line.startswith("QUARANTINE_DIR="):
            return line.split("=", 1)[1]
    return ""


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, ok: bool, label: str) -> None:
        self.checks += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {label}")
        if not ok:
            self.failures.append(label)

    def eq(self, actual, expected, label: str) -> None:
        self.check(actual == expected, f"{label} (got {actual!r}, want {expected!r})")


def main() -> int:
    if shutil.which("git") is None:
        print("git not found — cannot run git-level quarantine test", file=sys.stderr)
        return 2
    bash = _bash_available()
    if bash is None:
        print("bash not found — cannot run git-level quarantine test", file=sys.stderr)
        return 2

    action = _load_action(ACTION_FILE)
    quarantine_body = step_body(action, "Quarantine V2-only opencode config")
    restore_body = step_body(action, "Restore quarantined opencode config")
    gate_body = step_body(action, "Verify worktree is clean before review")

    rep = Report()
    with tempfile.TemporaryDirectory(prefix="argus-git-test-") as td:
        sandbox = pathlib.Path(td)
        # mktemp -d inside the step must land outside the repo, or its own
        # backup directory would look like an untracked file to git.
        (sandbox / "tmp").mkdir()
        env = {"GITHUB_ENV": str(sandbox / "gh_env"), "TMPDIR": str(sandbox / "tmp")}
        (sandbox / "gh_env").write_text("", encoding="utf-8")
        originals = build_consumer_repo(sandbox)
        repo = sandbox / "consumer"

        # ---- 1. quarantine runs, worktree is clean from git's point of view ----
        print("\n[1] quarantine: V1 compatibility + invisible to git")
        r = _run_script(quarantine_body, repo, bash, env)
        rep.check(r.returncode == 0, f"quarantine step exits 0 (exit={r.returncode})")
        if r.returncode != 0:
            print(r.stdout[-800:])
            print(r.stderr[-800:])
            return 1
        print("      quarantine stdout:")
        for line in r.stdout.rstrip().splitlines():
            print(f"        {line}")

        status = git(repo, "status", "--porcelain").stdout.strip()
        rep.check(status == "", f"`git status --porcelain` empty after quarantine (got {status!r})")

        flagged = [ln for ln in git(repo, "ls-files", "-v").stdout.splitlines() if ln.startswith("S ")]
        rep.check(
            len(flagged) == 4,
            f"4 tracked paths carry --skip-worktree (got {len(flagged)}: {[ln[2:] for ln in flagged]})",
        )
        exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        rep.check(
            ".opencode/agent/scratch.md" in exclude,
            "untracked masked path recorded in .git/info/exclude",
        )
        rep.check(
            "argus-quarantine:BEGIN" in exclude and "argus-quarantine:END" in exclude,
            "exclude block is delimited so restore can remove it wholesale",
        )

        # ---- 2. V1 compatibility: the rewritten config parses and lost only `permissions` ----
        print("\n[2] V1 compatibility of the neutralised config")
        data = json.loads((repo / "opencode.json").read_text(encoding="utf-8"))
        rep.check("permissions" not in json.dumps(data), "opencode.json has no `permissions` key")
        rep.check(not _find_keys(data, "permissions"), "no nested `permissions` key remains")
        rep.check(data.get("default_agent") == "men", "default_agent survives")
        rep.eq(data.get("agent", {}).get("men", {}).get("model"), "deepseek-v4-flash", "men model survives")
        rep.eq(data.get("agent", {}).get("ji", {}).get("model"), "senseNova-6.8-flash-lite", "ji model survives")
        rep.check(
            (repo / ".opencode/opencode.json").exists() and not _find_keys(
                json.loads((repo / ".opencode/opencode.json").read_text(encoding="utf-8")), "permissions"
            ),
            ".opencode/opencode.json neutralised too",
        )
        agent_text = (repo / ".opencode/agent/men.md").read_text(encoding="utf-8")
        rep.check("permissions:" not in agent_text, "agent frontmatter permissions block stripped")
        rep.check(agent_text.startswith("---\n"), "agent frontmatter still opens")
        rep.check("## Role\nOrchestrates the review." in agent_text, "agent body intact after the frontmatter")
        rep.check(agent_text.count("---") == 2, "frontmatter still closed (two `---`)")
        for keep in ("description:", "mode:", "model:"):
            rep.check(keep in agent_text, f"frontmatter keeps `{keep}`")
        # The untracked agent md goes through the same code path but is hidden
        # by .git/info/exclude rather than --skip-worktree.
        scratch = (repo / ".opencode/agent/scratch.md").read_text(encoding="utf-8")
        rep.check("permissions:" not in scratch, "untracked agent md stripped too")
        rep.check(scratch.startswith("---\n") and scratch.count("---") == 2, "untracked agent frontmatter intact")
        rep.check(
            (repo / ".opencode/package.json").read_text(encoding="utf-8") == PACKAGE_JSON,
            "package.json untouched by quarantine (mask only)",
        )
        for rel in MASKED:
            rep.check((repo / rel).exists(), f"{rel} still exists (quarantine deletes nothing)")

        # ---- 3. the CLI's own push cannot include any quarantined path ----
        print("\n[3] simulated `git add .` (pushToLocalBranch) excludes every quarantined path")
        # What the V1 CLI does mid-run, from the defect report.
        pkg = repo / ".opencode/package.json"
        dep = json.loads(pkg.read_text(encoding="utf-8"))
        dep["dependencies"]["@opencode-ai/plugin"] = "1.19.3"
        pkg.write_text(json.dumps(dep, indent=2) + "\n", encoding="utf-8")
        (repo / ".opencode/package-lock.json").write_text('{"name": "men"}\n', encoding="utf-8")
        (repo / "src/app.css").write_text("/* agent edit */\n.card { color: var(--ds-color); }\n", encoding="utf-8")
        git(repo, "add", ".")
        staged = git(repo, "diff", "--cached", "--name-only").stdout.split()
        rep.check(staged == ["src/app.css"], f"`git add .` stages only the real agent edit (got {staged!r})")
        for rel in MASKED:
            rep.check(rel not in staged, f"`git add .` does not stage {rel}")
        rep.check(".opencode/package-lock.json" not in staged, "CLI-generated lockfile is not staged")
        c = git(repo, "commit", "-q", "-m", "simulated opencode push")
        rep.check(c.returncode == 0, f"commit succeeds (exit={c.returncode})")
        committed = git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split()
        rep.check(committed == ["src/app.css"], f"commit contains only the real agent edit (got {committed!r})")
        for rel in MASKED:
            rep.check(rel not in committed, f"commit does not contain {rel}")

        # ---- 4. restore brings every byte back and clears the git flags ----
        print("\n[4] restore: byte-for-byte + flags cleared")
        qdir = read_quarantine_dir(pathlib.Path(env["GITHUB_ENV"]))
        rep.check(qdir != "", "QUARANTINE_DIR exported for the restore step")
        r2 = _run_script(restore_body, repo, bash, {**env, "QUARANTINE_DIR": qdir})
        rep.check(r2.returncode == 0, f"restore step exits 0 (exit={r2.returncode})")
        if r2.returncode != 0:
            print(r2.stdout[-800:])
            print(r2.stderr[-800:])
        print("      restore stdout:")
        for line in r2.stdout.rstrip().splitlines():
            print(f"        {line}")
        for rel, original in originals.items():
            if rel == "src/app.css":
                continue  # the CLI committed this real edit; restore must not roll it back
            rep.check((repo / rel).read_bytes() == original, f"{rel} restored byte-for-byte")
        rep.check(
            "var(--ds-color)" in (repo / "src/app.css").read_text(encoding="utf-8"),
            "restore does not roll back the agent's real edit",
        )
        rep.check(
            not (repo / ".opencode/package-lock.json").exists(),
            "CLI-generated lockfile removed on restore",
        )
        rep.check(git(repo, "status", "--porcelain").stdout.strip() == "", "`git status --porcelain` empty after restore")
        rep.check(not [ln for ln in git(repo, "ls-files", "-v").stdout.splitlines() if ln.startswith("S ")],
                  "no --skip-worktree flag left behind")
        exclude = (repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")
        rep.check("argus-quarantine" not in exclude, ".git/info/exclude marker removed")

        # ---- 5. the pre-review gate is a real gate ----
        print("\n[5] worktree gate fails closed")
        g = _run_script(gate_body, repo, bash, {})
        rep.check(g.returncode == 0, f"clean worktree passes (exit={g.returncode})")
        rep.check("clean before review" in g.stdout, "clean worktree reports it is clean")
        (repo / "stray.txt").write_text("an earlier step's artifact\n", encoding="utf-8")
        g2 = _run_script(gate_body, repo, bash, {})
        rep.check(g2.returncode == 1, f"dirty worktree fails the run (exit={g2.returncode})")
        rep.check("stray.txt" in (g2.stdout + g2.stderr), "gate names the offending path")

    print(f"\n{len(rep.failures)} failure(s) across {rep.checks} checks")
    for f in rep.failures:
        print(f"  FAIL: {f}")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main())
