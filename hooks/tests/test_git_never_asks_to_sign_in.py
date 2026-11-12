#!/usr/bin/env python3
# windows-ci: python | No git call a hook makes can open a sign-in window or ask a question
"""A hook's git calls fail rather than ask anyone to sign in.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_git_never_asks_to_sign_in.py`.

Every session start fetches the toolkits, asks the marketplace remote for its
latest commit, and may run `claude plugin update`, which makes the CLI run git
too. Against a repository the machine can read, none of that needs a credential.
Against one it cannot read (a private repository on a machine with no GitHub
sign-in), git goes looking for someone to ask:

* its own terminal question, stopped by GIT_TERMINAL_PROMPT=0 (already set);
* Git Credential Manager, the default on Windows, which IGNORES that setting
  and opens a sign-in window. Only GCM_INTERACTIVE=never stops it;
* an askpass helper, a second program git runs to ask. An empty GIT_ASKPASS
  turns it off.

From a hook that is a window nobody asked for, at every session start, on every
PC. What this pins: all three are switched off for every git call the hooks
make AND for every `claude plugin` call that fetches, in both hooks.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
WINDOWS = os.name == "nt"
WANT = {"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": ""}

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def load(name, cfg):
    os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
    os.environ["NSLS_NO_PLUGIN_MIGRATION"] = "1"  # importing the migration must not migrate
    spec = importlib.util.spec_from_file_location(f"m_{name.replace('-', '_')}_{time.time_ns()}", HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def has_all(env):
    return all(env.get(k) == v for k, v in WANT.items())


# Records the three settings it was started with, one JSON line per call.
RECORDER = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    keys = ("GIT_TERMINAL_PROMPT", "GCM_INTERACTIVE", "GIT_ASKPASS")
    with open(os.environ["RECORD_TO"], "a") as fh:
        fh.write(json.dumps({"argv": sys.argv[1:], "env": {k: os.environ.get(k) for k in keys}}) + "\\n")
    sys.exit(1)
''')


def recorder(tmp, name):
    bindir = Path(tmp) / f"bin-{name}"
    bindir.mkdir()
    exe = bindir / name
    exe.write_text(RECORDER, encoding="utf-8")
    exe.chmod(0o755)
    return bindir


def recorded(log):
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


print("session-start.py")
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / "claude"
    cfg.mkdir()
    saved = dict(os.environ)
    try:
        os.environ["GIT_ASKPASS"] = "/usr/bin/some-askpass"   # a helper someone configured
        os.environ.pop("GCM_INTERACTIVE", None)
        ss = load("session-start", cfg)
        env = ss._git_env()
        check("the git environment switches off all three ways of asking", has_all(env), str({k: env.get(k) for k in WANT}))
        check("an askpass helper from the builder's own environment is overridden", env["GIT_ASKPASS"] == "")
        check("the variables that aim git at another repository are still cleared",
              not any(k in env for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")))

        if not WINDOWS:
            log = Path(tmp) / "calls.jsonl"
            log.write_text("", encoding="utf-8")
            os.environ["RECORD_TO"] = str(log)
            path = os.environ["PATH"]
            os.environ["PATH"] = str(recorder(tmp, "git")) + os.pathsep + path
            ss._git_rc(tmp, "ls-remote", "origin", "HEAD")
            ss._git_out(tmp, "rev-parse", "HEAD")
            got = recorded(log)
            check("every git call the hook makes carries them", len(got) == 2 and all(has_all(c["env"]) for c in got), str(got))

            log.write_text("", encoding="utf-8")
            claude = [str(recorder(tmp, "claude") / "claude")]
            ss._run_plugin_update(claude)
            ss._heal_plugin_drift(claude, {"installPath": "", "sha": None, "version": "?"}, "0" * 40,
                                  time.monotonic() + 10)
            ss._find_claude = lambda: claude
            ss.org_plugin_installed = lambda: True
            ss.update_now()
            got = recorded(log)
            kinds = sorted({" ".join(c["argv"][:2]) for c in got})
            check("the update, the repair and 'update my toolkit' all reach the CLI",
                  kinds == ["plugin uninstall", "plugin update"] and len(got) >= 3, str(kinds))
            check("and every one of those CLI calls carries them", all(has_all(c["env"]) for c in got), str(got))
    finally:
        os.environ.clear()
        os.environ.update(saved)

print("migrate_to_plugin.py")
with tempfile.TemporaryDirectory() as tmp:
    cfg = Path(tmp) / "claude"
    cfg.mkdir()
    saved = dict(os.environ)
    try:
        mig = load("migrate_to_plugin", cfg)
        check("its CLI environment switches off all three", has_all(mig._no_prompt_env()))
        if not WINDOWS:
            log = Path(tmp) / "calls.jsonl"
            log.write_text("", encoding="utf-8")
            os.environ["RECORD_TO"] = str(log)
            claude = [str(recorder(tmp, "claude") / "claude")]
            mig._find_claude = lambda: claude
            mig._DEADLINE = time.monotonic() + 30
            mig._claude(["plugin", "marketplace", "add", "https://example.invalid/x.git"], timeout=10)
            got = recorded(log)
            check("the marketplace add, the one that clones, carries them",
                  len(got) == 1 and has_all(got[0]["env"]), str(got))
    finally:
        os.environ.clear()
        os.environ.update(saved)

print("session-start.ps1")
ps1 = (HOOKS / "session-start.ps1").read_text(encoding="utf-8")
check("the hook's own environment tells Git Credential Manager never to ask",
      "$env:GCM_INTERACTIVE = 'never'" in ps1)
check("set before any git call runs", ps1.index("$env:GCM_INTERACTIVE = 'never'") < ps1.index("function Invoke-GitBounded"))
check("and so does every bounded git call",
      "$psi.EnvironmentVariables['GCM_INTERACTIVE'] = 'never'" in ps1)
check("the terminal question is still off as well", "$env:GIT_TERMINAL_PROMPT = '0'" in ps1)
check("session-start.ps1 is ASCII-only", all(ord(c) < 128 for c in ps1))

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
