#!/usr/bin/env python3
# windows-ci: python | Hooks running from the organization-delivered copy earn their beacons, so old shims retire there too
"""Beacons from the copy NSLS's Claude organization delivers.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_synced_beacons.py`.

A beacon is the proof that the PLUGIN copy of a hook fires on a machine, and
stage B retires an installer's settings.json shim only on that proof. The proof
used to be accepted from one place only: plugins/cache/, a marketplace install.
A machine that gets the toolkit through organization sync runs its hooks from
plugins/synced/ instead, so no beacon was ever written or believed there. The
shims would have stayed for good, and every hook would have run twice: two
credit pings per session, two gate checks per tool call.

What this pins:

1. A hook running from the synced copy writes its beacon, and it is believed.
2. Evidence is still earned, not inherited: a beacon from another account's
   copy, from a copy since replaced by a newer version, from a copy that a
   marketplace install now outranks, or from a clone, proves nothing.
3. On a synced machine with all three hooks proven, stage B removes the shims
   and the pointer stubs; with none proven, it removes nothing.
4. The installers' two questions (--proven, --installed) answer for a synced
   machine, so re-running an installer does not put the shims back.
5. With no synced copy, every answer is what it was.
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
ORG = "11111111-2222-3333-4444-555555555555"
ACCT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
FOLDER = f"{ORG}_{ACCT}"
OTHER = f"{ORG}_99999999-0000-0000-0000-000000000000"
WINDOWS = os.name == "nt"
ALL = ("session-start", "skill-event", "guardrail-gate")

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def new_cfg(tmp):
    cfg = Path(tmp) / "claude"
    cfg.mkdir(parents=True)
    (cfg / ".claude.json").write_text(json.dumps(
        {"oauthAccount": {"organizationUuid": ORG, "accountUuid": ACCT}}), encoding="utf-8")
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    os.environ["NSLS_NO_PLUGIN_MIGRATION"] = "1"  # importing the migration must not migrate
    return cfg


def add_copy(cfg, folder=FOLDER, version="3.50.0", mcp=False):
    root = cfg / "plugins" / "synced" / folder / PLUGIN
    (root / ".claude-plugin").mkdir(parents=True)
    (root / "hooks").mkdir()
    set_version(root, version)
    (root / "hooks" / "hooks.json").write_text("{}", encoding="utf-8")
    if mcp:
        (root / ".mcp.json").write_text("{}", encoding="utf-8")
    return root


def set_version(root, version):
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": PLUGIN, "version": version}, indent=2), encoding="utf-8")


def add_marketplace(cfg, version="3.6.0"):
    root = cfg / "plugins" / "cache" / "nsls-toolkit" / PLUGIN / version
    (root / "hooks").mkdir(parents=True)
    (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
        {"plugins": {f"{PLUGIN}@nsls-toolkit": [{"scope": "user", "version": version,
                                                  "installPath": str(root)}]}}), encoding="utf-8")
    return root


def load(name, cfg):
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    for cached in ("synced_copy", "plugin_beacon"):
        sys.modules.pop(cached, None)
    spec = importlib.util.spec_from_file_location(f"m_{name.replace('-', '_')}_{time.time_ns()}", HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def beacon(cfg, hook):
    return json.loads((cfg / ".nsls-plugin-beacons" / f"{hook}.json").read_text(encoding="utf-8"))


def prove(pb, root, hooks=ALL):
    for hook in hooks:
        f = root / "hooks" / f"{hook}-copy.py"
        f.write_text("# plugin copy", encoding="utf-8")
        assert pb.record(hook, f), f"a beacon for {hook} should have been written"


SAVED_ENV = dict(os.environ)


def reset_env():
    os.environ.clear()
    os.environ.update(SAVED_ENV)


# ---------------------------------------------------------------------------
print("a hook running from the organization's copy earns its beacon")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    root = add_copy(cfg)
    pb = load("plugin_beacon", cfg)
    check("the synced copy is the plugin root of a file inside it",
          pb.plugin_root(root / "hooks" / "session-start.py") == str(root.resolve()))
    check("record() writes the beacon", pb.record("session-start", root / "hooks" / "session-start.py"))
    rec = beacon(cfg, "session-start")
    check("it names the synced root", rec.get("root") == str(root.resolve()), str(rec))
    check("and the copy's own version, not its folder name", rec.get("version") == "3.50.0", str(rec))
    check("fired() believes it", pb.fired("session-start"))
    check("one hook's evidence says nothing about another's", not pb.fired("skill-event"))
    check("the plugin counts as active", pb.active())

    set_version(root, "3.51.0")
    check("the copy was replaced by a newer version: the old evidence is not inherited",
          not pb.fired("session-start"))
    pb.record("session-start", root / "hooks" / "session-start.py")
    check("and is re-earned the next time the hook runs", pb.fired("session-start"))

    rec = beacon(cfg, "session-start")
    for blank in ("", "synced"):
        rec["version"] = blank
        (cfg / ".nsls-plugin-beacons" / "session-start.json").write_text(json.dumps(rec), encoding="utf-8")
        check(f"a beacon carrying no real version ({blank!r}) proves nothing about this copy",
              not pb.fired("session-start"))
    (root / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": PLUGIN, "version": "not-a-version"}), encoding="utf-8")
    pb.record("session-start", root / "hooks" / "session-start.py")
    check("and a copy whose own version cannot be read earns no evidence at all",
          beacon(cfg, "session-start").get("version") == "" and not pb.fired("session-start"))
    set_version(root, "3.51.0")
    pb.record("session-start", root / "hooks" / "session-start.py")
    check("with its version readable again, the next run earns it back", pb.fired("session-start"))

    market = add_marketplace(cfg)
    check("a marketplace install outranks it: the synced beacon stops counting",
          not pb.fired("session-start"))
    (cfg / "settings.json").write_text(
        json.dumps({"enabledPlugins": {f"{PLUGIN}@nsls-toolkit": False}}), encoding="utf-8")
    check("unless that install is switched off, when the synced copy is the live one again",
          pb.fired("session-start") and pb.active())
    (cfg / "settings.json").unlink()

    shutil.rmtree(market)
    check("a registry entry whose folder is gone is not the live copy: the synced copy is",
          pb._installed_root() == str(root.resolve()) and pb.active() and pb.fired("session-start"))
    (cfg / "plugins" / "installed_plugins.json").unlink()

    shutil.rmtree(root)
    check("a beacon for a copy that is gone proves nothing", not pb.fired("session-start"))
    check("and the plugin is no longer active", not pb.active())
reset_env()

print("\nevidence that must not count")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    stray = add_copy(cfg, folder=OTHER)
    pb = load("plugin_beacon", cfg)
    pb.record("session-start", stray / "hooks" / "session-start.py")
    check("a beacon from another account's copy is not believed", not pb.fired("session-start"))
    check("and that copy does not make the plugin active", not pb.active())

    clone = cfg / "local-plugins" / PLUGIN / "hooks"
    clone.mkdir(parents=True)
    check("a clone still cannot write a beacon (as before)",
          not pb.record("skill-event", clone / "skill-event.sh"))
    check("nor can this test's own copy of the hooks", not pb.record("skill-event", HOOKS / "skill-event.sh"))

    forged = cfg / "plugins" / "synced-lookalike" / FOLDER / PLUGIN
    (forged / "hooks").mkdir(parents=True)
    (cfg / ".nsls-plugin-beacons").mkdir(exist_ok=True)
    (cfg / ".nsls-plugin-beacons" / "guardrail-gate.json").write_text(json.dumps(
        {"hook": "guardrail-gate", "root": str(forged), "version": "3.50.0"}), encoding="utf-8")
    check("a forged beacon naming a synced-shaped path is not evidence", not pb.fired("guardrail-gate"))
reset_env()

with tempfile.TemporaryDirectory() as tmp:
    # A marketplace install that was removed leaves its cache folder, and the
    # beacons it earned, behind. Once the organization's copy is the live one,
    # that old evidence must not retire a shim on its behalf.
    cfg = new_cfg(tmp)
    stale = cfg / "plugins" / "cache" / "nsls-toolkit" / PLUGIN / "3.6.0"
    (stale / "hooks").mkdir(parents=True)
    (cfg / ".nsls-plugin-beacons").mkdir()
    (cfg / ".nsls-plugin-beacons" / "guardrail-gate.json").write_text(json.dumps(
        {"hook": "guardrail-gate", "root": str(stale.resolve()), "version": "3.6.0"}), encoding="utf-8")
    pb = load("plugin_beacon", cfg)
    check("with no plugin registered at all, a cache beacon is believed (as before)", pb.fired("guardrail-gate"))
    add_copy(cfg)
    check("with the organization's copy live, the removed install's beacon proves nothing",
          not pb.fired("guardrail-gate"))
    check("so nothing is proven until the organization's copy earns it", pb.proven() == [])
reset_env()

print("\nswitches")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    root = add_copy(cfg, mcp=True)
    pb = load("plugin_beacon", cfg)
    prove(pb, root)
    check("all three hooks proven from the synced copy", sorted(pb.proven()) == sorted(ALL), str(pb.proven()))
    check("and it serves its MCP config", pb.serves_mcp())
    (cfg / "settings.json").write_text(
        json.dumps({"enabledPlugins": {f"{PLUGIN}@synced": False}}), encoding="utf-8")
    check("switched off by the builder: not active, so nothing is proven",
          not pb.active() and pb.proven() == [])
    (root.parent / f"{PLUGIN}.meta.json").write_text(
        json.dumps({"installation_preference": "required"}), encoding="utf-8")
    check("required by NSLS: the switch does not stop it", pb.active() and len(pb.proven()) == 3)
    (cfg / "settings.json").write_text(json.dumps({"syncClaudeAiPlugins": False}), encoding="utf-8")
    check("all syncing switched off: not active", not pb.active())
reset_env()

print("\nthe installers' two questions")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    root = add_copy(cfg, mcp=True)
    pb = load("plugin_beacon", cfg)
    prove(pb, root)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg))
    out = subprocess.run([sys.executable, str(HOOKS / "plugin_beacon.py"), "--proven"],
                         capture_output=True, text=True, env=env, timeout=30).stdout.split()
    check("--proven lists all three, so a re-run installer leaves the shims out",
          sorted(out) == sorted(ALL), str(out))
    out = subprocess.run([sys.executable, str(HOOKS / "plugin_beacon.py"), "--installed"],
                         capture_output=True, text=True, env=env, timeout=30).stdout.strip()
    check("--installed says installed, so no second MCP entry is registered", out == "installed", out)
reset_env()

with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg))
    out = subprocess.run([sys.executable, str(HOOKS / "plugin_beacon.py"), "--proven"],
                         capture_output=True, text=True, env=env, timeout=30).stdout.strip()
    check("no plugin of either kind: --proven lists nothing (as before)", out == "", out)
    out = subprocess.run([sys.executable, str(HOOKS / "plugin_beacon.py"), "--installed"],
                         capture_output=True, text=True, env=env, timeout=30).stdout.strip()
    check("and --installed says nothing (as before)", out == "", out)
reset_env()

print("\na marketplace machine is judged exactly as before")
with tempfile.TemporaryDirectory() as tmp:
    cfg = new_cfg(tmp)
    market = add_marketplace(cfg, "3.8.6")
    pb = load("plugin_beacon", cfg)
    f = market / "hooks" / "session-start.py"
    f.write_text("# plugin copy", encoding="utf-8")
    check("a beacon from the cache is written", pb.record("session-start", f))
    check("with the version folder's name", beacon(cfg, "session-start").get("version") == "3.8.6")
    check("and believed", pb.fired("session-start") and pb.active())
    (cfg / "settings.json").write_text(
        json.dumps({"enabledPlugins": {f"{PLUGIN}@nsls-toolkit": False}}), encoding="utf-8")
    check("switched off by the builder: not active", not pb.active())
    (cfg / "settings.json").write_text(
        json.dumps({"enabledPlugins": {f"{PLUGIN}@synced": False}}), encoding="utf-8")
    check("the synced copy's switch does not turn a marketplace install off", pb.active())
reset_env()

# ---------------------------------------------------------------------------
print("\nstage B on an organization-delivered machine")
SHIM = "/Users/someone/.claude/local-plugins/nsls-builder-toolkit/hooks/"


def shim_machine(cfg):
    """Three installer shims, one hook of the builder's own, one org pointer."""
    (cfg / "settings.json").write_text(json.dumps({"hooks": {
        "SessionStart": [{"matcher": "startup", "hooks": [
            {"type": "command", "command": f'python3 "{SHIM}session-start.py"'}]}],
        "PreToolUse": [
            {"matcher": "Skill", "hooks": [{"type": "command", "command": f'bash "{SHIM}skill-event.sh"'}]},
            {"matcher": "Bash|Write|Edit", "hooks": [
                {"type": "command", "command": f'python3 "{SHIM}guardrail-gate.py"'}]},
            {"matcher": "Write", "hooks": [{"type": "command", "command": "python3 /home/me/my-own-hook.py"}]},
        ]}}, indent=2), encoding="utf-8")
    stub = cfg / "skills" / "gws"
    stub.mkdir(parents=True)
    (stub / "SKILL.md").write_text(
        "---\nname: gws\ndescription: >-\n  Google Workspace\n---\n\n"
        "Read and follow the full skill at "
        "`~/.claude/local-plugins/nsls-builder-toolkit/skills/gws/SKILL.md`.\n", encoding="utf-8")


