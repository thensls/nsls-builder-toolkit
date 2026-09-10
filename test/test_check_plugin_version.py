#!/usr/bin/env python3
"""The PR gate that refuses a merge to main without a plugin.json version bump.

Plain stdlib, no pytest: run with `python3 test/test_check_plugin_version.py`.

The failure this exists to prevent (2026-09-10): eight PRs merged to main
between 2026-09-05 and 2026-09-09 without touching `.claude-plugin/plugin.json`.
Every builder's machine ran `claude plugin update` daily and was told
"already at the latest version (3.6.0)" while serving a cache 37 commits
behind main — the whole guardrails series never reached anyone. The plugin
cache is version-pinned, so a merge that does not bump the version is a
merge nobody receives.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_plugin_version.py"
MANIFEST = ".claude-plugin/plugin.json"

failures = []


def check(label, cond):
    print(f"{'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(label)


def git(cwd, *args):
    subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )


def write_manifest(repo, version):
    path = Path(repo) / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {"name": "nsls-builder-toolkit", "version": version}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def make_repo(tmp, base_version, head_version=None, head_raw=None):
    """A repo whose `main` carries base_version and whose checked-out feature
    branch carries head_version (or head_raw, a literal file body for the
    malformed cases). Mirrors what CI sees: the PR head checked out, the base
    reachable as a ref."""
    repo = Path(tmp) / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.test")
    git(repo, "config", "user.name", "t")
    if base_version is not None:
        write_manifest(repo, base_version)
    else:
        (repo / "README.md").write_text("no manifest yet\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "base")
    git(repo, "checkout", "-q", "-b", "feature")
    if head_raw is not None:
        path = repo / MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(head_raw, encoding="utf-8")
    else:
        write_manifest(repo, head_version)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", "head")
    return repo


def run(repo, base="main", head=None):
    argv = [sys.executable, str(SCRIPT), base] + ([head] if head else [])
    r = subprocess.run(argv, cwd=str(repo), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.6.0"))
    check("same version is refused", code != 0)
    check("refusal names the file to edit", MANIFEST in out)
    check("refusal shows both versions", "3.6.0" in out)
    check("refusal suggests the next patch version", "3.6.1" in out)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.6.1"))
    check("patch bump passes", code == 0)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.7.0"))
    check("minor bump passes", code == 0)
    check("a pass says what it compared", "3.6.0" in out and "3.7.0" in out)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "4.0.0"))
    check("major bump passes", code == 0)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.5.9"))
    check("a version lower than main is refused", code != 0)

with tempfile.TemporaryDirectory() as tmp:
    # String comparison would call "3.10.0" < "3.9.0". Numeric must win.
    code, out = run(make_repo(tmp, "3.9.0", "3.10.0"))
    check("compares numerically, not lexically (3.10.0 > 3.9.0)", code == 0)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.7"))
    check("two-part version is refused", code != 0)
    check("malformed version names the expected shape", "X.Y.Z" in out)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", head_raw="{not json\n"))
    check("unparseable manifest is refused, not crashed", code != 0)
    check("unparseable manifest is explained", "plugin.json" in out.lower())

with tempfile.TemporaryDirectory() as tmp:
    # First commit ever to add a manifest: nothing to compare against, allow.
    code, out = run(make_repo(tmp, None, "1.0.0"))
    check("a base with no manifest passes (first version)", code == 0)

with tempfile.TemporaryDirectory() as tmp:
    code, out = run(make_repo(tmp, "3.6.0", "3.7.0"), base="refs/heads/does-not-exist")
    check("an unresolvable base ref fails loudly", code != 0)
    check("unresolvable base is explained", "does-not-exist" in out)

# --- two-argument form: what the workflow runs under pull_request_target ------
with tempfile.TemporaryDirectory() as tmp:
    # Base checked out, PR head only as a ref. The working tree is the BASE
    # (unbumped) — with an explicit head ref it must be ignored.
    repo = make_repo(tmp, "3.6.0", "3.7.0")
    git(repo, "checkout", "-q", "main")
    code, out = run(repo, base="HEAD", head="feature")
    check("head-ref form: reads the manifest from the ref, not the working tree", code == 0)
    check("head-ref form: reports both versions", "3.6.0" in out and "3.7.0" in out)

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(tmp, "3.6.0", "3.6.0")
    git(repo, "checkout", "-q", "main")
    code, out = run(repo, base="HEAD", head="feature")
    check("head-ref form: unbumped head is refused", code != 0)

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(tmp, "3.6.0", "3.7.0")
    code, out = run(repo, base="main", head="refs/remotes/pr/nope")
    check("head-ref form: unresolvable head fails loudly", code != 0 and "nope" in out)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print(f"all passed")
