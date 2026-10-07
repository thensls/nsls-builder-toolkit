#!/usr/bin/env python3
"""List the Claude Code sessions you worked in during a date window.

Reads Claude Code's own transcript files on this computer (read-only) and prints
one compact JSON record per session: its title, folder, the days it was active,
how many times you spoke, a few of your asks, and Claude's last reply. Nothing is
sent anywhere. Works on Mac, Windows and Linux, in the desktop app or terminal.

Usage:
    python3 sweep_sessions.py --start 2026-09-21 --end 2026-09-25
"""
import argparse
import glob
import json
import os
from datetime import date, datetime
from pathlib import Path

NOISE = (
    "<command-", "<local-command", "<system-reminder", "<task-notification",
    "Caveat:", "Base directory for this skill", "[Request interrupted",
    "This session is being continued", "<user-prompt-submit-hook",
    "Continue from where you left off",
)


def config_dirs():
    found = []
    env = os.environ.get("CLAUDE_CONFIG_DIR")
    for d in ([Path(env).expanduser()] if env else []) + [Path.home() / ".claude"]:
        if (d / "projects").is_dir() and d not in found:
            found.append(d)
    return found


def local_day(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date()
    except Exception:
        return None


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def clip(text, n):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def read_session(path, start, end):
    title, cwd, last_reply = "", "", ""
    asks, days, scheduled = [], set(), False
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return None
    with fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "custom-title" and row.get("customTitle"):
                title = row["customTitle"]
            if row.get("isSidechain") or row.get("type") not in ("user", "assistant"):
                continue
            text = text_of((row.get("message") or {}).get("content")).strip()
            if row["type"] == "user" and text.startswith("<scheduled-task"):
                scheduled = True  # a routine the person set up, not typed work
                continue
            day = local_day(row.get("timestamp", ""))
            if not day or day < start or day > end:
                continue
            cwd = cwd or row.get("cwd", "")
            if not text:
                continue
            if row["type"] == "user" and not text.startswith(NOISE):
                asks.append(text)
                days.add(day)
            elif row["type"] == "assistant":
                last_reply = text
    if not asks:
        return None
    picks = asks if len(asks) <= 3 else [asks[0], asks[len(asks) // 2], asks[-1]]
    return {
        "title": title or clip(asks[0], 60),
        "folder": cwd,
        "active_days": sorted(d.isoformat() for d in days),
        "your_messages": len(asks),
        "started_by_schedule": scheduled,
        "asks": [clip(a, 200) for a in picks],
        "last_reply": clip(last_reply, 500),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True, help="YYYY-MM-DD, inclusive")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD, inclusive")
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)

    sessions, scanned = [], 0
    for cfg in config_dirs():
        for f in glob.glob(str(cfg / "projects" / "*" / "*.jsonl")):
            try:
                if date.fromtimestamp(os.path.getmtime(f)) < start:
                    continue
            except OSError:
                continue
            scanned += 1
            rec = read_session(f, start, end)
            if rec:
                sessions.append(rec)
    sessions.sort(key=lambda r: -r["your_messages"])
    print(json.dumps({
        "window": {"start": args.start, "end": args.end},
        "files_checked": scanned,
        "sessions_found": len(sessions),
        "sessions": sessions[: args.limit],
    }, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
