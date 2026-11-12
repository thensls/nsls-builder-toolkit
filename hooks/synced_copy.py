#!/usr/bin/env python3
"""synced_copy.py - is the toolkit here delivered by NSLS's Claude organization?

Claude Code can receive a plugin two ways. The one this toolkit grew up with is
a marketplace install: a record in installed_plugins.json, a versioned copy
under plugins/cache/, and `claude plugin update` to move it. The other is
organization sync: an Owner adds the repository in the Claude organization's
settings, and every member's Claude Code downloads the plugin by itself at
start-up. Claude Code calls that copy `nsls-builder-toolkit@synced`. It has NO
record in installed_plugins.json and no version folder; it lives at

    <config>/plugins/synced/<organizationUuid>_<accountUuid>/nsls-builder-toolkit/

Nothing a builder runs can update it, and nothing needs to: Claude Code
replaces it when NSLS publishes. So every part of the toolkit that asks "is the
plugin installed?" by reading installed_plugins.json gets the wrong answer on
such a machine, and acts on it: it tries to install the marketplace plugin
beside the synced one, checks GitHub for updates it cannot apply, and tells the
builder the toolkit "is not installed as a plugin". This module is the one
place that knows what a synced copy looks like, so the hooks, the migration and
the beacons agree.

Two different claims, kept apart on purpose:

* running_root(file) - THIS code is running from the synced copy. That is
  proof Claude Code loaded it, whatever any settings file says.
* live_root() / active() - a synced copy is on disk for the signed-in account.
  It may still be shadowed: a marketplace install of the same plugin outranks a
  synced one, and Claude Code then reports the synced copy as not loaded.

Never raises. Plain stdlib. Verified against Claude Code 2.1.322 (2026-11-12).
"""

import json
import os
import re
import tempfile
from pathlib import Path

PLUGIN = "nsls-builder-toolkit"
SYNCED_ID = PLUGIN + "@synced"

# Both halves of the account folder name are UUIDs. Anything else is not a
# folder name this module will build a path from.
_UUID = re.compile(r"^[0-9A-Fa-f][0-9A-Fa-f-]{7,63}\Z")
_VERSION = re.compile(r"^\d{1,5}\.\d{1,5}\.\d{1,5}\Z")


def config_dir() -> Path:
    """The Claude config directory, resolved without ever raising."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR")
    if raw:
        return Path(raw)
    try:
        return Path.home() / ".claude"
    except Exception:
        return Path(tempfile.gettempdir()) / "nsls-claude-config"


def _read_json(path):
    # utf-8-sig: files written by PowerShell carry a BOM.
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _synced_dir(cfg) -> Path:
    return Path(cfg) / "plugins" / "synced"


def _is_copy(root) -> bool:
    """A folder that holds this plugin, whole enough to run its hooks."""
    try:
        root = Path(root)
        if not root.is_dir():
            return False
        manifest = _read_json(root / ".claude-plugin" / "plugin.json")
        return (isinstance(manifest, dict) and manifest.get("name") == PLUGIN
                and (root / "hooks" / "hooks.json").is_file())
    except Exception:
        return False


def _account_folder(cfg):
    """The folder name Claude Code keeps the signed-in account's synced plugins
    under, or None when the account cannot be read.

    Claude Code records the account in .claude.json: beside the config
    directory by default (~/.claude.json), inside it when CLAUDE_CONFIG_DIR is
    set. A machine that has been signed in to two accounts keeps one folder per
    account, and only the current account's is loaded.
    """
    candidates = []
    if not os.environ.get("CLAUDE_CONFIG_DIR"):
        try:
            candidates.append(Path.home() / ".claude.json")
        except Exception:
            pass
    candidates.append(Path(cfg) / ".claude.json")
    for path in candidates:
        try:
            account = _read_json(path).get("oauthAccount") or {}
            org, acct = account.get("organizationUuid"), account.get("accountUuid")
            if (isinstance(org, str) and isinstance(acct, str)
                    and _UUID.match(org) and _UUID.match(acct)):
                return f"{org}_{acct}"
        except Exception:
            continue
    return None


def copies(cfg=None) -> dict:
    """{account folder name: plugin root} for every complete synced copy on disk."""
    cfg = config_dir() if cfg is None else Path(cfg)
    found = {}
    try:
        for folder in sorted(_synced_dir(cfg).iterdir()):
            if folder.name.startswith(".") or not folder.is_dir():
                continue
            root = folder / PLUGIN
            if _is_copy(root):
                found[folder.name] = root
    except Exception:
        pass
    return found


def live_root(cfg=None):
    """The synced copy Claude Code holds for the signed-in account, or None.

    With the account readable, only that account's folder counts: a copy left
    behind by another account is on disk but never loaded. With the account
    unreadable, a copy counts only when it is the only one, so there is nothing
    to confuse it with.
    """
    cfg = config_dir() if cfg is None else Path(cfg)
    found = copies(cfg)
    if not found:
        return None
    folder = _account_folder(cfg)
    if folder is not None:
        # Windows file names are case-insensitive; UUIDs are not always
        # written in one case.
        for name, root in found.items():
            if name.lower() == folder.lower():
                return root
        return None
    return next(iter(found.values())) if len(found) == 1 else None


def running_root(running_file, cfg=None) -> str:
    """The synced copy `running_file` belongs to, or "".

    Anchored on the plugins/synced folder, not on a path that merely contains
    the word: the local clone and a marketplace install both answer "".
    """
    try:
        cfg = config_dir() if cfg is None else Path(cfg)
        base = _synced_dir(cfg).resolve()
        here = Path(running_file).resolve()
        for parent in here.parents:
            if parent == base:
                break
            if base in parent.parents and _is_copy(parent):
                return str(parent)
    except Exception:
        pass
    return ""


def required(root) -> bool:
    """True when NSLS marked the plugin required. Claude Code then loads it
    whatever the builder's own settings say."""
    try:
        root = Path(root)
        meta = _read_json(root.parent / f"{root.name}.meta.json")
        return "required" in str(meta.get("installation_preference", "")).lower()
    except Exception:
        return False


