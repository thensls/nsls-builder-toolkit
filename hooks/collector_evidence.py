#!/usr/bin/env python3
"""Is the NSLS usage collector reporting from this machine?

The collector writes `<CLAUDE_CONFIG_DIR or ~/.claude>/.nsls-collector/reported.json`
containing exactly `{machine_id, at, version}` (`at` in ISO-8601 UTC), and only
after a run in which every upload succeeded and the kill switch was off. While
that file is fresh, the collector already reports this machine's daily session
and skill use, so:

  - session_ping() in session-start.py adds `"collector_backed": true`, and the
    tracker skips ONLY the daily-session credit (PR credit, installs, stages
    and announcements still run);
  - skill-event.sh / skill-event.ps1 exit without posting.

A collector that dies, fails or is paused stops refreshing the file, and within
7 days the hooks take back over on their own. Fresh means all of:

  - the file is at most MAX_BYTES and parses as a JSON object;
  - `machine_id` is a non-empty string;
  - `at` is ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SS[.fff](Z|+00:00)`), no more than
    7 days old and no more than 1 day in the future (clock skew, not a forgery
    that never expires).

The file is untrusted input: anything unexpected means "not fresh", never an
exception. skill-event.sh and collector_evidence.ps1 implement the same rules;
hooks/tests/test_collector_evidence.py runs the bash copy against every case.

Deliberately standalone: stdlib only, no dependency on the plugin beacons.
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_BYTES = 4096
FRESH_FOR = timedelta(days=7)
FUTURE_SLACK = timedelta(days=1)

_AT = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.[0-9]+)?(?:Z|\+00:00)"
)


def evidence_path(config_dir=None):
    if config_dir is None:
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")
    return Path(config_dir) / ".nsls-collector" / "reported.json"


def _parse_at(value):
    if not isinstance(value, str):
        return None
    m = _AT.fullmatch(value)
    if not m:
        return None
    y, mo, d, h, mi, s = (int(g) for g in m.groups())
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)


def fresh(config_dir=None, now=None):
    """True only when the collector evidence file is present and fresh."""
    try:
        path = evidence_path(config_dir)
        if path.stat().st_size > MAX_BYTES:
            return False
        with open(path, "rb") as f:
            raw = f.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            return False
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return False
        machine_id = data.get("machine_id")
        if not isinstance(machine_id, str) or not machine_id:
            return False
        at = _parse_at(data.get("at"))
        if at is None:
            return False
        now = now or datetime.now(timezone.utc)
        age = now - at
        return -FUTURE_SLACK <= age <= FRESH_FOR
    except Exception:
        return False


if __name__ == "__main__":
    print("fresh" if fresh() else "not fresh")
