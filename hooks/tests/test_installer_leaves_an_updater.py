#!/usr/bin/env python3
"""install.sh never leaves a copy that nothing updates without saying so.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_installer_leaves_an_updater.py`.

A builder's Mac (2026-11) had held the same folder copy for weeks. Two things
keep a copy current: the toolkit plugin, or the session hook the installer
writes into settings.json. He had neither, and the installer had said
"installed!".

1. No settings.json. Claude Code does not create that file until something is
   written to it, so a machine that has only used the desktop app has none.
   The installer's settings step ran only where the file existed; elsewhere it
   printed "the plugin will be enabled on first use" and registered nothing.
2. No claude CLI found, so no plugin. The note saying so sat in the middle of
   the skill list and named only the two recommended plugins.

This runs the installer's own settings step and its closing banner, cut from
the real install.sh, against throwaway config dirs. Nothing is downloaded.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SH = (REPO / "install.sh").read_text(encoding="utf-8")
failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def cut(start, end=None):
    a = SH.index(start)
    return SH[a:SH.index(end, a) if end else len(SH)]


SETTINGS_STEP = cut("# --- Step 2: Enable the local plugin", "# --- Step 2.5:")
BANNER = cut("# --- Done ---")
MARKER = "nsls-builder-toolkit/hooks/session-start"


def run(block, cfg, **variables):
    """Run a piece of install.sh under the installer's own shell options."""
    names = {"TEST_MODE": "0", "CONFIG_DIR": str(cfg), "PLUGIN_DIR": str(REPO),
             "INSTALL_FAILED": "", "UPDATE_FAILED": "0", "CLAUDE_BIN": "", **variables}
    head = "set -euo pipefail\n" + "".join(f'{k}="{v}"\n' for k, v in names.items())
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
    r = subprocess.run(["bash", "-c", head + block], capture_output=True, text=True,
                       timeout=120, env=env)
    return r.returncode, r.stdout


def commands(cfg):
    written = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
    return [h["command"] for g in written.get("hooks", {}).values()
            for e in g for h in e.get("hooks", [])]


def with_plugin(cfg):
    """The toolkit plugin, installed and enabled, as plugin_beacon reads it."""
    inst = cfg / "plugins" / "cache" / "nsls-toolkit" / "nsls-builder-toolkit" / "3.46.0"
    inst.mkdir(parents=True)
    (inst / ".mcp.json").write_text('{"mcpServers": {}}')
    (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
        {"plugins": {"nsls-builder-toolkit@nsls-toolkit": [{"installPath": str(inst)}]}}))


def shim(cfg):
    (cfg / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"matcher": "startup", "hooks": [{"type": "command", "command":
            f"python3 -c \"exec(open('{cfg}/local-plugins/{MARKER}.py').read())\""}]}]}}))


print("the settings step on a machine with no settings.json")
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    rc, out = run(SETTINGS_STEP, cfg)
    check("the step finishes", rc == 0, f"({rc} {out[-300:]!r})")
    check("settings.json is started", (cfg / "settings.json").is_file())
    cmds = commands(cfg) if (cfg / "settings.json").is_file() else []
    check("and the session hook is registered in it", any(MARKER in c for c in cmds), f"({cmds})")
    check("with the other two hooks", len(cmds) == 3, f"({cmds})")
    check("the old promise is no longer printed", "will be enabled on first use" not in out
          and "No settings.json found" not in SH, out)

with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    (cfg / "settings.json").write_text(json.dumps({"model": "opus", "permissions": {"deny": ["x"]}}))
    rc, out = run(SETTINGS_STEP, cfg)
    kept = json.loads((cfg / "settings.json").read_text())
    check("a builder's existing settings are kept",
          kept.get("model") == "opus" and kept.get("permissions", {}).get("deny") == ["x"], f"({kept})")
    check("and the session hook is added to them", any(MARKER in c for c in commands(cfg)))

if hasattr(os, "geteuid") and os.geteuid() != 0:
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / ".claude"
        cfg.mkdir()
        cfg.chmod(0o555)
        try:
            rc, out = run(SETTINGS_STEP, cfg)
        finally:
            cfg.chmod(0o755)
        check("a settings.json that cannot be written is said out loud, and the installer goes on",
              rc == 0 and "session hook is NOT registered" in out, f"({rc} {out[-300:]!r})")

print("\nthe closing banner")
with tempfile.TemporaryDirectory() as tmp:
    # The builder's Mac after the fix to the settings step: no CLI, hook registered.
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    shim(cfg)
    rc, out = run(BANNER, cfg)
    tail = "\n".join(out.strip().splitlines()[-9:])
    check("no CLI, hook registered: not called installed", "NSLS Builder Toolkit installed!" not in out, out[-400:])
    check("the headline says one step is left", "One step is left" in out)
    check("the missing plugin is the last thing on the screen",
          "ONE STEP LEFT" in tail and "installs it by itself" in tail, tail)
    check("the skipped list names the toolkit's own plugin",
          "the NSLS toolkit's own plugin" in out)
    check("it is not a failure: the hook finishes the job", rc == 0, f"({rc})")

with tempfile.TemporaryDirectory() as tmp:
    # The builder's Mac as it was: no CLI, and no hook either.
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    (cfg / "settings.json").write_text("{}")
    rc, out = run(BANNER, cfg)
    tail = "\n".join(out.strip().splitlines()[-8:])
    check("no plugin and no hook: the headline says NOT finished",
          "NOT finished" in out and "NSLS Builder Toolkit installed!" not in out, out[-400:])
    check("and the last thing on the screen says the copy will not update itself",
          "THIS COPY WILL NOT UPDATE ITSELF" in tail and "Run this installer again" in tail, tail)
    check("and the installer exits 1", rc == 1, f"({rc})")

with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    (cfg / "settings.json").write_text("{}")
    with_plugin(cfg)
    rc, out = run(BANNER, cfg, CLAUDE_BIN="/somewhere/claude")
    check("plugin installed: installed, exit 0, no warning",
          rc == 0 and "NSLS Builder Toolkit installed!" in out
          and "ONE STEP LEFT" not in out and "NOT FINISHED" not in out, f"({rc} {out[-400:]!r})")

with tempfile.TemporaryDirectory() as tmp:
    # A builder who switched the plugin off keeps the hook; the CLI was found.
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    shim(cfg)
    rc, out = run(BANNER, cfg, CLAUDE_BIN="/somewhere/claude")
    check("CLI found, hook registered, plugin not active: never blamed on a missing CLI",
          rc == 0 and "ONE STEP LEFT" not in out and "was not found" not in out, f"({rc} {out[-400:]!r})")

with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / ".claude"
    cfg.mkdir()
    (cfg / "settings.json").write_text("{}")
    rc, out = run(BANNER, cfg, INSTALL_FAILED="nsls-builder-toolkit", CLAUDE_BIN="/somewhere/claude")
    check("a failed plugin install keeps its own message and exit 1",
          rc == 1 and "did NOT install: nsls-builder-toolkit" in out
          and "SOMETHING DID NOT INSTALL" in out and "NOT FINISHED" not in out, f"({rc} {out[-400:]!r})")

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