def switched_off(cfg=None, root=None) -> bool:
    """True when this machine's own settings stop the synced copy loading.

    Two switches exist: `syncClaudeAiPlugins: false` stops every synced plugin,
    and `"nsls-builder-toolkit@synced": false` stops this one, unless NSLS made
    it required. Settings that cannot be read are not a switch.

    The machine's own settings file, on purpose, and not a project's. What
    this answer gates is machine-wide: pointer files in ~/.claude/skills, the
    shims in ~/.claude/settings.json, whether to install a plugin. A project
    that turns the toolkit off for itself must not make the hook write a
    pointer file per skill for every other project, or reinstall anything.
    """
    cfg = config_dir() if cfg is None else Path(cfg)
    try:
        settings = _read_json(cfg / "settings.json")
    except Exception:
        return False
    if not isinstance(settings, dict):
        return False
    if settings.get("syncClaudeAiPlugins") is False:
        return True
    plugins = settings.get("enabledPlugins")
    if isinstance(plugins, dict) and plugins.get(SYNCED_ID) is False:
        return not (root is not None and required(root))
    return False


def present(cfg=None, running_file=None) -> bool:
    """True when the organization's copy is on this machine for this account."""
    if running_file is not None and running_root(running_file, cfg):
        return True
    return live_root(cfg) is not None


def active(cfg=None, running_file=None) -> bool:
    """True when the organization's copy is what delivers the toolkit here:
    this code runs from it, or it is on disk for the signed-in account and the
    builder has not switched it off."""
    if running_file is not None and running_root(running_file, cfg):
        return True
    root = live_root(cfg)
    return root is not None and not switched_off(cfg, root)


def version(root):
    """The toolkit version a copy carries (X.Y.Z), or None."""
    try:
        value = _read_json(Path(root) / ".claude-plugin" / "plugin.json").get("version")
        return value if isinstance(value, str) and _VERSION.match(value) else None
    except Exception:
        return None


if __name__ == "__main__":
    import sys

    # For shell callers, which ask rather than re-implement the rules above:
    # `python synced_copy.py --active` prints "active" (and nothing otherwise).
    if sys.argv[1:] == ["--active"]:
        if active():
            print("active")
    elif sys.argv[1:] == ["--root"]:
        _root = live_root()
        if _root is not None:
            print(_root)
