#!/usr/bin/env python3
# windows-ci: python | Lesson check: offered after the builder corrects Claude, never on volume alone, never on top of log it
"""The lesson check is offered when the builder has been correcting Claude, and
only then.

Plain stdlib: `python3 hooks/tests/test_lesson_trigger.py`.

Compound saves a lesson so a builder never repeats a correction to Claude, and
nothing triggered it (0 runs in 30 days on the test machine). The Stop hook now
offers it. These checks pin WHEN: two corrections, or one plus an interrupt or
a declined call, in a stretch of real work; never on volume alone, never twice
in 45 minutes or more than twice a session, never in a headless or scheduled
session, never when Claude's turn ends on a question, and never in the same
turn as the exploration log's own question.

Every subprocess runs sandboxed: its own config dir, no git identity, and a dead
tracker URL.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


TMP = Path(tempfile.mkdtemp(prefix="lesson-trigger-test-"))
HOME = TMP / "home"
(HOME / ".claude").mkdir(parents=True)
GITCFG = TMP / "gitconfig"
GITCFG.write_text("", encoding="utf-8")
ENV = dict(os.environ, HOME=str(HOME), USERPROFILE=str(HOME), CLAUDE_CONFIG_DIR=str(HOME / ".claude"),
           GIT_CONFIG_GLOBAL=str(GITCFG), GIT_CONFIG_NOSYSTEM="1", NSLS_TRACKER_URL="http://127.0.0.1:9",
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
ENV.pop("NSLS_LESSON_CHECK", None)
os.environ.update(CLAUDE_CONFIG_DIR=ENV["CLAUDE_CONFIG_DIR"], HOME=ENV["HOME"])
os.environ.pop("NSLS_LESSON_CHECK", None)
STATE = HOME / ".claude" / ".nsls-logit-state.json"

import lesson_trigger as lt  # noqa: E402

# ── transcript builders ─────────────────────────────────────────────────────
_n = [0]


def say(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tools(n, name="Bash"):
    rows = []
    for _ in range(n):
        _n[0] += 1
        tid = f"t{_n[0]}"
        rows.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": name,
                                                                    "input": {}}]}})
        rows.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                                               "content": "ok"}]}})
    return rows


def denial():
    _n[0] += 1
    tid = f"t{_n[0]}"
    return [{"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tid, "name": "Bash",
                                                           "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": True,
                                                      "content": "The user doesn't want to proceed with this tool "
                                                                 "use. The tool use was rejected."}]}}]


def interrupt():
    return {"type": "user", "message": {"content": [{"type": "text", "text": "[Request interrupted by user]"}]}}


def write(path, rows, mode="w"):
    with open(path, mode, encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    return str(path)


def payload(transcript, sid="s1", **extra):
    return {"session_id": sid, "transcript_path": str(transcript), "hook_event_name": "Stop",
            "cwd": str(TMP), "last_assistant_message": "Done.", **extra}


def run_stop(p, env=None):
    r = subprocess.run([sys.executable, str(HOOKS / "logit-checkpoint.py")], input=json.dumps(p),
                       env=env or ENV, capture_output=True, text=True, encoding="utf-8", timeout=30)
    out = r.stdout.strip()
    try:
        return r.returncode, json.loads(out) if out else None
    except Exception:
        return r.returncode, {"unparsed": out}


def is_lesson(out):
    return bool(out) and "Lesson check" in out.get("systemMessage", "") and \
        "lesson check" in out.get("hookSpecificOutput", {}).get("additionalContext", "")


T = 1_000_000.0  # a fixed clock for the in-process checks

print("what counts as a correction")
for text in ("No, that's the wrong file", "actually use the other one", "I already told you to skip that",
             "why did you push that", "you forgot the version bump", "don't ever send that again",
             "that's not what I asked"):
    check(f"correction: {text!r}", lt.is_correction(text))
for text in ("great, thanks", "now do the next one", "can you also add tests", "looks good to me"):
    check(f"not a correction: {text!r}", not lt.is_correction(text))
check("a system reminder is not the builder speaking", lt.human_text(say("<system-reminder>no</system-reminder>")) is None)
check("an interrupt is not the builder speaking", lt.human_text(interrupt()) is None)
check("a tool result is not the builder speaking", lt.human_text(tools(1)[1]) is None)

print("when it is offered (in process)")


def sess_after(rows, now=T, **extra):
    sess = {}
    out = lt.on_stop(sess, payload(write(TMP / "t.jsonl", rows), **extra), now=now)
    return sess, out


_, out = sess_after([say("No, start with the README"), *tools(15)])
check("the opening message never counts as a correction", out is None)
_, out = sess_after([say("build it"), *tools(15), say("no, wrong folder"), say("you forgot the tests")])
check("two corrections in real work: offered", is_lesson(out), str(out))
_, out = sess_after([say("build it"), *tools(15), say("no, wrong folder"), interrupt()])
check("one correction plus an interrupt: offered", is_lesson(out), str(out))
_, out = sess_after([say("build it"), *tools(14), say("no, wrong folder"), *denial()])
check("one correction plus a declined call: offered", is_lesson(out), str(out))
_, out = sess_after([say("build it"), *tools(15), say("no, wrong folder")])
check("one correction alone: not offered", out is None)
_, out = sess_after([say("build it"), *tools(60)])
check("volume alone: never offered", out is None)
_, out = sess_after([say("build it"), *tools(5), say("no"), say("wrong again")])
check("too little work (under 12 tool calls): not offered", out is None)
_, out = sess_after([say("build it"), *tools(15), say("no, wrong folder"), say("you forgot the tests")],
                    last_assistant_message="Which folder did you mean?")
check("Claude's turn ends on a question: not offered", out is None)
_, out = sess_after([say("build it"), *tools(15), say("no"), say("wrong again")], background_tasks=[{"id": 1}])
check("background work still running: not offered", out is None)
_, out = sess_after([say("build it"), *tools(15), say("no"), say("wrong again")], stop_hook_active=True)
check("already continuing from a Stop hook: not offered", out is None)
_, out = sess_after([{"type": "user", "entrypoint": "sdk-cli", "message": {"content": "build it"}}, *tools(15),
                     say("no"), say("wrong again")])
check("headless session: not offered", out is None)
_, out = sess_after([say("<scheduled-task name=x>run it</scheduled-task>"), *tools(15), say("no"), say("wrong")])
check("scheduled task: not offered", out is None)

print("pacing: cooldown, cap, and the check's own work")
tx = TMP / "pace.jsonl"
sess = {}
write(tx, [say("build it"), *tools(15), say("no, wrong folder"), say("you forgot the tests")])
out = lt.on_stop(sess, payload(tx), now=T)
check("first check offered", is_lesson(out))
write(tx, [*tools(3)], mode="a")
check("the check's own continuation is never asked on", lt.on_stop(sess, payload(tx, stop_hook_active=True),
                                                                   now=T + 5) is None)
check("and its tool calls don't count toward the next stretch", sess["lesson"]["tool_calls"] == 0,
      str(sess["lesson"]))
write(tx, [*tools(15), say("no"), say("wrong again")], mode="a")
check("within 45 minutes: not offered", lt.on_stop(sess, payload(tx), now=T + 600) is None)
check("second check offered after the cooldown", is_lesson(lt.on_stop(sess, payload(tx), now=T + 46 * 60)))
write(tx, [*tools(15), say("no"), say("wrong again")], mode="a")
check("never a third check in one session", lt.on_stop(sess, payload(tx), now=T + 200 * 60) is None)

print("turned off")
(HOME / ".claude" / ".nsls-lesson-check").mkdir(exist_ok=True)
(HOME / ".claude" / ".nsls-lesson-check" / "config.json").write_text('{"enabled": false}', encoding="utf-8")
_, out = sess_after([say("build it"), *tools(15), say("no"), say("wrong again")])
check("off in config: not offered", out is None)
(HOME / ".claude" / ".nsls-lesson-check" / "config.json").write_text('{"enabled": true}', encoding="utf-8")
os.environ["NSLS_LESSON_CHECK"] = "off"
_, out = sess_after([say("build it"), *tools(15), say("no"), say("wrong again")])
check("NSLS_LESSON_CHECK=off: not offered", out is None)
os.environ.pop("NSLS_LESSON_CHECK", None)

print("through the real Stop hook, combined with log it")
work = [say("build it"), *tools(15), say("no, wrong folder"), say("you forgot the tests")]
code, out = run_stop(payload(write(TMP / "a.jsonl", work), sid="hook-a"))
check("the Stop hook offers it, exit 0", code == 0 and is_lesson(out), str(out))
check("the systemMessage the builder sees survives as JSON", "\U0001F9E0" in (out or {}).get("systemMessage", ""),
      str(out))
code, out = run_stop(payload(write(TMP / "a.jsonl", work), sid="hook-a"))
check("the same stretch is not offered twice", code == 0 and out is None, str(out))

state = json.loads(STATE.read_text(encoding="utf-8"))
state["sessions"]["hook-b"] = {"offset": 0, "changes": 9, "prompts": 4, "asked_at": "2026-11-01T10:00:05Z",
                               "answer": "", "reminded": False, "counted": False, "changes_at_answer": 0,
                               "prompt_at": "2026-11-01T10:00:00Z", "key": "folder:x", "updated": "2026-11-01T10:00:05Z"}
state["sessions"]["hook-c"] = dict(state["sessions"]["hook-b"], answer="not-yet")
STATE.write_text(json.dumps(state), encoding="utf-8")
code, out = run_stop(payload(write(TMP / "b.jsonl", work), sid="hook-b"))
ctx = (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
check("log it's unanswered question wins: its reminder, not a lesson check",
      code == 0 and "exploration log" in ctx and "systemMessage" not in (out or {}), str(out))
code, out = run_stop(payload(write(TMP / "c.jsonl", work), sid="hook-c"))
check("log it asked (and was answered) this turn: the lesson check waits", code == 0 and out is None, str(out))
state = json.loads(STATE.read_text(encoding="utf-8"))
state["sessions"]["hook-c"]["prompt_at"] = "2026-11-01T10:05:00Z"
STATE.write_text(json.dumps(state), encoding="utf-8")
code, out = run_stop(payload(write(TMP / "c.jsonl", work + [say("no"), say("wrong again")]), sid="hook-c"))
check("next turn, log it quiet: the lesson check goes out", code == 0 and is_lesson(out), str(out))

r = subprocess.run([sys.executable, str(HOOKS / "lesson-check.py"), "status"], env=ENV, capture_output=True,
                   text=True, encoding="utf-8", timeout=30)
check("lesson status lists the checks the hook offered", "lesson check(s) offered" in r.stdout, r.stdout)

for bad in ("", "not json", "[]", '{"hook_event_name": "Stop"}',
            json.dumps(payload(str(TMP / "missing.jsonl"), sid="hook-d"))):
    r = subprocess.run([sys.executable, str(HOOKS / "logit-checkpoint.py")], input=bad, env=ENV,
                       capture_output=True, text=True, encoding="utf-8", timeout=30)
    check(f"bad payload {bad[:30]!r}: silent, exit 0", r.returncode == 0 and not r.stdout.strip() and
          not r.stderr.strip(), r.stdout + r.stderr)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'all passed'}")
sys.exit(1 if failures else 0)
