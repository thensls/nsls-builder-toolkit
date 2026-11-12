#!/usr/bin/env python3
"""The organization's copy takes over from a marketplace install, safely.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_org_copy_handover.py`.

Claude Code loads one plugin per name, and a marketplace install outranks the
copy NSLS's Claude organization delivers. A machine with both keeps running the
marketplace one, which can no longer update once the repository is private and
the machine has no GitHub sign-in. hand_over_to_org_copy() is the switch.

The danger is a machine left with NO toolkit: the marketplace install retired
and the organization's copy not loading. Once that happens no hook runs, so
nothing can repair it. Every check here is about that:

1. Step 1 switches the marketplace install OFF (never uninstalls it), and only
   when Claude Code itself lists the organization's copy as enabled.
2. If Claude Code does not then show the organization's copy as the one it will
   load, the marketplace install is switched straight back on.
3. Nothing happens when any precondition is missing: no synced copy, another
   account's copy, a copy that is switched off, older, or too old to know it is
   one; a session that cannot load synced plugins; the opt-out.
4. Step 2 uninstalls only an install THIS hook switched off, and only when
   running from the organization's copy.
5. A machine with no synced copy makes no CLI call at all: today's path.

A fake `claude` keeps the plugin state in a JSON file and answers
`plugin list --json`, `disable`, `enable`, `uninstall` and `marketplace remove`
the way the real CLI does. No network, no real install.
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
PLUGIN = "nsls-builder-toolkit"
KEY = f"{PLUGIN}@nsls-toolkit"
SYNCED = f"{PLUGIN}@synced"
ORG = "11111111-2222-3333-4444-555555555555"
ACCT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FOLDER = f"{ORG}_{ACCT}"
WINDOWS = os.name == "nt"

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


# The fake CLI. State lives beside the real files the hook reads, so the hook
# and the "CLI" always agree: settings.json's enabledPlugins and the registry.
FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
    args = sys.argv[1:]
    with open(os.environ["FAKE_LOG"], "a") as fh:
        fh.write(" ".join(args) + "\\n")
    behave = os.environ.get("FAKE_BEHAVE", "")
    settings_path = cfg / "settings.json"
    registry_path = cfg / "plugins" / "installed_plugins.json"
    def load(p, default):
        try:
            return json.loads(p.read_text())
        except Exception:
            return default
    settings = load(settings_path, {})
    registry = load(registry_path, {"plugins": {}})
    enabled = settings.setdefault("enabledPlugins", {})
    key, synced = "nsls-builder-toolkit@nsls-toolkit", "nsls-builder-toolkit@synced"
    if args[:3] == ["plugin", "list", "--json"]:
        out = []
        market_on = key in registry["plugins"] and enabled.get(key) is not False
        if key in registry["plugins"]:
            out.append({"id": key, "scope": "user", "enabled": enabled.get(key) is not False,
                        "installPath": registry["plugins"][key][0]["installPath"]})
        root = os.environ.get("FAKE_SYNCED_ROOT", "")
        if root and Path(root).is_dir() and behave != "not-listed":
            shadowed = market_on or behave == "never-loads"
            out.append({"id": synced, "scope": "synced",
                        "enabled": behave != "listed-disabled" and enabled.get(synced) is not False,
                        "installPath": "" if shadowed else root})
        print(json.dumps(out))
        sys.exit(0)
    if args[:2] == ["plugin", "disable"] and args[2:] == [key]:
        if behave == "disable-fails":
            sys.exit(1)
        enabled[key] = False
    elif args[:2] == ["plugin", "enable"] and args[2:] == [key]:
        enabled[key] = True
    elif args[:2] == ["plugin", "uninstall"] and args[2:] == [key]:
        if behave == "uninstall-fails":
            sys.exit(1)
        registry["plugins"].pop(key, None)
        enabled.pop(key, None)
        registry_path.write_text(json.dumps(registry))
    elif args[:3] == ["plugin", "marketplace", "remove"]:
        pass
    else:
        sys.exit(2)
    settings_path.write_text(json.dumps(settings))
    sys.exit(0)
''')

SAVED_ENV = dict(os.environ)


def machine(tmp, synced="3.50.0", installed="3.49.0", folder=FOLDER, aware=True, real=False,
            settings=None, behave=""):
    """A throwaway config dir with a marketplace install and (optionally) the
    organization's copy. real=True copies this repo's hooks into the synced
    copy so session-start.py can be run FROM it."""
    os.environ.clear()
    os.environ.update(SAVED_ENV)
    for name in ("ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK",
                 "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
                 "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "NSLS_NO_PLUGIN_MIGRATION",
                 "NSLS_HOOK_STARTED_AT"):
        os.environ.pop(name, None)
    cfg = Path(tmp) / "claude"
    cfg.mkdir(parents=True)
    (cfg / ".claude.json").write_text(json.dumps(
        {"oauthAccount": {"organizationUuid": ORG, "accountUuid": ACCT}}), encoding="utf-8")
    cache = cfg / "plugins" / "cache" / "nsls-toolkit" / PLUGIN / (installed or "0")
    if installed:
        (cache / "hooks").mkdir(parents=True)
        (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {KEY: [{
            "scope": "user", "version": installed, "installPath": str(cache),
            "gitCommitSha": "58b5a0227d37a72f3baaf911226e7b318ef4c497"}]}}), encoding="utf-8")
    else:
        (cfg / "plugins").mkdir(parents=True)
    (cfg / "settings.json").write_text(
        json.dumps(settings if settings is not None else {"enabledPlugins": {KEY: True}}), encoding="utf-8")
    root = None
    if synced:
        root = cfg / "plugins" / "synced" / folder / PLUGIN
        (root / ".claude-plugin").mkdir(parents=True)
        (root / ".claude-plugin" / "plugin.json").write_text(
            json.dumps({"name": PLUGIN, "version": synced}), encoding="utf-8")
        if real:
            shutil.copytree(HOOKS, root / "hooks", ignore=shutil.ignore_patterns("tests", "__pycache__"))
        else:
            (root / "hooks").mkdir()
            (root / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
            if aware:
                (root / "hooks" / "synced_copy.py").write_text("# present", encoding="utf-8")
    bindir = Path(tmp) / "bin"
    bindir.mkdir()
    exe = bindir / "claude"
    exe.write_text(FAKE_CLAUDE, encoding="utf-8")
    exe.chmod(0o755)
    log = Path(tmp) / "claude.log"
    log.write_text("", encoding="utf-8")
    os.environ.update({"CLAUDE_CONFIG_DIR": str(cfg), "FAKE_LOG": str(log), "FAKE_BEHAVE": behave,
                       "FAKE_SYNCED_ROOT": str(root) if root else "",
                       "PATH": str(bindir) + os.pathsep + SAVED_ENV["PATH"]})
    return cfg, root, log


def load(path):
    sys.modules.pop("synced_copy", None)
    spec = importlib.util.spec_from_file_location(f"ss_{time.time_ns()}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def calls(log):
    return [line for line in log.read_text(encoding="utf-8").splitlines() if line]


def enabled(cfg):
    return json.loads((cfg / "settings.json").read_text(encoding="utf-8")).get("enabledPlugins", {})


def registered(cfg):
    return KEY in json.loads((cfg / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))["plugins"]


if WINDOWS:
    # The fake CLI is a script with a shebang, which Windows cannot execute.
    # The real hand-over is the same Python on every platform.
    print("skipped on Windows (the fake CLI needs a shebang)")
    sys.exit(0)

print("step 1: the organization's copy is ready, so the marketplace install is switched off")
with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp)
    ss = load(HOOKS / "session-start.py")
    did = ss.hand_over_to_org_copy()
    seen = calls(log)
    check("it reports having handed over", did is True, str(seen))
    check("it asked Claude Code first, switched the install off, then asked again",
          seen == ["plugin list --json", f"plugin disable {KEY}", "plugin list --json"], str(seen))
    check("the marketplace install is switched off", enabled(cfg).get(KEY) is False)
    check("and NOT uninstalled: its record and files are still there", registered(cfg))
    check("nothing was uninstalled or removed", not [c for c in seen if "uninstall" in c or "remove" in c])
    marker = json.loads((cfg / ".nsls-org-copy-handover").read_text(encoding="utf-8"))
    check("the hook left its own marker, with the versions", marker.get("from") == "3.49.0" and marker.get("to") == "3.50.0", str(marker))
    check("the freshness check now has nothing to keep fresh", not ss.marketplace_plugin_active() and ss.org_plugin_active())
    log.write_text("", encoding="utf-8")
    check("a second session start does nothing more from the marketplace side",
          ss.hand_over_to_org_copy() is False and calls(log) == [])

print("\nstep 1 undone: Claude Code would not load the organization's copy")
with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, behave="never-loads")
    ss = load(HOOKS / "session-start.py")
    did = ss.hand_over_to_org_copy()
    seen = calls(log)
    check("it does not claim a hand-over", did is False)
    check("the marketplace install was switched straight back on",
          seen[-1] == f"plugin enable {KEY}" and enabled(cfg).get(KEY) is True, str(seen))
    check("no marker is left", not (cfg / ".nsls-org-copy-handover").exists())
    check("and the machine still has its toolkit", registered(cfg) and ss.marketplace_plugin_active())
    log.write_text("", encoding="utf-8")
    ss.hand_over_to_org_copy()
    check("it does not try again every session", calls(log) == [])

print("\nstep 1 never starts without every precondition")
CASES = [
    ("no synced copy on disk (today's machines)", dict(synced=None), {}, []),
    ("the copy belongs to another account", dict(folder=f"{ORG}_99999999-0000-0000-0000-000000000000"), {}, []),
    ("the copy is older than the install it would replace", dict(synced="3.48.0"), {}, []),
    ("the copy is from before the toolkit knew how to run as one", dict(aware=False), {}, []),
    ("the builder switched the organization's copy off",
     dict(settings={"enabledPlugins": {KEY: True, SYNCED: False}}), {}, []),
    ("all syncing is switched off",
     dict(settings={"enabledPlugins": {KEY: True}, "syncClaudeAiPlugins": False}), {}, []),
    ("the marketplace install is already switched off by the builder",
     dict(settings={"enabledPlugins": {KEY: False}}), {}, []),
    ("this session signs in with a token, so synced plugins never load", {}, {"CLAUDE_CODE_OAUTH_TOKEN": "x"}, []),
    ("this session runs on Bedrock", {}, {"CLAUDE_CODE_USE_BEDROCK": "1"}, []),
    ("the migration is frozen", {}, {"NSLS_NO_PLUGIN_MIGRATION": "1"}, []),
    ("Claude Code does not list the organization's copy", dict(behave="not-listed"), {}, ["plugin list --json"]),
    ("Claude Code lists it as disabled", dict(behave="listed-disabled"), {}, ["plugin list --json"]),
    ("the switch-off itself fails", dict(behave="disable-fails"), {},
     ["plugin list --json", f"plugin disable {KEY}"]),
]
for label, kwargs, env, expected in CASES:
    with tempfile.TemporaryDirectory() as tmp:
        cfg, root, log = machine(tmp, **kwargs)
        os.environ.update(env)
        before = (cfg / "settings.json").read_bytes()
        ss = load(HOOKS / "session-start.py")
        did = ss.hand_over_to_org_copy()
        seen = calls(log)
        check(label, did is False and seen == expected and (cfg / "settings.json").read_bytes() == before
              and registered(cfg) and not (cfg / ".nsls-org-copy-handover").exists(),
              f"did={did} calls={seen}")

print("\nshort of time, it leaves the hand-over to a later session")
with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp)
    os.environ["NSLS_HOOK_STARTED_AT"] = str(int(time.time()) - 80)   # 80 of the hook's 90 seconds gone
    ss = load(HOOKS / "session-start.py")
    check("no CLI call is started that it could not finish",
          ss.hand_over_to_org_copy() is False and calls(log) == [] and enabled(cfg).get(KEY) is True)
    check("and the next session is free to do it at once",
          not (cfg / ".nsls-org-copy-handover-check").exists())
    os.environ.pop("NSLS_HOOK_STARTED_AT")
    ss = load(HOOKS / "session-start.py")
    check("which it does", ss.hand_over_to_org_copy() is True and enabled(cfg).get(KEY) is False)

print("\nstep 2: running FROM the organization's copy")
DRIVER = textwrap.dedent('''\
    import importlib.util, json, sys
    spec = importlib.util.spec_from_file_location("ss", sys.argv[1])
    ss = importlib.util.module_from_spec(spec); spec.loader.exec_module(ss)
    print(json.dumps({"root": ss.org_copy_root(), "did": ss.hand_over_to_org_copy()}))
''')


def run_from_synced(root):
    done = subprocess.run([sys.executable, "-c", DRIVER, str(root / "hooks" / "session-start.py")],
                          capture_output=True, text=True, env=dict(os.environ), timeout=120)
    try:
        return json.loads(done.stdout.strip().splitlines()[-1]), done.stdout + done.stderr
    except Exception:
        return {}, done.stdout + done.stderr


with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, real=True, settings={"enabledPlugins": {KEY: False}})
    (cfg / ".nsls-org-copy-handover").write_text(json.dumps({"at": 1, "from": "3.49.0", "to": "3.50.0"}), encoding="utf-8")
    got, raw = run_from_synced(root)
    seen = calls(log)
    check("the hook knows it runs from the organization's copy", got.get("root") == str(root.resolve()), raw)
    check("it uninstalls the install it switched off, then drops the marketplace",
          got.get("did") is True and seen == [f"plugin uninstall {KEY}", "plugin marketplace remove nsls-toolkit"], str(seen))
    check("the marketplace install is gone", not registered(cfg))
    check("and so is the marker", not (cfg / ".nsls-org-copy-handover").exists())
    log.write_text("", encoding="utf-8")
    got, raw = run_from_synced(root)
    check("the next session has nothing left to do", got.get("did") is False and calls(log) == [], raw)

with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, real=True, settings={"enabledPlugins": {KEY: False}})
    got, raw = run_from_synced(root)
    check("an install the BUILDER switched off (no marker) is never touched",
          got.get("did") is False and calls(log) == [] and registered(cfg), raw)

with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, real=True, settings={"enabledPlugins": {KEY: True}})
    (cfg / ".nsls-org-copy-handover").write_text(json.dumps({"at": 1}), encoding="utf-8")
    got, raw = run_from_synced(root)
    check("an install someone switched back on is left alone, marker or not",
          got.get("did") is False and calls(log) == [] and registered(cfg), raw)

with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, real=True, settings={"enabledPlugins": {KEY: False}}, behave="uninstall-fails")
    (cfg / ".nsls-org-copy-handover").write_text(json.dumps({"at": 1}), encoding="utf-8")
    got, raw = run_from_synced(root)
    check("a failed uninstall keeps the marker, so a later session finishes the job",
          got.get("did") is False and (cfg / ".nsls-org-copy-handover").exists() and registered(cfg), raw)

with tempfile.TemporaryDirectory() as tmp:
    cfg, root, log = machine(tmp, real=True, installed=None, settings={})
    (cfg / ".nsls-org-copy-handover").write_text(json.dumps({"at": 1}), encoding="utf-8")
    got, raw = run_from_synced(root)
    check("a marker with no install behind it is simply cleared",
          got.get("did") is False and calls(log) == [] and not (cfg / ".nsls-org-copy-handover").exists(), raw)

os.environ.clear()
os.environ.update(SAVED_ENV)
print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
