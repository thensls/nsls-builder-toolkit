#!/usr/bin/env python3
# windows-ci: python | Harvest nudge: speaks once a day, only when harvest is on and hasn't run today
"""The harvest nudge asks Claude to check Fathom only when there could be something to harvest.

Plain stdlib: `python3 hooks/tests/test_harvest_nudge.py`.

Pins: silent without the personal toolkit's harvest skill, with `kb_harvest: off`
(CRLF too), in an SDK session, after a harvest already ran today, and on the second
session of the day; otherwise one instruction naming the last harvest date, or a
seven-day lookback when there is no harvest log.

Every subprocess runs sandboxed in its own config dir.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import datetime
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "harvest-nudge.py"
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


TODAY = datetime.date.today()


def sandbox(profile="---\nname: x\n---\n", log_dates=None, skill=True):
    tmp = Path(tempfile.mkdtemp(prefix="harvest-nudge-test-"))
    cfg = tmp / ".claude"
    personal = cfg / "local-plugins" / "nsls-personal-toolkit"
    vault = tmp / "vault"
    (vault / "50-reference").mkdir(parents=True)
    personal.mkdir(parents=True)
    if skill:
        (personal / "skills" / "harvest-meeting").mkdir(parents=True)
        (personal / "skills" / "harvest-meeting" / "SKILL.md").write_text("x", encoding="utf-8")
    (personal / ".env").write_text(f'OBSIDIAN_VAULT_PATH="{vault}"\n', encoding="utf-8")
    (vault / "50-reference" / "builder-profile.md").write_bytes(profile.encode("utf-8"))
    if log_dates:
        rows = [f'{{"ts": "{d.isoformat()}T18:00:00", "meetings": 1}}' for d in log_dates]
        (vault / ".harvest-log.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return tmp, cfg


def run(tmp, cfg, **extra):
    env = dict(os.environ, HOME=str(tmp), USERPROFILE=str(tmp), CLAUDE_CONFIG_DIR=str(cfg),
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    env.update(extra)
    r = subprocess.run([sys.executable, str(HOOK)], env=env, capture_output=True, text=True,
                       encoding="utf-8", timeout=20)
    return r.returncode, r.stdout


print("harvest nudge")

tmp, cfg = sandbox()
code, out = run(tmp, cfg)
week_ago = TODAY - datetime.timedelta(days=7)
check("no harvest log: looks back seven days", f"since {week_ago.isoformat()}" in out, out)
check("exits 0", code == 0)
check("tells Claude to stay silent when there are no meetings", "say nothing" in out, out)
code, out = run(tmp, cfg)
check("second session the same day is silent", out == "", out)

three_ago = TODAY - datetime.timedelta(days=3)
tmp, cfg = sandbox(log_dates=[TODAY - datetime.timedelta(days=9), three_ago])
_, out = run(tmp, cfg)
check("uses the newest harvest-log date", f"since {three_ago.isoformat()}" in out, out)

tmp, cfg = sandbox(log_dates=[TODAY])
_, out = run(tmp, cfg)
check("silent when a harvest already ran today", out == "", out)

tmp, cfg = sandbox(profile="---\nkb_harvest: off\n---\n")
_, out = run(tmp, cfg)
check("silent when kb_harvest is off", out == "", out)

tmp, cfg = sandbox(profile="---\r\nkb_harvest: off\r\n---\r\n")
_, out = run(tmp, cfg)
check("silent when kb_harvest is off with CRLF line endings", out == "", out)

tmp, cfg = sandbox(profile="---\nname: x\n---\nkb_harvest: off\n")
_, out = run(tmp, cfg)
check("an `off` in the note body does not count", out != "", out)

tmp, cfg = sandbox(skill=False)
_, out = run(tmp, cfg)
check("silent without the personal toolkit's harvest skill", out == "", out)

tmp, cfg = sandbox()
_, out = run(tmp, cfg, CLAUDE_CODE_ENTRYPOINT="sdk-cli")
check("silent in a headless SDK session", out == "", out)

tmp, cfg = sandbox()
(cfg / ".nsls-harvest-nudge-2000-01-01").write_text("", encoding="utf-8")
env = dict(os.environ, HOME=str(tmp), USERPROFILE=str(tmp), CLAUDE_CONFIG_DIR=str(cfg),
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
env.pop("CLAUDE_CODE_ENTRYPOINT", None)
procs = [subprocess.Popen([sys.executable, str(HOOK)], env=env, stdout=subprocess.PIPE, text=True,
                          encoding="utf-8") for _ in range(6)]
spoke = sum(1 for p in procs if p.communicate(timeout=20)[0].strip())
check("six sessions opened at once: exactly one speaks", spoke == 1, f"spoke={spoke}")
check("yesterday's claim file is cleaned up", not (cfg / ".nsls-harvest-nudge-2000-01-01").exists())

for ep in ("sdk-py", "local-agent", "remote", "mcp"):
    tmp, cfg = sandbox()
    _, out = run(tmp, cfg, CLAUDE_CODE_ENTRYPOINT=ep)
    check(f"silent when the session is not interactive ({ep})", out == "", out)

tmp, cfg = sandbox()
_, out = run(tmp, cfg, CLAUDE_CODE_ENTRYPOINT="claude-desktop")
check("speaks in the desktop app", out != "", out)

if failures:
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1)
print("\nall passed")
