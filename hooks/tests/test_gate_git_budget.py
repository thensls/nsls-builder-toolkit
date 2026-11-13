#!/usr/bin/env python3
"""The guardrail gate's git calls: a slow first call still decides, and all of
them together stay inside the hook's 10 seconds.

Plain stdlib: `python3 hooks/tests/test_gate_git_budget.py`. Mac and Linux only
(the slow git is a shell script).

A git call that times out reads as "no repo", and the gate allows. On a Mac
without Homebrew, `git` is Apple's /usr/bin/git shim, whose first call has to
find the developer tools: 0.93s on a macOS CI runner on 2026-10-18 and past the
old 2-second cap often enough that a gate test flaked ten times in a week. So
the first call now gets 3.5 seconds, later calls 2, and all of them 4 together.
A fake `git` in front of the real one sleeps to play the slow shim.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GATE = Path(os.environ.get("GATE_UNDER_TEST") or
            Path(__file__).resolve().parents[1] / "guardrail-gate.py")
PUSH = {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}}
failures = []


def check(label, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {label} {'' if cond else detail}")
    if not cond:
        failures.append(label)


if os.name == "nt":
    print("skip: the slow git here is a shell script")
    sys.exit(0)

REAL_GIT = shutil.which("git")
SLOW_GIT = """#!/bin/sh
if [ "$FAKE_GIT_SLOW" = first ] && [ ! -e "$FAKE_GIT_DIR/first-done" ]; then
  : > "$FAKE_GIT_DIR/first-done"; sleep "$FAKE_GIT_SLEEP"
fi
[ "$FAKE_GIT_SLOW" = all ] && sleep "$FAKE_GIT_SLEEP"
exec "$REAL_GIT" "$@"
"""


def personal_repo(tmp):
    repo = Path(tmp) / "nsls-thing"
    repo.mkdir()
    (repo / "README.md").write_text("# NSLS chapter dashboard\nInternal NSLS tool.\n")
    for args in (["init", "-q"], ["remote", "add", "origin",
                                   "https://github.com/someones-personal-account/nsls-thing.git"]):
        subprocess.run([REAL_GIT, *args], cwd=repo, capture_output=True, check=True)
    return repo


def run_gate(tmp, slow, sleep):
    fake = Path(tmp) / f"fakegit-{slow}-{sleep}"
    fake.mkdir()
    (fake / "git").write_text(SLOW_GIT)
    (fake / "git").chmod(0o755)
    cfg = Path(tmp) / f"cfg-{slow}-{sleep}"
    cfg.mkdir()
    env = dict(os.environ)
    env.update({
        "PATH": f"{fake}{os.pathsep}{env.get('PATH', '')}",
        "REAL_GIT": REAL_GIT, "FAKE_GIT_DIR": str(fake),
        "FAKE_GIT_SLOW": slow, "FAKE_GIT_SLEEP": str(sleep),
        "CLAUDE_CONFIG_DIR": str(cfg),
        "NSLS_GUARDRAIL_EVENT_LOG": str(Path(tmp) / f"events-{slow}-{sleep}.jsonl"),
    })
    env.pop("NSLS_GUARDRAILS_DISABLED", None)
    started = time.monotonic()
    r = subprocess.run([sys.executable, str(GATE)], input=json.dumps(PUSH), capture_output=True,
                       text=True, cwd=REPO, env=env, timeout=30)
    return r, time.monotonic() - started


def denied(r):
    try:
        return json.loads(r.stdout or "{}").get("hookSpecificOutput", {}).get(
            "permissionDecision") == "deny"
    except Exception:
        return False


with tempfile.TemporaryDirectory() as tmp:
    REPO = personal_repo(tmp)

    r, took = run_gate(tmp, "none", 0)
    check("fast git: a push from a personal repo is blocked", denied(r), r.stdout[:200])

    # Wall-clock bounds are generous on purpose (CI runners stall): each one
    # still fails if git could run unbudgeted, about 2s per call, 4+ calls.
    r, took = run_gate(tmp, "first", 2.5)  # past the old flat 2s cap
    print(f"  info cold first call: {took:.1f}s")
    check("cold first git call (2.5s): still blocked", denied(r), f"({took:.1f}s) {r.stdout[:200]}")


    r, took = run_gate(tmp, "all", 3)
    print(f"  info every call slow: {took:.1f}s")
    check("every git call slow: the gate exits cleanly", r.returncode == 0, f"(exit {r.returncode})")
    check("every git call slow: git stops at its 4s budget, nowhere near the hook's 10s",
          took < 7.5, f"({took:.1f}s)")

# The budget itself, on a fake clock (no wall-clock waits, so nothing to flake):
# a first call that succeeds just under its cap leaves later calls only what is
# left of the shared budget, and a spent budget spawns no git at all.
import importlib.util
spec = importlib.util.spec_from_file_location("gate_budget", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
clock = [1000.0]
gate.time.monotonic = lambda: clock[0]
first = gate._git_timeout()
check("first call may take GIT_FIRST_TIMEOUT", first == gate.GIT_FIRST_TIMEOUT, f"({first})")
clock[0] += 3.4  # it succeeded just under its cap
later = gate._git_timeout()
check("a later call gets only what is left of the budget",
      abs(later - (gate.GIT_BUDGET - 3.4)) < 1e-9, f"({later})")
clock[0] += 0.7  # budget spent
spawned = []
gate.subprocess.run = lambda *a, **k: spawned.append(a)
check("spent budget: git returns empty", gate.git("rev-parse", "--show-toplevel", cwd="/x") == "")
check("spent budget: no git process is started", spawned == [])
check("git can never use up the tracker lookup's window",
      gate.LOOKUP_DEADLINE - gate.GIT_BUDGET >= 4, f"({gate.LOOKUP_DEADLINE} - {gate.GIT_BUDGET})")

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all passed")