def commands(cfg):
    left = []
    for groups in json.loads((cfg / "settings.json").read_text(encoding="utf-8")).get("hooks", {}).values():
        for group in groups:
            left += [h["command"] for h in group.get("hooks", [])]
    return left


for label, proven in (("nothing proven yet: every shim and the pointer stay", ()),
                      ("all three proven from the synced copy: the shims and the pointer go", ALL)):
    with tempfile.TemporaryDirectory() as tmp:
        cfg = new_cfg(tmp)
        root = add_copy(cfg)
        shim_machine(cfg)
        pb = load("plugin_beacon", cfg)
        prove(pb, root, proven)
        mig = load("migrate_to_plugin", cfg)
        mig._IS_OWN_POINTER = load("session-start", cfg).is_own_pointer
        got = mig._proven_hooks()
        removed = mig._remove_settings_hooks(only=got)
        stubs = mig._remove_org_stubs(allowed="session-start" in got)
        left = commands(cfg)
        if proven:
            check(label, removed == 3 and stubs == 1 and left == ["python3 /home/me/my-own-hook.py"],
                  f"removed={removed} stubs={stubs} left={left}")
            check("and the machine reads as clean, so stage B can finish",
                  not mig._shims_present() and not mig._org_stubs_exist())
        else:
            check(label, removed == 0 and stubs == 0 and len(left) == 4 and (cfg / "skills" / "gws").exists(),
                  f"removed={removed} stubs={stubs} left={left}")
    reset_env()

