#!/usr/bin/env python3
"""harvest-nudge.py — UserPromptSubmit: offer knowledge base harvest only when there is something to harvest.

Harvest (the personal toolkit's /harvest-meeting) ran only inside /close-day and
/close-week, so a builder who skipped those never had a meeting reach the KB: the
company KB got no harvest commits from 5 Aug to 2 Nov 2026. This hook covers them.

It speaks to Claude, never to the builder directly. A hook can't reach the Fathom
connector, so the hook decides *whether to look* and Claude does the looking:
  - silent unless the personal toolkit's harvest skill is installed and the
    builder hasn't set `kb_harvest: off` in builder-profile.md;
  - at most once a day (claim file), and never if a harvest already ran today;
  - only on a message a person typed, in a session they are sitting at (CLI,
    desktop app, IDE). It runs on the message, not at session start, because the
    desktop app's scheduled tasks open as ordinary desktop sessions: at session
    start they were taking the day's only nudge, and nobody reads them. A
    scheduled task's first message starts "<scheduled-task", but its later ones
    (a background job reporting back) don't, so the hook also reads the
    session's first message from its transcript;
  - not when the message already asks for a harvest or a close-day/close-week,
    which harvest anyway.
When it does speak, Claude checks Fathom for meetings the builder recorded since
their last harvest and says nothing at all if there are none. Only the person who
recorded a meeting is asked, so attendees aren't all asked about the same call.

Fails silent: any error is no output.
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (HOME / ".claude"))
PERSONAL_DIR = CONFIG_DIR / "local-plugins" / "nsls-personal-toolkit"
ENV_FILE = PERSONAL_DIR / ".env"
# One claim file per day, created with O_EXCL: two messages sent at the same moment
# can't both pass a read-then-write check, so exactly one of them speaks.
# Each version that changed who may take the nudge gets its own name ("asked" when it
# moved to the typed message, "typed" when background-job reports stopped counting),
# because a session left open keeps running the copy it started with: on 8 Nov such
# sessions took the "asked" claim within a minute of it being cleared, every time.
# The cleanup removes other days' claims of every name and leaves today's alone, so an
# older copy that has already spoken today stays quiet. Once this copy speaks it also
# writes today's claim under the older names: an older copy then sees the day as taken,
# instead of speaking again and deleting this claim in its own cleanup.
CLAIM_GLOB = ".nsls-harvest-nudge-*"
CLAIM_PREFIX = ".nsls-harvest-nudge-typed-"
OLDER_CLAIM_PREFIXES = (".nsls-harvest-nudge-", ".nsls-harvest-nudge-asked-")
LOOKBACK_DAYS = 7  # first run, or no harvest log yet
# Sessions a person is sitting at. Everything else (print mode `-p` and the SDKs are
# sdk-*, Cowork's local agent, remote and Slack runs, MCP) stays silent: a nudge there
# is chatter nobody reads. Unset means an older CLI, which is interactive.
INTERACTIVE = {"", "cli", "claude-desktop", "claude-vscode", "claude-jetbrains"}
# Messages the app sends by itself: a scheduled task's opening prompt, and a
# background job reporting back, which also arrives as a message.
NOT_TYPED = ("<scheduled-task", "<task-notification")
TRANSCRIPT_SCAN_LINES = 200  # the first message is near the top; don't read a long session
# A message that will harvest anyway: no point offering it alongside.
HARVESTING = re.compile(r"harvest|close[ -]?day|close[ -]?week", re.I)


def read_env(key):
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def harvest_switch(vault):
    """The `kb_harvest:` value from the first frontmatter block, as close-day reads it."""
    try:
        lines = (vault / "50-reference" / "builder-profile.md").read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    if not lines or lines[0].rstrip("\r") != "---":
        return ""
    for line in lines[1:]:
        line = line.rstrip("\r")
        if line == "---":
            break
        if line.startswith("kb_harvest:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'").lower()
    return ""


def last_harvest_date(vault):
    """Date of the newest row in the harvest log (Step 7b writes one per run)."""
    try:
        rows = (vault / ".harvest-log.jsonl").read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for row in reversed(rows):
        try:
            return datetime.date.fromisoformat(json.loads(row)["ts"][:10])
        except Exception:
            continue
    return None


def read_payload():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def began_as_scheduled_task(transcript):
    """True when the session's first message was a scheduled task's prompt.

    Its later messages don't say so: on 8 Nov 2026 a background job reporting back
    inside the git health check took the day's nudge. No transcript yet (a new
    session's first message) means no: that message speaks for itself.
    """
    try:
        with open(transcript, encoding="utf-8") as f:
            for n, line in enumerate(f):
                if n >= TRANSCRIPT_SCAN_LINES:
                    break
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if not isinstance(row, dict) or row.get("type") != "user" or row.get("isMeta"):
                    continue
                content = (row.get("message") or {}).get("content")
                if isinstance(content, list):
                    content = "".join(b.get("text", "") for b in content if isinstance(b, dict))
                return str(content or "").lstrip().startswith(NOT_TYPED[0])
    except Exception:
        pass
    return False


def main():
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT", "") not in INTERACTIVE:
        return
    today = datetime.date.today()
    claim = CONFIG_DIR / f"{CLAIM_PREFIX}{today.isoformat()}"
    if claim.exists():
        return  # this runs on every message; the usual answer is the cheapest one
    payload = read_payload()
    prompt = str(payload.get("prompt") or payload.get("user_prompt") or "").lstrip()
    if not prompt or prompt.startswith(NOT_TYPED) or HARVESTING.search(prompt):
        return  # nobody at the keyboard, or it harvests anyway: leave the day's nudge unclaimed
    if payload.get("transcript_path") and began_as_scheduled_task(payload["transcript_path"]):
        return
    if not (PERSONAL_DIR / "skills" / "harvest-meeting" / "SKILL.md").exists():
        return
    vault_raw = read_env("OBSIDIAN_VAULT_PATH")
    if not vault_raw:
        return
    vault = Path(os.path.expanduser(vault_raw))
    if harvest_switch(vault) == "off":
        return
    last = last_harvest_date(vault)
    if last is not None and last >= today:
        return
    since = last or (today - datetime.timedelta(days=LOOKBACK_DAYS))
    try:
        fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except Exception:
        return  # already claimed today, or can't record the claim: stay quiet rather than repeat
    for prefix in OLDER_CLAIM_PREFIXES:
        try:
            os.close(os.open(CONFIG_DIR / f"{prefix}{today.isoformat()}", os.O_CREAT | os.O_WRONLY, 0o600))
        except Exception:
            pass
    for old in CONFIG_DIR.glob(CLAIM_GLOB):
        if today.isoformat() not in old.name:
            try:
                old.unlink()
            except Exception:
                pass
    print(
        "[Knowledge base harvest check — do this quietly, once]\n"
        f"Using the Fathom connector, list meetings this user recorded since {since.isoformat()}. "
        "If there are none, or no Fathom connector is available, say nothing about this at all. "
        "If there are some, answer this message as normal, then add one plain line: "
        f"'<N> of your meetings since {since:%b} {since.day} aren't in the knowledge base yet. "
        "Say \"harvest my meetings\" to review them.' "
        "Do not start a harvest unless they ask."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
