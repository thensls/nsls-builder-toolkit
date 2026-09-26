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

  - the path is a regular file (a FIFO or device must never block a hook) of
    at most MAX_BYTES;
  - the whole document is one flat JSON object with EXACTLY the three keys
    machine_id, at and version, each once, in any order, each a plain string
    of printable ASCII with no escapes (anything else - nesting, duplicates,
    extra or missing keys, trailing commas - is ambiguous and fails closed);
  - `machine_id` is non-empty;
  - `at` is a real UTC calendar time `YYYY-MM-DDTHH:MM:SS[.fff](Z|+00:00)`
    (no Feb 30, no hour 24), no more than 7 days old and no more than 1 day
    in the future (clock skew, not a forgery that never expires).

The file is untrusted input: anything unexpected means "not fresh", never an
exception. skill-event.sh and collector_evidence.ps1 implement the same
grammar with the same regex; hooks/tests/test_collector_evidence.py runs the
Python and bash copies against every case, and the Windows smoke test runs
the PowerShell copy.

Deliberately standalone: stdlib only, no dependency on the plugin beacons.
"""

import os
import re
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

MAX_BYTES = 4096
FRESH_FOR = timedelta(days=7)
FUTURE_SLACK = timedelta(days=1)

# One flat object of exactly three "key": "value" members. Strings are
# printable ASCII minus `"` and `\`, so no escapes can hide a key or a value.
_WS = r"[ \t\r\n]*"
_STR = r'"([\x20\x21\x23-\x5b\x5d-\x7e]*)"'
_MEMBER = _WS + _STR + _WS + ":" + _WS + _STR + _WS
_DOC = re.compile(r"\{" + _MEMBER + "," + _MEMBER + "," + _MEMBER + r"\}")
_KEYS = ["at", "machine_id", "version"]

_AT = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.[0-9]+)?(?:Z|\+00:00)"
)


def evidence_path(config_dir=None):
    if config_dir is None:
        config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")
    return Path(config_dir) / ".nsls-collector" / "reported.json"


def _parse_at(value):
    # Fractional seconds are truncated. That moves `at` earlier, so a file can
    # only look OLDER than it is: the 7-day window closes early, never late.
    # The bash and PowerShell copies truncate the same way, so all three agree.
    if not isinstance(value, str):
        return None
    m = _AT.fullmatch(value)
    if not m:
        return None
    y, mo, d, h, mi, s = (int(g) for g in m.groups())
    return datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc)


def _read_regular(path):
    """Bytes of `path` if it is a small regular file, else None. Never blocks:
    the type is checked before opening and again on the open descriptor, and
    O_NONBLOCK covers a FIFO swapped in between the two."""
    st = os.stat(path)
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
        return None
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return None
        raw = os.read(fd, MAX_BYTES + 1)
    finally:
        os.close(fd)
    return raw if len(raw) <= MAX_BYTES else None


def fresh(config_dir=None, now=None):
    """True only when the collector evidence file is present and fresh."""
    try:
        raw = _read_regular(evidence_path(config_dir))
        if raw is None:
            return False
        m = _DOC.fullmatch(raw.decode("ascii").strip(" \t\r\n"))
        if not m:
            return False
        g = m.groups()
        fields = {g[0]: g[1], g[2]: g[3], g[4]: g[5]}
        if sorted([g[0], g[2], g[4]]) != _KEYS:
            return False
        if not fields["machine_id"]:
            return False
        at = _parse_at(fields["at"])
        if at is None:
            return False
        now = now or datetime.now(timezone.utc)
        age = now - at
        return -FUTURE_SLACK <= age <= FRESH_FOR
    except Exception:
        return False


if __name__ == "__main__":
    print("fresh" if fresh() else "not fresh")