# ---------------------------------------------------------------------------
print("\nskill-event.sh, run the way Claude Code runs it")


def git_bash():
    if not WINDOWS:
        return "bash"
    git = shutil.which("git")
    for cand in ([Path(git).resolve().parents[1] / "bin" / "bash.exe"] if git else []) + [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"]:
        if cand.is_file():
            return str(cand)
    return None


bash = git_bash()
if not bash:
    check("Git Bash is present on this PC", False, "(not found)")
else:
    for label, pretty in (("plugin.json written over several lines", True),
                          ("plugin.json written on one line", False)):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = new_cfg(tmp)
            root = add_copy(cfg)
            if not pretty:
                (root / ".claude-plugin" / "plugin.json").write_text(
                    json.dumps({"name": PLUGIN, "version": "3.50.0"}), encoding="utf-8")
            shutil.copy(HOOKS / "skill-event.sh", root / "hooks" / "skill-event.sh")
            env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), HOME=tmp, NSLS_SKILL_EVENT_DRYRUN="1")
            shapes = [("forward slashes", root.as_posix() + "/hooks/skill-event.sh")]
            if WINDOWS:
                shapes.append(("Claude Code's Windows shape", str(root) + "/hooks/skill-event.sh"))
            for shape, script in shapes:
                path = cfg / ".nsls-plugin-beacons" / "skill-event.json"
                if path.exists():
                    path.unlink()
                subprocess.run([bash, script], input="{}", capture_output=True, text=True, env=env, timeout=30)
                check(f"{label}, {shape}: the beacon is written", path.exists())
                if path.exists():
                    rec = json.loads(path.read_text(encoding="utf-8"))
                    check(f"{label}, {shape}: it carries the copy's version", rec.get("version") == "3.50.0", str(rec))
                    code = ("import sys; sys.path.insert(0, sys.argv[1]); import plugin_beacon; "
                            "print(plugin_beacon.fired('skill-event'))")
                    out = subprocess.run([sys.executable, "-c", code, str(HOOKS)], capture_output=True,
                                         text=True, env=env, timeout=30)
                    check(f"{label}, {shape}: and fired() accepts it", out.stdout.strip() == "True",
                          out.stdout + out.stderr[-200:])
        reset_env()

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
