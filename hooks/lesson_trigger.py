"""When to offer a lesson check: a stretch of work in which the builder corrected Claude.

Called by logit-checkpoint.py's Stop handler, inside the exploration log's lock
and with its session record, so the toolkit's two end-of-turn questions (log it,
and this) never land in the same turn. Plain stdlib, no model call, fails open.

WHY. The compound skill saves a lesson so the builder never repeats a
correction to Claude, and nothing ever triggered it: 0 runs in 30 days on the
machine it was tested on, against about two corrections per long session.
This decides WHEN to ask, from the transcript; Claude decides WHETHER there is
a lesson, from the conversation, and the builder decides whether it is saved.

THE SIGNAL. Since the last check: the builder's messages that read as a
correction (3 points each), interrupts (2) and declined tool calls (2), with at
least 12 tool calls of real work. A score of 5 asks: two corrections, or one
plus an interrupt or a declined call. Volume alone never asks. Tuned on 30 days
of real sessions (2026-10-11): about 0.8 checks per long session, and in a
18-day trial 5 of 11 checks found a lesson worth keeping.

NEVER ASKS WHEN: lesson checks are off · the session is headless or a
scheduled task · background work or crons are still running · Claude's turn
ends on a question to the builder · already continuing from a Stop hook ·
twice already this session · within 45 minutes of the last check.
"""
import json
import os
import re
import time
from pathlib import Path

MIN_TOOL_CALLS = 12
THRESHOLD = 5
WEIGHTS = {"corrections": 3, "interrupts": 2, "denials": 2}
MAX_PER_SESSION = 2
COOLDOWN_SECONDS = 45 * 60
SCAN_BUDGET_BYTES = 4 * 1024 * 1024
MAX_TRANSCRIPT_BYTES = 64 * 1024 * 1024

# A builder message that reads as a correction. Each message counts once, and
# the session's opening message never counts (it sets the task, it corrects
# nothing).
CORRECTION_PATTERNS = [re.compile(p, re.I) for p in (
    r"^\W*(no|nope|nah|wrong|stop|wait|hold on|hang on|undo|revert|incorrect)\b",
    r"^\W*actually\b",
    r"\b(that'?s|that is|this is|it'?s|you'?re) (not right|wrong|incorrect|not what)\b",
    r"\bnot what i (asked|meant|wanted|said)\b",
    r"\bi (already )?(said|told you|asked you|meant)\b",
    r"\bwhy (did|didn'?t|would|are|is) (you|it|this|that)\b",
    r"\byou (didn'?t|did not|forgot|missed|ignored|should have|shouldn'?t have|keep|still)\b",
    r"\b(that|this|it) (broke|didn'?t work|doesn'?t work|failed|is broken)\b",
    r"\b(again|still)\b[^.?!]{0,40}\b(wrong|broken|failing|missing|not working)\b",
    r"\bstop (doing|asking|adding|using)\b",
    r"\b(don'?t|never) (do|use|run|send|push|add|make|say|write|put|ask|ever)\b",
)]
DENIAL_MARKERS = ("doesn't want to proceed", "tool use was rejected", "user rejected", "user declined")
NOT_HUMAN_PREFIXES = ("<command-", "<local-command", "<task-notification", "<system-reminder",
                      "<bash-", "Caveat:", "Stop hook feedback", "<user-memory-input")
INTERRUPT_PREFIX = "[Request interrupted by user"


def fresh():
    return {"offset": 0, "tool_calls": 0, "corrections": 0, "interrupts": 0, "denials": 0,
            "skills": [], "checks": 0, "last_check": 0, "seen_human": False, "skip": "",
            "pending": False}


def state(sess):
    st = sess.get("lesson")
    if not isinstance(st, dict):
        st = sess["lesson"] = fresh()
    for k, v in fresh().items():
        st.setdefault(k, v)
    return st


# ── reading the transcript ──────────────────────────────────────────────────

def _blocks(entry):
    c = (entry.get("message") or {}).get("content")
    return [b for b in c if isinstance(b, dict)] if isinstance(c, list) else []


def _result_text(block):
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def _user_text(entry):
    """Text of a user entry that is not a tool result, else None."""
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return None
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    c = (entry.get("message") or {}).get("content")
    if isinstance(c, str):
        return c
    bl = _blocks(entry)
    if not bl or any(b.get("type") == "tool_result" for b in bl):
        return None
    return "\n".join(b.get("text", "") for b in bl if b.get("type") == "text")


def human_text(entry):
    """The builder's own words in this entry, or None (tool results, injected context, interrupts)."""
    if entry.get("type") == "attachment":
        att = entry.get("attachment") or {}
        if att.get("type") == "queued_command" and isinstance(att.get("prompt"), str):
            return att["prompt"]
        return None
    text = _user_text(entry)
    if text is None:
        return None
    stripped = text.lstrip()
    if not stripped or stripped.startswith(NOT_HUMAN_PREFIXES) or stripped.startswith(INTERRUPT_PREFIX):
        return None
    return text


def is_correction(text):
    head = text.strip()[:600]
    return any(p.search(head) for p in CORRECTION_PATTERNS)


