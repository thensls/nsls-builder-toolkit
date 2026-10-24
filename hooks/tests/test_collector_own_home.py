#!/usr/bin/env python3
# windows-ci: python | The collector bootstrap refuses a scratch profile, and a real PC's own profile still passes
"""The collector installs only from the account's own home, as the OS records it.

A test ran session start with a scratch HOME. The bootstrap downloaded the real
installer, and the installer pointed the developer's one launchd job at the
scratch folder; once the folder was deleted every run failed, silently, for
days. collector_bootstrap.own_home() now compares the home it was handed with
the one the OS has on record for the signed-in account (the passwd entry on a
Mac, GetUserProfileDirectoryW on Windows), and anything else stands down.

This runs the real OS lookup: on Mac and Linux in hook-tests, on Windows in
windows-hooks. So it also proves a builder's own home still passes. Popen is
always stubbed. Plain stdlib: `python3 hooks/tests/test_collector_own_home.py`.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("collector_bootstrap_own_home",
                                               HOOKS / "collector_bootstrap.py")
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

WINDOWS = os.name == "nt"
PLATFORM = "win32" if WINDOWS else "darwin"  # Linux runs the Mac rules: same lookup
KEY = "USERPROFILE" if WINDOWS else "HOME"
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


launched = []


def fake_popen(*args, **kwargs):
    launched.append(args)
    return object()


print("the OS knows this account's home, and it is the one this run was given")
real = cb.account_home(PLATFORM)
check("it is found", real is not None)
given = os.environ.get(KEY, "")
check(f"it is this run's {KEY}", real is not None and cb._same_dir(given, real),
      f"({given!r} vs {real!r})")
check("so a builder's own home still installs", cb.own_home(PLATFORM, os.environ, real),
      f"({KEY}={given!r}, LOCALAPPDATA={os.environ.get('LOCALAPPDATA')!r}, account={real!r})")

print("\nit is read from the OS, not from the environment")
with tempfile.TemporaryDirectory() as tmp:
    saved = os.environ.get(KEY)
    os.environ[KEY] = tmp
    try:
        moved = cb.account_home(PLATFORM)
    finally:
        if saved is None:
            os.environ.pop(KEY, None)
        else:
            os.environ[KEY] = saved
    check(f"a scratch {KEY} does not move it", moved is not None and real is not None
          and cb._same_dir(moved, real), f"({moved!r} vs {real!r})")

print("\na scratch home never installs")
with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    cfg = t / "claude"
    cfg.mkdir()
    home = t / "home"
    scratch = {"HOME": str(home), "USERPROFILE": str(home),
               "LOCALAPPDATA": str(home / "AppData" / "Local")}
    status = cb.run(config_dir=cfg, platform=PLATFORM, env=scratch, popen=fake_popen)
    check("a scratch home -> sandboxed", status == "sandboxed", f"({status})")
    check("nothing launched, nothing written", launched == [] and list(cfg.iterdir()) == []
          and not home.exists(), f"({launched}, {list(cfg.iterdir())})")
    if WINDOWS:
        mixed = {k: v for k, v in os.environ.items() if k != "NSLS_COLLECTOR_OPTOUT"}
        mixed["LOCALAPPDATA"] = str(t / "Local")
        status = cb.run(config_dir=cfg, platform=PLATFORM, env=mixed, popen=fake_popen)
        check("the account's own USERPROFILE with a scratch LOCALAPPDATA -> sandboxed",
              status == "sandboxed" and launched == [], f"({status}, {launched})")

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all passed")
