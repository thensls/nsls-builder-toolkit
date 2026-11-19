#!/usr/bin/env python3
"""The claude CLI running the session is found from CLAUDE_PID, wherever it lives.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_running_claude.py`.

Jeff's PC (18 Nov 2026) ran Claude Code only through the desktop app. There was
no claude on PATH and none in any folder the toolkit searched, so every
session's update failed with "the claude command could not be found" and the
plugin sat on 3.32.3 for a month. Claude Code tells every hook which process
started it (CLAUDE_PID), and that process is the CLI, so nothing has to guess
where the app keeps it.

These tests start a real process named claude (a copy of a system program) and
look it up by pid, on whichever system runs them, Windows included.
"""
# windows-ci: python | The running claude CLI is found from CLAUDE_PID on a real process, and a blind plugin copy catches up with it

import collector_off  # noqa: F401  (first: no test may install the real collector)
import ast
import contextlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath, PureWindowsPath

HOOKS = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"
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


def start(folder, name):
    """A real, long-running process whose program file is folder/name."""
    if WINDOWS:
        src = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "PING.EXE"
        prog = folder / f"{name}.exe"
        shutil.copyfile(src, prog)
        args = ["ping", "-n", "60", "127.0.0.1"]
    else:
        src = Path(shutil.which("sleep") or "/bin/sleep")
        prog = folder / name
        # copyfile, not copy2: a Mac system program carries a flag that may
        # not be copied onto a file outside /bin.
        shutil.copyfile(src, prog)
        prog.chmod(0o755)
        if sys.platform == "darwin":
            # A Mac kills a copied system program on start (its signature is
            # tied to /bin) unless the copy is signed again, ad hoc.
            subprocess.run(["codesign", "--force", "--sign", "-", str(prog)],
                           capture_output=True, check=True)
        # Named by its original name in argv[0]: on newer Ubuntu, sleep is one
        # program shared by every coreutils command, which picks the command
        # from argv[0] and refuses "claude". The file it runs is still claude.
        args = ["sleep", "60"]
    proc = subprocess.Popen(args, executable=str(prog),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.2)
    if proc.poll() is not None:
        raise RuntimeError(f"the stand-in {prog} exited at start (code {proc.returncode})")
    return proc, prog


def eventually(fn, timeout=5.0):
    """fn()'s first non-empty answer within `timeout`, so a slow CI machine
    starting the stand-in process is not a failure; the last answer otherwise."""
    deadline = time.monotonic() + timeout
    while True:
        got = fn()
        if got or time.monotonic() >= deadline:
            return got
        time.sleep(0.1)


def same(a, b):
    try:
        return a is not None and os.path.samefile(a, b)
    except OSError:
        return False


def empty_world(t):
    """Environment where no claude can be found by any of the old searches."""
    for d in ("home", "prof", "Roaming", "Local", "bin"):
        (t / d).mkdir(exist_ok=True)
    return dict(HOME=str(t / "home"), USERPROFILE=str(t / "prof"),
                APPDATA=str(t / "Roaming"), LOCALAPPDATA=str(t / "Local"),
                PATH=str(t / "bin"))


def stop(running):
    for p in running:
        try:
            p.kill()
            p.wait(timeout=5)
        except Exception:
            pass


