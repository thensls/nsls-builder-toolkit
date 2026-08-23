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

Also holds the builder's declared Airtable sandbox bases, for the same reason:
the bulk-write gate cannot tell a test base from the real one (same host, only
the base ID differs), so a builder rehearsing a backfill against a copy used to
get blocked for being careful. They say "that's my sandbox" once, and that base
stops stopping them.

Usage:
    guardrail-memory.py record <topic> [--note "..."] [--cwd PATH]
    guardrail-memory.py list [--cwd PATH]
    guardrail-memory.py trust-base <appXXXXXXXXXXXXXX>
    guardrail-memory.py list-bases

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


def report_decline(topic, note, cwd):
    """Tell the tracker a soft guardrail was declined. Best-effort, never fatal.

    This is what makes the docstring above true. A decline was always meant to
    be two things: local memory so Claude stops asking, and one org-level row
    so the guardrail page can show that the system asked and the answer was no.
    Only the first half was ever built, which left `guardrail_proceeded` as one
    of the seven labels Signal counts and nothing produced -- so the page could
    show hard blocks and nothing else.

    Declines are not failures and the row is not a black mark. A build that was
    offered a reviewer and said no is a build someone thought about; the reason
    to record it is that a guardrail declined by everyone is a guardrail that is
    wrong, and that only becomes visible if the noes are counted too.
    """
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from guardrail_emit import emit

        detail = f" — {note}" if note else ""
        emit(
            "guardrail_proceeded",
            f"declined {topic}{detail}",
            cwd=cwd,
            variant=topic,
        )
    except Exception:
        pass  # the local memory is the part that must not fail


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
    # After saving, so a slow tracker can never cost the builder the local
    # memory -- being asked again is the failure this script exists to prevent.
    report_decline(topic, note, cwd)


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


# Same override the gate honours, so tests and the writer agree on one path.
TEST_BASES_FILE = Path(
    os.environ.get("NSLS_AIRTABLE_TEST_BASES_FILE")
    or (Path.home() / ".claude" / ".nsls-airtable-test-bases")
)

# Airtable base IDs are "app" + exactly 14 alphanumerics. Validated rather than
# trusted: this file decides what the bulk-write gate lets through, so a typo
# or a pasted URL fragment must not silently become an allowlist entry.
BASE_ID_RE = re.compile(r"^app[A-Za-z0-9]{14}$")


def trust_base(base_id):
    if not BASE_ID_RE.match(base_id or ""):
        print(f"Not an Airtable base ID: {base_id!r} (expected app + 14 chars)")
        return
    try:
        existing = {
            ln.strip() for ln in TEST_BASES_FILE.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        }
    except Exception:
        existing = set()
    if base_id in existing:
        print(f"{base_id} is already trusted as a test base.")
        return
    try:
        TEST_BASES_FILE.parent.mkdir(parents=True, exist_ok=True)
        new = not TEST_BASES_FILE.exists()
        with TEST_BASES_FILE.open("a") as f:
            if new:
                f.write("# Airtable bases this builder has declared as sandboxes.\n"
                        "# The bulk-write guardrail will not stop writes to these.\n")
            f.write(base_id + "\n")
        print(f"{base_id} trusted as a test base — bulk writes to it won't be stopped.")
    except Exception:
        print("Couldn't save that — the guardrail will keep asking.")


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
    elif cmd == "trust-base" and len(args) > 1:
        trust_base(args[1])
    elif cmd == "list-bases":
        try:
            print(TEST_BASES_FILE.read_text().strip())
        except Exception:
            print("No test bases declared.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break a session over a memory file
    sys.exit(0)
