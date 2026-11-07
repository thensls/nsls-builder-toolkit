#!/usr/bin/env python3
"""
student-data-log.py: PreToolUse hook that keeps a local record of student-record
lookups made from Claude Code.

RECORD ONLY. It never denies, never asks and prints nothing. It always exits 0,
and any internal error is a silent pass: a logger that can break a tool call
costs more trust than the record is worth.

WHAT IT RECORDS (one line per hit, nothing for any other call):
  registered  a call to a vendor's own MCP server, recognised by the HOST its
              URL points at, never by its name. The name is resolved the way
              Claude Code resolves it: `projects[<dir>].mcpServers` in
              ~/.claude.json, then the project's `.mcp.json`, then the user
              `mcpServers`. A same-named server on another host is not one; a
              record host under any name is.
  connector   a record tool on a shared claude.ai connector. HubSpot: every
              tool except the reviewed list below, so a new HubSpot tool counts
              until someone reviews it. PostHog, Customer.io, Hex: every tool.
  carrier     a Google Drive or Gmail call whose input looks like student
              records (roster, GPA, a .edu address, a spreadsheet file).
              Logged with the detector label only.

HOW A CONNECTOR IS RECOGNISED. The CLI names them `mcp__claude_ai_<Name>__tool`;
the desktop app names them `mcp__<uuid>__tool`, and the uuid changes when a
connector is re-registered. So, in order: the name (CLI); a uuid known in
advance (KNOWN_IDS); the tool's own shape, which also teaches the hook that
uuid; then the uuids it has learned, so a later tool with a generic name on the
same connector (send_message, a new HubSpot tool) is still recognised.

LOG FORMAT, stable, because a later change ships these lines to central
storage: JSON Lines in <config dir>/.nsls-student-data-log.jsonl, where the
config dir is CLAUDE_CONFIG_DIR or ~/.claude. At 5 MB the file moves to
`.jsonl.1` (one old file kept). Add fields; never rename or repurpose one.
  ts               UTC, "2026-11-07T15:04:05Z"
  tool             the tool name exactly as Claude Code reports it
  server           the MCP server part of that name
  platform         hubspot | posthog | customerio | hex | google_drive | gmail
  route            registered | connector | carrier
  detector         how it was recognised: host | name | id | shape; for a
                   carrier, the smell: roster | gpa | chapter_roster |
                   edu_address | spreadsheet_file
  session_id       Claude Code's session id
  toolkit_version  this plugin's version
NEVER WRITTEN: tool inputs or outputs, query text, record ids, email addresses,
or the text a detector matched.
"""

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

LOG_NAME = ".nsls-student-data-log.jsonl"
LEARNED_NAME = ".nsls-student-data-connectors.json"
MAX_BYTES = 5_000_000
MAX_LEARNED = 50

# The vendors' own MCP servers. Fixed by the plan; /connect registers them.
RECORD_HOSTS = {
    "mcp.hubspot.com": "hubspot",
    "mcp.posthog.com": "posthog",
    "mcp.customer.io": "customerio",
    "mcp-eu.customer.io": "customerio",
    "app.hex.tech": "hex",
}
_HOST_BYTES = tuple(h.encode() for h in RECORD_HOSTS)

# HubSpot tools reviewed as unable to return a student record (schema,
# org metadata, content authoring). Everything else on HubSpot is a record tool.
HUBSPOT_REVIEWED = frozenset({
    "manage_campaign_objects", "manage_blog_post", "manage_landing_page",
    "render_asset", "get_organization_details", "get_user_details",
    "search_owners", "get_properties", "search_properties",
    "discover_hubspot_schema", "tool_guidance", "show_feedback_form",
})
RECORD_PLATFORMS = ("hubspot", "posthog", "customerio", "hex")
CARRIERS = ("google_drive", "gmail")

