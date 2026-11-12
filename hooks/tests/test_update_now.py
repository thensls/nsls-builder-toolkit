#!/usr/bin/env python3
""""Update my NSLS toolkit": the on-request update behind the update-toolkit skill.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_update_now.py`.

The skill runs `run-hook.sh update`, which runs session-start.py with
--update-now. That is the session-start update without the session-start
limits (no 10-minute throttle, 120 seconds instead of 20), and its output is
plain sentences Claude passes on. A fake `claude` on PATH records each call and
moves the registry the way the real CLI does. No network, no real install.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
PLUGIN_KEY = "nsls-builder-toolkit@nsls-toolkit"
OLD = "58b5a0227d37a72f3baaf911226e7b318ef4c497"

failures = []


def check(label, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {label} {'' if cond else detail}")
    if not cond:
        failures.append(label)


FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    Path(os.environ["FAKE_LOG"]).open("a").write(" ".join(args) + "\\n")
    if args[:2] == ["plugin", "update"]:
        if os.environ.get("FAKE_UPDATE_FAILS"):
            sys.exit(1)
        if os.environ.get("FAKE_DROP_RECORD"):
            reg = Path(os.environ["FAKE_REGISTRY"])
            reg.write_text(json.dumps({"version": 2, "plugins": {"nsls-builder-toolkit@nsls-toolkit": []}}))
            sys.exit(0)
        new_path = os.environ.get("FAKE_NEW_PATH")
        if new_path:
            for name in os.environ["FAKE_NEW_SKILLS"].split(","):
                d = Path(new_path) / "skills" / name
                d.mkdir(parents=True, exist_ok=True)
                (d / "SKILL.md").write_text(f"---\\nname: {name}\\n---\\n")
            reg = Path(os.environ["FAKE_REGISTRY"])
            d = json.loads(reg.read_text())
            d["plugins"]["nsls-builder-toolkit@nsls-toolkit"] = [{
                "scope": "user", "version": "3.7.0", "installPath": new_path,
                "gitCommitSha": os.environ["FAKE_HEAD"]}]
            reg.write_text(json.dumps(d))
    sys.exit(0)
''')


def machine(tmp, release=None, installed=True, cli=True, update_fails=False):
    """A fake ~/.claude with 3.6.0 installed (skills alpha, beta) and a
    marketplace clone. `release`: skill names the fake update installs as 3.7.0."""
    root = Path(tmp)
    cfg = root / "cfg"
    cache = cfg / "plugins" / "cache" / "nsls-toolkit" / "nsls-builder-toolkit"
    old_path = cache / "3.6.0"
    for name in ("alpha", "beta"):
        (old_path / "skills" / name).mkdir(parents=True)
        (old_path / "skills" / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
    market = cfg / "plugins" / "marketplaces" / "nsls-toolkit"
    market.mkdir(parents=True)
    env_git = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@example.test"],
                 ["config", "user.name", "t"], ["commit", "-q", "--allow-empty", "-m", "c"]):
        subprocess.run(["git", "-C", str(market), *args], check=True, env=env_git, capture_output=True)
    head = subprocess.run(["git", "-C", str(market), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    registry = cfg / "plugins" / "installed_plugins.json"
    sha = OLD if release else head  # nothing to release: already on the clone's HEAD
    registry.write_text(json.dumps({"version": 2, "plugins": {PLUGIN_KEY: [{
        "scope": "user", "version": "3.6.0", "installPath": str(old_path),
        "gitCommitSha": sha}]}} if installed else {"version": 2, "plugins": {}}))
    (cfg / "settings.json").write_text(json.dumps({"enabledPlugins": {PLUGIN_KEY: True}}))
    bin_dir = root / "bin"
    bin_dir.mkdir()
    if cli:
        (bin_dir / "claude").write_text(FAKE_CLAUDE)
        (bin_dir / "claude").chmod(0o755)
    log = root / "calls.log"
    log.write_text("")
    env = {**os.environ,
           "CLAUDE_CONFIG_DIR": str(cfg), "HOME": str(root / "home"),
           "PATH": f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin",
           "FAKE_LOG": str(log), "FAKE_REGISTRY": str(registry), "FAKE_HEAD": head}
    if release:
        env["FAKE_NEW_PATH"] = str(cache / "3.7.0")
        env["FAKE_NEW_SKILLS"] = ",".join(release)
    if update_fails:
        env["FAKE_UPDATE_FAILS"] = "1"
    return cfg, log, env


def run(env, via_launcher=False):
    if via_launcher:
        cmd = ["bash", str(HOOKS / "run-hook.sh"), "update"]
        env = {**env, "CLAUDE_PLUGIN_ROOT": str(HOOKS.parent)}
    else:
        cmd = [sys.executable, str(HOOKS / "session-start.py"), "--update-now"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    return r.stdout


with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["alpha", "beta", "quicknote"])
    out = run(env)
    check("release: one update call, nothing else", log.read_text().split("\n")[:-1] == [f"plugin update {PLUGIN_KEY}"],
          log.read_text())
    check("release: says it updated, from and to", "Updated the NSLS toolkit from version 3.6.0 to version 3.7.0." in out, out)
    check("release: names only the new skill", "New skills: /quicknote." in out and "/alpha" not in out, out)
    check("release: says to open a new session", "open a new session" in out, out)
    check("release: the session-start check is not repeated straight away",
          (cfg / ".nsls-plugin-fresh-check").exists())

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["alpha", "beta", "quicknote"])
    out = run(env, via_launcher=True)
    check("launcher: `run-hook.sh update` reaches the same code", "Updated the NSLS toolkit" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp)
    out = run(env)
    check("up to date: says so, with the version", "already up to date (version 3.6.0)" in out, out)
    check("up to date: no reinstall", "uninstall" not in log.read_text())

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["quicknote"], update_fails=True)
    out = run(env)
    check("update fails: says it did not finish", "did not finish" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["quicknote"])
    (cfg / ".nsls-plugin-heal.lock").write_text("123")
    out = run(env)
    check("another session updating: says so, no update call", "Another Claude session" in out and log.read_text() == "", out)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["quicknote"])
    env["FAKE_DROP_RECORD"] = "1"
    out = run(env)
    check("record unreadable after the update: never 'up to date'",
          "already up to date" not in out and "could not be checked" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # A project-scope install only: the plugin is there, but no user-scope
    # record to compare against before the update.
    cfg, log, env = machine(tmp, release=["alpha", "beta", "quicknote"])
    reg = cfg / "plugins" / "installed_plugins.json"
    d = json.loads(reg.read_text())
    d["plugins"][PLUGIN_KEY][0]["scope"] = "project"
    reg.write_text(json.dumps(d))
    out = run(env)
    check("no record before the update: reports the new version, not 'up to date'",
          "now on version 3.7.0" in out and "already up to date" not in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # Nothing released, but the registry carries no commit and the clone no
    # version: "up to date" would be a guess.
    cfg, log, env = machine(tmp)
    reg = cfg / "plugins" / "installed_plugins.json"
    d = json.loads(reg.read_text())
    d["plugins"][PLUGIN_KEY][0].pop("gitCommitSha")
    reg.write_text(json.dumps(d))
    out = run(env)
    check("unverifiable commit: never 'up to date'",
          "already up to date" not in out and "could not be verified" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # Same, but the clone carries the installed version: that IS evidence.
    cfg, log, env = machine(tmp)
    reg = cfg / "plugins" / "installed_plugins.json"
    d = json.loads(reg.read_text())
    d["plugins"][PLUGIN_KEY][0].pop("gitCommitSha")
    reg.write_text(json.dumps(d))
    market = cfg / "plugins" / "marketplaces" / "nsls-toolkit"
    (market / ".claude-plugin").mkdir()
    (market / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": "3.6.0"}))
    out = run(env)
    check("no commit but the clone carries the installed version: up to date", "already up to date" in out, out)

src = (HOOKS / "session-start.py").read_text(encoding="utf-8")
import re as _re
stale = int(_re.search(r"^HEAL_LOCK_STALE_S = (\d+)", src, _re.M).group(1))
upd = int(_re.search(r"^UPDATE_NOW_TIMEOUT_S = (\d+)", src, _re.M).group(1))
check("the lock outlives the longest holder (update now + its 60s heal)", stale > upd + 60)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, installed=False)
    out = run(env)
    check("no plugin and no folder copy: says it cannot update from here, never 'up to date'",
          "not on this machine in a form this command can update" in out
          and "up to date" not in out and "newest release" not in out, out)


# --- the folder copy: a clone and no plugin ----------------------------------
#
# What install.sh leaves on a machine where it found no claude CLI. This branch
# used to print "its folder copy already updates itself at every session start"
# and run nothing. On a builder's Mac (2026-11) no session hook was registered
# either, so nothing updated the copy at all, and he was told there was nothing
# to do while 125 commits behind.

SHIM = ("python3 -c \"exec(open('{}/local-plugins/nsls-builder-toolkit/hooks/"
        "session-start.py').read())\"")


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, env=env).stdout.strip()


def folder_copy(tmp, cfg, env, behind=False, hook=None, branch=None):
    """NSLS's repo (a local bare repo) and this machine's clone of it, tracking
    main, as install.sh leaves it. `behind`: NSLS has released 3.7.0 on main
    since. `hook`: the SessionStart command in settings.json, if any. `branch`:
    the copy follows that branch of NSLS's repo instead of main. git runs with
    an isolated config so a builder's own settings cannot change the fixture."""
    root = Path(tmp)
    (root / "gitconfig").write_text(
        "[user]\n\tname = T\n\temail = t@t.test\n[commit]\n\tgpgsign = false\n"
        "[init]\n\tdefaultBranch = main\n[protocol \"file\"]\n\tallow = always\n")
    env.update(GIT_CONFIG_GLOBAL=str(root / "gitconfig"), GIT_CONFIG_NOSYSTEM="1")
    seed, nsls = root / "seed", root / "nsls.git"

    def release(version):
        (seed / ".claude-plugin").mkdir(exist_ok=True)
        (seed / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": version}))
        git(seed, "add", ".", env=env)
        git(seed, "commit", "--quiet", "-m", f"release {version}", env=env)

    seed.mkdir()
    git(seed, "init", "--quiet", env=env)
    git(seed, "checkout", "--quiet", "-b", "main", env=env)
    release("3.6.0")
    git(root, "clone", "--quiet", "--bare", str(seed), str(nsls), env=env)
    copy = cfg / "local-plugins" / "nsls-builder-toolkit"
    copy.parent.mkdir(parents=True)
    if branch:
        git(seed, "push", "--quiet", str(nsls), f"main:{branch}", env=env)
    git(root, "clone", "--quiet", str(nsls), str(copy), env=env)
    if branch:
        git(copy, "checkout", "--quiet", "-b", branch, "--track", f"origin/{branch}", env=env)
    if behind:
        release("3.7.0")
        git(seed, "push", "--quiet", str(nsls), "main", env=env)
    settings = {}
    if hook:
        settings["hooks"] = {"SessionStart": [{"matcher": "startup", "hooks": [
            {"type": "command", "command": hook}]}]}
    (cfg / "settings.json").write_text(json.dumps(settings))
    return copy, git(nsls, "rev-parse", "main", env=env)


with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True, hook=SHIM.format(cfg))
    out = run(env)
    check("folder copy, behind: it is updated now, not described",
          git(copy, "rev-parse", "HEAD", env=env) == released, out)
    check("folder copy, behind: says so, with the version",
          "Updated this machine's copy of the NSLS toolkit to the newest release (version 3.7.0)." in out, out)
    check("folder copy, behind: says to open a new session", "open a new session" in out, out)
    check("folder copy with its session hook: says it updates itself",
          "updates itself each time a Claude Code session starts" in out
          and "nothing on this machine updates it" not in out, out)
    check("folder copy: the plugin CLI is never called", log.read_text() == "", log.read_text())
    check("the old sentence is gone", "already updates itself at every session start" not in out, out)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, hook=SHIM.format(cfg))
    out = run(env)
    check("folder copy, level: says it is already on the newest release",
          "already on the newest release (version 3.6.0)" in out and "open a new session" not in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # The builder's Mac: a clone, no plugin, and no session hook in settings.
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True)
    out = run(env)
    check("no session hook: the copy is still updated now",
          git(copy, "rev-parse", "HEAD", env=env) == released, out)
    check("no session hook: says nothing updates it automatically",
          "nothing on this machine updates it automatically" in out
          and "updates itself each time" not in out, out)
    check("no session hook: gives the repair, from the copy already here",
          f'bash "{copy / "install.sh"}"' in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # A PC's hook is session-start.ps1, written with backslashes.
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(
        tmp, cfg, env,
        hook='powershell -NoProfile -ExecutionPolicy Bypass -File '
             '"C:\\Users\\b\\.claude\\local-plugins\\nsls-builder-toolkit\\hooks\\session-start.ps1"')
    out = run(env)
    check("a PC's session hook counts as registered", "updates itself each time" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # Somebody else's SessionStart hook is not ours.
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, hook="python3 /opt/other/hooks/session-start.py")
    out = run(env)
    check("another tool's session hook does not count",
          "nothing on this machine updates it automatically" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # NSLS cannot be reached: nothing is claimed.
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True, hook=SHIM.format(cfg))
    git(copy, "remote", "set-url", "origin", str(Path(tmp) / "gone.git"), env=env)
    out = run(env)
    check("unreachable: says it could not be updated, never 'newest release'",
          "could not be updated just now" in out and "newest release" not in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # The builder committed to the copy and NSLS moved on: a fast-forward is
    # refused. That is the checkout's doing, never "no internet".
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True, hook=SHIM.format(cfg))
    (copy / "mine.md").write_text("mine\n")
    git(copy, "add", ".", env=env)
    git(copy, "commit", "--quiet", "-m", "mine", env=env)
    out = run(env)
    check("refused by the checkout: says so, and does not blame the internet",
          "its own checkout refused the update" in out and "no internet" not in out
          and "newest release" not in out, out)
    check("refused by the checkout: the builder's commit is still there",
          git(copy, "log", "-1", "--format=%s", env=env) == "mine")

with tempfile.TemporaryDirectory() as tmp:
    # The copy follows a branch of its own. Its pull succeeds and changes
    # nothing while main moves on: level with its branch is not "the newest
    # release" (Macroscope on PR #333).
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True, hook=SHIM.format(cfg), branch="feat/x")
    out = run(env)
    check("on another branch: never called the newest release",
          "is level with the branch it follows" in out
          and "not necessarily the newest release" in out
          and "the newest release (" not in out and "on the newest release" not in out, out)
    check("on another branch: the behind-main note a session start gives is kept",
          "NOTE - nsls-builder-toolkit is 1 commit(s) behind main" in out, out)
    check("on another branch: the copy is left on its branch",
          git(copy, "rev-parse", "--abbrev-ref", "HEAD", env=env) == "feat/x"
          and git(copy, "rev-parse", "HEAD", env=env) != released)

