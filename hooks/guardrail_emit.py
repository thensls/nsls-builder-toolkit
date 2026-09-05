#!/usr/bin/env python3
"""
The one place a guardrail event is turned into a tracker row.

WHY THIS MODULE EXISTS

    Until now `guardrail_blocked` was the only guardrail event anything ever
    sent, because the only emitter lived inside guardrail-gate.py's block()
    path. The other seven labels existed in Signal's `GUARDRAIL_EVENT_LABELS`,
    in register-automation/SKILL.md and in a docstring -- and nothing produced
    them. Three of the four tiles on Signal's guardrail page could therefore
    never move, and hard blocks are rare by design, so the honest reading of
    that dashboard was "permanently near-zero" rather than "nothing is
    happening".

    The soft events are the ones that carry the story. A hard block is the
    system failing to persuade someone; a registration, a reviewer being
    brought in, a build moving off a personal repo, a nudge being declined --
    those are the ordinary outcomes, and they are most of what the guardrails
    actually do. Leaving them unwired meant the page could only ever show the
    rare bad news.

    Both emitters (the PreToolUse gate, and guardrail-event.py for the
    conversational ones) come through here so the payload contract with
    POST /guardrail-event exists once. It was already duplicated once in a
    docstring that had drifted out of date.

THE PAYLOAD CONTRACT

    {"builder_email": str, "event_type": str, "description": str,
     "automation_name": str, "repo_url": str}

    lands in Airtable's Events table as Event Type / Description / Builder /
    Automation. `Event Type` is free text, so no Airtable schema change is
    needed; the proxy enforces a `guardrail_` prefix.

    `repo_url` exists because `automation_name` is a directory name
    ("mex-tools") while Airtable's Name is human-entered ("MEx Tools"), so name
    matching alone leaves most events with no build attached -- and an event
    trail that cannot say which build tripped the gate is most of the value
    gone. The Automations table already has a GitHub Repo URL field, which is
    an exact key rather than a guess.

WHY THE LABEL SET IS CLOSED

    The proxy only checks the `guardrail_` prefix. Signal checks the exact
    string: `isGuardrailLabel` drops anything not in its list, so an invented
    label like `guardrail_noticed` writes a real Airtable row that the
    dashboard silently ignores -- the worst outcome available, because it looks
    like reporting worked. LABELS below must stay in step with
    GUARDRAIL_EVENT_LABELS in Signal's lib/guardrails.ts.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TRACKER_URL = os.environ.get(
    "NSLS_TRACKER_URL", "https://web-production-6281e.up.railway.app"
)

# Must match GUARDRAIL_EVENT_LABELS in Signal's lib/guardrails.ts. Values are
# what each one means at the moment it is emitted -- the distinctions matter
# because Signal derives the tiles from combinations (a build with `proceeded`
# and no `registered` is "declined"; `blocked` without `authorized` is "still
# stopped").
LABELS = {
    "guardrail_flagged": "Claude raised a guardrail conversationally",
    "guardrail_registered": "the build was registered in the tracker",
    "guardrail_mentor": "a reviewer or mentor was brought in",
    "guardrail_migrated": "the build moved to shared infrastructure",
    "guardrail_proceeded": "the builder declined a soft guardrail and continued",
    "guardrail_blocked": "a hard gate denied the call",
    "guardrail_authorized": "the authorization route was taken",
    "guardrail_disputed": "the builder says a gate misfired",
}

# Measured against the live proxy on 2026-08-23, five sequential POSTs to
# /guardrail-event: 1.31s, 1.47s, 1.48s, 1.51s, 1.93s. The old value here was
# 1.5s -- sitting exactly on the median.
#
# What that actually did is worth being precise about, because the obvious
# reading is wrong. It did NOT lose the events: eight labels fired with the 1.5s
# ceiling reported six client-side timeouts, and all eight rows were in Airtable
# afterwards. The server finishes the write and answers 200; the client has
# already hung up. (Railway logs the same shape for /session-ping -- 499 "client
# has closed the request", server 200, row recorded.)
#
# The damage is subtler than loss and mostly downstream:
#   * the caller cannot tell a delivered event from a dropped one, so nothing
#     built on the return value can be trusted;
#   * a retry on that false failure writes a SECOND row -- the duplicate pairs
#     in Airtable from 2026-08-23 12:40 and 13:34 are exactly this;
#   * the gate spent 1.5s of its 10s budget waiting for an answer it discards.
#
# The lookup-plus-create is inherently ~1.5s, so the fix is not a bigger number
# picked by feel. Anything on a hook budget hands the POST to a detached child
# (emit_detached) and stops waiting; anything with time to spare waits long
# enough that a slow day doesn't turn a delivered event into a reported failure.
EMIT_TIMEOUT = 10
GIT_TIMEOUT = 2

# Repeat suppression. Claude may mention the same guardrail more than once in a
# session, and each mention would otherwise be its own Airtable row. The tiles
# are boolean per build so duplicates barely move them, but the activity list
# is read by a human and a page of the same line eight times is a page nobody
# reads. One row per build per label per day.
SEEN_FILE = Path.home() / ".claude" / ".nsls-guardrail-emitted.json"
SEEN_MAX = 400


def _git(args, cwd=None):
    try:
        out = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True,
            timeout=GIT_TIMEOUT,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def builder_email():
    """Same precedence as session-start.py, skill-event.sh and guardrail-gate.py."""
    try:
        cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
        env_file = cfg / "local-plugins" / "nsls-personal-toolkit" / ".env"
        if env_file.is_file():
            for line in env_file.read_text(errors="ignore").splitlines():
                if line.startswith("BUILDER_EMAIL="):
                    return line.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return _git(["config", "user.email"])


# https://<token>@github.com/org/repo.git is a perfectly ordinary way to have a
# remote configured, and this value is POSTed to the tracker and stored in
# Airtable in cleartext. Sending it verbatim turns an event trail into
# credential exfiltration, so userinfo comes off before the URL leaves.
_USERINFO_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)[^/@]*@")


def origin_url(cwd=None):
    """The origin remote with any embedded credentials stripped."""
    return _USERINFO_RE.sub(r"\1", _git(["remote", "get-url", "origin"], cwd=cwd))


def normalize(label: str) -> str:
    """Accept `mentor` as readily as `guardrail_mentor`.

    The CLI is typed by a model mid-conversation, and requiring the prefix buys
    nothing -- getting it wrong would just drop the event.
    """
    # str() rather than assuming a string: this module promises never to raise,
    # and it is called from a hook path where the alternative to a junk label is
    # a traceback in the middle of somebody's build.
    label = str(label or "").strip().lower().replace("-", "_")
    if label and not label.startswith("guardrail_"):
        label = "guardrail_" + label
    return label


def build_key(cwd=None):
    """Same identity guardrail-memory.py uses: remote slug, else repo root."""
    root = _git(["rev-parse", "--show-toplevel"], cwd=cwd)
    if not root:
        return os.path.abspath(cwd or os.getcwd())
    remote = origin_url(cwd=root)
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", remote) if remote else None
    return m.group(1).lower() if m else root


def _load_seen():
    try:
        data = json.loads(SEEN_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _seen_today(key, label):
    """Has this build already reported this label today?

    Read-only on purpose. The marker is written only after the POST succeeds
    (see _mark_seen) -- an earlier version recorded the attempt up front, so a
    tracker timeout suppressed every retry for the rest of the day and the
    event was lost outright rather than merely delayed.
    """
    return _load_seen().get(f"{key}|{label}") == _today()


def _mark_seen(key, label):
    """Remember a delivered event. Never raises; a lost marker costs a
    duplicate row, which is the harmless direction."""
    data = _load_seen()
    data[f"{key}|{label}"] = _today()
    if len(data) > SEEN_MAX:
        for stale in sorted(data, key=lambda k: data.get(k) or "")[: len(data) - SEEN_MAX]:
            data.pop(stale, None)
    try:
        SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SEEN_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True))
        tmp.replace(SEEN_FILE)
    except Exception:
        pass


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def emit_detached(event_type: str, description: str, automation: str = "",
                  dedupe: bool = True, variant: str = ""):
    """Hand the POST to a child process and return immediately.

    For callers on a budget -- the PreToolUse gate has 10s total for a repo
    lookup, a tracker lookup and this. Waiting ~1.5s for a report it does not
    read is the wrong trade twice over: it eats a sixth of the budget, and the
    timeout tight enough to protect the budget is what was losing the events.

    Detached with start_new_session so the harness reaping the hook's process
    group does not take the report with it. stdout goes to /dev/null because
    the gate's own stdout is the JSON permission decision the harness parses --
    one stray line there and the block itself is lost.

    Never raises. If the spawn fails there is nothing sensible left to try.
    """
    try:
        cli = Path(__file__).resolve().parent / "guardrail-event.py"
        args = [sys.executable, str(cli), event_type, description or ""]
        if automation:
            args += ["--automation", automation]
        if variant:
            args += ["--variant", variant]
        if not dedupe:
            args.append("--no-dedupe")
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


def emit(event_type: str, description: str, automation: str = "", cwd=None,
         dedupe: bool = True, variant: str = ""):
    """Fire-and-forget guardrail event. Never raises, never affects a decision.

    Returns a short status string for the CLI to report; callers on a hook path
    ignore it. An unknown label is refused rather than sent, because the proxy
    would accept it and Signal would drop it -- see the module docstring.
    """
    label = normalize(event_type)
    if label not in LABELS:
        return f"unknown label {label!r}"
    email = builder_email()
    if not email:
        return "no builder email configured"
    # `variant` splits the dedupe slot so genuinely different events sharing a
    # label stay distinct -- declining registration and declining a design doc
    # are both `guardrail_proceeded`, and collapsing them would leave the page
    # saying a nudge was declined without saying which.
    key = build_key(cwd) + (f"#{variant}" if variant else "")
    if dedupe and _seen_today(key, label):
        return f"{label} already recorded for this build today"
    try:
        import urllib.request

        body = json.dumps({
            "builder_email": email,
            "event_type": label,
            "description": str(description or "")[:500],
            "automation_name": automation or "",
            "repo_url": origin_url(cwd=cwd) or "",
        }).encode()
        req = urllib.request.Request(
            f"{TRACKER_URL}/guardrail-event",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=EMIT_TIMEOUT).read()
        _mark_seen(key, label)
        return f"recorded {label}"
    except Exception as e:
        # Reporting is never worth failing or delaying a decision over. The
        # tracker being slow must not be something a builder ever notices.
        return f"could not reach the tracker ({type(e).__name__})"
