#!/usr/bin/env python3
# windows-ci: python | Student-data activity log: records record-server, connector and carrier hits, never an input value, always exits 0
"""The student-data activity log records what it should and nothing else.

Plain stdlib: `python3 hooks/tests/test_student_data_log.py`.

The hook is record only: it never denies or asks, prints nothing and exits 0.
These checks pin what it records (a registered vendor server by HOST, a
connector's record tools, a Drive or Gmail call that looks like student
records), what it must never record (any input value), and that a broken
payload or a missing ~/.claude.json is a silent pass.

Every call runs with a throwaway HOME. All values are made up.
"""
import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
ROOT = HOOKS.parent
HOOK = HOOKS / "student-data-log.py"
LAUNCHER = HOOKS / "run-hook.sh"
WINDOWS = os.name == "nt"
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


def git_bash():
    if not WINDOWS:
        return shutil.which("bash")
    git = shutil.which("git")
    for cand in ([Path(git).resolve().parents[1] / "bin" / "bash.exe"] if git else []) + [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "bin" / "bash.exe"]:
        if cand.is_file():
            return str(cand)
    return None


TMP = Path(tempfile.mkdtemp(prefix="sdlog-test-"))
HOME = TMP / "home"
CFG = HOME / ".claude"
CFG.mkdir(parents=True)
PROJECT = TMP / "project"
PROJECT.mkdir()
LOG = CFG / ".nsls-student-data-log.jsonl"
LEARNED = CFG / ".nsls-student-data-connectors.json"
ENV = dict(os.environ, HOME=str(HOME), USERPROFILE=str(HOME), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
for k in ("CLAUDE_CONFIG_DIR", "CLAUDE_PROJECT_DIR"):
    ENV.pop(k, None)

FIELDS = {"ts", "tool", "server", "platform", "route", "detector", "session_id", "toolkit_version"}
VERSION = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
HS_ID = "39bb8873-bcdf-4c02-95b1-59fd7ba9b014"
NEW_ID = "0f0f0f0f-1111-2222-3333-444455556666"   # a re-registered connector
# Made-up values that must never reach the log.
SECRETS = ("Zzyzx Testperson", "zz.test@example-state.edu", "fall roster", "rec-424242",
           "gpa above 3", "pat-na1-00000000")


def claude_json(servers=None, projects=None):
    data = {"mcpServers": servers or {}}
    if projects is not None:
        data["projects"] = projects
    (HOME / ".claude.json").write_text(json.dumps(data), encoding="utf-8")


def lines():
    if not LOG.exists():
        return []
    return [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]


def call(tool, tool_input=None, raw=None, env=None, cwd=None):
    """(new log lines, exit code, stdout) for one hook run."""
    before = len(lines())
    if raw is None:
        raw = json.dumps({"session_id": "sess-test-1", "tool_name": tool, "tool_input": tool_input or {},
                          "cwd": str(cwd or PROJECT), "hook_event_name": "PreToolUse"})
    r = subprocess.run([sys.executable, str(HOOK)], input=raw.encode("utf-8") if isinstance(raw, str) else raw,
                       capture_output=True, env=env or ENV, cwd=str(cwd or PROJECT), timeout=30)
    return lines()[before:], r.returncode, r.stdout


def one(tool, tool_input=None, **kw):
    new, code, out = call(tool, tool_input, **kw)
    check(f"  ({tool}: exit 0, prints nothing)", code == 0 and not out.strip(), f"(exit {code}, out {out[:80]!r})")
    return new


print("registered servers are recognised by host")
claude_json({
    "hubspot-records": {"type": "http", "url": "https://mcp.hubspot.com"},
    "hubspot-pilot": {"type": "http", "url": "https://mcp.hubspot.com/"},
    "posthog-records": {"type": "http", "url": "https://mcp.posthog.com/mcp"},
    "customerio-records": {"type": "http", "url": "https://mcp-eu.customer.io/mcp"},
    "hex-records": {"type": "http", "url": "https://app.hex.tech/mcp"},
    "crm-proxy": {"type": "stdio", "command": "npx", "args": ["-y", "mcp-remote", "https://mcp.hubspot.com"]},
    "posthog-lookalike": {"type": "http", "url": "https://mcp.posthog.com.example.net/mcp"},
})
new = one("mcp__hubspot-records__search_crm_objects", {"zz_input_key": SECRETS[0], "id": SECRETS[3]})
check("a registered HubSpot server is logged once", len(new) == 1, f"({new})")
if new:
    rec = new[0]
    check("as route=registered, platform=hubspot, detector=host",
          (rec["route"], rec["platform"], rec["detector"]) == ("registered", "hubspot", "host"), f"({rec})")
    check("with exactly the agreed fields", set(rec) == FIELDS, f"({sorted(rec)})")
    check("naming the tool and the server", rec["tool"] == "mcp__hubspot-records__search_crm_objects"
          and rec["server"] == "hubspot-records", f"({rec})")
    check("with the session id and toolkit version", rec["session_id"] == "sess-test-1"
          and rec["toolkit_version"] == VERSION, f"({rec})")
    check("and a UTC timestamp", re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", rec["ts"]) is not None, rec["ts"])
new = one("mcp__hubspot-pilot__get_crm_objects")
check("Davo's hubspot-pilot counts (a record host under another name)",
      [r["route"] for r in new] == ["registered"], f"({new})")
for name, platform in (("posthog-records", "posthog"), ("customerio-records", "customerio"),
                       ("hex-records", "hex"), ("crm-proxy", "hubspot")):
    new = one(f"mcp__{name}__anything")
    check(f"{name} is logged as {platform}", [(r["route"], r["platform"]) for r in new]
          == [("registered", platform)], f"({new})")
new = one("mcp__posthog-lookalike__query-run")
check("a host that only starts with a record host is not one", not new, f"({new})")

print("\nthe same name on the wrong host is not a record server")
claude_json({"hubspot-records": {"type": "http", "url": "https://evil.example.com"}})
new = one("mcp__hubspot-records__search_crm_objects", {"query": SECRETS[0]})
check("hubspot-records pointing elsewhere is not logged", not new, f"({new})")

print("\nscope order: local, then project, then user, as Claude Code resolves a name")
claude_json({"hubspot-records": {"type": "http", "url": "https://mcp.hubspot.com"}},
            projects={str(PROJECT): {"mcpServers": {"hubspot-records": {"type": "http",
                                                                        "url": "https://evil.example.com"}}}})
new = one("mcp__hubspot-records__search_crm_objects")
check("a local-scope server on another host shadows the user-scope one", not new, f"({new})")
claude_json({})
(PROJECT / ".mcp.json").write_text(json.dumps({"mcpServers": {"team-crm": {"type": "http",
                                                                          "url": "https://mcp.hubspot.com"}}}))
new = one("mcp__team-crm__search_crm_objects")
check("a project .mcp.json server on a record host is logged", [r["route"] for r in new] == ["registered"],
      f"({new})")
(PROJECT / ".mcp.json").unlink()
new = one("mcp__ccd_session_mgmt__list_sessions")
check("an unrelated MCP server is not logged", not new, f"({new})")

print("\nHubSpot connector: record tools logged, reviewed content tools not")
for tool in ("mcp__claude_ai_HubSpot__search_crm_objects", f"mcp__{HS_ID}__get_crm_objects",
             f"mcp__{HS_ID}__query_crm_data", "mcp__claude_ai_HubSpot__brand_new_tool"):
    new = one(tool, {"query": SECRETS[0]})
    check(f"{tool.split('__')[-1]} ({tool.split('__')[1][:14]}) is logged",
          [(r["route"], r["platform"]) for r in new] == [("connector", "hubspot")], f"({new})")
for tool in ("mcp__claude_ai_HubSpot__manage_blog_post", f"mcp__{HS_ID}__render_asset",
             f"mcp__{HS_ID}__get_properties", "mcp__claude_ai_HubSpot__search_owners"):
    new = one(tool)
    check(f"{tool.split('__')[-1]} is not logged", not new, f"({new})")

print("\na re-registered HubSpot connector (new uuid) is still recognised")
new = one(f"mcp__{NEW_ID}__generic_new_tool")
check("an unknown uuid with a generic tool name is not logged (nothing known yet)", not new, f"({new})")
new = one(f"mcp__{NEW_ID}__search_crm_objects")
check("its CRM tool is logged by shape", [r["detector"] for r in new] == ["shape"], f"({new})")
check("and the uuid is remembered", json.loads(LEARNED.read_text()).get(NEW_ID) == "hubspot"
      if LEARNED.exists() else False)
new = one(f"mcp__{NEW_ID}__generic_new_tool")
check("then a new tool with a generic name on it is logged by id",
      [(r["platform"], r["detector"]) for r in new] == [("hubspot", "id")], f"({new})")
new = one(f"mcp__{NEW_ID}__manage_landing_page")
check("and a reviewed content tool on it still is not", not new, f"({new})")

print("\nPostHog, Customer.io and Hex connectors: every tool")
for tool, platform in (("mcp__claude_ai_PostHog__query-run", "posthog"),
                       ("mcp__claude_ai_PostHog__dashboards-get-all", "posthog"),
                       ("mcp__claude_ai_Customer_io__list_campaigns", "customerio"),
                       ("mcp__claude_ai_Customer_io__get_customer", "customerio"),
                       ("mcp__claude_ai_Hex__search_projects", "hex"),
                       ("mcp__claude_ai_Hex__run_project", "hex")):
    new = one(tool, {"q": SECRETS[0]})
    check(f"{tool} is logged as {platform}",
          [(r["route"], r["platform"], r["detector"]) for r in new] == [("connector", platform, "name")],
          f"({new})")
HEXISH = "1a2b3c4d-0000-1111-2222-333344445555"
new = one(f"mcp__{HEXISH}__hex_to_rgb")
check("a desktop tool with a 'hex' token is logged once, by shape",
      [(r["platform"], r["detector"]) for r in new] == [("hex", "shape")], f"({new})")
new = one(f"mcp__{HEXISH}__list_palettes")
check("but a generic token teaches nothing: the connector's other tools are not logged", not new, f"({new})")
new = one("mcp__claude_ai_Hexagon_Maps__search")
check("a connector whose name only contains 'hex' is not Hex", not new, f"({new})")
new = one("mcp__claude_ai_Slack__slack_read_channel", {"q": SECRETS[2]})
check("an untracked connector is not logged, even with a smell", not new, f"({new})")

print("\nDrive and Gmail: logged only when the input looks like student records")
new = one("mcp__claude_ai_Google_Drive__search_files", {"query": SECRETS[2]})
check("Drive with 'roster' is logged with the detector",
      [(r["route"], r["platform"], r["detector"]) for r in new] == [("carrier", "google_drive", "roster")],
      f"({new})")
new = one("mcp__claude_ai_Google_Drive__search_files", {"query": "chapter members fall"})
check("a chapter list is labelled chapter_roster", [r["detector"] for r in new] == ["chapter_roster"], f"({new})")
new = one("mcp__claude_ai_Google_Drive__search_files", {"query": "student success plan"})
check("an ordinary Drive search is not logged", not new, f"({new})")
new = one("mcp__9b014556-1195-4e6d-ab17-08677a2ddaa4__search_threads", {"q": SECRETS[1]})
check("Gmail (desktop id) with a .edu address is logged as edu_address",
      [(r["platform"], r["detector"]) for r in new] == [("gmail", "edu_address")], f"({new})")
new = one("mcp__claude_ai_Gmail__send_message", {"body": SECRETS[4]})
check("Gmail with a GPA mention is logged as gpa", [r["detector"] for r in new] == ["gpa"], f"({new})")
new = one("mcp__claude_ai_Google_Drive__create_file", {"name": "export.csv"})
check("a spreadsheet file is labelled spreadsheet_file", [r["detector"] for r in new] == ["spreadsheet_file"],
      f"({new})")

print("\nthe log never holds an input value")
text = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
check("there is a log to inspect", text.count("\n") >= 10, f"({text.count(chr(10))} lines)")
leaked = [s for s in SECRETS if s.lower() in text.lower()] + [w for w in ("example-state", "@", "zz_input_key")
                                                              if w in text]
check("no made-up value, address or input key appears in it", not leaked, f"({leaked})")
check("every line has exactly the agreed fields", all(set(r) == FIELDS for r in lines()))
check("routes are only registered | connector | carrier",
      {r["route"] for r in lines()} <= {"registered", "connector", "carrier"})
if not WINDOWS:
    check("the log is readable by its owner only", (LOG.stat().st_mode & 0o077) == 0, oct(LOG.stat().st_mode))

print("\nbroken input and a missing ~/.claude.json are a silent pass")
for label, raw in (("malformed JSON", "{not json"), ("empty stdin", ""), ("a JSON list", "[1, 2]"),
                   ("a non-string tool name", json.dumps({"tool_name": 7})),
                   ("invalid UTF-8", b"\xff\xfe{\"tool_name\": \"mcp__x__y\"}")):
    new, code, out = call(None, raw=raw)
    check(f"{label}: exit 0, nothing printed, nothing logged", code == 0 and not out.strip() and not new,
          f"(exit {code}, {out[:80]!r}, {new})")
(HOME / ".claude.json").unlink()
new = one("mcp__hubspot-records__search_crm_objects")
check("with no ~/.claude.json a named server is simply not logged", not new, f"({new})")
new = one("mcp__claude_ai_HubSpot__search_crm_objects")
check("and connectors are still logged", len(new) == 1, f"({new})")
(HOME / ".claude.json").write_text("{truncated", encoding="utf-8")
new = one("mcp__hubspot-records__search_crm_objects")
check("a corrupt ~/.claude.json is a silent pass too", not new, f"({new})")
new = one("Bash", {"command": "curl https://api.hubapi.com/x"})
check("a non-MCP tool is ignored", not new, f"({new})")

print("\nCLAUDE_CONFIG_DIR moves the log and the config it reads")
alt = TMP / "altcfg"
alt.mkdir()
(alt / ".claude.json").write_text(json.dumps({"mcpServers": {"hs": {"url": "https://mcp.hubspot.com"}}}))
new, code, _ = call("mcp__hs__search_crm_objects", env=dict(ENV, CLAUDE_CONFIG_DIR=str(alt)))
alt_log = alt / ".nsls-student-data-log.jsonl"
check("it writes inside the config dir", code == 0 and alt_log.exists() and not new,
      f"(exit {code}, {alt_log.exists()}, {new})")

print("\na cp1252 pipe (Windows) still decodes the payload as UTF-8")
new, code, _ = call(None, raw=json.dumps({"tool_name": "mcp__claude_ai_PostHog__query-run",
                                          "tool_input": {"q": "caf\u00e9 \U0001F44D"}}, ensure_ascii=False),
                    env=dict({k: v for k, v in ENV.items() if k != "PYTHONUTF8"}, PYTHONIOENCODING="cp1252"))
check("an emoji in the input does not stop the record", code == 0 and len(new) == 1, f"(exit {code}, {new})")

print("\nthe log has a size cap")
filler = b'{"ts":"filler"}\n'
LOG.write_bytes(filler * (5_000_000 // len(filler) + 1))
_, code, _ = call("mcp__claude_ai_Hex__run_project")
rotated = LOG.with_name(LOG.name + ".1")
fresh = lines()
check("a full log moves to .1 and a fresh one starts with the new record",
      code == 0 and rotated.exists() and rotated.stat().st_size >= 5_000_000
      and [r["platform"] for r in fresh] == ["hex"], f"({rotated.exists()}, {fresh})")

print("\nthrough the real launcher, as hooks.json runs it")
bash = git_bash()
if not bash:
    check("bash is available to run the launcher", False)
else:
    lenv = dict(ENV, CLAUDE_PLUGIN_ROOT=str(ROOT), CLAUDE_CONFIG_DIR=str(CFG))
    payload = json.dumps({"session_id": "sess-launcher", "tool_name": "mcp__claude_ai_HubSpot__search_crm_objects",
                          "tool_input": {"query": SECRETS[0]}})
    before = len(lines())
    started = time.monotonic()
    r = subprocess.run([bash, str(LAUNCHER), "student-data-log"], input=payload.encode("utf-8"),
                       capture_output=True, env=lenv, timeout=60)
    took = time.monotonic() - started
    new = lines()[before:]
    check("the launcher exits 0 and prints nothing", r.returncode == 0 and not r.stdout.strip(),
          f"(exit {r.returncode}, {r.stdout[:120]!r}, {r.stderr[-200:]!r})")
    check("and the call is logged", [x["session_id"] for x in new] == ["sess-launcher"], f"({new})")
    print(f"  info launcher run took {took:.2f}s (first run probes for Python)")

print("\nhooks.json wiring")
hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
entries = [(g, h) for g in hooks.get("PreToolUse", []) for h in g.get("hooks", [])
           if h.get("command", "").rstrip().endswith('run-hook.sh" student-data-log')]
check("registered once, as a PreToolUse hook", len(entries) == 1, f"({len(entries)})")
others = [h for groups in hooks.values() for g in groups for h in g.get("hooks", [])
          if "student-data-log" in h.get("command", "")]
check("and nowhere else", len(others) == 1, f"({len(others)})")
if entries:
    group, hook = entries[0]
    rx = re.compile(group.get("matcher", ""))
    check("matcher is anchored to MCP tools", group.get("matcher", "").startswith("^mcp__"), group.get("matcher"))
    for tool in ("mcp__claude_ai_HubSpot__search_crm_objects", f"mcp__{HS_ID}__get_crm_objects",
                 "mcp__hubspot-records__x"):
        check(f"matcher admits {tool[:40]}", bool(rx.search(tool)))
    for tool in ("Bash", "PowerShell", "Skill", "Read", "WebFetch", "Write"):
        check(f"matcher ignores {tool}", not rx.search(tool))
    check("shell is named explicitly", hook.get("shell") == "bash", f"({hook.get('shell')!r})")
    check("a short timeout (it never waits on anything)", isinstance(hook.get("timeout"), int)
          and hook["timeout"] <= 10, f"({hook.get('timeout')})")
launcher = LAUNCHER.read_text(encoding="utf-8")
check("run-hook.sh dispatches student-data-log",
      re.search(r"^\s*student-data-log\)\s*script=\"\$root/hooks/student-data-log\.py\"", launcher, re.M)
      is not None)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
