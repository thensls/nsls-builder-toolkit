#!/usr/bin/env python3
"""Refuse a PR to main that does not bump `.claude-plugin/plugin.json`.

Usage: python3 .github/scripts/check_plugin_version.py <base-ref> [<head-ref>]

With one argument the PR head is the working tree. With two, the head
manifest is read from <head-ref> via `git show` — the shape the workflow
uses under `pull_request_target`, where this script and the workflow come
from the BASE branch and nothing from the PR is ever executed, only read.

Why this gate exists: builders run the toolkit from a VERSION-PINNED plugin
cache. `claude plugin update` compares version strings and nothing else, so a
merge that leaves the version alone is a merge no machine ever receives — the
CLI keeps saying "already at the latest version" over a stale cache. Eight PRs
landed that way between 2026-09-05 and 2026-09-09 (37 commits, the whole
guardrails series) and nobody got them.

Rule: the version on the PR head must be strictly greater than the version on
the base branch, compared numerically as X.Y.Z. Patch for fixes, minor for new
skills or behavior, major for breaking changes to how builders install or use
the toolkit. A base with no manifest at all (the first version ever) passes.

Tests: test/test_check_plugin_version.py
"""

import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST = ".claude-plugin/plugin.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def fail(msg):
    print(f"::error file={MANIFEST}::{msg}")
    print(f"\nFAIL: {msg}")
    sys.exit(1)


def parse_version(raw, where):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"{where} {MANIFEST} is not valid JSON ({e.msg} at line {e.lineno}).")
    version = data.get("version") if isinstance(data, dict) else None
    if not isinstance(version, str):
        fail(f"{where} {MANIFEST} has no string \"version\" field.")
    m = SEMVER.match(version.strip())
    if not m:
        fail(f"{where} {MANIFEST} version {version!r} is not of the form X.Y.Z "
             f"(three integers, e.g. 3.7.0).")
    return tuple(int(g) for g in m.groups()), version.strip()


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(2)
    base_ref = sys.argv[1]
    head_ref = sys.argv[2] if len(sys.argv) == 3 else None

    if head_ref is None:
        head_path = Path(MANIFEST)
        if not head_path.exists():
            fail(f"{MANIFEST} is missing from the PR head.")
        head_raw = head_path.read_text(encoding="utf-8-sig")
    else:
        resolve_head = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"{head_ref}^{{commit}}"],
            capture_output=True, text=True,
        )
        if resolve_head.returncode != 0:
            fail(f"head ref {head_ref!r} does not resolve to a commit — was it fetched?")
        show_head = subprocess.run(
            ["git", "show", f"{head_ref}:{MANIFEST}"], capture_output=True, text=True,
        )
        if show_head.returncode != 0:
            fail(f"{MANIFEST} is missing from the PR head ({head_ref}).")
        head_raw = show_head.stdout
    head_tuple, head_str = parse_version(head_raw, "PR head")

    # Does the base ref resolve at all? A typo'd or unfetched ref must not
    # read as "no manifest on base" and wave the PR through.
    resolve = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{base_ref}^{{commit}}"],
        capture_output=True, text=True,
    )
    if resolve.returncode != 0:
        fail(f"base ref {base_ref!r} does not resolve to a commit — was it fetched?")

    show = subprocess.run(
        ["git", "show", f"{base_ref}:{MANIFEST}"],
        capture_output=True, text=True,
    )
    if show.returncode != 0:
        print(f"ok: {base_ref} has no {MANIFEST}; {head_str} is the first version.")
        return
    base_tuple, base_str = parse_version(show.stdout, f"base ({base_ref})")

    if head_tuple > base_tuple:
        print(f"ok: {MANIFEST} version {base_str} ({base_ref}) -> {head_str} (PR head)")
        return

    major, minor, patch = base_tuple
    fail(
        f"{MANIFEST} version must be bumped above {base_str} ({base_ref}); "
        f"the PR head has {head_str}. Builders install from a version-pinned "
        f"cache, so an unbumped merge never reaches them. Set \"version\" to "
        f"{major}.{minor}.{patch + 1} for a fix or {major}.{minor + 1}.0 for a "
        f"new skill or behavior, then push."
    )


if __name__ == "__main__":
    main()