def _count(st, entry):
    ep = entry.get("entrypoint")
    if isinstance(ep, str) and ep.startswith("sdk"):
        st["skip"] = "headless"
    if entry.get("isSidechain"):
        return
    if entry.get("type") == "assistant":
        for b in _blocks(entry):
            if b.get("type") == "tool_use":
                st["tool_calls"] += 1
                if b.get("name") == "Skill":
                    skill = str((b.get("input") or {}).get("skill") or "")[:80]
                    if skill and skill not in st["skills"] and len(st["skills"]) < 8:
                        st["skills"].append(skill)
        return
    if entry.get("type") == "user":
        for b in _blocks(entry):
            if b.get("type") == "tool_result":
                if any(m in _result_text(b) for m in DENIAL_MARKERS):
                    st["denials"] += 1
            elif b.get("type") == "text" and b.get("text", "").lstrip().startswith(INTERRUPT_PREFIX):
                st["interrupts"] += 1
        raw = (entry.get("message") or {}).get("content")
        if isinstance(raw, str) and raw.lstrip().startswith(INTERRUPT_PREFIX):
            st["interrupts"] += 1
    text = human_text(entry)
    if text is None:
        return
    if not st["seen_human"]:
        st["seen_human"] = True
        if text.lstrip().startswith("<scheduled-task"):
            st["skip"] = "scheduled"
        return
    if is_correction(text):
        st["corrections"] += 1


def scan(st, transcript_path):
    """Count what was appended since the last scan. Reads only new bytes; a
    shorter file means a new transcript."""
    try:
        p = Path(transcript_path)
        size = p.stat().st_size
    except Exception:
        return
    if size > MAX_TRANSCRIPT_BYTES:
        return
    if size < st["offset"]:
        st.update(offset=0, tool_calls=0, corrections=0, interrupts=0, denials=0, skills=[], seen_human=False)
    try:
        with open(p, "rb") as fh:
            fh.seek(st["offset"])
            chunk = fh.read(SCAN_BUDGET_BYTES)
    except Exception:
        return
    end = chunk.rfind(b"\n")
    if end < 0:
        if len(chunk) >= SCAN_BUDGET_BYTES:  # one record bigger than the budget: step past it
            st["offset"] += len(chunk)
        return
    for raw in chunk[: end + 1].splitlines():
        try:
            entry = json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            continue
        if isinstance(entry, dict):
            _count(st, entry)
    st["offset"] += end + 1


def skip_to_end(st, transcript_path):
    try:
        st["offset"] = Path(transcript_path).stat().st_size
    except Exception:
        pass


# ── deciding ────────────────────────────────────────────────────────────────

def score(st):
    return sum(w * st.get(k, 0) for k, w in WEIGHTS.items())


def ends_on_question(message):
    lines = [ln.strip() for ln in str(message or "").strip().splitlines() if ln.strip()]
    return bool(lines) and lines[-1].endswith("?")


def due(st, payload, now):
    if st["skip"] or st["checks"] >= MAX_PER_SESSION:
        return False
    if now - (st.get("last_check") or 0) < COOLDOWN_SECONDS:
        return False
    if payload.get("background_tasks") or payload.get("session_crons"):
        return False
    if ends_on_question(payload.get("last_assistant_message")):
        return False
    return st["tool_calls"] >= MIN_TOOL_CALLS and score(st) >= THRESHOLD


def summary(st):
    parts = [f"{st['tool_calls']} tool calls"]
    for key, label in (("corrections", "correction"), ("interrupts", "interrupt"), ("denials", "declined call")):
        if st[key]:
            parts.append(f"{st[key]} {label}{'s' if st[key] != 1 else ''}")
    return " · ".join(parts)


def fire(st, now):
    """Record the check and start the next stretch from zero. Returns the
    summary and skills of the stretch that earned it."""
    told = (summary(st), list(st["skills"]))
    st.update(checks=st["checks"] + 1, last_check=now, pending=True,
              tool_calls=0, corrections=0, interrupts=0, denials=0, skills=[])
    return told


def nudge(stretch, skills):
    used = ", ".join(skills) or "none"
    return (
        "[NSLS Builder Toolkit — lesson check] "
        f"Since the last check: {stretch}. Skills used: {used}.\n"
        "The builder corrected you during this stretch. So they never have to repeat it, load the toolkit's "
        "compound skill (kw:compound) and follow its \"Lesson check\" section now: at most two lessons, each "
        "shown with exactly where it would be saved, and nothing saved until the builder says yes. Judge "
        "from what you remember of this stretch; the transcript may lag. If nothing is worth keeping, or "
        "you're mid-task, say so in one line. Don't repeat your earlier answer. If the skill won't load: "
        "state the lesson in one line, say where you'd save it, and ask before saving anything."
    )


SYSTEM_MESSAGE = "🧠 Lesson check: Claude will offer to save what you corrected, so you don't have to repeat it."


def on_stop(sess, payload, now=None):
    """The Stop hook's output dict for a lesson check, or None. Mutates sess."""
    now = now or time.time()
    try:
        import lesson_core
        on = lesson_core.enabled()
    except Exception:
        on = True
    if not on:
        return None
    path = payload.get("transcript_path") or ""
    if not path:
        return None
    st = state(sess)
    if payload.get("stop_hook_active"):
        # Continuing after a Stop hook (this check's own answer, or log it's
        # reminder): never ask on top, and don't count the check's own work.
        if st["pending"]:
            skip_to_end(st, path)
            st["pending"] = False
        return None
    st["pending"] = False
    scan(st, path)
    if not due(st, payload, now):
        return None
    stretch, skills = fire(st, now)
    try:
        import lesson_core
        lesson_core.append_log({"event": "check", "summary": stretch, "skills": skills})
    except Exception:
        pass
    return {"systemMessage": SYSTEM_MESSAGE,
            "hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": nudge(stretch, skills)}}
