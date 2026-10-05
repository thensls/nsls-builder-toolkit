#!/usr/bin/env python3
"""A PC stuck on an old plugin copy updates itself from the checkout.

Plain stdlib: `python3 hooks/tests/test_stuck_plugin_rescue.py`.

PC Test Round 5 (2026-10-05): the Store app moved its CLI to
claude-code\\<version>\\<hash>\\claude.exe on 2026-10-03. The installed plugin
copy (3.16.2) searched only <version>\\claude.exe, so its daily
`plugin update` found no CLI and skipped itself every session, while the
checkout beside it was already on 3.16.13. The running copy's finder can never
learn the new layout without the update it cannot run. migrate_to_plugin.py is
read from the checkout every session, so it carries its own finder and does the
update itself when the copy's finder comes back empty.

A fake claude.exe (a script that logs its arguments) stands in for the CLI, in
the Store layout, found through the APPDATA/LOCALAPPDATA variables on any OS.
"""
import json
import os
import stat
import sys
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


def machine(tmp, installed="3.16.2", clone="3.17.3", cli=True, cli_fails=False):
    t = Path(tmp)
    cfg = t / "cfg"
    root = cfg / "plugins" / "cache" / "nsls-toolkit" / "nsls-builder-toolkit" / installed
    root.mkdir(parents=True)
    (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
        {"plugins": {"nsls-builder-toolkit@nsls-toolkit": [
            {"installPath": str(root), "version": installed}]}}))
    (cfg / "settings.json").write_text("{}")
    clone_dir = t / "clone"
    (clone_dir / "hooks").mkdir(parents=True)
    (clone_dir / ".claude-plugin").mkdir()
    (clone_dir / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": clone}))
    script = clone_dir / "hooks" / "migrate_to_plugin.py"
    script.write_text((HOOKS / "migrate_to_plugin.py").read_text(encoding="utf-8"), encoding="utf-8")
    log = t / "cli.log"
    local = t / "Local"
    if cli:
        exe = (local / "Packages" / "Claude_pzs8sxrjxfjjc" / "LocalCache" / "Roaming" / "Claude"
               / "claude-code" / "2.1.286" / "635c1867224a" / "claude.exe")
        exe.parent.mkdir(parents=True)
        tail = "echo 'network error' >&2\nexit 1\n" if cli_fails else "echo updated\n"
        exe.write_text(f"#!/bin/sh\necho \"$@\" >> '{log}'\n" + tail)
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    return cfg, script, log, t / "Roaming", local


def load(cfg, script, roaming, local, finder):
    g = {"__name__": "nsls_migrate", "__file__": str(script),
         "_NSLS_MIGRATION_DEADLINE": time.monotonic() + 25, "_NSLS_FIND_CLAUDE": finder}
    saved = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "NSLS_NO_PLUGIN_MIGRATION", "APPDATA",
                                            "LOCALAPPDATA", "USERPROFILE", "PATH")}
    os.environ.update(CLAUDE_CONFIG_DIR=str(cfg), NSLS_NO_PLUGIN_MIGRATION="1", APPDATA=str(roaming),
                      LOCALAPPDATA=str(local), USERPROFILE=str(cfg.parent / "prof"), PATH="/usr/bin:/bin")
    exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), g)
    return g, saved


def restore(saved):
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def run(tmp, finder=lambda: None, **kw):
    cfg, script, log, roaming, local = machine(tmp, **kw)
    g, saved = load(cfg, script, roaming, local, finder)
    try:
        g["_catch_up_plugin"]()
        return cfg, (log.read_text().split("\n") if log.exists() else []), g
    finally:
        restore(saved)


# The fallback tries the Mac install paths before the Windows ones. If this
# machine has a real CLI there, the test would drive it, so it stops instead.
real = [p for p in ("/usr/local/bin/claude", "/opt/homebrew/bin/claude") if Path(p).exists()]
if real:
    print(f"SKIPPED: a real claude CLI is installed at {real[0]}; run this where none is")
    sys.exit(0)

