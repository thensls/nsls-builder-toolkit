#!/usr/bin/env python3
"""Finding the claude CLI on a Mac that has the desktop app and nothing else.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_mac_app_cli_discovery.py`.

A builder's Mac (2026-11) had run the toolkit from a folder copy for 81 days:
no plugin, so no agents and none of the plugin's hooks. He uses the Claude
desktop app and has no separate `claude` on his PATH. Two causes:

1. install.sh looked for the app's bundled CLI at claude-code/<version>/claude.
   The app now keeps it at
   claude-code/<version>/<hash>/claude.app/Contents/MacOS/claude, so the
   installer found nothing and skipped the plugin. Windows had the same move
   in October and was fixed for claude.exe only.
2. session-start.py's finder knew no Mac app location at all, and nor did the
   migration's own fallback, so the self-install that runs at session start
   could never finish what the installer had skipped.

The fixtures are small shell scripts standing in for the CLI. No real CLI is
run and nothing outside the temp dir is read.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import contextlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
REPO = HOOKS.parent
failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


@contextlib.contextmanager
def env(**values):
    saved = {k: os.environ.get(k) for k in values}
    try:
        for k, v in values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def load_session_start(cfg):
    with env(CLAUDE_CONFIG_DIR=str(cfg)):
        spec = importlib.util.spec_from_file_location(
            f"ss_{time.time_ns()}", HOOKS / "session-start.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    return mod


def load_migration(cfg, finder):
    """Exec the migration the way session-start.py does, without migrating."""
    script = HOOKS / "migrate_to_plugin.py"
    g = {"__name__": "nsls_migrate", "__file__": str(script),
         "_NSLS_MIGRATION_DEADLINE": time.monotonic() + 25,
         "_NSLS_FIND_CLAUDE": finder}
    with env(CLAUDE_CONFIG_DIR=str(cfg), NSLS_NO_PLUGIN_MIGRATION="1"):
        exec(compile(script.read_text(encoding="utf-8"), str(script), "exec"), g)
    return g


def cli(path, kind="runs"):
    """A stand-in CLI. `runs`: answers --version. `linux`: the build the app
    keeps for its VM, which a Mac cannot run. `broken`: executable, exits 126.
    `not-executable`: a leftover without the executable bit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if kind == "linux":
        path.write_bytes(b"\x7fELF\x02\x01\x01" + b"\0" * 32)
    elif kind == "broken":
        path.write_text("#!/bin/sh\nexit 126\n")
    else:
        path.write_text("#!/bin/sh\necho '2.1.0 (Claude Code)'\nexit 0\n")
    path.chmod(0o644 if kind == "not-executable" else 0o755)
    return path


def app_folder(home, vm=False):
    return (home / "Library" / "Application Support" / "Claude"
            / ("claude-code-vm" if vm else "claude-code"))


def new_layout(folder, version, hash_="ddbdf2b334e1"):
    return folder / version / hash_ / "claude.app" / "Contents" / "MacOS" / "claude"


def world(tmp):
    t = Path(tmp)
    cfg, home = t / "cfg", t / "home"
    cfg.mkdir()
    home.mkdir()
    return cfg, home


NO_CLI_PATH = "/usr/bin:/bin"

print("session-start.py finds the app's CLI where the app keeps it today")
with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    folder = app_folder(home)
    # 2.1.99 is there to prove the comparison is numeric: as text it sorts last.
    for v in ("2.1.99", "2.1.309", "2.1.321"):
        cli(new_layout(folder, v))
    ss = load_session_start(cfg)
    check("<version>/<hash>/claude.app/Contents/MacOS/claude is found, newest version",
          ss._mac_app_cli(folder) == new_layout(folder, "2.1.321"), f"({ss._mac_app_cli(folder)})")

    ss._IS_MAC = True
    with env(HOME=str(home), PATH=NO_CLI_PATH, APPDATA=None, LOCALAPPDATA=None, USERPROFILE=None):
        found = ss._find_claude()
    check("_find_claude returns it on a Mac with no other claude",
          found == [str(new_layout(folder, "2.1.321"))], f"({found})")

    ss._IS_MAC = False
    with env(HOME=str(home), PATH=NO_CLI_PATH, APPDATA=None, LOCALAPPDATA=None, USERPROFILE=None):
        found = ss._find_claude()
    check("and the Mac folder is not searched on another system", found is None, f"({found})")

    on_path = cli(Path(tmp) / "bin" / "claude")
    ss._IS_MAC = True
    with env(HOME=str(home), PATH=f"{on_path.parent}{os.pathsep}{NO_CLI_PATH}",
             APPDATA=None, LOCALAPPDATA=None, USERPROFILE=None):
        found = ss._find_claude()
    check("a claude on the PATH still comes first", found == [str(on_path)], f"({found})")

