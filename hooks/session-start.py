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
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

HOME = Path.home()
# Respect CLAUDE_CONFIG_DIR (Claude Code passes it through to hook processes),
# falling back to ~/.claude. Keeps a --test install fully isolated: the test
# copy of this hook operates on the test config dir, never the real one.
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (HOME / ".claude"))
PLUGIN_DIR = CONFIG_DIR / "local-plugins" / "nsls-builder-toolkit"
SKILLS_DIR = CONFIG_DIR / "skills"
ENV_FILE = CONFIG_DIR / "local-plugins" / "nsls-personal-toolkit" / ".env"
PROXY_URL = os.environ.get("NSLS_TRACKER_URL", "https://web-production-6281e.up.railway.app")

# When a session-ping can't be delivered (timeout / network / proxy down), we
# stash the payload here and replay it at the start of the next session so a
# queued announcement or credit isn't lost. Deleted once delivery succeeds.
PING_FAIL_MARKER = PLUGIN_DIR / ".last-ping-failed"
# was 8, then 20 — live measurement (2026-07-03): /session-ping takes ~8s WARM
# (server-side Airtable writes + announcement scan) and 15-27s on Railway cold
# start, so 20 was still marginal. The SessionStart hook budget must stay
# comfortably above this (install.sh sets 90).
PING_TIMEOUT = 35

# Plugins to sync, in precedence order — earlier entries win on name collision.
SYNC_PLUGINS = [
    "nsls-builder-toolkit",
    "nsls-personal-toolkit",
]
MARKERS = tuple(f"local-plugins/{p}" for p in SYNC_PLUGINS)


# A bare block-scalar indicator is not a description. If `description: >-` (or
# `|`) has no indented body, the value is empty — the indicator itself must
# never become the description text.
BLOCK_INDICATORS = (">", ">-", ">+", "|", "|-", "|+")

# One left-to-right pass over a double-quoted scalar's escapes. Single-pass
# matters: chained .replace() calls would decode the output of an earlier
# replacement (\\" would collapse to " and lose its backslash).
_DQ_ESCAPE = re.compile(r"\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})|\\U([0-9a-fA-F]{8})|\\(.)")
_DQ_SIMPLE = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "n": "\n",
              "v": "\v", "f": "\f", "r": "\r", "e": "\x1b",
              # The four named Unicode escapes YAML defines beyond the C set:
              # next-line, non-breaking space, line separator, paragraph
              # separator. Decoded faithfully; the collapse below folds all four
              # to spaces (\x85 via _CONTROL, the rest because str.split treats
              # them as whitespace), which is what a YAML value folded onto a
              # single line should become.
              "N": "\x85", "_": "\xa0", "L": "\u2028", "P": "\u2029"}

# Decoded control characters (NUL, BEL, ESC…) would make the generated pointer's
# frontmatter unparseable, so they're mapped to spaces and folded away by the
# whitespace collapse. \t \n \r are deliberately absent — they're whitespace and
# the collapse already handles them.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _dq_unescape(match):
    for group in (1, 2, 3):
        if match.group(group):
            return chr(int(match.group(group), 16))
    ch = match.group(4)
    # Anything else (\" \\ \/ \space) stands for itself.
    return _DQ_SIMPLE.get(ch, ch)


def unquote_scalar(value):
    """Turn a single-line YAML scalar into the string a YAML parser would give.

    The folded-block branch never sees quotes, but a description written as
    `description: "Brain dump…"` reaches the single-line fallback with its
    delimiters attached, and they end up verbatim in the generated pointer.
    We can't just call a YAML parser here — pyyaml isn't guaranteed on a fresh
    machine, which is why this extraction is hand-rolled in the first place.

    Whitespace is collapsed at the end because the caller embeds the result as
    a single indented line under `description: >-`. A decoded `\\n` left as a
    real newline would break the generated frontmatter, so folding it to a
    space is both safe and what the folded-block branch already does.
    """
    v = value.strip()
    if v in BLOCK_INDICATORS:
        return ""
    quote = v[:1]
    if len(v) >= 2 and v[-1:] == quote and quote in ('"', "'"):
        inner = v[1:-1]
        if quote == '"':
            inner = _DQ_ESCAPE.sub(_dq_unescape, inner)
        else:
            # Single-quoted YAML has exactly one escape: '' is a literal quote.
            inner = inner.replace("''", "'")
        v = inner
    return " ".join(_CONTROL.sub(" ", v).split())


# ff-only pull failures that mean the checkout ITSELF blocks updating (frozen),
# as opposed to being offline or having no upstream (both fine and quiet).
# Real incident: a single local commit froze a builder's toolkit for a month
# with zero signal — every session "synced" and nothing ever changed.
_FREEZE_SIGNS = (
    "fast-forward",            # ff-only refused: local commits diverge from upstream
    "would be overwritten",    # dirty working tree blocks the update
    "unmerged",                # conflicted / unfinished state
    "not concluded",           # "you have not concluded your merge"
)


def _warn_if_frozen(plugin, plugin_dir, err):
    """Announce a self-update blocked by the checkout's own state. stdout of a
    SessionStart hook lands in the model's context, so Claude can tell the
    user and offer the repair — a frozen toolkit must never be silent.
    Network/offline failures stay quiet (a laptop on a plane is not an
    incident)."""
    if not any(s in err for s in _FREEZE_SIGNS):
        return
    print(
        f"WARNING - {plugin} could not self-update: the checkout at {plugin_dir} "
        f"has local commits or edits, so automatic updates are FROZEN and this "
        f"toolkit is going stale. Tell the user at the first natural moment and "
        f"offer the fix: preserve their local changes on a backup branch, then "
        f"fast-forward the checkout to its upstream. (Skills in ~/.claude/skills "
        f"are the right place for personal edits and are unaffected.)"
    )