print("a PC whose plugin copy can't find the CLI")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp)
    check("the checkout finds the Store CLI in its hash folder and runs the update",
          calls[:1] == ["plugin update nsls-builder-toolkit@nsls-toolkit"], f"({calls})")
    check("and touches the shared daily marker", (cfg / ".nsls-plugin-update-check").exists())
    check("nothing is reported stuck", not (cfg / ".nsls-plugin-update-status").exists())
with tempfile.TemporaryDirectory() as tmp:
    cfg, script, log, roaming, local = machine(tmp)
    (cfg / ".nsls-plugin-update-check").touch()
    g, saved = load(cfg, script, roaming, local, lambda: None)
    try:
        g["_catch_up_plugin"]()
    finally:
        restore(saved)
    check("at most once a day: a fresh marker means no second update", not log.exists())

print("\nwhen it stays out of the way")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, finder=lambda: ["/somewhere/claude"])
    check("a copy whose own finder works keeps doing its own update", calls == [], f"({calls})")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, installed="3.17.3", clone="3.17.3")
    check("an installed plugin as new as the checkout is left alone", calls == [], f"({calls})")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, installed="3.16.10", clone="3.16.9")
    check("the comparison is numeric (3.16.10 is newer than 3.16.9)", calls == [], f"({calls})")

with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, installed="3.16.2", clone="3.17.3-beta")
    check("a suffixed checkout version still counts as newer (3.17.3-beta > 3.16.2)",
          calls[:1] == ["plugin update nsls-builder-toolkit@nsls-toolkit"], f"({calls})")

print("\nstage B never takes 'no answer' for 'no signal entry'")
with tempfile.TemporaryDirectory() as tmp:
    cfg, script, log, roaming, local = machine(tmp)
    g, saved = load(cfg, script, roaming, local, lambda: None)
    try:
        for out in (g["_BUDGET_EXHAUSTED"], g["_TIMED_OUT"], g["_NOT_FOUND"]):
            g["_claude"] = lambda args, timeout, out=out: (False, out)
            check(f"'{out}' leaves stage B not clean, so the done marker waits",
                  g["_remove_user_scope_signal"]() == (False, False))
        g["_claude"] = lambda args, timeout: (False, "No MCP server found with name: signal")
        check("a real 'not registered' answer is still clean", g["_remove_user_scope_signal"]() == (False, True))
    finally:
        restore(saved)

print("\nwhen the update itself fails")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, cli_fails=True)
    st = json.loads((cfg / ".nsls-plugin-update-status").read_text()) if (cfg / ".nsls-plugin-update-status").exists() else {}
    check("the failure is recorded in the update status file",
          st.get("stage") == "update" and st.get("reason") == "a plugin command failed"
          and "network error" in st.get("detail", ""), f"({st})")
    check("and the marker is set, so a failing update is not retried every session",
          (cfg / ".nsls-plugin-update-check").exists())

print("\nwhen no CLI can be found at all")
with tempfile.TemporaryDirectory() as tmp:
    cfg, calls, g = run(tmp, cli=False)
    st = json.loads((cfg / ".nsls-plugin-update-status").read_text()) if (cfg / ".nsls-plugin-update-status").exists() else {}
    check("it says so, in its own status file, instead of returning silently",
          st.get("stage") == "update" and st.get("reason") == "the claude command could not be found", f"({st})")
    check("and leaves the marker alone, so it retries next session",
          not (cfg / ".nsls-plugin-update-check").exists())
    check("setup's own status file is untouched", not (cfg / ".nsls-plugin-migration-status").exists())

print("\nthe wiring")
src = (HOOKS / "migrate_to_plugin.py").read_text(encoding="utf-8")
i = src.index("def run_migration():")
body = src[i:]
check("the catch-up runs for an installed, enabled plugin, before stage B",
      body.index("_catch_up_plugin()") < body.index("_stage_b()")
      and "if not _plugin_disabled_by_user():" in body)
check("the update shares session-start.py's daily marker",
      '_UPDATE_MARKER = _CONFIG_DIR / ".nsls-plugin-update-check"' in src
      and '".nsls-plugin-update-check"' in (HOOKS / "session-start.py").read_text(encoding="utf-8"))

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
