#!/usr/bin/env python3
"""harvest-nudge.py — SessionStart: offer knowledge base harvest only when there is something to harvest.

Harvest (the personal toolkit's /harvest-meeting) ran only inside /close-day and
/close-week, so a builder who skipped those never had a meeting reach the KB: the
company KB got no harvest commits from 5 Aug to 2 Nov 2026. This hook covers them.

It speaks to Claude, never to the builder directly. A hook can't reach the Fathom
connector, so the hook decides *whether to look* and Claude does the looking:
  - silent unless the personal toolkit's harvest skill is installed and the
    builder hasn't set `kb_harvest: off` in builder-profile.md;
  - at most once a day (stamp file), and never if a harvest already ran today;
  - never in a headless or SDK session.
When it does speak, Claude checks Fathom for meetings the builder recorded since
their last harvest and says nothing at all if there are none. Only the person who
recorded a meeting is asked, so attendees aren't all asked about the same call.

Fails silent: any error is no output.
"""
import datetime
import json
import os
import sys
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (HOME / ".claude"))
PERSONAL_DIR = CONFIG_DIR / "local-plugins" / "nsls-personal-toolkit"
ENV_FILE = PERSONAL_DIR / ".env"
STAMP = CONFIG_DIR / ".nsls-harvest-nudge"
LOOKBACK_DAYS = 7  # first run, or no harvest log yet


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


def main():
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk"):
        return
    if not (PERSONAL_DIR / "skills" / "harvest-meeting" / "SKILL.md").exists():
        return
    vault_raw = read_env("OBSIDIAN_VAULT_PATH")
    if not vault_raw:
        return
    vault = Path(os.path.expanduser(vault_raw))
    if harvest_switch(vault) == "off":
        return
    today = datetime.date.today()
    try:
        if STAMP.read_text(encoding="utf-8").strip() == today.isoformat():
            return
    except Exception:
        pass
    last = last_harvest_date(vault)
    if last is not None and last >= today:
        return
    since = last or (today - datetime.timedelta(days=LOOKBACK_DAYS))
    try:
        STAMP.write_text(today.isoformat(), encoding="utf-8")
    except Exception:
        return  # can't record the once-a-day stamp: stay quiet rather than repeat
    print(
        "[Knowledge base harvest check — do this quietly, once]\n"
        f"Using the Fathom connector, list meetings this user recorded since {since.isoformat()}. "
        "If there are none, or no Fathom connector is available, say nothing about this at all. "
        "If there are some, answer the user's first message as normal, then add one plain line: "
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
