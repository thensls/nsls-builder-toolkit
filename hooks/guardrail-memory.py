#!/usr/bin/env python3
"""
Remembers which guardrails a BUILD has already declined, so Claude stops asking.

Voice rule 6 says take the first no gracefully and remember it per BUILD, not
per session. Round-2 voice testing found that unenforceable: nothing recorded a
soft decline anywhere Claude could read it back, so every new session started
fresh and re-raised guardrails the builder had already refused. Being asked a
third time about the same script is precisely how someone decides the toolkit
is nagware.

Deliberately LOCAL rather than a tracker lookup:

  * The hook's whole budget is ~1.5s; a network round-trip per check spends most
    of it, and the answer is needed before Claude speaks, not after.
  * A decline is about this builder's experience of this build. It is not org
    reporting -- the `guardrail_proceeded` event still goes to the tracker for
    that, separately and asynchronously.
  * It has to work on a plane. A tracker lookup that fails would either block
    (unacceptable) or fall through to asking again (the bug we are fixing).

Keyed by git remote slug where there is one, so the memory survives a re-clone
and follows the build rather than the directory. Falls back to the absolute path
for repos with no remote.

Usage:
    guardrail-memory.py record <topic> [--note "..."] [--cwd PATH]
    guardrail-memory.py list [--cwd PATH]

Any failure prints nothing and exits 0. A broken memory must never be the reason
a builder cannot work.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STORE = Path.home() / ".claude" / ".nsls-guardrail-declines.json"

# Keep the file from growing without bound on a long-lived machine. Well above
# any realistic number of distinct builds one person has on the go.
MAX_BUILDS = 200


def git(args, cwd):
    try:
        out = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, timeout=2
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def build_key(cwd):
    """Stable identifier for 'this build'.

    Remote slug first: a builder who re-clones, or works from two checkouts,
    is still working on the same thing and should not be asked again.
    """
    root = git(["rev-parse", "--show-toplevel"], cwd)
    if not root:
        return None
    remote = git(["remote", "get-url", "origin"], root)
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", remote) if remote else None
    return m.group(1).lower() if m else root


def load():
    try:
        return json.loads(STORE.read_text())
    except Exception:
        return {}


def save(data):
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STORE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
        tmp.replace(STORE)  # atomic: a crash mid-write can't corrupt the store
    except Exception:
        pass


def record(topic, note, cwd):
    key = build_key(cwd)
    if not key:
        return
    data = load()
    entry = data.setdefault(key, {})
    entry[topic] = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "note": (note or "")[:200],
    }
    if len(data) > MAX_BUILDS:
        # Drop whole builds least-recently-touched, never individual declines --
        # a half-remembered build would ask again about some topics and not
        # others, which reads worse than forgetting it entirely.
        def newest(b):
            return max((v.get("at", "") for v in data[b].values()), default="")
        for stale in sorted(data, key=newest)[: len(data) - MAX_BUILDS]:
            data.pop(stale, None)
    save(data)


def describe(cwd):
    """One-line-per-decline summary for session context, or '' if none."""
    key = build_key(cwd)
    if not key:
        return ""
    entry = load().get(key)
    if not entry:
        return ""
    lines = []
    for topic, v in sorted(entry.items()):
        note = f" — {v['note']}" if v.get("note") else ""
        lines.append(f"- {topic} (declined {v.get('at', 'previously')}){note}")
    return (
        "This build has already declined the following. Do NOT raise them again "
        "unless the scope genuinely escalated since:\n" + "\n".join(lines)
    )


def main():
    args = sys.argv[1:]
    if not args:
        return
    cmd = args[0]
    cwd = os.getcwd()
    if "--cwd" in args:
        cwd = args[args.index("--cwd") + 1]

    if cmd == "record" and len(args) > 1:
        note = args[args.index("--note") + 1] if "--note" in args else ""
        record(args[1], note, cwd)
    elif cmd == "list":
        out = describe(cwd)
        if out:
            print(out)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break a session over a memory file
    sys.exit(0)
