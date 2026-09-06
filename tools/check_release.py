#!/usr/bin/env python3
"""
Release gate — verify the repo's VERSION is (or is not) released.

A version counts as "released" iff the tag `v{VERSION}` exists on the
`origin` remote. This script is the single gate shared by CI and
`make release` so the two can never disagree:

  CI:            python3 tools/check_release.py --expect-released
                 Fail unless v{VERSION} is tagged on origin. Catches
                 "phantom versions" — VERSION (and the site/docs that read
                 it) bumped and merged, but no release was ever cut
                 (the v0.5.0 incident: files said 0.5.0, no tag existed).

  make release:  python3 tools/check_release.py --expect-unreleased
                 Refuse to release when v{VERSION} already exists
                 (duplicate release) or when VERSION is not strictly newer
                 than the latest released tag (an accidental revert would
                 re-publish an older version as GitHub latest).

  No flag:       print release status (informational, exit 0).

Exit codes: 0 = ok, 1 = gate failed, 2 = usage/environment error.
Run from the repository root.
"""

import re
import subprocess
import sys

TAG_PREFIX = "v"
VERSION_FILE = "VERSION"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"FAIL: {VERSION_FILE} not found — run from the repository root")
        sys.exit(2)


def parse_semver(ver: str) -> tuple:
    if not SEMVER_RE.match(ver):
        print(f"FAIL: version '{ver}' in {VERSION_FILE} is not a valid x.y.z semver")
        sys.exit(2)
    return tuple(int(g) for g in ver.split("."))


def get_tags() -> set:
    """Tag names, preferring live ls-remote on origin; falls back to local tags.

    Returns (tags, used_remote) where used_remote is False only when origin
    was unreachable (offline dev box) and local tags were used instead.
    """
    try:
        out = subprocess.run(
            ["git", "ls-remote", "--tags", "origin"],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            tags = set()
            for line in out.stdout.splitlines():
                if "\t" not in line:
                    continue
                ref = line.split("\t", 1)[1]
                if ref.startswith("refs/tags/") and not ref.endswith("^{}"):
                    tags.add(ref[len("refs/tags/"):])
            return tags, True
        print(
            f"WARNING: 'git ls-remote --tags origin' failed (exit {out.returncode}) "
            f"— falling back to local tags. Gate verdict may be stale.",
            file=sys.stderr,
        )
    except OSError as e:
        print(
            f"WARNING: 'git ls-remote --tags origin' unavailable ({e}) "
            f"— falling back to local tags. Gate verdict may be stale.",
            file=sys.stderr,
        )
    out = subprocess.run(["git", "tag", "-l"], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        print("FAIL: could not list tags (git ls-remote and git tag -l both failed)")
        sys.exit(2)
    return set(out.stdout.splitlines()), False


def latest_released(tags: set):
    """Return (version_tuple, tag_name) of the newest v*.*.* tag, or None."""
    best = None
    for t in tags:
        m = re.fullmatch(re.escape(TAG_PREFIX) + r"(\d+)\.(\d+)\.(\d+)", t)
        if not m:
            continue
        v = tuple(int(g) for g in m.groups())
        if best is None or v > best[0]:
            best = (v, t)
    return best


def main() -> None:
    allowed = ("--expect-released", "--expect-unreleased")
    argv = sys.argv[1:]
    if len(argv) > 1 or (argv and argv[0] not in allowed):
        print(__doc__)
        sys.exit(2)
    mode = argv[0] if argv else None

    version = read_version()
    ver = parse_semver(version)
    tag = TAG_PREFIX + version
    tags, used_remote = get_tags()
    latest = latest_released(tags)
    released = tag in tags

    print(f"VERSION {version} -> {tag} [{'released' if released else 'NOT released'}]")
    if latest:
        print(f"latest released tag: {latest[1]}")
    if not used_remote:
        print("note: origin unreachable — verdict based on local tags only")

    if mode is None:
        return  # informational

    if mode == "--expect-released":
        if released:
            print(f"ok: {tag} exists on origin - release is current")
            return
        if latest and ver < latest[0]:
            print(
                f"FAIL: VERSION {version} is OLDER than the latest released "
                f"{latest[1]} - this looks like an accidental revert of VERSION. "
                f"Fix VERSION (or the merge that reverted it) before proceeding."
            )
            sys.exit(1)
        print(
            f"FAIL: VERSION {version} has no release tag {tag} on origin - "
            f"a version bump was committed but never released, so the site/docs/"
            f"agent advertise {version} with no GitHub Release or skill package. "
            f"Cut the release: 'make release' (or push tag {tag})."
        )
        sys.exit(1)

    # --expect-unreleased (make release)
    if released:
        print(
            f"FAIL: {tag} is ALREADY released on origin - refusing to release twice. "
            f"Bump VERSION first: 'make bump-patch'."
        )
        sys.exit(1)
    if latest and ver <= latest[0]:
        print(
            f"FAIL: VERSION {version} is not strictly newer than the latest "
            f"released {latest[1]} - refusing to re-release an older/equal "
            f"version (GitHub would mark it 'latest'). Bump VERSION first: "
            f"'make bump-patch'."
        )
        sys.exit(1)
    print(f"ok: {tag} is unreleased and newer than every tag - releasing is allowed")


if __name__ == "__main__":
    main()