def _git_out(plugin_dir, *args):
    try:
        r = subprocess.run(
            ["git", "-C", str(plugin_dir), *args],
            capture_output=True, text=True, timeout=3,
            stdin=subprocess.DEVNULL,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _warn_if_stale_by_configuration(plugin, plugin_dir):
    """Catch the freeze that _warn_if_frozen structurally cannot see.

    _warn_if_frozen only speaks when the pull FAILS. Two shapes of frozen
    checkout produce a pull that does not fail, and both went unreported for
    weeks on this machine:

      1. **Tracking a feature branch.** The builder toolkit sat on
         feat/builder-guardrails, whose upstream is that same branch on origin.
         Every session pulled, every pull said "already up to date", and main
         moved five commits ahead. Nothing was wrong with the pull; the pull was
         aimed somewhere that never changes.
      2. **A named branch with no upstream at all.** The personal toolkit sat on
         feat/completion-sweep, nine commits BEHIND main with five of its own. A
         bare pull exits non-zero with "no tracking information", which is not
         in _FREEZE_SIGNS -- deliberately, so a pinned fork stays quiet -- and
         so this said nothing either, forever.

    A detached HEAD stays quiet: that is the deliberate pin the git_pull
    docstring protects, and it is a different git state than a branch with
    nowhere to pull from.

    Costs no network. `git pull` fetches the whole remote by default, so
    origin/main is already current by the time this runs, and everything here is
    a local ref comparison.
    """
    branch = _git_out(plugin_dir, "rev-parse", "--abbrev-ref", "HEAD")
    if not branch or branch == "HEAD":
        return  # detached: pinned on purpose
    behind = _git_out(plugin_dir, "rev-list", "--count", "HEAD..origin/main")
    if not behind.isdigit() or int(behind) == 0:
        return  # nothing on main this checkout is missing
    has_upstream = bool(_git_out(plugin_dir, "rev-parse", "--abbrev-ref",
                                "--symbolic-full-name", "@{u}"))
    why = (f"it is on branch '{branch}', which tracks itself rather than main"
           if has_upstream else
           f"branch '{branch}' has no upstream, so there is nothing to pull from")
    print(
        f"WARNING - {plugin} is {behind} commit(s) behind main and NOT updating: "
        f"{why}. The checkout at {plugin_dir} reports a clean pull every session "
        f"while going stale, which is why this needs saying out loud. Tell the "
        f"user at the first natural moment. The repair depends on what that "
        f"branch is for: if the work on it is finished, merge or land it and put "
        f"the checkout back on main; if it is still in progress, merging "
        f"origin/main into it catches this checkout up without losing it. Do not "
        f"switch branches on the user's behalf — a live plugin checkout is what "
        f"their current session is running."
    )


def git_pull():
    """Pull latest changes for every toolkit in SYNC_PLUGINS.

    Parity fix with the Windows hook: session-start.ps1 has always looped
    @($BuilderDir, $PersonalDir) and pulled both, but this function pulled only
    the builder dir — so on macOS/Linux the personal toolkit was cloned once and
    then frozen at install-time state forever. Fixes shipped upstream (like the
    visual-companion self-heal) never reached those machines. SYNC_PLUGINS
    already names both toolkits for pointer sync; pull the same list.

    Bare `pull --ff-only` — no explicit remote/refspec — follows each
    checkout's configured upstream, the same convention personal-setup's own
    update path uses. Hardcoding `origin main` here would silently fast-forward
    a supported fork checkout (NSLS_PERSONAL_REPO / NSLS_PERSONAL_BRANCH) or a
    deliberately pinned detached HEAD onto a branch it never tracked; with no
    upstream configured, a bare pull just exits nonzero and the checkout is
    left alone. --ff-only matches the .ps1: the `pull origin main` this
    replaces could stop on merge conflicts (leaving a conflicted tree) or, on
    modern git with no reconcile config, refuse divergence outright — neither
    visible here, since the exit status is ignored and output captured, while
    the toolkit quietly never updated again. ff-only refuses cleanly instead
    of half-merging.

    Prompts are disabled (GIT_TERMINAL_PROMPT=0, stdin closed) so a remote
    that wants credentials fails in milliseconds instead of hanging out the
    timeout, and the loop shares one 15s deadline so the worst case — every
    pull wedged — still leaves the 35s replay + 35s live ping inside the 90s
    hook budget install.sh configures.

    A pull refused for checkout-local reasons (divergence, dirty tree) prints
    a warning to stdout — SessionStart stdout reaches the model's context — so
    a frozen toolkit is announced instead of silently stale. Offline failures
    and missing upstreams stay quiet.
    """
    deadline = time.monotonic() + 15
    for plugin in SYNC_PLUGINS:
        plugin_dir = CONFIG_DIR / "local-plugins" / plugin
        if not (plugin_dir / ".git").exists():
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            r = subprocess.run(
                ["git", "-C", str(plugin_dir), "pull", "--ff-only", "--quiet"],
                capture_output=True, text=True, timeout=min(10, remaining),
                stdin=subprocess.DEVNULL,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            if r.returncode != 0:
                _warn_if_frozen(plugin, plugin_dir, (r.stderr or "") + (r.stdout or ""))
            # Runs whether the pull succeeded or not: a clean pull aimed at a
            # branch that never moves is the freeze this catches.
            _warn_if_stale_by_configuration(plugin, plugin_dir)
        except Exception:
            pass


def org_plugin_installed():
    """True once the toolkit is installed as a real Claude Code plugin."""
    try:
        # utf-8-sig: tolerate a UTF-8 BOM (PowerShell-written files carry one).
        registry = json.loads(
            (CONFIG_DIR / "plugins" / "installed_plugins.json").read_text(
                encoding="utf-8-sig"
            )
        )
        return any(
            key.startswith("nsls-builder-toolkit@")
            for key in registry.get("plugins", {})
        )
    except Exception:
        return False


def org_plugin_active():
    """Installed AND not explicitly disabled.

    The distinction matters: a user who disables the plugin must fall back to
    the pointer-stub path (the disabled plugin can't deliver skills), so
    anything that hands responsibility over to the plugin gates on active,
    never on merely installed.
    """
    if not org_plugin_installed():
        return False
    try:
        settings = json.loads(
            (CONFIG_DIR / "settings.json").read_text(encoding="utf-8-sig")
        )
        for key, enabled in settings.get("enabledPlugins", {}).items():
            if key.startswith("nsls-builder-toolkit@") and enabled is False:
                return False
    except Exception:
        pass
    return True


def run_plugin_migration():
    """Run the shim→plugin migration from the just-pulled clone.

    Executed from the clone (not this file's own copy) so migration fixes
    take effect one session after landing on main. On plugin-only machines
    the clone is absent and this is a no-op. Fail-open: a broken migration
    must never break the session — shims keep working and we retry next
    session.

    Bounded: the migration's CLI calls are individually timed out but their
    sum was not, and stage A's worst case (30 + 60 + 60) is nearly double the
    whole 90s SessionStart budget install.sh configures. Overrunning kills the
    hook, which also drops sync_pointers and the session ping — so a slow
    migration would quietly cost the builder pointer updates and credit.

    Budget arithmetic for the 90s hook: git_pull takes up to 15s and the live
    session_ping up to 35s (PING_TIMEOUT), so ~40s is genuinely spare;
    ensure_plugin_fresh claims 20s of it. 25s here leaves headroom for
    sync_pointers and keeps the common path well inside budget. A first
    migration may need more than one session to finish, which is exactly how
    the stages are built — both are idempotent and resume next session.
    """
    script = PLUGIN_DIR / "hooks" / "migrate_to_plugin.py"
    if not script.exists():
        return
    try:
        code = compile(script.read_text(encoding="utf-8"), str(script), "exec")
        exec(code, {
            "__name__": "nsls_migrate",
            "__file__": str(script),
            # Consumed by migrate_to_plugin.py as its cumulative ceiling.
            "_NSLS_MIGRATION_DEADLINE": time.monotonic() + 25,
        })
    except Exception:
        pass


def ensure_plugin_fresh():
    """At most once a day, ask the CLI to sync the installed plugin.

    Plugin installs run from a version-pinned cache that only refreshes via
    `claude plugin update` after a plugin.json version bump — without this,
    a machine that loses the settings-shim git-pull path would silently
    freeze on an old version.
    """
    if not org_plugin_active():
        return
    marker = CONFIG_DIR / ".nsls-plugin-update-check"
    try:
        if marker.exists() and (
            datetime.now(timezone.utc).timestamp() - marker.stat().st_mtime < 86400
        ):
            return
        import shutil as _shutil
        claude = _shutil.which("claude")
        if not claude:
            return
        marker.touch()
        # 20s, not the hook's whole 90s budget — a hung update must leave room
        # for sync_pointers and the session pings behind it. On timeout the
        # marker is already touched, so the next attempt is tomorrow; releases
        # just arrive a day later on that machine.
        subprocess.run(
            [claude, "plugin", "update", "nsls-builder-toolkit@nsls-toolkit"],
            capture_output=True, timeout=20,
        )
    except Exception:
        pass


def sync_pointers():
    """Sync skill pointers from installed plugins to ~/.claude/skills/.

    Iterates plugins in SYNC_PLUGINS precedence order. On name collision,
    earlier plugins win (org skills override personal). Skips skills that
    look user-customized (no managed marker present in the existing pointer).
    """
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    written = set()
    created = 0

    for plugin_name in SYNC_PLUGINS:
        # Once the org toolkit is an ACTIVE plugin, its skills load through
        # the plugin system — stop regenerating its pointer stubs so the
        # stage-B migration cleanup sticks. Gates on active, not installed:
        # a disabled plugin can't deliver skills, so those users keep the
        # stub path. Personal-toolkit pointers keep syncing regardless.
        if plugin_name == "nsls-builder-toolkit" and org_plugin_active():
            continue
        plugin_dir = CONFIG_DIR / "local-plugins" / plugin_name
        skills_src = plugin_dir / "skills"
        if not skills_src.is_dir():
            continue

        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill = skill_dir.name

            # Skill name is interpolated into a bash literal in the generated
            # pointer (see report_cmd below). Reject names with characters
            # that would break the JSON or shell quoting.
            if any(c in skill for c in "'\"\\$`\n\r"):
                print(f"sync: skipping skill with unsafe name: {skill!r}", file=sys.stderr)
                continue

            # Org-wins precedence: skip if a higher-precedence plugin
            # already wrote this skill in the current run.
            if skill in written:
                continue

            src = skill_dir / "SKILL.md"
            if not src.exists():
                continue

            dest = SKILLS_DIR / skill
            dest_skill = dest / "SKILL.md"

            # Skip if the existing file looks user-customized — i.e., no
            # managed marker for any of our plugins is present.
            if dest.is_dir() and dest_skill.exists():
                try:
                    existing = dest_skill.read_text(encoding="utf-8")
                    if not any(m in existing for m in MARKERS):
                        continue
                except Exception:
                    continue

            try:
                content = src.read_text(encoding="utf-8")
            except Exception:
                continue

            name_match = re.search(r"^name:\s*(.+)", content, re.MULTILINE)
            if not name_match:
                continue
            name = name_match.group(1).strip()

            desc = f"{plugin_name} skill: {skill}"
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm_match:
                fm = fm_match.group(1)
                # `*` not `+`: an empty folded block still belongs to the folded
                # branch. With `+` it fell through to the fallback, which then
                # captured the literal `>-` as the description.
                ml_match = re.search(r"description:\s*>-?\s*\n((?:[ \t]+.+\n?)*)", fm)
                if ml_match:
                    extracted = " ".join(l.strip() for l in ml_match.group(1).strip().split("\n"))
                else:
                    sl_match = re.search(r"description:[ \t]*(.+)", fm, re.MULTILINE)
                    extracted = unquote_scalar(sl_match.group(1)) if sl_match else ""
                # Only override the default when we actually recovered text —
                # a blank or `""` description must not produce a blank pointer.
                if extracted.strip():
                    desc = extracted

            dest.mkdir(parents=True, exist_ok=True)
            hook_path = CONFIG_DIR / "local-plugins" / "nsls-builder-toolkit" / "hooks" / "skill-event.sh"
            skill_path = CONFIG_DIR / "local-plugins" / plugin_name / "skills" / skill / "SKILL.md"
            report_cmd = (
                f"echo '{{\"tool_input\":{{\"skill\":\"{skill}\"}}}}' | "
                f"bash {hook_path}"
            )
            dest_skill.write_text(
                f"---\nname: {name}\ndescription: >-\n  {desc}\n---\n\n"
                f"Before reading the skill, run this Bash command exactly once in the "
                f"background (do not wait, do not announce, do not retry on failure) "
                f"to record skill usage:\n\n"
                f"```bash\n{report_cmd}\n```\n\n"
                f"Then read and follow the full skill at "
                f"`{skill_path}`.\n",
                encoding="utf-8",
            )
            written.add(skill)
            created += 1

    if created > 0:
        print(f"{created} skill pointers synced", file=sys.stderr)


def read_env(key):
    """Read a value from the personal toolkit .env file."""
    if not ENV_FILE.exists():
        return ""
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def _http_post_json(url, body, timeout):
    """POST JSON to url and return the parsed JSON response. Raises on failure.

    curl first, urllib as the fallback — not the other way around: python.org
    framework builds ship WITHOUT CA certificates, so every urllib HTTPS call
    on such a Mac fails cert verification and the ping dies silently (this
    cost a builder ~6 weeks of session points, June–Aug 2026, while
    skill-event.sh — which shells out to curl — kept working). curl uses the
    OS trust store, so it works on a stock install.
    """
    payload = json.dumps(body)
    if shutil.which("curl"):
        # curl PRESENT is not curl WORKING. A broken proxy/TLS config, or a curl
        # that can't reach this host while Python can, made every POST fail
        # permanently — the old code raised here, so the urllib fallback below
        # was only ever reached when curl was missing entirely. Treat a curl
        # failure as "try the other transport", and only fail if both lose.
        started = time.monotonic()
        try:
            result = subprocess.run(
                ["curl", "-s", "--fail", "--max-time", str(timeout), "-X", "POST",
                 url, "-H", "Content-Type: application/json",
                 "--data-binary", payload],
                # encoding is explicit: text=True alone decodes with the platform
                # locale, so on Windows with a legacy code page (cp1252) a
                # non-ASCII announcement raises UnicodeDecodeError out of this
                # call. A ping that actually succeeded then counts as failed,
                # the failure marker gets written, and the announcement is lost.
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout + 10,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            # 28 == curl's own operation-timeout. The host is slow or
            # unreachable, so urllib would burn the same wait again for the same
            # answer — and this runs inside a SessionStart hook whose whole
            # budget (90s, install.sh) covers a replayed ping AND a live one.
            # Retrying only NON-timeout failures is what keeps a second
            # transport from doubling the worst case.
            if result.returncode == 28:
                raise RuntimeError("curl exited 28 (timeout)")
        except subprocess.TimeoutExpired:
            raise RuntimeError("curl timed out")
        except (OSError, ValueError):
            pass  # curl unusable or returned unparseable JSON — try urllib
        # Only the remaining slice of this call's budget, for the same reason.
        timeout = max(5, timeout - (time.monotonic() - started))
    req = urllib.request.Request(
        url,
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _post_session_ping(body, timeout=PING_TIMEOUT):
    """POST a session-ping body dict. Returns parsed response, or raises."""
    return _http_post_json(f"{PROXY_URL}/session-ping", body, timeout)


def _discard_marker():
    """Remove the marker entirely."""
    try:
        PING_FAIL_MARKER.unlink()
    except OSError:
        pass


def _write_marker(state):
    """Write the marker atomically: temp file in the same dir, then os.replace.

    Builders open several sessions at once — three inside six seconds is what
    produced the original false alarm — so two SessionStart hooks racing over
    this file is the normal case, not the exotic one. write_text() truncates
    before it writes, which leaves a window where a concurrent reader sees
    empty or half-written JSON and concludes the marker is corrupt. os.replace
    is atomic on POSIX and Windows: a reader sees the old file or the new one,
    never a partial one.
    """
    try:
        PING_FAIL_MARKER.parent.mkdir(parents=True, exist_ok=True)
        tmp = PING_FAIL_MARKER.with_name(PING_FAIL_MARKER.name + f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, PING_FAIL_MARKER)
    except Exception:
        try:
            tmp.unlink()
        except Exception:
            pass


def _retire_ping_payload(drop_today):
    """Retire the retry payload, but keep the failed-day ledger.

    The two have different lifetimes and used to share one unlink(), which is
    how a real point loss went silent. `failed_days` records days whose credit
    never landed ON THAT DAY; `payload` is just the thing waiting to be
    resent. Deleting the file on success threw both away, so intermittent
    failures could never reach the three-day notice: day 1 fails, day 2's
    replay wipes day 1, day 3 starts the count from zero. The docstring in
    note_ping_failure asserted this could not happen — "the day's credit lands
    from whichever ping gets through" — which is true within one day and false
    across two.

    drop_today: a successful delivery means TODAY's credit landed today, so
    today comes off the ledger. It does NOT rescue an earlier day: the payload
    carries no timestamp and the server stamps arrival (see session_ping), so
    replaying Monday's ping on Tuesday credits Tuesday. Monday really did lose
    its point, and it stays on the ledger to say so.

    `attempts` is deliberately dropped: it counts consecutive failures for the
    outage notice, and a delivery means the outage is over.
    """
    try:
        prior = json.loads(PING_FAIL_MARKER.read_text(encoding="utf-8"))
    except Exception:
        prior = None
    if not isinstance(prior, dict):
        _discard_marker()
        return

    raw = prior.get("failed_days")
    days = [d for d in raw if isinstance(d, str)] if isinstance(raw, list) else []
    if drop_today:
        today = datetime.now(timezone.utc).date().isoformat()
        days = [d for d in days if d != today]

    if not days:
        _discard_marker()  # no payload, no lost days: nothing worth a file
        return

    ledger = {"failed_days": days}
    last = prior.get("last_notified_at")
    if isinstance(last, str) and not drop_today:
        # last_notified_at suppresses repeats of an ONGOING condition, so it
        # only survives when the condition is still on: a malformed or
        # undelivered payload. A successful delivery ends the outage, and
        # carrying the timestamp across it would silence a genuine NEW outage
        # for the rest of the 24h — breaking rule 3 of note_ping_failure,
        # "never go quiet while it IS broken." (My first cut kept it here to
        # stop a flapping tracker nagging; that is already handled by
        # attempts >= 2, which a delivery resets, so Branch A needs two fresh
        # consecutive failures before it can speak again.)
        ledger["last_notified_at"] = last
    _write_marker(ledger)


def replay_failed_ping():
    """Replay a previously failed session-ping before the current one.

    Runs at session start, ahead of the live ping. If delivery succeeds (or
    the marker is malformed), the marker is cleared; if it fails again, the
    marker is left in place for the next session to retry. We deliberately do
    not re-surface the replayed response — the live ping right after fetches
    fresh announcements, so processing the stale body here would double up.

    Returns the successfully replayed payload (dict) or None. The caller uses
    it to skip the live ping when the payloads are identical — the endpoint is
    slow (~8s warm), so a redundant back-to-back POST both wastes time and
    risks a pointless timeout that would re-write the marker.
    """
    if not PING_FAIL_MARKER.exists():
        return None
    try:
        saved = json.loads(PING_FAIL_MARKER.read_text(encoding="utf-8"))
    except Exception:
        # Do NOT delete it. Unreadable here is far more likely to be a
        # concurrent SessionStart mid-write than real corruption, and deleting
        # it makes the writer finish into an unlinked inode — the payload is
        # gone and nothing replays it. Leaving it costs nothing: the next
        # note_ping_failure() already treats an unreadable prior as {} and
        # overwrites, so a genuinely corrupt marker cannot get stuck either.
        return None
    if not isinstance(saved, dict):
        return None  # same reasoning: let the next failure overwrite it

    body = saved.get("payload")
    if body is None and saved.get("failed_days"):
        return None  # ledger-only marker — nothing to replay, and the days
        # it holds are the record of credit already lost. Leave it alone.
    if not isinstance(body, dict) or not body:
        # Malformed, per the contract above. Truthiness alone is not shape: a
        # payload left as a string or a list by a crash or a hand-edit used to
        # be POSTed as-is, and the raise that followed was caught, which KEPT
        # the marker — retrying the same broken payload at every session start
        # forever, indistinguishable from "the tracker is still unreachable."
        # Nothing was delivered, so today stays on the ledger.
        _retire_ping_payload(drop_today=False)
        return None

    try:
        _post_session_ping(body)
    except Exception:
        return None  # still unreachable — keep the marker for the next attempt
    _retire_ping_payload(drop_today=True)
    return body


def _http_probe(url, timeout=4, any_response=False):
    """Probe url inside a TOTAL time budget. curl first, urllib with what's left.

    any_response=False — True only on 2xx/3xx: "is this service healthy".
    any_response=True  — True if the host answered AT ALL, error statuses
    included: "is this machine online". api.github.com hands out unauthenticated
    403s freely, and reading a 403 as "no internet" is exactly how a real
    tracker outage could have stayed silent forever — the suppression branch
    below only stays quiet when the control says we are offline.

    Transport order and its reasoning are _http_post_json's: a stock Python can
    carry a CA bundle that trusts nothing, so urllib alone would read a healthy
    host as dead, and curl failing means "try the other transport".

    The budget is TOTAL, not per transport. This runs on a path that may already
    have spent ~70s on a replayed POST plus a live one against a 90s SessionStart
    budget (install.sh), so two full-length probes would run the hook out of room.
    """
    deadline = time.monotonic() + timeout
    if shutil.which("curl"):
        args = ["curl", "-s", "--max-time", str(max(1, int(timeout))),
                "-o", os.devnull, "-w", "%{http_code}", url]
        if not any_response:
            args.insert(1, "--fail")
        try:
            done = subprocess.run(args, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=timeout + 5)
            if any_response:
                code = (done.stdout or "").strip()
                if code and code != "000":
                    return True  # answered, whatever it said
            elif done.returncode == 0:
                return True
        except Exception:
            pass
    left = deadline - time.monotonic()
    if left < 1:
        return False  # no headroom for a second transport; caller must not stall
    try:
        with urllib.request.urlopen(url, timeout=left) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except urllib.error.HTTPError:
        return any_response  # the host answered; the status is a health question
    except Exception:
        return False


def _tracker_unreachable():
    """Is the tracker actually gone, or was that one write just slow?

    A /session-ping timeout is NOT evidence the tracker is unreachable.
    Measured 2026-08-20 across 24h of Railway HTTP logs for the service:
    293 pings, p50 9.0s, p90 22.2s, and 45 of them (15%) ran into the 35s
    client ceiling and were logged 499 "client has closed the request" — while
    the server went on to answer 200 and record the session. The slow part is
    the announcement scan plus the Airtable writes, and concurrent session
    starts queue behind each other, so opening three sessions at once is
    enough to burn three pings inside six seconds.

    GET / on the same host is a static health payload that answers in ~0.2s,
    so it tells the two cases apart.
    """
    return not _http_probe(f"{PROXY_URL}/", timeout=4)


def _internet_up():
    """True if anything outside this machine answers — any status counts.

    Without this, a laptop on a plane trips the "tracker is down" notice: the
    tracker probe fails for the same reason every other request does.
    api.github.com is the control because every builder already depends on
    GitHub reachability for the toolkit to update at all.
    """
    return _http_probe("https://api.github.com/", timeout=3, any_response=True)


def note_ping_failure(body):
    """Stash a failed session-ping, and speak only when it means something.

    Three rules, each of them paid for:

    1. One failure per DAY, not per attempt. The old counter counted attempts,
       so three sessions opened in the same minute read out as "your last 3
       sessions" — which is exactly what fired the false alarm on 2026-08-20
       (three 499s inside six seconds, server recorded all three, no points
       lost, and it still told the builder to raise it in #builders).
    2. Only speak when the builder is actually losing something. A slow write
       is invisible to them: the payload replays at the next session start and
       daily points dedupe per builder per day, so the day's credit lands from
       whichever ping gets through.
    3. Never go quiet while it IS broken. The old `failures == 3` fired once
       and then never again for the life of an outage, which is the
       silent-forever mode the original comment was trying to avoid. Both
       notices below repeat once every 24h for as long as the condition holds.

    Every value read back from the marker is treated as hostile. The file is
    hand-editable, can be left half-written by a crash, and this function runs
    inside session_ping()'s failure handler with nothing above it to catch a
    raise — so a corrupt marker must not be what takes SessionStart down.
    """
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    prior = None
    try:
        prior = json.loads(PING_FAIL_MARKER.read_text(encoding="utf-8"))
    except Exception:
        pass
    if not isinstance(prior, dict):
        prior = {}  # valid JSON is not the same as the shape we wrote

    # A day only counts if it is a real calendar day at or before today, and it
    # is stored canonically. isinstance(str) was not enough on either axis:
    # "x" counted as a failed day (so one failure could trip the three-day
    # notice), and on 3.11+ date.fromisoformat also accepts "20260825", which
    # would survive the set() alongside "2026-08-25" and count the same day
    # twice. Normalising on the way in closes both.
    raw_days = prior.get("failed_days")
    days = []
    if isinstance(raw_days, list):
        for d in raw_days:
            if not isinstance(d, str):
                continue
            try:
                parsed = date.fromisoformat(d)
            except (TypeError, ValueError):
                continue
            if parsed > now.date():
                continue  # clock skew or a hand-edit: a day that has not
                # happened yet cannot have cost anyone their points
            days.append(parsed.isoformat())
    if today not in days:
        days.append(today)
    days = sorted(set(days))[-14:]

    # max(0, ...) because a negative attempts — a hand-edit, or a partial
    # write — is the right type and still poisons the counter: it never
    # reaches 2, so Branch A's outage notice stays silent for the whole
    # outage, which is the exact failure this function exists to prevent.
    try:
        attempts = max(0, int(prior.get("attempts", prior.get("failures", 0)) or 0)) + 1
    except (TypeError, ValueError):
        attempts = 1

    last_notified = prior.get("last_notified_at")
    if not isinstance(last_notified, str):
        last_notified = None

    def spoke_within_a_day():
        if not last_notified:
            return False
        try:
            when = datetime.fromisoformat(last_notified)
        except (TypeError, ValueError):
            return False
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        elapsed = (now - when).total_seconds()
        if elapsed < 0:
            return False  # clock rolled back, or hand-edited: don't let a
            # timestamp from the future mute an outage for longer than a day
        return elapsed < 86400

    def _write(notified_at):
        _write_marker({
            "payload": body,
            "attempted_at": now.isoformat(),
            "attempts": attempts,
            "failed_days": days,
            "last_notified_at": notified_at,
        })

    # Persist FIRST, probe SECOND. SessionStart runs under a wall-clock budget
    # that the replay, the live ping and git_pull() have already eaten into,
    # and the two probes below can spend 8s more of it. If the hook is killed
    # mid-probe, anything not yet written is gone — and the payload is the one
    # value whose loss actually costs the builder a point, because nothing can
    # replay what was never stashed. The notice is a nicety; the payload is
    # the credit. Write the payload where no network call can precede it, and
    # come back for last_notified_at only if we end up speaking.
    _write(last_notified)

    # Both probes cost an HTTP round-trip, and both branches below need them,
    # so evaluate each at most once per call.
    _probed = {}

    def unreachable():
        if "unreachable" not in _probed:
            _probed["unreachable"] = _tracker_unreachable()
        return _probed["unreachable"]

    def online():
        if "online" not in _probed:
            _probed["online"] = _internet_up()
        return _probed["online"]

    notice = None
    if not spoke_within_a_day():
        # Branch A — the host itself is gone. Two attempts, so one DNS hiccup
        # stays quiet, and only when the rest of the internet answers.
        if attempts >= 2 and unreachable() and online():
            notice = (
                "The NSLS automation tracker can't be reached right now, so "
                "your builder points aren't recording. Your sessions are "
                "queued and replay on their own once it's back — nothing for "
                "you to fix. Say \"check the tracker\" if you want it looked "
                "into."
            )
        # Branch B — the host answers but the writes keep timing out. Harmless
        # for a day or two (see rule 2); past three separate days the daily
        # dedupe is no longer covering it and credit really is going missing.
        #
        # The probes are the whole point of this branch, not decoration. "Too
        # slow to record" is a claim about the tracker, and three failed days
        # on a laptop that was offline are not evidence for it — the writes
        # failed for the same reason every other request did. Requiring the
        # tracker to answer its health endpoint RIGHT NOW is what earns the
        # claim: online, host up, and your writes still failed on 3 days.
        # (Checking only _internet_up() would not do it — being online now
        # says nothing about the three days already in the ledger, so an
        # offline stretch would still fire this on the next online session.)
        elif len(days) >= 3 and online() and not unreachable():
            notice = (
                f"The NSLS automation tracker has been too slow to record "
                f"your sessions on {len(days)} separate days, so some builder "
                f"points are probably missing. Say \"check the tracker\" if "
                f"you want it looked into."
            )

    if notice:
        # Second write, only when we actually spoke — the payload above is
        # already safe on disk whatever the probes did.
        _write(now.isoformat())

    if notice:
        print(
            "[NSLS Builder Toolkit — surface the following to the user at the "
            "start of your first reply, then proceed with their request:]\n\n"
            + notice
        )


def _http_probe(url, timeout=4, any_response=False):
    """Probe url inside a TOTAL time budget. curl first, urllib with what's left.

    any_response=False — True only on 2xx/3xx: "is this service healthy".
    any_response=True  — True if the host answered AT ALL, error statuses
    included: "is this machine online". api.github.com hands out unauthenticated
    403s freely, and reading a 403 as "no internet" is exactly how a real
    tracker outage could have stayed silent forever — the suppression branch
    below only stays quiet when the control says we are offline.

    Transport order and its reasoning are _http_post_json's: a stock Python can
    carry a CA bundle that trusts nothing, so urllib alone would read a healthy
    host as dead, and curl failing means "try the other transport".

    The budget is TOTAL, not per transport. This runs on a path that may already
    have spent ~70s on a replayed POST plus a live one against a 90s SessionStart
    budget (install.sh), so two full-length probes would run the hook out of room.
    """
    deadline = time.monotonic() + timeout
    if shutil.which("curl"):
        args = ["curl", "-s", "--max-time", str(max(1, int(timeout))),
                "-o", os.devnull, "-w", "%{http_code}", url]
        if not any_response:
            args.insert(1, "--fail")
        try:
            done = subprocess.run(args, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=timeout + 5)
            if any_response:
                code = (done.stdout or "").strip()
                if code and code != "000":
                    return True  # answered, whatever it said
            elif done.returncode == 0:
                return True
        except Exception:
            pass
    left = deadline - time.monotonic()
    if left < 1:
        return False  # no headroom for a second transport; caller must not stall
    try:
        with urllib.request.urlopen(url, timeout=left) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except urllib.error.HTTPError:
        return any_response  # the host answered; the status is a health question
    except Exception:
        return False


def _tracker_unreachable():
    """Is the tracker actually gone, or was that one write just slow?

    A /session-ping timeout is NOT evidence the tracker is unreachable.
    Measured 2026-08-20 across 24h of Railway HTTP logs for the service:
    293 pings, p50 9.0s, p90 22.2s, and 45 of them (15%) ran into the 35s
    client ceiling and were logged 499 "client has closed the request" — while
    the server went on to answer 200 and record the session. The slow part is
    the announcement scan plus the Airtable writes, and concurrent session
    starts queue behind each other, so opening three sessions at once is
    enough to burn three pings inside six seconds.

    GET / on the same host is a static health payload that answers in ~0.2s,
    so it tells the two cases apart.
    """
    return not _http_probe(f"{PROXY_URL}/", timeout=4)


def _internet_up():
    """True if anything outside this machine answers — any status counts.

    Without this, a laptop on a plane trips the "tracker is down" notice: the
    tracker probe fails for the same reason every other request does.
    api.github.com is the control because every builder already depends on
    GitHub reachability for the toolkit to update at all.
    """
    return _http_probe("https://api.github.com/", timeout=3, any_response=True)


def note_ping_failure(body):
    """Stash a failed session-ping, and speak only when it means something.

    Three rules, each of them paid for:

    1. One failure per DAY, not per attempt. The old counter counted attempts,
       so three sessions opened in the same minute read out as "your last 3
       sessions" — which is exactly what fired the false alarm on 2026-08-20
       (three 499s inside six seconds, server recorded all three, no points
       lost, and it still told the builder to raise it in #builders).
    2. Only speak when the builder is actually losing something. A slow write
       is invisible to them: the payload replays at the next session start and
       daily points dedupe per builder per day, so the day's credit lands from
       whichever ping gets through.
    3. Never go quiet while it IS broken. The old `failures == 3` fired once
       and then never again for the life of an outage, which is the
       silent-forever mode the original comment was trying to avoid. Both
       notices below repeat once every 24h for as long as the condition holds.

    Every value read back from the marker is treated as hostile. The file is
    hand-editable, can be left half-written by a crash, and this function runs
    inside session_ping()'s failure handler with nothing above it to catch a
    raise — so a corrupt marker must not be what takes SessionStart down.
    """
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    prior = None
    try:
        prior = json.loads(PING_FAIL_MARKER.read_text(encoding="utf-8"))
    except Exception:
        pass
    if not isinstance(prior, dict):
        prior = {}  # valid JSON is not the same as the shape we wrote

    def is_day(value):
        """A real YYYY-MM-DD, not merely a string. `["x","y"]` in a hand-edited
        marker used to count toward the three-day threshold and fire the
        missing-points notice after a single real failure."""
        if not isinstance(value, str):
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return False
        return True

    raw_days = prior.get("failed_days")
    days = ([d for d in raw_days if is_day(d)]
            if isinstance(raw_days, list) else [])
    if today not in days:
        days.append(today)
    days = sorted(set(days))[-14:]

    try:
        # Clamped: a negative value in the marker would hold `attempts >= 2`
        # false through every future failure and silence Branch A for good.
        attempts = max(0, int(prior.get("attempts", prior.get("failures", 0)) or 0)) + 1
    except (TypeError, ValueError):
        attempts = 1

    last_notified = prior.get("last_notified_at")
    if not isinstance(last_notified, str):
        last_notified = None

    def spoke_within_a_day():
        if not last_notified:
            return False
        try:
            when = datetime.fromisoformat(last_notified)
        except (TypeError, ValueError):
            return False
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        elapsed = (now - when).total_seconds()
        if elapsed < 0:
            return False  # clock rolled back, or hand-edited: don't let a
            # timestamp from the future mute an outage for longer than a day
        return elapsed < 86400

    notice = None
    # Probing costs a round trip, so only reach for it when a notice is in play.
    if not spoke_within_a_day() and (attempts >= 2 or len(days) >= 3):
        if _tracker_unreachable():
            # Branch A — the host itself is gone. Two attempts, so one DNS
            # hiccup stays quiet, and only when the rest of the internet
            # answers.
            if attempts >= 2 and _internet_up():
                notice = (
                    "The NSLS automation tracker can't be reached right now, "
                    "so your builder points aren't recording. Your sessions "
                    "are queued and replay on their own once it's back — "
                    "nothing for you to fix. Say \"check the tracker\" if you "
                    "want it looked "
                    "into."
                )
        # Branch B — the host ANSWERS but the writes keep timing out. That is
        # the only reading under which "too slow" is honest, which is why this
        # hangs off the reachable branch rather than off falling through: three
        # days offline used to land here and blame the tracker for a flight.
        # Harmless for a day or two (see rule 2); past three separate days the
        # daily dedupe is no longer covering it and credit is going missing.
        elif len(days) >= 3:
            notice = (
                f"The NSLS automation tracker has been too slow to record "
                f"your sessions on {len(days)} separate days, so some builder "
                f"points are probably missing. Say \"check the tracker\" if "
                f"you want it looked into."
            )

    if notice:
        last_notified = now.isoformat()

    try:
        PING_FAIL_MARKER.parent.mkdir(parents=True, exist_ok=True)
        PING_FAIL_MARKER.write_text(
            json.dumps({
                "payload": body,
                "attempted_at": now.isoformat(),
                "attempts": attempts,
                "failed_days": days,
                "last_notified_at": last_notified,
            }),
            encoding="utf-8",
        )
    except Exception:
        pass

    if notice:
        print(
            "[NSLS Builder Toolkit — surface the following to the user at the "
            "start of your first reply, then proceed with their request:]\n\n"
            + notice
        )


def session_ping(replayed=None):
    """Ping the automation tracker for points, PR credits, and announcements.

    replayed: payload dict just delivered by replay_failed_ping(), or None.
    If it matches today's payload, the session is already recorded — skip the
    redundant POST (the payload carries no timestamp; the server stamps
    arrival time, so a successful replay IS today's ping).
    """
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
    if PLUGIN_DIR.exists() or org_plugin_installed():
        toolkit = "both"

    platform_map = {"darwin": "mac", "win32": "windows", "linux": "linux"}
    platform = platform_map.get(sys.platform, sys.platform)

    body = {
        "builder_email": email,
        "toolkit": toolkit,
        "github_username": github,
        "platform": platform,
    }

    if replayed == body:
        return  # this exact payload was just delivered by the replay

    try:
        data = _post_session_ping(body)
    except Exception:
        # Delivery failed (timeout / network / proxy down). Stash the payload
        # so the next session start replays it, and decide separately whether
        # this is worth a word to the builder. Best-effort — never raise.
        note_ping_failure(body)
        return

    # Delivered — retire the queued payload. Today's credit landed today, so
    # today comes off the ledger; earlier days stay, because their credit did
    # not land on their day and no later delivery can give it back.
    _retire_ping_payload(drop_today=True)

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
        # Dismiss (same curl-first transport as the ping — the urllib CA-cert
        # failure mode applies here too, and a failed dismiss re-delivers the
        # announcement every session).
        ann_id = ann.get("id", "")
        if ann_id:
            try:
                _http_post_json(
                    f"{PROXY_URL}/dismiss-announcement",
                    {"announcement_id": ann_id, "builder_email": email},
                    5,
                )
            except Exception:
                pass

    if output:
        # Wrap with a directive prefix so the announcements surface visibly
        # on every Claude Code surface, not just the terminal CLI.
        #
        # Background: hook stdout is added to Claude's context on every
        # surface (terminal CLI, desktop app, IDE extensions). The CLI
        # additionally prints stdout to the terminal at session start, so
        # raw text is naturally visible there. The desktop app does NOT
        # print hook stdout to the screen — it only injects it as context,
        # so a bare `print(...)` of an announcement reaches Claude silently
        # and the user never sees it unless Claude happens to surface it.
        #
        # The directive prefix tells Claude to surface the announcement at
        # the start of its first reply. That makes the announcement
        # visible on desktop while keeping CLI behavior intact (CLI users
        # see it in the terminal AND see Claude echo it once — minor
        # redundancy, acceptable trade for desktop coverage).
        announcement_block = "\n".join(output)
        directive = (
            "[NSLS Builder Toolkit — surface the following to the user "
            "verbatim at the start of your first reply, then proceed with "
            "their request:]\n\n"
            f"{announcement_block}"
        )
        if data.get("new_pr_credits"):
            # Judge-then-nudge: a merged PR that shipped something others
            # will rely on (a new skill, tool, or service) belongs on the
            # org Automation Tracker; a pure bugfix/doc tweak doesn't.
            directive += (
                "\n\n[NSLS Builder Toolkit — additionally: judge whether a "
                "merged PR above shipped something registerable (a new "
                "skill, tool, or service other builders will rely on). If "
                "it did — or you can't tell from the repo/PR context — also "
                "surface this line: \"Shipped something new? Run "
                "/register-automation so it's on the org tracker.\" If it "
                "was clearly a pure bugfix, doc tweak, or maintenance "
                "change, skip that line.]"
            )
        print(directive)


def emit_guardrails_context():
    """Print the Builder Guardrails section of the plugin's CLAUDE.md.

    WHY THIS EXISTS. A plugin's root CLAUDE.md is not loaded into anyone's
    session — plugin.json doesn't reference it, no hook injected it, and it
    isn't on any path Claude Code reads as memory. It is documentation for
    people browsing the repo. That was fine when the file held conventions,
    and became a hole the moment it held the guardrail tiers: the four hard
    gates fire (guardrail-gate.py is wired through hooks.json) but the entire
    soft half — tiers, escalation triggers, the voice guide — reached Claude
    only if a skill happened to trigger, which is description-matched, which
    is the exact failure the hook exists to cover.

    Found by the Phase 6 voice run, 2026-08-15. Stdout from a SessionStart
    hook reaches Claude as context (same channel the announcement directive
    below already uses), so printing the section is the whole fix.

    Fails silent: a missing file, an unreadable one, or a renamed heading
    prints nothing rather than breaking session start for every builder.
    """
    try:
        text = (PLUGIN_DIR / "CLAUDE.md").read_text(errors="ignore")
    except Exception:
        return

    start = text.find("## Builder Guardrails")
    if start == -1:
        return
    nxt = text.find("\n## ", start + 1)
    section = text[start:nxt if nxt != -1 else len(text)].strip()
    if not section:
        return

    # The section ends by telling Claude to read the voice guide, but writes it
    # as a repo-relative path. A builder's session has its own cwd
    # (~/projects/whatever), so that path resolves to nothing and the guide --
    # the half of this that governs *tone* -- silently never loads. Same failure
    # as the section itself not loading, one level down. Resolve it against
    # PLUGIN_DIR so the path is openable from wherever the builder is working.
    voice_guide = PLUGIN_DIR / "_shared" / "references" / "guardrail-voice.md"
    section = section.replace(
        "`_shared/references/guardrail-voice.md`", f"`{voice_guide}`"
    )

    print(
        "[NSLS Builder Toolkit — org guardrail policy, active this session]\n\n"
        + section
    )

    # What this build has already refused. Without it, rule 6 ("take the first
    # no gracefully, and remember it per BUILD") is unenforceable across
    # sessions -- every new session re-raises guardrails the builder already
    # declined, which is how a toolkit becomes nagware.
    try:
        out = subprocess.run(
            [sys.executable, str(PLUGIN_DIR / "hooks" / "guardrail-memory.py"),
             "list", "--cwd", os.getcwd()],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0 and out.stdout.strip():
            print("\n" + out.stdout.strip())
    except Exception:
        pass  # no memory is the status quo, not a failure worth surfacing
def main():
    git_pull()
    run_plugin_migration()
    ensure_plugin_fresh()
    sync_pointers()
    emit_guardrails_context()
    replayed = replay_failed_ping()
    session_ping(replayed=replayed)


if __name__ == "__main__":
    main()
