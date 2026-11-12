#!/usr/bin/env python3
# windows-ci: python | A copy delivered by NSLS's Claude organization counts as installed, so self-install, the update check and pointers stand down
"""The copy NSLS's Claude organization delivers counts as an installed plugin.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_synced_copy.py`.

Organization sync puts the toolkit on a machine with no record in
installed_plugins.json, under plugins/synced/<org>_<account>/. Every part of
the toolkit that asked "is the plugin installed?" by reading that registry got
"no" and acted on it. What this pins:

1. hooks/synced_copy.py recognises a synced copy: only a whole one, only the
   signed-in account's, and not one the builder switched off.
2. With one present, session start does not install the marketplace plugin
   beside it (stage A), does not ask GitHub about updates, does not pull the
   old checkout, and stops writing a pointer file per toolkit skill.
3. "Update my NSLS toolkit" says the truth instead of "not installed".
4. With NO synced copy, every answer is what it was before: nothing here may
   change today's install and update path.

No network, no real install: a throwaway config dir and a fake `claude`.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
REPO = HOOKS.parent
PLUGIN = "nsls-builder-toolkit"
ORG = "11111111-2222-3333-4444-555555555555"
ACCT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FOLDER = f"{ORG}_{ACCT}"
OTHER = f"{ORG}_99999999-0000-0000-0000-000000000000"
WINDOWS = os.name == "nt"

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def new_cfg(tmp, account=True):
    """A throwaway config dir, signed in to one account unless told otherwise."""
    cfg = Path(tmp) / "claude"
    cfg.mkdir(parents=True)
    if account:
        (cfg / ".claude.json").write_text(json.dumps(
            {"oauthAccount": {"organizationUuid": ORG, "accountUuid": ACCT},
             "projects": {"/a": {}}}), encoding="utf-8")
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    return cfg


def add_copy(cfg, folder=FOLDER, version="3.50.0", name=PLUGIN, hooks_json=True, real=False):
    """Put a synced copy on disk. real=True copies this repo's hooks into it,
    so its session-start.py can be run from the synced path."""
    root = cfg / "plugins" / "synced" / folder / PLUGIN
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": name, "version": version}), encoding="utf-8")
    if real:
        shutil.copytree(HOOKS, root / "hooks", ignore=shutil.ignore_patterns("tests", "__pycache__"))
    else:
        (root / "hooks").mkdir()
        if hooks_json:
            (root / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
    return root


def settings(cfg, **keys):
    (cfg / "settings.json").write_text(json.dumps(keys), encoding="utf-8")


def registry(cfg, key=f"{PLUGIN}@nsls-toolkit"):
    (cfg / "plugins").mkdir(parents=True, exist_ok=True)
    (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
        {"version": 2, "plugins": {key: [{"scope": "user", "version": "3.6.0",
                                          "installPath": str(cfg / "nowhere")}]}}), encoding="utf-8")


def load(path, cfg):
    """Import a hook module against a throwaway config dir."""
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    sys.modules.pop("synced_copy", None)  # each machine gets its own
    spec = importlib.util.spec_from_file_location(f"m_{Path(path).stem.replace('-', '_')}_{time.time_ns()}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import os, sys
    open(os.environ["FAKE_LOG"], "a").write(" ".join(sys.argv[1:]) + "\\n")
    sys.exit(0)
''')


def fake_cli(tmp):
    """A `claude` on PATH that records every call and succeeds."""
    bindir = Path(tmp) / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(FAKE_CLAUDE, encoding="utf-8")
    exe.chmod(0o755)
    log = Path(tmp) / "claude.log"
    log.write_text("", encoding="utf-8")
    os.environ["FAKE_LOG"] = str(log)
    os.environ["PATH"] = str(bindir) + os.pathsep + os.environ["PATH"]
    return log


def calls(log):
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line]


def git(cwd, *args):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.test",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.test"}
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, env=env,
                          capture_output=True, text=True).stdout.strip()


def behind_checkout(tmp, dest):
    """A checkout at `dest` one commit behind its remote. Returns the remote head."""
    remote = Path(tmp) / (dest.name + "-remote.git")
    seed = Path(tmp) / (dest.name + "-seed")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(seed)], check=True, capture_output=True)
    (seed / "f").write_text("1\n")
    git(seed, "add", "f"); git(seed, "commit", "-q", "-m", "one"); git(seed, "push", "-q", "origin", "HEAD:main")
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(dest)], check=True, capture_output=True)
    (seed / "f").write_text("2\n")
    git(seed, "commit", "-q", "-am", "two"); git(seed, "push", "-q", "origin", "HEAD:main")
    return git(seed, "rev-parse", "HEAD")


SAVED_ENV = dict(os.environ)


def reset_env():
    os.environ.clear()
    os.environ.update(SAVED_ENV)


# ---------------------------------------------------------------------------
print("synced_copy: what counts as the organization's copy")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    sc = load(HOOKS / "synced_copy.py", cfg)
    check("no synced folder at all: nothing is present or active",
          sc.live_root(cfg) is None and not sc.present(cfg) and not sc.active(cfg))

    root = add_copy(cfg)
    check("a whole copy in the signed-in account's folder is the live one", sc.live_root(cfg) == root)
    check("and it is present and active", sc.present(cfg) and sc.active(cfg))
    check("its version is read from its own plugin.json", sc.version(root) == "3.50.0")
    check("a file inside it is running from it",
          sc.running_root(root / "hooks" / "session-start.py", cfg) == str(root.resolve()))
    check("a file in a marketplace cache is not",
          sc.running_root(cfg / "plugins" / "cache" / "nsls-toolkit" / PLUGIN / "3.6.0" / "hooks" / "x.py", cfg) == "")
    check("nor is a file in the old checkout",
          sc.running_root(cfg / "local-plugins" / PLUGIN / "hooks" / "session-start.py", cfg) == "")
    check("nor is this test's own copy of the hooks", sc.running_root(HOOKS / "session-start.py", cfg) == "")

    settings(cfg, syncClaudeAiPlugins=False)
    check("syncClaudeAiPlugins off: on disk, but not active", sc.present(cfg) and not sc.active(cfg))
    settings(cfg, enabledPlugins={f"{PLUGIN}@synced": False})
    check("the plugin's own switch off: not active", sc.present(cfg) and not sc.active(cfg))
    check("but code running from it is active whatever the settings say",
          sc.active(cfg, root / "hooks" / "session-start.py"))
    (root.parent / f"{PLUGIN}.meta.json").write_text(
        json.dumps({"installation_preference": "required"}), encoding="utf-8")
    check("required by NSLS: the builder's switch does not stop it", sc.active(cfg))
    settings(cfg, enabledPlugins={f"{PLUGIN}@nsls-toolkit": False})
    check("a marketplace install's switch is not the synced copy's", sc.active(cfg))
    (cfg / "settings.json").write_text("{not json", encoding="utf-8")
    check("settings that cannot be read are not a switch", sc.active(cfg))

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    sc = load(HOOKS / "synced_copy.py", cfg)
    add_copy(cfg, folder=OTHER)
    check("a copy another account left behind does not count", sc.live_root(cfg) is None and not sc.present(cfg))
    add_copy(cfg, folder=FOLDER.upper())
    check("the account folder matches whatever its letter case", sc.live_root(cfg) is not None)

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp, account=False)
    sc = load(HOOKS / "synced_copy.py", cfg)
    only = add_copy(cfg, folder=OTHER)
    check("account unreadable, one copy on disk: it counts", sc.live_root(cfg) == only)
    add_copy(cfg, folder=FOLDER)
    check("account unreadable, two copies: neither is assumed", sc.live_root(cfg) is None)

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    sc = load(HOOKS / "synced_copy.py", cfg)
    add_copy(cfg, hooks_json=False)
    check("a copy with no hooks.json is not whole, so it does not count", sc.live_root(cfg) is None)

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    sc = load(HOOKS / "synced_copy.py", cfg)
    add_copy(cfg, name="some-other-plugin")
    check("a folder holding a different plugin does not count", sc.live_root(cfg) is None)
    (cfg / "plugins" / "synced" / f".bucket-{FOLDER}").write_text("", encoding="utf-8")
    (cfg / "plugins" / "synced" / ".hidden").mkdir()
    check("marker files and dot folders are ignored", sc.copies(cfg) == {})

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp, account=False)
    (cfg / ".claude.json").write_text(json.dumps(
        {"oauthAccount": {"organizationUuid": "../../etc", "accountUuid": ACCT}}), encoding="utf-8")
    sc = load(HOOKS / "synced_copy.py", cfg)
    only = add_copy(cfg)
    check("an account id that is not an id is never built into a path", sc._account_folder(cfg) is None)
    check("and the lone copy still counts", sc.live_root(cfg) == only)

# ---------------------------------------------------------------------------
print("session-start.py: installed and active")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    ss = load(HOOKS / "session-start.py", cfg)
    check("no registry, no synced copy: not installed (as before)",
          not ss.org_plugin_installed() and not ss.org_plugin_active())
    registry(cfg)
    check("a marketplace install: installed and active (as before)",
          ss.org_plugin_installed() and ss.org_plugin_active())
    settings(cfg, enabledPlugins={f"{PLUGIN}@nsls-toolkit": False})
    check("switched off by the builder: installed, not active (as before)",
          ss.org_plugin_installed() and not ss.org_plugin_active())

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    ss = load(HOOKS / "session-start.py", cfg)
    add_copy(cfg)
    check("the organization's copy alone: installed and active",
          ss.org_plugin_installed() and ss.org_plugin_active())
    check("without a marketplace install", not ss.marketplace_plugin_installed())
    check("this test's copy of the hook is not running from it", ss.org_copy_root() == "")
    settings(cfg, enabledPlugins={f"{PLUGIN}@synced": False})
    check("the organization's copy switched off: installed, not active",
          ss.org_plugin_installed() and not ss.org_plugin_active())
    registry(cfg)
    check("its switch does not disable a marketplace install beside it",
          ss.marketplace_plugin_active() and ss.org_plugin_active())

# ---------------------------------------------------------------------------
print("session-start.py: pointers")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    ss = load(HOOKS / "session-start.py", cfg)
    skill = cfg / "local-plugins" / PLUGIN / "skills" / "slack"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: slack\ndescription: the slack skill\n---\nbody\n", encoding="utf-8")
    ss.sync_pointers()
    check("no plugin: the old checkout's skills get pointer files (as before)",
          (cfg / "skills" / "slack" / "SKILL.md").is_file())
    shutil.rmtree(cfg / "skills" / "slack")
    add_copy(cfg)
    ss.sync_pointers()
    check("the organization's copy delivers the skills: no pointer file is written",
          not (cfg / "skills" / "slack").exists())

# ---------------------------------------------------------------------------
print("migrate_to_plugin.py: installed, and never stage A")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    os.environ["NSLS_NO_PLUGIN_MIGRATION"] = "1"  # importing it must not migrate
    mig = load(HOOKS / "migrate_to_plugin.py", cfg)
    check("no registry, no synced copy: not installed (as before)", not mig._plugin_installed())
    add_copy(cfg)
    check("the organization's copy counts as installed", mig._plugin_installed())
    settings(cfg, enabledPlugins={f"{PLUGIN}@nsls-toolkit": False})
    check("and it is not 'disabled by the user' while it delivers the toolkit",
          not mig._plugin_disabled_by_user())
    settings(cfg, enabledPlugins={f"{PLUGIN}@synced": False})
    check("switched off by the builder: respected", mig._plugin_disabled_by_user())
reset_env()

if not WINDOWS:
    for label, synced in (("no synced copy: stage A installs the plugin (as before)", False),
                          ("the organization's copy is here: stage A never runs", True)):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = new_cfg(tmp)
            log = fake_cli(tmp)
            clone = cfg / "local-plugins" / PLUGIN
            shutil.copytree(HOOKS, clone / "hooks", ignore=shutil.ignore_patterns("tests", "__pycache__"))
            if synced:
                add_copy(cfg)
            ss = load(HOOKS / "session-start.py", cfg)
            ss.PLUGIN_DIR = clone
            stage_a = ss.run_plugin_migration()
            seen = calls(log)
            installs = [c for c in seen if c.startswith("plugin install") or c.startswith("plugin marketplace add")]
            if synced:
                check(label, not stage_a and not installs, f"stage_a={stage_a} calls={seen}")
            else:
                check(label, stage_a and any(c.startswith("plugin install") for c in seen),
                      f"stage_a={stage_a} calls={seen}")
        reset_env()

# ---------------------------------------------------------------------------
print("running FROM the organization's copy")
if not WINDOWS:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = new_cfg(tmp)
        log = fake_cli(tmp)
        root = add_copy(cfg, real=True)
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(cfg)}

        out = subprocess.run([sys.executable, str(root / "hooks" / "session-start.py"), "--update-now"],
                             capture_output=True, text=True, env=env, timeout=60).stdout
        check("'update my toolkit' says the organization keeps it up to date",
              "through NSLS's Claude organization" in out and "nothing to run" in out, out)
        check("and names the version it is on", "version 3.50.0" in out, out)
        check("and no longer says it is not installed", "not installed" not in out, out)
        check("and runs no CLI update", calls(log) == [], str(calls(log)))

        # The old checkout, one commit behind; the personal toolkit, likewise.
        org_head = behind_checkout(tmp, cfg / "local-plugins" / PLUGIN)
        personal_head = behind_checkout(tmp, cfg / "local-plugins" / "nsls-personal-toolkit")
        driver = textwrap.dedent(f'''\
            import importlib.util, json, sys, time
            spec = importlib.util.spec_from_file_location("ss", {str(root / "hooks" / "session-start.py")!r})
            ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)
            ss.report_personal_fork_drift = lambda deadline=None: None
            ss.git_pull()
            ss.ensure_plugin_fresh()
            print(json.dumps({{"root": ss.org_copy_root(), "installed": ss.org_plugin_installed(),
                               "stage_a": ss.run_plugin_migration()}}))
        ''')
        res = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, env=env, timeout=120)
        try:
            got = json.loads(res.stdout.strip().splitlines()[-1])
        except Exception:
            got = {}
        check("the hook knows it runs from the organization's copy",
              got.get("root") == str(root.resolve()), res.stdout + res.stderr)
        check("and reports the toolkit installed", got.get("installed") is True)
        check("the old builder checkout is left alone (no GitHub call for it)",
              git(cfg / "local-plugins" / PLUGIN, "rev-parse", "HEAD") != org_head)
        check("the personal toolkit is still pulled",
              git(cfg / "local-plugins" / "nsls-personal-toolkit", "rev-parse", "HEAD") == personal_head)
        check("no update check is claimed or stamped", not (cfg / ".nsls-plugin-fresh-check").exists())
        seen = calls(log)
        check("this session is not stage A", got.get("stage_a") is False)
        check("nothing installs or updates a marketplace plugin",
              not [c for c in seen if c.startswith("plugin ")], str(seen))
    reset_env()

    # The same copy with a marketplace install enabled beside it is not this
    # hook's to judge from the synced path, but the old question still works:
    # a marketplace machine with no synced copy keeps its update check.
    with tempfile.TemporaryDirectory() as tmp:
        cfg = new_cfg(tmp)
        registry(cfg)
        ss = load(HOOKS / "session-start.py", cfg)
        ss.ensure_plugin_fresh()
        check("a marketplace machine still claims its update check (as before)",
              (cfg / ".nsls-plugin-fresh-check").exists())
    reset_env()

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
