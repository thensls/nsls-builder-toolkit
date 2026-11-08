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
  - `mcpServers` in every .claude-plugin/plugin.json in the repo and in each
    plugin entry of .claude-plugin/marketplace.json: inline servers, a path to
    a file of them (then read too), or a list of either

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
    """(name, config) pairs in a server-list file. `.mcp.json` wraps them in
    `mcpServers`; a file named from plugin.json may hold them bare. The shape is
    only a guess, so nothing is dropped on it: the other top-level keys are kept
    too (a server named `mcpServers` can't hide its neighbours), and a file
    that isn't a map at all is searched whole."""
    if not isinstance(data, dict):
        return [("(whole file)", data)]
    inner = data.get("mcpServers")
    if not isinstance(inner, dict):
        return list(data.items())
    return [(k, v) for k, v in data.items() if k != "mcpServers"] + list(inner.items())


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
    """(label, server pairs) for a manifest's `mcpServers` field: inline servers,
    a path, or a list whose items are paths or inline servers. An inline map is
    the servers themselves, never unwrapped."""
    if field is None:
        return []
    items = field if isinstance(field, list) else [field]
    if not all(isinstance(p, (str, dict)) for p in items):
        raise Unreadable(f"{label}: mcpServers is neither servers, a path, nor a list of them")
    out = []
    for p in items:
        if isinstance(p, dict):
            out.append((label, list(p.items())))
            continue
        target = (base / p).resolve()
        if not target.is_file():
            raise Unreadable(f"{label}: mcpServers names {p!r}, which isn't a file")
        out.append((f"{target} (named by {label})", servers_in(load_json(target))))
    return out


def in_repo(root, path):
    return not SKIP_DIRS.intersection(path.relative_to(root).parts)


def server_lists(root):
    root = Path(root).resolve()
    found = []
    for path in sorted(root.rglob(".mcp.json")):
        if in_repo(root, path):
            found.append((str(path.relative_to(root)), servers_in(load_json(path))))
    # Every plugin manifest in the repo, not only the root one: a marketplace
    # entry can point at a plugin in a subfolder, and its manifest ships too.
    for manifest in sorted(root.rglob("plugin.json")):
        if manifest.parent.name == ".claude-plugin" and in_repo(root, manifest):
            label = str(manifest.relative_to(root))
            found += declared_lists(load_json(manifest).get("mcpServers"), manifest.parent.parent, label)
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
        for name, config in servers:
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