procs = []
try:
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        cfg = t / "cfg"
        cfg.mkdir()
        progs = t / "progs"
        progs.mkdir()
        claude_proc, claude_prog = start(progs, "claude")
        node_proc, node_prog = start(progs, "node")
        procs += [claude_proc, node_proc]
        ss = load_session_start(cfg)

        print("a real process is looked up by its pid")
        found = eventually(lambda: ss._process_path(claude_proc.pid))
        check("the program a live process runs is found from its pid",
              same(found, claude_prog), f"({found} vs {claude_prog})")
        with env(CLAUDE_PID=str(claude_proc.pid)):
            found = eventually(ss._running_claude)
        check("CLAUDE_PID pointing at claude gives that CLI", same(found, claude_prog), f"({found})")

        print("\nonly the claude program itself, never an interpreter")
        check("a process named node is still found by pid",
              same(eventually(lambda: ss._process_path(node_proc.pid)), node_prog))
        with env(CLAUDE_PID=str(node_proc.pid)):
            check("but is never taken for the CLI (an npm install runs as node)",
                  ss._running_claude() is None)
        for p in (PurePosixPath("/Applications/x/claude.app/Contents/MacOS/claude"),
                  PureWindowsPath(r"C:\Users\j\AppData\Roaming\Claude\claude-code\2.1.3\claude.exe"),
                  PureWindowsPath(r"C:\Program Files\Claude\CLAUDE.EXE"),
                  PurePosixPath("/home/j/.local/share/claude/versions/2.1.325")):
            check(f"accepted: {p}", ss._is_claude_cli(p))
        for p in (PurePosixPath("/usr/local/bin/node"), PureWindowsPath(r"C:\nodejs\node.exe"),
                  PurePosixPath("/usr/bin/python3"), PurePosixPath("/opt/other/versions/2.1.325")):
            check(f"refused: {p}", not ss._is_claude_cli(p))

        print("\nno usable pid is never an error")
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        for label, value in (("unset", None), ("not a number", "abc"), ("zero", "0"),
                             ("negative", "-5"), ("a process that has ended", str(dead.pid))):
            with env(CLAUDE_PID=value):
                try:
                    got = ss._running_claude()
                except Exception as e:  # noqa: BLE001
                    got = e
            check(f"CLAUDE_PID {label}: nothing found, no exception", got is None, f"({got!r})")

        print("\nthe running CLI comes before anything else")
        world = empty_world(t)
        with env(**world, CLAUDE_PID=None):
            check("with no running CLI and nothing installed, nothing is found (Jeff's PC before)",
                  ss._find_claude() is None, f"({ss._find_claude()})")
        with env(**world, CLAUDE_PID=str(claude_proc.pid)):
            found = ss._find_claude()
        check("on that same machine the running CLI is found",
              found is not None and len(found) == 1 and same(found[0], claude_prog), f"({found})")
        old = t / "bin" / ("claude.exe" if WINDOWS else "claude")
        old.write_text("an old CLI")
        old.chmod(0o755)
        with env(**world, CLAUDE_PID=str(claude_proc.pid)):
            found = ss._find_claude()
        check("it beats an older claude on PATH (a Mac with a May CLI in ~/.local/bin)",
              found is not None and same(found[0], claude_prog), f"({found})")
        old.unlink()

        print("\na plugin copy whose own finder is blind catches up through the migration")
        (cfg / "plugins").mkdir()
        (cfg / "plugins" / "installed_plugins.json").write_text(json.dumps({"plugins": {
            "nsls-builder-toolkit@nsls-toolkit": [{
                "version": "3.32.3",
                "installPath": str(cfg / "plugins" / "cache" / "nsls-toolkit"
                                   / "nsls-builder-toolkit" / "3.32.3")}]}}))
        calls = []

        class Done:
            returncode, stdout, stderr = 0, "updated", ""

        class FakeSubprocess:
            TimeoutExpired = subprocess.TimeoutExpired

            @staticmethod
            def run(argv, **kw):
                calls.append(list(argv))
                return Done()

        # The finder a 3.32.3 session-start hands over: it searches the old
        # folders and finds nothing on a desktop-only PC.
        g = load_migration(cfg, lambda: None)
        g["subprocess"] = FakeSubprocess
        with env(**world, CLAUDE_PID=None):
            g["_catch_up_plugin"]()
        status = cfg / ".nsls-plugin-update-status"
        rec = json.loads(status.read_text()) if status.exists() else {}
        check("without a running CLI it records Jeff's exact symptom and runs nothing",
              calls == [] and "could not be found" in rec.get("reason", ""), f"({calls} {rec})")

        g = load_migration(cfg, lambda: None)
        g["subprocess"] = FakeSubprocess
        with env(**world, CLAUDE_PID=str(claude_proc.pid)):
            g["_catch_up_plugin"]()
        ran = calls[-1] if calls else []
        check("with it, the plugin is updated by the CLI running the session",
              len(ran) == 4 and same(ran[0], claude_prog)
              and ran[1:] == ["plugin", "update", "nsls-builder-toolkit@nsls-toolkit"], f"({ran})")
        check("and the stuck record is cleared", not status.exists())
        # Before the folder goes: Windows will not delete a program that runs.
        stop(procs)

    print("\nthe migration's copy is the same code as session-start's")
    def functions(path):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        return {n.name: ast.get_source_segment(src, n) for n in tree.body
                if isinstance(n, ast.FunctionDef)}
    a, b = functions(HOOKS / "session-start.py"), functions(HOOKS / "migrate_to_plugin.py")
    for name in ("_process_path", "_is_claude_cli", "_running_claude"):
        check(f"{name} is identical in both files", a.get(name) and a.get(name) == b.get(name))
finally:
    stop(procs)

print()
if failures:
    print(f"FAILED: {len(failures)}: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
