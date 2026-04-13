#!/usr/bin/env python3
"""
session-start.py — Cross-platform SessionStart hook for the NSLS Builder Toolkit.

Runs on every Claude Code session start. Does three things:
1. git pull the toolkit to get latest updates
2. Sync skill pointers from the plugin to ~/.claude/skills/
3. Ping the automation tracker for points, PR credits, and announcements

Must be fast and fail silently. Works on Mac, Linux, and Windows.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

HOME = Path.home()
PLUGIN_DIR = HOME / ".claude" / "local-plugins" / "nsls-builder-toolkit"
SKILLS_DIR = HOME / ".claude" / "skills"
ENV_FILE = HOME / ".claude" / "local-plugins" / "nsls-personal-toolkit" / ".env"
PROXY_URL = "https://web-production-6281e.up.railway.app"
MARKER = "local-plugins/nsls-builder-toolkit"


def git_pull():
    """Pull latest toolkit changes."""
    try:
        subprocess.run(
            ["git", "-C", str(PLUGIN_DIR), "pull", "origin", "main", "--quiet"],
            capture_output=True, timeout=10
        )
    except Exception:
        pass


def sync_pointers():
    """Sync skill pointers from plugin to ~/.claude/skills/."""
    skills_src = PLUGIN_DIR / "skills"
    if not skills_src.is_dir():
        return

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    created = 0

    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill = skill_dir.name
        src = skill_dir / "SKILL.md"
        if not src.exists():
            continue

        dest = SKILLS_DIR / skill
        dest_skill = dest / "SKILL.md"

        # Skip if user has a custom (non-pointer) skill
        if dest.is_dir() and dest_skill.exists():
            try:
                if MARKER not in dest_skill.read_text():
                    continue
            except Exception:
                continue

        # Extract name from frontmatter
        try:
            content = src.read_text()
        except Exception:
            continue

        name_match = re.search(r"^name:\s*(.+)", content, re.MULTILINE)
        if not name_match:
            continue
        name = name_match.group(1).strip()

        # Extract description
        desc = f"NSLS Builder Toolkit skill: {skill}"
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            ml_match = re.search(r"description:\s*>-?\s*\n((?:\s+.+\n)*)", fm)
            if ml_match:
                desc = " ".join(l.strip() for l in ml_match.group(1).strip().split("\n"))
            else:
                sl_match = re.search(r"description:\s*(.+)", fm, re.MULTILINE)
                if sl_match:
                    desc = sl_match.group(1).strip()

        dest.mkdir(parents=True, exist_ok=True)
        dest_skill.write_text(
            f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n"
            f"Read and follow the full skill at "
            f"`~/.claude/local-plugins/nsls-builder-toolkit/skills/{skill}/SKILL.md`.\n"
        )
        created += 1

    if created > 0:
        print(f"{created} skill pointers synced", file=sys.stderr)


def read_env(key):
    """Read a value from the personal toolkit .env file."""
    if not ENV_FILE.exists():
        return ""
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def session_ping():
    """Ping the automation tracker for points, PR credits, and announcements."""
    email = read_env("BUILDER_EMAIL")
    if not email:
        try:
            result = subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True, text=True, timeout=5
            )
            email = result.stdout.strip()
        except Exception:
            pass
    if not email:
        return

    github = read_env("GITHUB_USERNAME")

    toolkit = "personal"
    if PLUGIN_DIR.exists():
        toolkit = "both"

    platform_map = {"darwin": "mac", "win32": "windows", "linux": "linux"}
    platform = platform_map.get(sys.platform, sys.platform)

    payload = json.dumps({
        "builder_email": email,
        "toolkit": toolkit,
        "github_username": github,
        "platform": platform,
    }).encode()

    try:
        req = urllib.request.Request(
            f"{PROXY_URL}/session-ping",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return

    output = []

    # PR credits
    for pr in data.get("new_pr_credits", []):
        repo = pr.get("repo", "?")
        pr_num = pr.get("pr", "?")
        output.append(f"Your PR #{pr_num} to {repo} was merged.")

    # Stage advancement
    adv = data.get("stage_advanced")
    if adv:
        output.append(f"You advanced to {adv.get('to', '?')} on the builder path.")

    # Announcements
    for ann in data.get("announcements", []):
        title = ann.get("title", "")
        body = ann.get("body", "")
        output.append(f"{title}: {body}")
        # Dismiss
        ann_id = ann.get("id", "")
        if ann_id:
            try:
                dismiss_payload = json.dumps({
                    "announcement_id": ann_id,
                    "builder_email": email,
                }).encode()
                dismiss_req = urllib.request.Request(
                    f"{PROXY_URL}/dismiss-announcement",
                    data=dismiss_payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(dismiss_req, timeout=5)
            except Exception:
                pass

    if output:
        print("\n".join(output))


def main():
    git_pull()
    sync_pointers()
    session_ping()


if __name__ == "__main__":
    main()