# Desktop-app connector ids seen on Davo's machine. Hints only: an id changes
# when a connector is re-registered, which is why shapes and learning exist.
KNOWN_IDS = {
    "39bb8873-bcdf-4c02-95b1-59fd7ba9b014": "hubspot",
    "a5fc0140-a692-4183-9087-8cb68930773f": "google_drive",
    "9b014556-1195-4e6d-ab17-08677a2ddaa4": "gmail",
}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Tool names that name the vendor on their own: (platform, pattern, learn).
# Narrow on purpose. A `learn` match also teaches the hook that connector's id,
# which then sticks, so only vendor-specific shapes learn; a generic one (a
# `hex` token, as in `to_hex`) logs that call and teaches nothing.
SHAPES = (
    ("hubspot", re.compile(r"hubspot|crm_(objects|data|records|associations)"
                           r"|(^|_)aeo_|campaign_attribution|content_analytics|intent_signals"), True),
    ("posthog", re.compile(r"posthog|hogql"), True),
    ("posthog", re.compile(r"feature-flag|^insights?-"), False),
    ("customerio", re.compile(r"customer[._-]?io"), True),
    ("hex", re.compile(r"(^|[_-])hex([_-]|$)"), False),
    ("google_drive", re.compile(r"^(read_file_content|download_file_content|search_files"
                                r"|list_recent_files|get_file_metadata|get_file_permissions)$"), True),
    ("gmail", re.compile(r"^(search_threads|get_thread|create_draft|list_drafts|get_draft"
                         r"|update_draft|delete_draft)$"), True),
)

# Carrier smells, most specific first. Only the label is ever logged.
SMELLS = (
    ("chapter_roster", re.compile(r"(?i)\bchapter\s+(roster|list|members?)")),
    ("roster", re.compile(r"(?i)\broster")),
    ("gpa", re.compile(r"(?i)\bgpa\b")),
    ("edu_address", re.compile(r"(?i)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]*\.edu\b")),
    ("spreadsheet_file", re.compile(r"(?i)\.(csv|xlsx?)\b")),
)


def _config_dir() -> Path:
    """CLAUDE_CONFIG_DIR or ~/.claude, resolved without ever raising."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    if raw:
        return Path(raw)
    try:
        return Path.home() / ".claude"
    except Exception:
        return Path(tempfile.gettempdir()) / "nsls-claude-config"


def _read_bytes(path) -> bytes:
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except Exception:
        return b""


def _global_config() -> bytes:
    """~/.claude.json, or the copy inside CLAUDE_CONFIG_DIR when one is set."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    if raw:
        data = _read_bytes(Path(raw) / ".claude.json")
        if data:
            return data
    try:
        return _read_bytes(Path.home() / ".claude.json")
    except Exception:
        return b""


