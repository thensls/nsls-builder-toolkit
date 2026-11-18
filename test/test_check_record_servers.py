#!/usr/bin/env python3
"""The CI guard that keeps student-record servers out of every server list the plugin ships.

Plain stdlib, no pytest: run with `python3 test/test_check_record_servers.py`.

Why it exists: HubSpot, PostHog, Customer.io and Hex record lookups are added
per person in Claude Code only (skills/connect § Student-record servers), so
Cowork never sees them. One line in the plugin's own .mcp.json would undo that
for everyone who installs the plugin in Cowork, and nothing else would notice.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "check_record_servers.py"
SIGNAL = {"signal": {"type": "stdio", "command": "node", "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/signal/signal-mcp.js"]}}

failures = []


def check(label, cond):
    print(f"{'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(label)


def run(root):
    r = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def plugin(tmp, mcp=None, manifest=None, market=None, extra=None):
    """A minimal plugin tree: .mcp.json, plugin.json, marketplace.json, and any extra files."""
    root = Path(tmp)
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    if mcp is not None:
        (root / ".mcp.json").write_text(mcp if isinstance(mcp, str) else json.dumps({"mcpServers": mcp}), encoding="utf-8")
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest or {"name": "p", "version": "1.0.0"}), encoding="utf-8")
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps(market or {"name": "m", "plugins": [{"name": "p", "source": "./"}]}), encoding="utf-8")
    for rel, body in (extra or {}).items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(body if isinstance(body, str) else json.dumps(body), encoding="utf-8")
    return root


print("\nthis repo, as it is")
code, out = run(ROOT)
check(f"passes (exit {code}): {out.strip()[:160]}", code == 0)

print("\nevery record host is caught in the plugin's own .mcp.json")
for url in ["https://mcp.hubspot.com", "https://mcp.posthog.com/mcp", "https://mcp.customer.io/mcp",
            "https://mcp-eu.customer.io/mcp", "https://app.hex.tech/mcp", "HTTPS://MCP.HUBSPOT.COM/"]:
    with tempfile.TemporaryDirectory() as tmp:
        code, out = run(plugin(tmp, {**SIGNAL, "x-records": {"type": "http", "url": url}}))
        check(f"{url} fails and is named", code == 1 and "x-records" in out)

print("\nthe ways round a url-only check are caught too")
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, {"hs": {"command": "npx", "args": ["-y", "mcp-remote", "https://mcp.hubspot.com/"]}}))
    check("a stdio wrapper with the host in its args fails", code == 1)
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": {"hex": {"type": "http", "url": "https://app.hex.tech/mcp"}}}))
    check("servers inline in plugin.json fail", code == 1)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": "./config/servers.json"},
                           extra={"config/servers.json": {"mcpServers": {"ph": {"type": "http", "url": "https://mcp.posthog.com/mcp"}}}}))
    check("a file plugin.json points at fails", code == 1 and "servers.json" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, SIGNAL, market={"name": "m", "plugins": [
        {"name": "p", "source": "./", "mcpServers": {"cio": {"type": "http", "url": "https://mcp.customer.io/mcp"}}}]}))
    check("servers in a marketplace.json plugin entry fail", code == 1)
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, SIGNAL, extra={"nested/plugin/.mcp.json": {"mcpServers": {"h": {"type": "http", "url": "https://eu.mcp.posthog.com/mcp"}}}}))
    check("a .mcp.json further down the tree, on a subdomain, fails", code == 1)

print("\nno shape of server list hides a server")
HS = {"type": "http", "url": "https://mcp.hubspot.com"}
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, market={"name": "m", "plugins": [{"name": "q", "source": "./plugins/q"}]},
                           extra={"plugins/q/.claude-plugin/plugin.json": {"name": "q", "mcpServers": {"hs": HS}}}))
    check("a marketplace plugin in a subfolder whose own manifest has servers fails", code == 1 and "plugins/q" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": [{"hs": HS}]}))
    check("an inline server inside a list fails", code == 1 and "'hs'" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": [SIGNAL]}))
    check("and an unrelated inline server inside a list passes, not 'unreadable'", code == 0)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": {"mcpServers": SIGNAL["signal"], "hs": HS}}))
    check("an inline server named mcpServers doesn't hide its neighbour", code == 1 and "'hs'" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, json.dumps({"mcpServers": SIGNAL["signal"], "hs": HS})))
    check("nor does one in a bare .mcp.json", code == 1 and "'hs'" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, json.dumps([{"hs": HS}])))
    check("a .mcp.json that isn't a map is searched whole", code == 1)

print("\na file that can't be read fails rather than passing unread")
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, '{"mcpServers": {"x": '))
    check("broken .mcp.json fails", code == 1 and "can't read" in out)
with tempfile.TemporaryDirectory() as tmp:
    code, out = run(plugin(tmp, SIGNAL, manifest={"name": "p", "mcpServers": "./missing.json"}))
    check("plugin.json naming a missing file fails", code == 1 and "isn't a file" in out)

print("\nunrelated servers and look-alike names pass")
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, {**SIGNAL,
                               "a": {"type": "http", "url": "https://notmcp.hubspot.com/mcp"},
                               "b": {"type": "http", "url": "https://app.hex.tech.example/mcp"},
                               "c": {"type": "http", "url": "https://api.hubapi.com"}},
                         manifest={"name": "p", "description": "HubSpot help; see mcp.hubspot.com in the connect skill"}))
    check("look-alikes and a manifest description that mentions a host pass", code == 0)
with tempfile.TemporaryDirectory() as tmp:
    code, _ = run(plugin(tmp, None))
    check("a plugin with no server list at all passes", code == 0)

if failures:
    print(f"\n{len(failures)} failed:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nall passed")
