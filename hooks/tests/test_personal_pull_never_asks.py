#!/usr/bin/env python3
# windows-ci: python | The Personal Toolkit's own update entry is rewritten so it can never ask for a GitHub sign-in
"""The Personal Toolkit's own pull entry can no longer ask anyone to sign in.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_personal_pull_never_asks.py`.

The Personal Toolkit's installers register its update in settings.json as a
plain `git pull` of the toolkit folder. Nothing in that command stops git
asking for credentials. Against a public repository it never needs any. Once
the repository is private, on a computer with no GitHub sign-in, Git Credential
Manager (the default on Windows) opens a sign-in window: from a hook, at every
session start. The session hook now rewrites that entry, adding the three
settings that make git fail quietly instead. What this pins:

1. Each form an installer or an upgrade wrote gets the settings for ITS shell,
   and the rewritten command really runs git with them, on the same folder,
   with the same arguments.
2. Nothing else is touched: another checkout's entry, an entry someone wrote by
   hand, the bare form that has no shell of its own yet, the rest of the file.
3. It happens once: a second pass changes nothing, byte for byte.
4. A rewritten entry is still recognised as the installer's own, so a later
   take-over of the folder still removes it.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import contextlib
import importlib.util
import io
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
PLUGIN = "nsls-personal-toolkit"
WINDOWS = os.name == "nt"
NAMES = "GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR"
ENV_PATHS = ",".join("Env:" + n for n in NAMES.split())
BASH_QUIET = "GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS= "
PS_QUIET = ("$env:GIT_TERMINAL_PROMPT='0'; $env:GCM_INTERACTIVE='never'; "
            "Remove-Item Env:GIT_ASKPASS -ErrorAction Ignore; ")

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def load(cfg):
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    os.environ["NSLS_NO_PLUGIN_MIGRATION"] = "1"
    spec = importlib.util.spec_from_file_location(f"ss_{time.time_ns()}", HOOKS / "session-start.py")
    ss = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ss)
    return ss


def bare(folder):
    return f'git -C "{folder}" pull --ff-only --quiet'


def bash_form(folder):
    return f"unset {NAMES}; " + bare(folder)


def ps_form(folder):
    return f"Remove-Item {ENV_PATHS} -ErrorAction Ignore; " + bare(folder)


def write_settings(cfg, commands, **extra):
    data = dict(extra, hooks={"SessionStart": [
        {"matcher": "startup|resume", "hooks": [{"type": "command", "command": c, "timeout": 20} for c in commands]}]})
    (cfg / "settings.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def commands(cfg):
    data = json.loads((cfg / "settings.json").read_text(encoding="utf-8-sig"))
    return [h["command"] for group in data["hooks"]["SessionStart"] for h in group["hooks"]]


# Records how it was started, one JSON line per call.
RECORDER = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    keys = ("GIT_TERMINAL_PROMPT", "GCM_INTERACTIVE", "GIT_ASKPASS")
    with open(os.environ["RECORD_TO"], "a") as fh:
        fh.write(json.dumps({"argv": sys.argv[1:], "env": {k: os.environ.get(k) for k in keys}}) + "\\n")
''')

saved_env = dict(os.environ)

print("1. each form gets the settings for its own shell")
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / "home" / ".claude"
    folder = cfg / "local-plugins" / PLUGIN
    folder.mkdir(parents=True)
    other = Path(tmp) / "elsewhere" / PLUGIN
    edited = f'cd /x && git -C "{folder}" pull --ff-only --quiet'
    builder = 'bash "/x/nsls-builder-toolkit/hooks/run-hook.sh" session-start'
    sync = f'"/usr/bin/python3" "{folder}/hooks/session-start.py" --no-pull'
    before_list = [bash_form(folder), ps_form(folder), bare(folder), bash_form(other), edited, builder, sync]
    write_settings(cfg, before_list, model="opus", permissions={"allow": ["Bash(git pull:*)"]})
    ss = load(cfg)
    pd = ss._personal_delivery()
    err = io.StringIO()
    with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(err):
        ss.quieten_personal_pull()
    after = commands(cfg)
    check("the Git Bash / Mac form gains the three settings, written for a POSIX shell",
          after[0] == f"unset {NAMES}; {BASH_QUIET}" + bare(folder), after[0])
    check("the PowerShell form gains them, written for PowerShell",
          after[1] == f"Remove-Item {ENV_PATHS} -ErrorAction Ignore; {PS_QUIET}"
          + f'git -c core.askPass= -C "{folder}" pull --ff-only --quiet', after[1])
    check("the bare form, which has no shell of its own yet, is left for the installers' own upgrade",
          after[2] == bare(folder))
    check("another checkout's entry is not this folder's to change", after[3] == bash_form(other))
    check("an entry someone wrote by hand is theirs", after[4] == edited)
    check("the Builder Toolkit's hook and the folder's own session hook are untouched",
          after[5] == builder and after[6] == sync)
    data = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
    check("the rest of the file means what it meant", data["model"] == "opus"
          and data["permissions"] == {"allow": ["Bash(git pull:*)"]}
          and data["hooks"]["SessionStart"][0]["matcher"] == "startup|resume"
          and all(h["timeout"] == 20 and h["type"] == "command" for h in data["hooks"]["SessionStart"][0]["hooks"]))
    check("the file as it was is kept beside it", (cfg / "settings.json.pre-personal-quiet-pull").exists())
    check("nothing is said to Claude; one line goes to the log", out.getvalue() == "" and "can no longer ask" in err.getvalue())

    print("2. it happens once")
    once = (cfg / "settings.json").read_bytes()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ss.quieten_personal_pull()
    check("a second pass changes nothing, byte for byte", (cfg / "settings.json").read_bytes() == once)
    check("and reports nothing to do", pd.quieten_update_entries(cfg) == 0)

    print("3. a rewritten entry is still the installer's own")
    check("so it is counted with the rest (three pulls and the session hook), the hand-written one apart",
          pd.update_entries(cfg) == (4, 1), str(pd.update_entries(cfg)))
    check("and a take-over of the folder still removes it", pd.remove_update_entries(cfg) is True
          and commands(cfg) == [bash_form(other), edited, builder])

    print("4. the rewritten commands really run git that way")
    bindir = Path(tmp) / "bin"
    bindir.mkdir()
    log = Path(tmp) / "calls.jsonl"
    env = dict(os.environ, RECORD_TO=str(log), PATH=str(bindir) + os.pathsep + os.environ["PATH"],
               GIT_DIR="/some/other/repo", GIT_ASKPASS="/usr/bin/some-askpass")
    env.pop("GCM_INTERACTIVE", None)
    want_env = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}
    if WINDOWS:
        print("  (skipped on Windows: the recording git is a POSIX script)")
    else:
        (bindir / "git").write_text(RECORDER, encoding="utf-8")
        (bindir / "git").chmod(0o755)
        log.write_text("", encoding="utf-8")
        r = subprocess.run(["sh", "-c", after[0]], env=env, capture_output=True, text=True, timeout=30)
        got = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
        check("under sh: one git call, the same folder and arguments as before",
              r.returncode == 0 and len(got) == 1
              and got[0]["argv"] == ["-C", str(folder), "pull", "--ff-only", "--quiet"], f"{r.stderr} {got}")
        check("with all three ways of asking switched off, a configured askpass helper included",
              bool(got) and got[0]["env"] == dict(want_env, GIT_ASKPASS=""), str(got))
        pwsh = shutil.which("pwsh")
        if pwsh is None:
            print("  (PowerShell form not run: no pwsh on this machine)")
        else:
            log.write_text("", encoding="utf-8")
            r = subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", after[1]], env=env,
                               capture_output=True, text=True, timeout=120)
            got = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
            check("under PowerShell: one git call, the same folder and pull, with an empty askpass setting in front",
                  len(got) == 1 and got[0]["argv"] == ["-c", "core.askPass=", "-C", str(folder), "pull", "--ff-only", "--quiet"],
                  f"{r.stdout} {r.stderr} {got}")
            check("with the terminal question and Git Credential Manager's window switched off",
                  bool(got) and all(got[0]["env"].get(k) == v for k, v in want_env.items()), str(got))
            check("and the askpass helper this session inherited is gone from git's environment",
                  bool(got) and got[0]["env"].get("GIT_ASKPASS") is None, str(got))

print("5. nothing to rewrite: nothing is written")
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / "home" / ".claude"
    cfg.mkdir(parents=True)
    ss = load(cfg)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ss.quieten_personal_pull()
    check("no settings.json: none is created", not (cfg / "settings.json").exists())
    write_settings(cfg, ['bash "/x/nsls-builder-toolkit/hooks/run-hook.sh" session-start'])
    raw = (cfg / "settings.json").read_bytes()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ss.quieten_personal_pull()
    check("no Personal Toolkit entry: the file is byte for byte what it was, and no copy is made",
          (cfg / "settings.json").read_bytes() == raw and not (cfg / "settings.json.pre-personal-quiet-pull").exists())
    (cfg / "settings.json").write_text("{ not json, pull --ff-only --quiet", encoding="utf-8")
    raw = (cfg / "settings.json").read_bytes()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ss.quieten_personal_pull()
    check("a settings.json that cannot be read is left alone", (cfg / "settings.json").read_bytes() == raw)

os.environ.clear()
os.environ.update(saved_env)

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
