#!/usr/bin/env python3
"""The guards on the daily update every toolkit checkout runs at session start.

Plain stdlib, no pytest, no network: NSLS is a local bare repo and the
builder's checkout is a clone of it, tracking main, exactly as install.sh
leaves it. git runs with an isolated global config so a builder's own settings
cannot change the fixture. Run with `python3 hooks/tests/test_daily_pull_guards.py`.

The daily update was a plain `git pull --ff-only`. The clean-fork catch-up
(PR #198) proved four ways an unattended fast-forward goes wrong that a plain
pull does nothing about: it overwrites an ignored local file the update starts
tracking; a merge setting turns it into something else; the builder's own
hooks run on NSLS's checkout, and can hang; and an unfinished operation can sit
clean on the branch being moved. Each case below fails if its guard is removed.
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

# --- isolate git from the machine's own configuration ------------------------
ISO = Path(tempfile.mkdtemp(prefix="daily-pull-iso-"))
(ISO / "nohooks").mkdir()
(ISO / "gitconfig").write_text(
    "[user]\n\tname = T\n\temail = t@t.test\n"
    "[commit]\n\tgpgsign = false\n"
    "[init]\n\tdefaultBranch = main\n"
    "[clone]\n\tdefaultRemoteName = origin\n"
    f"[core]\n\thooksPath = {ISO / 'nohooks'}\n"
    "[protocol \"file\"]\n\tallow = always\n",
    encoding="utf-8",
)
os.environ["GIT_CONFIG_GLOBAL"] = str(ISO / "gitconfig")
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
os.environ["GIT_TERMINAL_PROMPT"] = "0"

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
    ).stdout.strip()


def commit(repo, name, text):
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", f"add {name}")


def make_world(tmp):
    """NSLS (bare, seeded from `seed`) and the builder's toolkit checkout, a
    clone of it on main tracking origin/main."""
    tmp = Path(tmp)
    seed = tmp / "seed"
    seed.mkdir()
    git(seed, "init", "--quiet")
    git(seed, "checkout", "--quiet", "-b", "main")
    commit(seed, "skill.md", "v1\n")
    nsls = tmp / "nsls.git"
    git(tmp, "clone", "--quiet", "--bare", str(seed), str(nsls))
    config_dir = tmp / ".claude"
    plugin_dir = config_dir / "local-plugins" / "nsls-builder-toolkit"
    plugin_dir.parent.mkdir(parents=True)
    git(tmp, "clone", "--quiet", str(nsls), str(plugin_dir))
    hook.CONFIG_DIR = config_dir
    return seed, nsls, plugin_dir


def ship(seed, nsls, name, text, branch="main"):
    """NSLS ships a commit."""
    commit(seed, name, text)
    git(seed, "push", "--quiet", str(nsls), f"HEAD:{branch}")


def run(deadline=None):
    buf = io.StringIO()
    with redirect_stdout(buf):
        hook.git_pull(deadline=deadline)
    return buf.getvalue()


def head(repo):
    return git(repo, "rev-parse", "HEAD")


def upstream(repo):
    return git(repo, "rev-parse", "@{u}")


# ------------------------------------------------------------ the plain case
with tempfile.TemporaryDirectory() as tmp:
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    out = run()
    check("a clean checkout behind NSLS is fast-forwarded onto it",
          head(plugin_dir) == git(nsls, "rev-parse", "main"))
    check("...silently, and with a clean tree", out == "" and git(plugin_dir, "status", "--porcelain") == "")
    check("...and the next session has nothing to do or say", run() == "")

with tempfile.TemporaryDirectory() as tmp:
    # A commit of her own and a commit from NSLS: only --ff-only stands between
    # this and an unattended merge commit in her checkout.
    seed, nsls, plugin_dir = make_world(tmp)
    commit(plugin_dir, "mine.md", "her own commit\n")
    ship(seed, nsls, "skill2.md", "new\n")
    before = head(plugin_dir)
    out = run()
    check("a checkout with its own commit is NOT merged into: HEAD and tree unchanged",
          head(plugin_dir) == before and not (plugin_dir / "skill2.md").exists())
    check("...and the freeze names her commit", "FROZEN" in out and "1 local commit(s)" in out)

with tempfile.TemporaryDirectory() as tmp:
    # A fetch that fails merges nothing, as a failed pull did — even when the
    # upstream ref already holds something an earlier fetch brought in.
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    git(plugin_dir, "fetch", "--quiet")
    git(plugin_dir, "remote", "set-url", "origin", str(Path(tmp) / "gone.git"))
    before = head(plugin_dir)
    out = run()
    check("with the fetch failing, an older fetched upstream is NOT merged",
          head(plugin_dir) == before and upstream(plugin_dir) != before and out == "")

# ------------------------------------- 1. an ignored file the update would replace
with tempfile.TemporaryDirectory() as tmp:
    # The personal toolkit ignores .env (API keys) and harvest-exclude.txt (a
    # private denylist). Plain git replaces such a file without a word the day
    # NSLS starts tracking that path.
    seed, nsls, plugin_dir = make_world(tmp)
    (plugin_dir / ".git" / "info").mkdir(exist_ok=True)
    (plugin_dir / ".git" / "info" / "exclude").write_text("harvest-exclude.txt\n")
    (plugin_dir / "harvest-exclude.txt").write_text("HER PRIVATE DENYLIST\n")
    ship(seed, nsls, "harvest-exclude.txt", "nsls's template\n")
    before = head(plugin_dir)
    out = run()
    check("an ignored file the update starts tracking is NOT overwritten",
          (plugin_dir / "harvest-exclude.txt").read_text() == "HER PRIVATE DENYLIST\n")
    check("...the checkout is left where it was", head(plugin_dir) == before)
    check("...and the refusal is announced, not a silent freeze",
          "FROZEN" in out and f"1 {hook.IGNORED_BLOCKER}" in out)
    check("...with the repair for ignored files, not a backup branch that cannot hold them",
          "copy them somewhere safe" in out and "backup branch" not in out)
    check("...and without echoing a path NSLS's update chose", "harvest-exclude" not in out)

with tempfile.TemporaryDirectory() as tmp:
    # A name git would quote ("caf\303\251.env") is still found on disk: the
    # paths are read NUL-separated, never quoted.
    seed, nsls, plugin_dir = make_world(tmp)
    (plugin_dir / ".git" / "info").mkdir(exist_ok=True)
    (plugin_dir / ".git" / "info" / "exclude").write_text("*.env\n")
    (plugin_dir / "café.env").write_text("HER KEYS\n")
    ship(seed, nsls, "café.env", "nsls's template\n")
    out = run()
    check("an ignored file with a non-ASCII name is kept, and still counted in the warning",
          (plugin_dir / "café.env").read_text() == "HER KEYS\n" and f"1 {hook.IGNORED_BLOCKER}" in out)

# --------------------------------------------- 2. merge settings are neutralised
with tempfile.TemporaryDirectory() as tmp:
    # "-s ours" in mergeOptions makes even `merge --ff-only` exit 0 with a merge
    # commit that keeps the old tree: the toolkit reports updated and every
    # change NSLS shipped is discarded. --ff-only on the command line does not
    # stop it; only blanking the setting does.
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "config", "branch.main.mergeOptions", "-s ours")
    ship(seed, nsls, "skill.md", "v2 from NSLS\n")
    out = run()
    check("with mergeOptions='-s ours', the update is a true fast-forward",
          head(plugin_dir) == upstream(plugin_dir)
          and len(git(plugin_dir, "rev-list", "--parents", "-n1", "HEAD").split()) == 2)
    check("...and NSLS's change actually arrives",
          (plugin_dir / "skill.md").read_text() == "v2 from NSLS\n")

with tempfile.TemporaryDirectory() as tmp:
    # The setting is blanked for the branch the checkout is ON, not just main: a
    # checkout on its own tracking branch gets the same update and the same guard.
    seed, nsls, plugin_dir = make_world(tmp)
    git(seed, "push", "--quiet", str(nsls), "HEAD:feat/pinned")
    git(plugin_dir, "fetch", "--quiet")
    git(plugin_dir, "checkout", "--quiet", "-b", "feat/pinned", "--track", "origin/feat/pinned")
    git(plugin_dir, "config", "branch.feat/pinned.mergeOptions", "-s ours")
    ship(seed, nsls, "skill.md", "v2 from NSLS\n", branch="feat/pinned")
    run()
    check("on a branch other than main, its own mergeOptions are blanked too",
          head(plugin_dir) == upstream(plugin_dir)
          and (plugin_dir / "skill.md").read_text() == "v2 from NSLS\n")

for name, blankable in (("we@ird;x", True), ("a=b", False), ("café", False)):
    # Any printable-ASCII name without "=" is blanked through `-c`; git splits
    # `-c` at the first "=", and a non-ASCII name may not survive a Windows code
    # page, so those are not merged at all rather than merged unguarded.
    with tempfile.TemporaryDirectory() as tmp:
        seed, nsls, plugin_dir = make_world(tmp)
        git(seed, "push", "--quiet", str(nsls), f"HEAD:{name}")
        git(plugin_dir, "fetch", "--quiet")
        git(plugin_dir, "checkout", "--quiet", "-b", name, "--track", f"origin/{name}")
        git(plugin_dir, "config", f"branch.{name}.mergeOptions", "-s ours")
        ship(seed, nsls, "skill.md", "v2 from NSLS\n", branch=name)
        before = head(plugin_dir)
        out = run()
        if blankable:
            check(f"on branch {name!r}, mergeOptions are blanked and it is a true fast-forward",
                  head(plugin_dir) == upstream(plugin_dir)
                  and (plugin_dir / "skill.md").read_text() == "v2 from NSLS\n")
        else:
            check(f"on branch {name!r}, which cannot be blanked, nothing is merged at all",
                  head(plugin_dir) == before and (plugin_dir / "skill.md").read_text() == "v1\n")
            check("...and, being behind, it says so instead of going stale in silence",
                  "cannot protect" in out and "FROZEN" in out and name not in out)

with tempfile.TemporaryDirectory() as tmp:
    # The same branch with nothing new upstream: nothing to say.
    seed, nsls, plugin_dir = make_world(tmp)
    git(seed, "push", "--quiet", str(nsls), "HEAD:a=b")
    git(plugin_dir, "fetch", "--quiet")
    git(plugin_dir, "checkout", "--quiet", "-b", "a=b", "--track", "origin/a=b")
    check("a branch that cannot be blanked but is level stays quiet", run() == "")

with tempfile.TemporaryDirectory() as tmp:
    # --squash stages the new tree and leaves the branch where it is; the next
    # session would then call NSLS's staged tree "uncommitted local edits".
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "config", "branch.main.mergeOptions", "--squash")
    ship(seed, nsls, "skill.md", "v2 from NSLS\n")
    out = run()
    check("with mergeOptions=--squash, the branch moves and nothing is left staged",
          head(plugin_dir) == upstream(plugin_dir) and git(plugin_dir, "status", "--porcelain") == "")

with tempfile.TemporaryDirectory() as tmp:
    # merge.autoStash would stash the builder's unsaved edit, move the branch,
    # and re-apply it on top — into a conflict here, with her edit left in a stash.
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "config", "merge.autoStash", "true")
    (plugin_dir / "skill.md").write_text("an edit she has not saved\n")
    ship(seed, nsls, "skill.md", "v2 from NSLS\n")
    before = head(plugin_dir)
    out = run()
    check("with merge.autoStash on, an unsaved edit still blocks the update: nothing moves",
          head(plugin_dir) == before)
    check("...the edit is exactly as she left it, not stashed or conflicted",
          (plugin_dir / "skill.md").read_text() == "an edit she has not saved\n"
          and git(plugin_dir, "stash", "list") == "")
    check("...and the freeze is announced", "FROZEN" in out and "uncommitted local edits" in out)

# ----------------------------------------------------- 3. no hooks, ever
with tempfile.TemporaryDirectory() as tmp:
    # Installed through the checkout's LOCAL core.hooksPath (the suite's isolated
    # global config points at an empty folder, and local beats global; only the
    # command-line override beats local). The shape a builder's own hooks
    # directory would have.
    seed, nsls, plugin_dir = make_world(tmp)
    hooks_dir = Path(tmp) / "builder-hooks"
    hooks_dir.mkdir()
    merge_marker = Path(tmp) / "post-merge-ran"
    ref_marker = Path(tmp) / "reference-transaction-ran"
    for name, body in (("post-merge", f"touch '{merge_marker}'\nsleep 30\n"),
                       ("reference-transaction", f"touch '{ref_marker}'\n")):
        (hooks_dir / name).write_text(f"#!/bin/sh\n{body}")
        (hooks_dir / name).chmod(0o755)
    git(plugin_dir, "config", "core.hooksPath", str(hooks_dir))
    ship(seed, nsls, "skill2.md", "new\n")
    t0 = time.monotonic()
    out = run()
    took = time.monotonic() - t0
    check("a hanging post-merge hook is never run", not merge_marker.exists())
    check("...nor a reference-transaction hook, on the fetch or the merge", not ref_marker.exists())
    check(f"...so the update completes promptly ({took:.1f}s), fast-forwarded and silent",
          took < 10 and head(plugin_dir) == upstream(plugin_dir) and out == "")
    hooks_path = Path(hook._no_hooks(plugin_dir)[1].split("=", 1)[1])
    check("the hooks path is a file, so no hook can ever be planted under it", hooks_path.is_file())

# ------------------------------------- 4. housekeeping stays off the merge
with tempfile.TemporaryDirectory() as tmp:
    # Auto-gc after the merge would hold the never-stopped write open past its
    # wait. Set up so auto-gc WOULD run in the foreground the moment anything
    # asks: two packs against a limit of one, and no detaching.
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    git(plugin_dir, "-c", "maintenance.auto=false", "repack", "-q")
    git(plugin_dir, "-c", "maintenance.auto=false", "fetch", "--quiet")
    git(plugin_dir, "-c", "maintenance.auto=false", "repack", "-q")
    packs = lambda: len(list((plugin_dir / ".git" / "objects" / "pack").glob("*.pack")))
    for k, v in (("gc.autoPackLimit", "1"), ("gc.autoDetach", "false"),
                 ("maintenance.autoDetach", "false")):
        git(plugin_dir, "config", k, v)
    before_packs = packs()
    code = hook._guarded_ff_merge(plugin_dir, "@{u}", "main", 20)
    check("the fixture is real: two packs, so auto-gc would consolidate them", before_packs == 2)
    check("the guarded merge fast-forwards without running auto-gc or maintenance",
          code == 0 and head(plugin_dir) == upstream(plugin_dir) and packs() == before_packs)

# -------------------------------------- 5. an operation in progress is left alone
with tempfile.TemporaryDirectory() as tmp:
    # `git bisect start` with nothing marked yet leaves the checkout clean and on
    # main. Moving main under it changes the bisect.
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "bisect", "start")
    ship(seed, nsls, "skill2.md", "new\n")
    before = head(plugin_dir)
    out = run()
    check("a checkout mid-bisect is NOT moved", head(plugin_dir) == before)
    check("...and it is said out loud, so an abandoned bisect cannot freeze it silently",
          "unfinished git operation" in out and "FROZEN" in out)
    check("...while the fetch still ran, so the stale-branch check sees today's main",
          git(plugin_dir, "rev-parse", "origin/main") == git(nsls, "rev-parse", "main"))

with tempfile.TemporaryDirectory() as tmp:
    # An operation started WHILE the fetch runs (it can take seconds) is still
    # seen: the check sits after the fetch, immediately before the merge.
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    real_rc = hook._git_rc
    def fetch_then_bisect(d, *args, **k):
        r = real_rc(d, *args, **k)
        if "fetch" in args:
            git(plugin_dir, "bisect", "start")
        return r
    before = head(plugin_dir)
    hook._git_rc = fetch_then_bisect
    try:
        out = run()
    finally:
        hook._git_rc = real_rc
    check("a bisect started during the fetch is seen: the checkout is NOT moved",
          head(plugin_dir) == before and "unfinished git operation" in out)

with tempfile.TemporaryDirectory() as tmp:
    # A detached checkout is a deliberate pin: still not moved, still quiet.
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "checkout", "--quiet", "--detach")
    ship(seed, nsls, "skill2.md", "new\n")
    before = head(plugin_dir)
    out = run()
    check("a detached (pinned) checkout is not moved, and nothing is said", head(plugin_dir) == before and out == "")

# ---------------------------------------------- 6. the 15s envelope holds
with tempfile.TemporaryDirectory() as tmp:
    # The merge's wait never runs past the caller's deadline.
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    real, waits = hook._guarded_ff_merge, []
    hook._guarded_ff_merge = lambda d, t, b, wait, **k: waits.append(wait) or real(d, t, b, wait, **k)
    out = run(deadline=time.monotonic() + 6)
    hook._guarded_ff_merge = real
    check("the merge's wait ends by the caller's deadline",
          len(waits) == 1 and 0 < waits[0] <= 6)
    check("...and a quick merge inside it lands", head(plugin_dir) == upstream(plugin_dir))

with tempfile.TemporaryDirectory() as tmp:
    # A write we might have to abandon is never begun.
    seed, nsls, plugin_dir = make_world(tmp)
    ship(seed, nsls, "skill2.md", "new\n")
    real, calls = hook._guarded_ff_merge, []
    hook._guarded_ff_merge = lambda *a, **k: calls.append(a) or real(*a, **k)
    before = head(plugin_dir)
    out = run(deadline=time.monotonic() + hook.PULL_MERGE_MIN_LEFT_S - 0.5)
    hook._guarded_ff_merge = real
    check("with too little of the envelope left, the merge is never started",
          calls == [] and head(plugin_dir) == before and out == "")

with tempfile.TemporaryDirectory() as tmp:
    # A remote that never answers is cut off at the deadline, not after a minute.
    seed, nsls, plugin_dir = make_world(tmp)
    git(plugin_dir, "config", "protocol.ext.allow", "always")
    # A duration unique to this run, so a helper left by some other run is never mistaken for ours.
    nap = f"{30 + os.getpid() % 1000}.{time.time_ns() % 997}"
    git(plugin_dir, "remote", "set-url", "origin", f"ext::sh -c sleep% {nap}")
    t0 = time.monotonic()
    out = run(deadline=time.monotonic() + 3)
    took = time.monotonic() - t0
    check(f"a wedged fetch is stopped inside the envelope ({took:.1f}s of 3s)", took < 4 and out == "")
    time.sleep(0.3)
    left_behind = subprocess.run(["pgrep", "-f", f"sleep {nap}"], capture_output=True).returncode == 0
    check("...together with its remote helper: nothing it started is left running", not left_behind)

with tempfile.TemporaryDirectory() as tmp:
    # The freeze diagnosis runs inside the envelope too: no time, no git, no guess.
    seed, nsls, plugin_dir = make_world(tmp)
    commit(plugin_dir, "mine.md", "her own commit\n")
    check("the freeze diagnosis spends nothing once the deadline has passed",
          hook._checkout_blocks_update(plugin_dir, deadline=time.monotonic() - 1) is None)
    check("...and still diagnoses with time left",
          hook._checkout_blocks_update(plugin_dir, deadline=time.monotonic() + 5)
          == "1 local commit(s) not in its upstream")

print()
if failures:
    print(f"{len(failures)} FAILED:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print(f"all {checks_run} checks passed")