with tempfile.TemporaryDirectory() as tmp:
    # Pinned to a commit on purpose: it is not moved, and not blamed on the network.
    cfg, log, env = machine(tmp, installed=False)
    copy, released = folder_copy(tmp, cfg, env, behind=True, hook=SHIM.format(cfg))
    pinned = git(copy, "rev-parse", "HEAD", env=env)
    git(copy, "checkout", "--quiet", "--detach", env=env)
    out = run(env)
    check("pinned: says so, and claims neither an update nor a network problem",
          "pinned to one fixed commit" in out and "no internet" not in out
          and "newest release" not in out, out)
    check("pinned: the commit is not moved", git(copy, "rev-parse", "HEAD", env=env) == pinned)

skill = (HOOKS.parent / "skills" / "update-toolkit" / "SKILL.md").read_text(encoding="utf-8")
no_updater = skill[skill.index("**Nothing on this machine updates it automatically:**"):]
check("the skill never tells Claude the update worked because the repair was offered",
      "does not mean the update worked" in no_updater and "was updated just now" not in skill, no_updater)
check("the skill has an answer for a copy that refused, is pinned, or is on another branch",
      "**Refused by the copy itself, pinned, or on another branch:**" in skill)

with tempfile.TemporaryDirectory() as tmp:
    cfg, log, env = machine(tmp, release=["quicknote"], cli=False)
    out = run(env)
    check("no CLI: says it could not update", "claude command was not found" in out, out)

with tempfile.TemporaryDirectory() as tmp:
    # Without the flag the file is still the session-start hook, not the updater.
    cfg, log, env = machine(tmp)
    env["NSLS_TRACKER_URL"] = "http://127.0.0.1:9"
    env["NSLS_COLLECTOR_OPTOUT"] = "1"
    r = subprocess.run([sys.executable, str(HOOKS / "session-start.py")], capture_output=True, text=True,
                       env=env, timeout=120)
    check("no flag: the hook does not run the on-request updater", "already up to date" not in r.stdout)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all passed")