print("\nthe app's older shapes still count")
with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    folder = app_folder(home)
    flat = cli(folder / "2.1.200" / "claude")
    ss = load_session_start(cfg)
    check("<version>/claude", ss._mac_app_cli(folder) == flat, f"({ss._mac_app_cli(folder)})")
    bundle = cli(folder / "2.1.250" / "claude.app" / "Contents" / "MacOS" / "claude")
    check("<version>/claude.app/Contents/MacOS/claude",
          ss._mac_app_cli(folder) == bundle, f"({ss._mac_app_cli(folder)})")

print("\nwhat must never be picked")
with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    folder = app_folder(home)
    ss = load_session_start(cfg)
    check("no app folder at all: nothing, no error", ss._mac_app_cli(folder) is None)
    cli(folder / "2.2.0" / "claude", kind="linux")
    check("the Linux build the app keeps for its VM", ss._mac_app_cli(folder) is None,
          f"({ss._mac_app_cli(folder)})")
    cli(new_layout(folder, "2.3.0"), kind="not-executable")
    check("a file without the executable bit", ss._mac_app_cli(folder) is None,
          f"({ss._mac_app_cli(folder)})")
    real = cli(new_layout(folder, "2.1.321"))
    check("an older copy that can run beats a newer one that cannot",
          ss._mac_app_cli(folder) == real, f"({ss._mac_app_cli(folder)})")

print("\nthe migration's own fallback finds it too (the running finder may be an old one)")
with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    folder = app_folder(home)
    for v in ("2.1.99", "2.1.321"):
        cli(new_layout(folder, v))
    cli(folder / "2.2.0" / "claude", kind="linux")
    g = load_migration(cfg, finder=lambda: None)   # an old finder: comes back empty
    g["_IS_MAC"] = True
    with env(HOME=str(home), PATH=NO_CLI_PATH):
        found = g["_mac_app_cli"]()
        argv = g["_find_claude"]()
    check("newest runnable copy, numerically", found == new_layout(folder, "2.1.321"), f"({found})")
    # _find_claude tries two fixed system paths first; a machine that has one
    # cannot show the fallback, and says so rather than failing.
    if any(Path(p).exists() for p in ("/usr/local/bin/claude", "/opt/homebrew/bin/claude")):
        print("  skip stage A's finder (this machine has a system-wide claude)")
    else:
        check("stage A's finder returns it when the injected finder finds nothing",
              argv == [str(new_layout(folder, "2.1.321"))], f"({argv})")
    g["_IS_MAC"] = False
    with env(HOME=str(home), PATH=NO_CLI_PATH):
        check("not searched on another system", g["_mac_app_cli"]() is None)

print("\ninstall.sh's own search, run for real")
lines = (REPO / "install.sh").read_text(encoding="utf-8").splitlines()
start = next(i for i, l in enumerate(lines) if l.startswith("# --- Desktop app CLI (begin)"))
end = next(i for i, l in enumerate(lines) if l.startswith("# --- Desktop app CLI (end)"))
BLOCK = "\n".join(lines[start:end + 1])


def installer_finds(home, already=""):
    """Run the installer's block under its own shell options; what it picked."""
    script = ("set -euo pipefail\n"
              f'CLAUDE_BIN="{already}"\n' + BLOCK + '\nprintf "%s" "$CLAUDE_BIN"\n')
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60,
                       env={**os.environ, "HOME": str(home), "PATH": NO_CLI_PATH})
    return r.returncode, r.stdout


with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    rc, out = installer_finds(home)
    check("no Claude app on this machine: finds nothing and carries on", (rc, out) == (0, ""), f"({rc} {out!r})")

    folder = app_folder(home)
    for v in ("2.1.99", "2.1.309", "2.1.321"):
        cli(new_layout(folder, v))
    rc, out = installer_finds(home)
    check("the app's current layout is found, newest version first",
          (rc, out) == (0, str(new_layout(folder, "2.1.321"))), f"({rc} {out!r})")

    rc, out = installer_finds(home, already="/somewhere/claude")
    check("a CLI found earlier is kept", (rc, out) == (0, "/somewhere/claude"), f"({rc} {out!r})")

    cli(new_layout(folder, "2.1.400"), kind="broken")
    rc, out = installer_finds(home)
    check("a newer copy that will not run is passed over for one that does",
          (rc, out) == (0, str(new_layout(folder, "2.1.321"))), f"({rc} {out!r})")

with tempfile.TemporaryDirectory() as tmp:
    cfg, home = world(tmp)
    cli(app_folder(home, vm=True) / "2.1.321" / "claude", kind="broken")
    rc, out = installer_finds(home)
    check("only the VM's build, which cannot run here: nothing, and the installer goes on",
          (rc, out) == (0, ""), f"({rc} {out!r})")
    flat = cli(app_folder(home) / "2.1.200" / "claude")
    rc, out = installer_finds(home)
    check("the older <version>/claude shape still works", (rc, out) == (0, str(flat)), f"({rc} {out!r})")

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
