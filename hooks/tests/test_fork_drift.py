#!/usr/bin/env python3
"""When the toolkit is allowed to say a personal-toolkit FORK has fallen behind.

Plain stdlib, no pytest, no network: NSLS and the fork are both local bare
repos. Run with `python3 hooks/tests/test_fork_drift.py`.

The silence these exist to end (verified 2026-09-09): an active builder's
personal toolkit was her own GitHub fork. Her checkout tracked the fork, the
fork never received anything NSLS shipped, so every session pulled cleanly,
every check reported healthy, and she sat 196 commits behind for months.
The personal toolkit's own hook now carries the same check — but that hook
lives inside the fork, so no fork can receive it; this hook self-updates
from NSLS on every machine and is the only channel that reaches a fork.
"""

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "session-start.py"

spec = importlib.util.spec_from_file_location("session_start_hook", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

failures = []


checks_run = 0


def check(label, cond):
    global checks_run
    checks_run += 1
    print(f"{'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(label)


def git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=True, capture_output=True, text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout.strip()


def commit(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", f"add {name}")


def seed_repo(path):
    path.mkdir()
    git(path, "init", "--quiet")
    git(path, "config", "user.email", "t@t.test")
    git(path, "config", "user.name", "T")
    git(path, "checkout", "--quiet", "-b", "main")
    return path


def make_world(tmp, nsls_ahead=5):
    """NSLS (bare) → fork (bare, frozen at NSLS's first commit) → the builder's
    checkout, cloned from the fork, with one customization of her own. NSLS then
    moves `nsls_ahead` commits on. This is Chelsea's machine in miniature."""
    tmp = Path(tmp)
    work = seed_repo(tmp / "seed")
    commit(work, "skill.md", "v1\n")
    nsls = tmp / "nsls.git"
    git(work, "clone", "--quiet", "--bare", str(work), str(nsls))
    fork = tmp / "fork.git"
    git(work, "clone", "--quiet", "--bare", str(nsls), str(fork))
    for i in range(nsls_ahead):
        commit(work, f"skill{i}.md", f"v{i}\n")
    git(work, "push", "--quiet", str(nsls), "main")

    config_dir = tmp / ".claude"
    plugin_dir = config_dir / "local-plugins" / "nsls-personal-toolkit"
    plugin_dir.parent.mkdir(parents=True)
    git(tmp, "clone", "--quiet", str(fork), str(plugin_dir))
    git(plugin_dir, "config", "user.email", "her@t.test")
    git(plugin_dir, "config", "user.name", "Her")
    commit(plugin_dir, "mine.md", "her own customization\n")

    hook.CONFIG_DIR = config_dir
    hook.PERSONAL_UPSTREAM_STAMP = config_dir / ".nsls-personal-upstream-check"
    hook.PERSONAL_UPSTREAM_URL = str(nsls)
    return plugin_dir, nsls


def run(deadline=None):
    buf = io.StringIO()
    with redirect_stdout(buf):
        hook.report_personal_fork_drift(deadline=deadline)
    return buf.getvalue()


# ---------------------------------------------------------------- URL forms
yes = [
    "https://github.com/thensls/nsls-personal-toolkit.git",
    "https://github.com/thensls/nsls-personal-toolkit",
    "https://github.com/thensls/nsls-personal-toolkit/",
    "git@github.com:thensls/nsls-personal-toolkit.git",
    "github.com:thensls/nsls-personal-toolkit.git",
    "ssh://git@github.com/thensls/nsls-personal-toolkit.git",
    "ssh://git@github.com:22/thensls/nsls-personal-toolkit.git",
    "https://user:tok@github.com/thensls/nsls-personal-toolkit.git",
    "https://www.github.com/thensls/nsls-personal-toolkit",
    "HTTPS://GitHub.com/THENSLS/NSLS-Personal-Toolkit.GIT",
]
no = [
    "https://github.com/grandmamischief/nsls-personal-toolkit.git",
    "https://github.com/cbyers-nsls/nsls-personal-toolkit.git",
    "https://gitlab.com/mirror/thensls/nsls-personal-toolkit.git",
    "https://github.com/thensls/nsls-personal-toolkit-experiments.git",
    "https://github.com/thensls/nsls-builder-toolkit.git",
    "https://github.com.evil.example/thensls/nsls-personal-toolkit.git",
    "C:\\Users\\x\\thensls\\nsls-personal-toolkit",
    "/Users/x/thensls/nsls-personal-toolkit",
    "file:///Users/x/thensls/nsls-personal-toolkit",
    "", None,
]
check("every canonical spelling is recognised",
      all(hook._is_canonical_origin(u) is True for u in yes))
check("no fork, mirror, look-alike or local path passes as canonical",
      all(hook._is_canonical_origin(u) is False for u in no))

# ------------------------------------------------------- the fork, behind
with tempfile.TemporaryDirectory() as tmp:
    plugin_dir, nsls = make_world(tmp, nsls_ahead=5)
    out = run()
    check("a fork 5 behind NSLS is announced with the exact count",
          "OWN FORK" in out and "is 5 commit(s) behind NSLS" in out)
    check("the notice names OUR remote, not a bare 'upstream'",
          "merge nsls-upstream/main into the checkout" in out and "merge upstream/main" not in out)
    check("the notice names the checkout path and the skill file to follow",
          str(plugin_dir) in out and "skills/update-personal-productivity/SKILL.md" in out)
    check("exactly one line, all of it ours — nothing of git's output leaks",
          out.count("\n") == 1 and out.startswith("[NSLS Personal Toolkit] ")
          and "fatal" not in out and "From " not in out)
    check("the remote we fetched was added under our own name",
          git(plugin_dir, "remote", "get-url", "nsls-upstream") == str(nsls))
    check("her own commit is untouched (we only fetched)",
          (plugin_dir / "mine.md").exists() and git(plugin_dir, "status", "--porcelain") == "")
    check("the stamp was written",
          hook.PERSONAL_UPSTREAM_STAMP.exists())

    check("an immediate second run is throttled into silence", run() == "")

    # A stamp from the FUTURE must not read as fresh.
    future = time.time() + 5 * 3600
    os.utime(hook.PERSONAL_UPSTREAM_STAMP, (future, future))
    check("a future-dated stamp does not silence the check", "OWN FORK" in run())

    # A stamp older than the window re-arms the check.
    stale = time.time() - 13 * 3600
    os.utime(hook.PERSONAL_UPSTREAM_STAMP, (stale, stale))
    check("a 13h-old stamp re-arms the check", "OWN FORK" in run())

    # A deadline already spent: silent, AND the slot is not claimed.
    hook.PERSONAL_UPSTREAM_STAMP.unlink(missing_ok=True)
    check("no time left in the hook budget: silent", run(deadline=time.monotonic() - 1) == "")
    check("...and the slot was NOT claimed, so the next session gets a real check",
          not hook.PERSONAL_UPSTREAM_STAMP.exists())

    # Her own `upstream` pointing at something unrelated: left alone, not counted.
    other = seed_repo(Path(tmp) / "other")
    for i in range(40):
        commit(other, f"o{i}.md", "x\n")
    git(plugin_dir, "remote", "add", "upstream", str(other))
    out = run()
    check("a foreign 'upstream' remote is neither fetched nor counted",
          "is 5 commit(s) behind NSLS" in out)
    check("...and is left exactly as she had it",
          git(plugin_dir, "remote", "get-url", "upstream") == str(other))

    # Our remote left pointing somewhere wrong gets repaired.
    git(plugin_dir, "remote", "set-url", "nsls-upstream", str(other))
    hook.PERSONAL_UPSTREAM_STAMP.unlink(missing_ok=True)
    out = run()
    check("a mis-pointed nsls-upstream is repaired to the real URL and the count is right",
          git(plugin_dir, "remote", "get-url", "nsls-upstream") == str(nsls)
          and "is 5 commit(s) behind NSLS" in out)

    # Mirror URL as origin (Macroscope's case): NOT canonical, so still checked.
    real_origin = git(plugin_dir, "remote", "get-url", "origin")
    git(plugin_dir, "remote", "set-url", "origin",
        "https://gitlab.example/mirror/thensls/nsls-personal-toolkit.git")
    hook.PERSONAL_UPSTREAM_STAMP.unlink(missing_ok=True)
    check("an origin that merely CONTAINS the canonical path is still checked",
          "OWN FORK" in run())

    # Canonical origin: not a fork, so this check says nothing and touches nothing.
    git(plugin_dir, "remote", "set-url", "origin",
        "https://github.com/thensls/nsls-personal-toolkit.git")
    hook.PERSONAL_UPSTREAM_STAMP.unlink(missing_ok=True)
    check("a canonical checkout is silent here (the freeze checks own it)", run() == "")
    check("...and no stamp is written for it", not hook.PERSONAL_UPSTREAM_STAMP.exists())
    git(plugin_dir, "remote", "set-url", "origin", real_origin)

    # Fork caught up: silent.
    git(plugin_dir, "merge", "--quiet", "--no-edit", "nsls-upstream/main")
    hook.PERSONAL_UPSTREAM_STAMP.unlink(missing_ok=True)
    check("a fork that has been caught up is silent", run() == "")

    # No checkout at all: silent, no crash.
    hook.CONFIG_DIR = Path(tmp) / "nowhere"
    check("no personal toolkit installed: silent", run() == "")

print()
if failures:
    print(f"{len(failures)} FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"all {checks_run} checks passed")