def _norm_name(name: str) -> str:
    """A server name the way Claude Code spells it inside a tool name."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(name))


def _norm_dir(path: str) -> str:
    p = str(path or "").replace("\\", "/").rstrip("/")
    return p.lower() if os.name == "nt" else p


def _record_host(entry) -> str:
    """The record platform a server definition points at, or ""."""
    if not isinstance(entry, dict):
        return ""
    urls = [entry.get("url")]
    # A stdio proxy (`npx mcp-remote https://...`) carries its URL in args.
    args = entry.get("args")
    if isinstance(args, list):
        urls += [a for a in args if isinstance(a, str) and a.lower().startswith(("http://", "https://"))]
    for url in urls:
        if not isinstance(url, str):
            continue
        try:
            host = (urlsplit(url.strip()).hostname or "").rstrip(".")
        except Exception:
            continue
        if host in RECORD_HOSTS:
            return RECORD_HOSTS[host]
    return ""


def registered_platform(server: str, dirs) -> str:
    """The record platform behind a named MCP server, or "".

    Claude Code resolves a name local scope first, then project, then user, so
    the first definition found in that order is the one that runs.
    """
    user_raw = _global_config()
    dot_mcp = []
    for d in dirs:
        raw = _read_bytes(Path(d) / ".mcp.json") if d else b""
        if raw:
            dot_mcp.append(raw)
    # No record host anywhere in the config: nothing named can be one, and the
    # JSON is never parsed. This is the common case, on every other MCP call.
    if not any(h in blob.lower() for blob in [user_raw] + dot_mcp for h in _HOST_BYTES):
        return ""

    def parse(raw):
        try:
            data = json.loads(raw.decode("utf-8-sig", "replace"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    user = parse(user_raw)
    scopes = []
    projects = user.get("projects")
    if isinstance(projects, dict):
        wanted = {_norm_dir(d) for d in dirs if d}
        for key, proj in projects.items():
            if _norm_dir(key) in wanted and isinstance(proj, dict):
                scopes.append(proj.get("mcpServers"))
    scopes += [parse(raw).get("mcpServers") for raw in dot_mcp]
    scopes.append(user.get("mcpServers"))
    for servers in scopes:
        if not isinstance(servers, dict):
            continue
        for name, entry in servers.items():
            if _norm_name(name) == server:
                return _record_host(entry)
    return ""


def _learned_path() -> Path:
    return _config_dir() / LEARNED_NAME


def _learned() -> dict:
    try:
        data = json.loads(_read_bytes(_learned_path()).decode("utf-8", "replace") or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _learn(server: str, platform: str) -> None:
    """Remember which vendor a connector id belongs to. Never overwrites."""
    try:
        known = _learned()
        if known.get(server) or len(known) >= MAX_LEARNED:
            return
        known[server] = platform
        path = _learned_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{LEARNED_NAME}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(known, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def connector_platform(server: str, tool: str):
    """(platform, detector) for a claude.ai connector, or (None, None)."""
    low = server.lower()
    if low.startswith("claude_ai_"):
        label = low[len("claude_ai_"):]
        flat = re.sub(r"[^a-z0-9]", "", label)
        for platform, key in (("hubspot", "hubspot"), ("posthog", "posthog"),
                              ("customerio", "customerio"), ("google_drive", "googledrive"),
                              ("gmail", "gmail")):
            if key in flat:
                return platform, "name"
        if "hex" in re.split(r"[^a-z0-9]+", label):
            return "hex", "name"
    elif not UUID_RE.match(low):
        return None, None
    if low in KNOWN_IDS:
        return KNOWN_IDS[low], "id"
    tl = tool.lower()
    for platform, rx, learn in SHAPES:
        if rx.search(tl):
            if learn:
                _learn(low, platform)
            return platform, "shape"
    platform = _learned().get(low)
    if platform in RECORD_PLATFORMS or platform in CARRIERS:
        return platform, "id"
    return None, None


def smell(tool_input):
    try:
        text = json.dumps(tool_input, ensure_ascii=False)
    except Exception:
        text = str(tool_input)
    for label, rx in SMELLS:
        if rx.search(text):
            return label
    return ""


def _clean(value, limit):
    return re.sub(r"[^A-Za-z0-9_.:-]", "", str(value or ""))[:limit]


def _toolkit_version() -> str:
    try:
        manifest = Path(__file__).resolve().parents[1] / ".claude-plugin" / "plugin.json"
        return _clean(json.loads(manifest.read_text(encoding="utf-8")).get("version"), 32)
    except Exception:
        return ""


def write(tool_name, server, platform, route, detector, session_id) -> None:
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": _clean(tool_name, 200),
        "server": _clean(server, 100),
        "platform": platform,
        "route": route,
        "detector": detector,
        "session_id": _clean(session_id, 100),
        "toolkit_version": _toolkit_version(),
    }
    line = (json.dumps(record, separators=(",", ":")) + "\n").encode("utf-8")
    path = _config_dir() / LOG_NAME
    try:
        if path.stat().st_size >= MAX_BYTES:
            os.replace(path, path.with_name(LOG_NAME + ".1"))
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags, 0o600)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


def main() -> None:
    raw = getattr(sys.stdin, "buffer", None)
    raw = raw.read() if raw is not None else sys.stdin.read().encode("utf-8")
    payload = json.loads(raw.decode("utf-8", "replace"))
    if not isinstance(payload, dict):
        return
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.startswith("mcp__"):
        return
    server, sep, tool = tool_name[len("mcp__"):].partition("__")
    if not sep or not server or server.startswith("plugin_"):
        return  # plugin servers are configured inside their plugin, not here
    session_id = payload.get("session_id")
    tool_input = payload.get("tool_input")

    # Proof the hook runs at all, so an empty log never has to mean "no hook".
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import plugin_beacon
        plugin_beacon.record("student-data-log", __file__)
    except Exception:
        pass

    platform, detector = connector_platform(server, tool)
    if platform in RECORD_PLATFORMS:
        if platform == "hubspot" and tool in HUBSPOT_REVIEWED:
            return
        write(tool_name, server, platform, "connector", detector, session_id)
        return
    if platform in CARRIERS:
        label = smell(tool_input)
        if label:
            write(tool_name, server, platform, "carrier", label, session_id)
        return
    if platform is None and (server.lower().startswith("claude_ai_") or UUID_RE.match(server.lower())):
        return  # a connector this hook does not track

    dirs = []
    for d in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd")):
        if isinstance(d, str) and d and d not in dirs:
            dirs.append(d)
    platform = registered_platform(server, dirs)
    if platform:
        write(tool_name, server, platform, "registered", "host", session_id)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
