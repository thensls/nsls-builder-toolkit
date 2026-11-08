#!/usr/bin/env python3
"""Refuse a student-record server in any server list this plugin ships.

Usage: python3 .github/scripts/check_record_servers.py [<repo root>]

Student-record lookups (HubSpot, PostHog, Customer.io, Hex) go through each
vendor's own server, added per person in Claude Code only; see
skills/connect/SKILL.md § Student-record servers. Cowork never reads a
person's Claude Code list, so it never sees them. A server list the plugin
ships is different: install the plugin in Cowork and the list goes with it,
which would put record lookups in the one place they must not reach.

What counts as a plugin server list, and is checked here:
  - every `.mcp.json` in the repo (the plugin's own is the one at the root)
  - `mcpServers` in .claude-plugin/plugin.json and in each plugin entry of
    .claude-plugin/marketplace.json: inline servers, or a path (or list of
    paths) to a file of them, which is then read too

Every string inside a server's config is searched, not only `url`, so a
stdio wrapper such as `npx mcp-remote https://mcp.hubspot.com` is caught as
well. A file that can't be read or parsed fails the check rather than
passing unread.

Tests: test/test_check_record_servers.py
"""

import json
import re
import sys
from pathlib import Path

RECORD_HOSTS = (
    "mcp.hubspot.com",
    "mcp.posthog.com",
    "mcp.customer.io",
    "mcp-eu.customer.io",
    "app.hex.tech",
)
# A host as a whole name: a subdomain of it matches, a longer name that merely
# ends in the same letters (notmcp.hubspot.com) or continues (app.hex.tech.example) does not.
HOST_RE = re.compile(
    r"(?<![\w-])(?:[\w-]+\.)*(" + "|".join(re.escape(h) for h in RECORD_HOSTS) + r")(?![\w-]|\.[\w-])",
    re.IGNORECASE,
)
SKIP_DIRS = {".git", "node_modules"}


class Unreadable(Exception):
    pass


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise Unreadable(f"{path}: can't read it as JSON ({e})")


def servers_in(data):
    """The name -> config map in a server-list document. `.mcp.json` wraps it in
    `mcpServers`; a file named from plugin.json may hold the map bare."""
    if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        return data["mcpServers"]
    return data if isinstance(data, dict) else {}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def declared_lists(field, base, label):
    """(label, servers map) for a manifest's `mcpServers` field: inline, a path, or a list of paths."""
    if field is None:
        return []
    if isinstance(field, dict):
        return [(label, servers_in(field))]
    paths = [field] if isinstance(field, str) else field
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise Unreadable(f"{label}: mcpServers is neither servers, a path, nor a list of paths")
    out = []
    for p in paths:
        target = (base / p).resolve()
        if not target.is_file():
            raise Unreadable(f"{label}: mcpServers names {p!r}, which isn't a file")
        out.append((f"{target} (named by {label})", servers_in(load_json(target))))
    return out


def server_lists(root):
    root = Path(root).resolve()
    found = []
    for path in sorted(root.rglob(".mcp.json")):
        if not SKIP_DIRS.intersection(path.relative_to(root).parts):
            found.append((str(path.relative_to(root)), servers_in(load_json(path))))
    plugin = root / ".claude-plugin" / "plugin.json"
    if plugin.is_file():
        found += declared_lists(load_json(plugin).get("mcpServers"), root, ".claude-plugin/plugin.json")
    market = root / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        for i, entry in enumerate(load_json(market).get("plugins") or []):
            if not isinstance(entry, dict):
                continue
            src = entry.get("source")
            base = (root / src) if isinstance(src, str) else root
            label = f".claude-plugin/marketplace.json plugins[{i}]"
            found += declared_lists(entry.get("mcpServers"), base, label)
    return found


def findings(root):
    out = []
    for where, servers in server_lists(root):
        for name, config in servers.items():
            hosts = sorted({m.group(1).lower() for s in strings({name: config}) for m in HOST_RE.finditer(s)})
            if hosts:
                out.append((where, name, hosts))
    return out


def main(argv):
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    try:
        lists = server_lists(root)
        bad = findings(root)
    except Unreadable as e:
        print(f"FAIL: {e}")
        return 1
    if bad:
        for where, name, hosts in bad:
            print(f"FAIL: {where}: server {name!r} points at {', '.join(hosts)}")
        print("Student-record servers are added per person in Claude Code only "
              "(skills/connect/SKILL.md § Student-record servers). A server list the plugin "
              "ships would carry them into Cowork. Remove them from that list.")
        return 1
    print(f"ok: no student-record host in {len(lists)} plugin server list(s): "
          + ", ".join(w for w, _ in lists))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
