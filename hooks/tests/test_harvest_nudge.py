#!/usr/bin/env python3
# windows-ci: python | Harvest nudge: speaks once a day, on a typed message, only when harvest is on and hasn't run today
"""The harvest nudge asks Claude to check Fathom only when there could be something to harvest.

Plain stdlib: `python3 hooks/tests/test_harvest_nudge.py`.

Pins: silent without the personal toolkit's harvest skill, with `kb_harvest: off`
(CRLF too), in an SDK session, after a harvest already ran today, and on the second
message of the day; otherwise one instruction naming the last harvest date, or a
seven-day lookback when there is no harvest log. A scheduled task's message, or one
that harvests anyway, stays silent AND leaves the day's nudge for the person.

Every subprocess runs sandboxed in its own config dir.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import datetime
import json
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


def payload(prompt):
    return json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt": prompt})


def run(tmp, cfg, prompt="what's on my plate today?", **extra):
    env = dict(os.environ, HOME=str(tmp), USERPROFILE=str(tmp), CLAUDE_CONFIG_DIR=str(cfg),
               PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    env.update(extra)
    r = subprocess.run([sys.executable, str(HOOK)], env=env, input=payload(prompt), capture_output=True,
                       text=True, encoding="utf-8", timeout=20)
    return r.returncode, r.stdout


print("harvest nudge")

tmp, cfg = sandbox()
code, out = run(tmp, cfg)
week_ago = TODAY - datetime.timedelta(days=7)
check("no harvest log: looks back seven days", f"since {week_ago.isoformat()}" in out, out)
check("exits 0", code == 0)
check("tells Claude to stay silent when there are no meetings", "say nothing" in out, out)
code, out = run(tmp, cfg)
check("second message the same day is silent", out == "", out)

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
(cfg / ".nsls-harvest-nudge-asked-2000-01-01").write_text("", encoding="utf-8")
env = dict(os.environ, HOME=str(tmp), USERPROFILE=str(tmp), CLAUDE_CONFIG_DIR=str(cfg),
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
env.pop("CLAUDE_CODE_ENTRYPOINT", None)
procs = [subprocess.Popen([sys.executable, str(HOOK)], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, encoding="utf-8") for _ in range(6)]
spoke = sum(1 for p in procs if p.communicate(payload("hi"), timeout=20)[0].strip())
check("six messages sent at once: exactly one speaks", spoke == 1, f"spoke={spoke}")
check("yesterday's claim file is cleaned up", not (cfg / ".nsls-harvest-nudge-asked-2000-01-01").exists())

for ep in ("sdk-py", "local-agent", "remote", "mcp"):
    tmp, cfg = sandbox()
    _, out = run(tmp, cfg, CLAUDE_CODE_ENTRYPOINT=ep)
    check(f"silent when the session is not interactive ({ep})", out == "", out)

tmp, cfg = sandbox()
_, out = run(tmp, cfg, CLAUDE_CODE_ENTRYPOINT="claude-desktop")
check("speaks in the desktop app", out != "", out)

tmp, cfg = sandbox()
_, out = run(tmp, cfg, prompt='<scheduled-task name="git-health-check" file="x">\nThis is an automated run')
check("silent on a scheduled task's message", out == "", out)
_, out = run(tmp, cfg)
check("the person's next message still gets the day's nudge", out != "", out)

for prompt in ("/close-day", "close day", "let's close-week", "harvest my meetings"):
    tmp, cfg = sandbox()
    _, out = run(tmp, cfg, prompt=prompt)
    check(f"silent when the message harvests anyway ({prompt})", out == "", out)
    _, out = run(tmp, cfg)
    check(f"and the nudge is still there afterwards ({prompt})", out != "", out)

tmp, cfg = sandbox()
_, out = run(tmp, cfg, prompt="")
check("silent on an empty message", out == "", out)

tmp, cfg = sandbox()
stale = cfg / f".nsls-harvest-nudge-{TODAY.isoformat()}"
stale.write_text("", encoding="utf-8")
_, out = run(tmp, cfg)
check("a claim left today by the session-start version doesn't silence the nudge", out != "", out)
check("and that old claim is cleaned up", not stale.exists())

if failures:
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1)
print("\nall passed")
