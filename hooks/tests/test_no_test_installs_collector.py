#!/usr/bin/env python3
"""No test may install the real usage collector.

Session start ends by installing the collector when it is missing, from the
real installer. A test that ran it with a scratch HOME re-pointed the
developer's own collector schedule at the scratch folder, and the collector
stopped running once the folder was deleted. Two layers stop that now:

  1. collector_off.py opts a test process out, children included. Every test
     file that runs or loads session start, run-hook.sh or the bootstrap must
     import it. This file fails the suite when one does not, and proves the
     module does what it says.
  2. collector_bootstrap.py refuses a home that is not the account's own
     (test_collector_bootstrap.py, test_collector_own_home.py). Checked here
     end to end, from a child process with a scratch HOME and no opt-out.

This file deliberately does not import collector_off: it needs a process
without it. Plain stdlib: `python3 hooks/tests/test_no_test_installs_collector.py`.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent
ROOT = HOOKS.parent
REACHES = re.compile(r"session-start\.(?:py|ps1)|collector_bootstrap|run-hook\.sh")
IMPORTS = re.compile(r"^import collector_off\b", re.M)
SELF = Path(__file__).resolve()
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


def needs_opt_out(text):
    """True when a test's source reaches session start but never opts out."""
    return bool(REACHES.search(text)) and not IMPORTS.search(text)


print("every test that can reach session start imports collector_off")
check("the rule flags a test that runs session start without it",
      needs_opt_out('subprocess.run([sys.executable, str(HOOKS / "session-start.py")])'))
check("and passes one that imports it",
      not needs_opt_out('import collector_off\nrun(HOOKS / "run-hook.sh")'))
files = sorted(p for p in list(HERE.rglob("*.py")) + list((ROOT / "test").rglob("*.py"))
               if p.resolve() != SELF and p.name != "collector_off.py")
missing = [p.relative_to(ROOT).as_posix() for p in files
           if needs_opt_out(p.read_text(encoding="utf-8", errors="replace"))]
check(f"all {len(files)} test files comply", not missing,
      "- add `import collector_off` before the other imports in: " + ", ".join(missing))


def child(code, env):
    r = subprocess.run([sys.executable, "-c", code, str(HERE), str(HOOKS)], env=env,
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip().splitlines(), r.stderr[-400:]


bare = {k: v for k, v in os.environ.items() if k != "NSLS_COLLECTOR_OPTOUT"}
FRESH_GRANDCHILD = (
    "import os, subprocess, sys\n"
    "env = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT') if k in os.environ}\n"
    "r = subprocess.run([sys.executable, '-c', "
    "'import os; print(os.environ.get(\"NSLS_COLLECTOR_OPTOUT\"))'],"
    " env=env, capture_output=True, text=True)\n"
    "print(r.stdout.strip())\n")

print("\ncollector_off opts out the process and every child it starts")
out, err = child("import sys; sys.path.insert(0, sys.argv[1]); import collector_off, os\n"
                 "print(os.environ.get('NSLS_COLLECTOR_OPTOUT'))\n" + FRESH_GRANDCHILD, bare)
check("the test process is opted out", out[:1] == ["1"], f"({out}, {err})")
check("a child given an environment built from scratch is opted out too",
      out[1:2] == ["1"], f"({out}, {err})")
out, err = child(FRESH_GRANDCHILD, bare)
check("(without it, that child would not be: the check above means something)",
      out == ["None"], f"({out}, {err})")

print("\na session-start bootstrap from a test stands down, with or without the opt-out")
RUN = ("import sys; sys.path.insert(0, sys.argv[2])\n"
       "import collector_bootstrap\n"
       "def boom(*a, **k): raise SystemExit('the real installer was launched')\n"
       "print(collector_bootstrap.run(popen=boom, platform='darwin'))\n")
with tempfile.TemporaryDirectory() as tmp:
    scratch = {**bare, "HOME": str(Path(tmp) / "home"), "USERPROFILE": str(Path(tmp) / "home"),
               "CLAUDE_CONFIG_DIR": str(Path(tmp) / "claude")}
    out, err = child("import sys; sys.path.insert(0, sys.argv[1]); import collector_off\n" + RUN, scratch)
    check("with collector_off: optout", out == ["optout"], f"({out}, {err})")
    out, err = child(RUN, scratch)
    check("without it, a scratch HOME: sandboxed (the bootstrap's own guard)",
          out == ["sandboxed"], f"({out}, {err})")
    check("and nothing was written in the scratch home or config", not any(Path(tmp).iterdir()),
          f"({[p.name for p in Path(tmp).iterdir()]})")

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all passed")
