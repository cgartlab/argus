#!/usr/bin/env python3
"""Regression tests for the Configure git / Scrub token steps.

Covers issue #195 (removing the remote credential broke `git fetch` on private
consumer repos, which made the review itself fail) and the original threat in
#183 (the review agent must not push to the consumer's branch).

The action resolves this by keeping the credential on the remote and blocking
push with a local `pre-push` hook instead. These tests extract the real step
scripts from action.yml and execute them in a scratch repository, so a change
to the YAML cannot silently drop either half of the contract.

Run: python3 tools/test_push_block_fetch_ok.py
"""

import os
import subprocess
import sys
import tempfile

import yaml

ACTION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    ".github", "actions", "argus-review", "action.yml",
)
FAKE_TOKEN = "SECRET123@github.com/x/y.git"
REPO = "cgartlab/argus"


def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr}")
    return r


def load_steps():
    with open(ACTION, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    steps = {s.get("name"): s for s in doc["runs"]["steps"]}
    return steps["Configure git"], steps["Scrub token from git config"]


def render(script, hooks_parent):
    """Substitute GitHub expression templates with test values.

    ``runner.temp`` becomes a dedicated directory (not the scratch repo), so
    the hook install cannot pollute the repository under test.
    """
    return (
        script.replace("${{ inputs.github-token }}", FAKE_TOKEN)
        .replace("${{ github.repository }}", REPO)
        .replace("${{ runner.temp }}", hooks_parent)
    )


def main():
    cfg_step, scrub_step = load_steps()
    failures = []

    # A fresh scratch repo standing in for the consumer's checkout.
    tmp = tempfile.mkdtemp(prefix="argus-cfgtest-")
    git(tmp, "init", "-q", tmp)
    git(tmp, "remote", "add", "origin", f"https://github.com/{REPO}.git")
    git(tmp, "config", "user.email", "t@t")
    git(tmp, "config", "user.name", "t")

    # ── Run the real Configure git script ──────────────────────────────────
    hooks_parent = tempfile.mkdtemp(prefix="argus-cfgtest-hooks-")
    env = dict(os.environ)
    env["GH_TOKEN_VALUE"] = FAKE_TOKEN
    r = subprocess.run(
        ["bash", "-c", render(cfg_step["run"], hooks_parent)],
        capture_output=True, text=True, env=env, cwd=tmp,
    )
    if r.returncode != 0:
        print(f"FAIL Configure git exited {r.returncode}: {r.stderr}")
        failures.append("configure-git-exit")
    else:
        print("PASS Configure git ran cleanly")

    # #195: the remote must keep its credential so `git fetch` works on a
    # private repo. This is the assertion whose absence caused the regression.
    url = git(tmp, "remote", "get-url", "origin").stdout.strip()
    if f"x-access-token:{FAKE_TOKEN}" in url:
        print("PASS remote retains credential (fetch works on private repos)")
    else:
        print(f"FAIL remote lost credential: {url}")
        failures.append("remote-credential")

    # #183: push must be blocked by the hook.
    hooks = git(tmp, "config", "--get", "core.hooksPath", check=False)
    if hooks.returncode == 0 and hooks.stdout.strip():
        hook_file = os.path.join(hooks.stdout.strip(), "pre-push")
        if os.path.isfile(hook_file):
            print("PASS core.hooksPath set with a pre-push hook")
        else:
            print(f"FAIL pre-push hook missing at {hook_file}")
            failures.append("hook-missing")
    else:
        print("FAIL core.hooksPath not set")
        failures.append("hooks-path")

    # The agent must still be able to commit — a review agent may commit as
    # part of finishing its work, and failing that would take the review down.
    with open(os.path.join(tmp, "f"), "w") as fh:
        fh.write("x")
    git(tmp, "add", "f")
    c = git(tmp, "commit", "-qm", "x", check=False)
    if c.returncode == 0:
        print("PASS commit still works")
    else:
        print(f"FAIL commit broken: {c.stderr}")
        failures.append("commit")

    # Push against a local bare remote, so an invalid fake token cannot mask
    # the hook: this asserts "push is blocked", not "the token is invalid".
    bare = tempfile.mkdtemp(prefix="argus-cfgtest-bare-")
    git(tmp, "init", "-q", "--bare", bare)
    p = git(tmp, "push", bare, "HEAD:refs/heads/test", check=False)
    if p.returncode != 0 and "disabled during the review run" in (p.stdout + p.stderr):
        print("PASS push blocked by the pre-push hook")
    else:
        print(f"FAIL push not blocked by hook: {p.stdout}{p.stderr}")
        failures.append("push-blocked")

    # ── Run the real Scrub script ──────────────────────────────────────────
    rs = subprocess.run(
        ["bash", "-c", render(scrub_step["run"], hooks_parent)],
        capture_output=True, text=True, cwd=tmp,
    )
    if rs.returncode != 0:
        print(f"FAIL Scrub exited {rs.returncode}: {rs.stdout}{rs.stderr}")
        failures.append("scrub-exit")
    else:
        print("PASS Scrub ran cleanly")

    url2 = git(tmp, "remote", "get-url", "origin").stdout.strip()
    if "x-access-token" not in url2:
        print("PASS Scrub removed the credential")
    else:
        print(f"FAIL credential survived scrub: {url2}")
        failures.append("scrub-credential")

    hooks2 = git(tmp, "config", "--get", "core.hooksPath", check=False)
    if hooks2.returncode != 0:
        print("PASS Scrub removed core.hooksPath")
    else:
        print("FAIL core.hooksPath survived scrub")
        failures.append("scrub-hooks")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {', '.join(failures)}")
        return 1
    print("All push-block/fetch-OK tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
