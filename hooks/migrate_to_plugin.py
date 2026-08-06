#!/usr/bin/env python3
"""
migrate_to_plugin.py — self-migration from the shim install to a real plugin.

Executed by session-start.py on every session start (from the freshly pulled
clone, so fixes to this file take effect one session after they land on main).
Two stages, at most one per session:

Stage A — plugin not installed yet:
    Register this repo as a private marketplace and install the plugin.
    Nothing else changes: the running session keeps using the shims, and the
    plugin loads at the NEXT session start. Anyone with git access to the repo
    can install; the marketplace is not public.

Stage B — plugin installed, shims still present (mac/linux only):
    Remove exactly the shims the installer created, now that the plugin
    provides the same components:
      * pointer stubs in ~/.claude/skills whose SKILL.md points at
        local-plugins/nsls-builder-toolkit/skills/ — personal-toolkit stubs
        and user-authored skills are never touched (their SKILL.md lacks that
        marker; see the /skills/ discriminator below),
      * settings.json hook entries whose command references
        nsls-builder-toolkit/hooks/ (session-start + skill-event),
      * the user-scope `signal` MCP registration if it points into this repo
        (the plugin registers signal at plugin scope).

Safety properties:
  * fail-open — every step is wrapped; any failure leaves the machine on the
    still-working shim path and retries next session
  * idempotent — each stage checks live state, never history
  * serialized — a lockfile keeps the settings-shim copy and the plugin-hook
    copy of session-start.py from migrating concurrently during the one
    overlap session
  * announced — every state change prints a visible line (silent failure is
    the recurring bug in this pipeline)
  * reversible — settings.json is backed up to settings.json.pre-plugin-migration
    before its first edit
  * escape hatch — set NSLS_NO_PLUGIN_MIGRATION=1 to freeze migration
  * Windows — stage A runs (agents start working); stage B is deferred until
    the plugin's hooks.json has verified Windows parity, so Windows builders
    stay on shims and lose nothing
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
_PLUGIN_DIR = _CONFIG_DIR / "local-plugins" / "nsls-builder-toolkit"
_SKILLS_DIR = _CONFIG_DIR / "skills"
_SETTINGS = _CONFIG_DIR / "settings.json"

_MARKETPLACE = "nsls-toolkit"
_PLUGIN_ID = f"nsls-builder-toolkit@{_MARKETPLACE}"
_REPO_URL = os.environ.get(
    "NSLS_TOOLKIT_REPO", "https://github.com/thensls/nsls-builder-toolkit.git"
)
# Matches the shim hook commands install.sh/.ps1 wrote into settings.json.
_HOOK_MARKER = "nsls-builder-toolkit/hooks/"
# Matches ONLY org-toolkit pointer stubs. Personal-toolkit stubs also mention
# nsls-builder-toolkit (their credit-logging command calls this repo's
# skill-event.sh), so the discriminator must be the skills path, not the repo
# name.
_STUB_MARKER = "local-plugins/nsls-builder-toolkit/skills/"
_LOCK = _CONFIG_DIR / ".nsls-plugin-migration.lock"
_LOCK_STALE_SECS = 300


def _find_claude():
    """Locate the claude CLI. None means retry next session."""
    found = shutil.which("claude")
    if found:
        return found
    for candidate in (
        _CONFIG_DIR / "local" / "claude",
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/claude"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _claude(args, timeout):
    """Run a claude CLI subcommand. Returns (ok, stdout+stderr)."""
    claude = _find_claude()
    if not claude:
        return False, "claude CLI not found"
    try:
        result = subprocess.run(
            [claude, *args], capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, (result.stdout or "") + (result.stderr or "")
    except Exception as e:
        return False, str(e)


def _plugin_installed():
    try:
        registry = json.loads(
            (_CONFIG_DIR / "plugins" / "installed_plugins.json").read_text(
                encoding="utf-8"
            )
        )
        return any(
            key.startswith("nsls-builder-toolkit@")
            for key in registry.get("plugins", {})
        )
    except Exception:
        return False


def _plugin_disabled_by_user():
    """True if the user explicitly disabled the plugin — respect that."""
    try:
        settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
        for key, enabled in settings.get("enabledPlugins", {}).items():
            if key.startswith("nsls-builder-toolkit@") and enabled is False:
                return True
    except Exception:
        pass
    return False


def _shims_present():
    try:
        return _HOOK_MARKER in _SETTINGS.read_text(encoding="utf-8")
    except Exception:
        return False


def _announce(text):
    # Directive prefix so the message is surfaced on every Claude Code surface
    # (desktop injects hook stdout as context without printing it) — same
    # pattern as session-start.py's announcement block.
    print(
        "[NSLS Builder Toolkit — surface the following to the user verbatim "
        "at the start of your first reply, then proceed with their request:]\n\n"
        f"{text}"
    )


def _stage_a():
    """Install the plugin. The running session stays on shims."""
    ok, out = _claude(["plugin", "marketplace", "list"], timeout=30)
    if not ok:
        return
    if _MARKETPLACE not in out:
        ok, out = _claude(["plugin", "marketplace", "add", _REPO_URL], timeout=60)
        if not ok:
            print(f"toolkit migration: marketplace add failed ({out.strip()[:200]}); "
                  "will retry next session", file=sys.stderr)
            return
    ok, out = _claude(["plugin", "install", _PLUGIN_ID], timeout=120)
    if not ok:
        print(f"toolkit migration: plugin install failed ({out.strip()[:200]}); "
              "will retry next session", file=sys.stderr)
        return
    _announce(
        "The NSLS Builder Toolkit installed itself as a Claude Code plugin "
        "(step 1 of 2). Starting next session, the toolkit's agents "
        "(knowledge-researcher and the two reviewers) are finally available. "
        "The old wiring will be cleaned up automatically in a later session — "
        "nothing to do."
    )


def _remove_settings_hooks():
    """Drop hook entries whose command references this repo. Returns count."""
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return 0

    backup = _SETTINGS.with_name("settings.json.pre-plugin-migration")
    if not backup.exists():
        shutil.copy2(_SETTINGS, backup)

    removed = 0
    for event in list(hooks.keys()):
        groups = hooks[event]
        if not isinstance(groups, list):
            continue
        kept_groups = []
        for group in groups:
            entries = group.get("hooks", []) if isinstance(group, dict) else []
            kept = [
                h for h in entries
                if _HOOK_MARKER not in str(h.get("command", ""))
            ]
            removed += len(entries) - len(kept)
            if kept:
                group["hooks"] = kept
                kept_groups.append(group)
            elif not entries:
                kept_groups.append(group)
        if kept_groups:
            hooks[event] = kept_groups
        else:
            del hooks[event]

    if removed:
        tmp = _SETTINGS.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, _SETTINGS)
    return removed


def _remove_org_stubs():
    """Delete org-toolkit pointer stubs. Returns count. Never touches
    personal-toolkit stubs or user-authored skills (marker check)."""
    removed = 0
    if not _SKILLS_DIR.is_dir():
        return 0
    for entry in sorted(_SKILLS_DIR.iterdir()):
        stub = entry / "SKILL.md"
        try:
            if not (entry.is_dir() and not entry.is_symlink() and stub.exists()):
                continue
            if _STUB_MARKER not in stub.read_text(encoding="utf-8"):
                continue
            shutil.rmtree(entry)
            removed += 1
        except Exception:
            continue
    return removed


def _remove_user_scope_signal():
    """Remove the user-scope signal MCP registration if it points into this
    repo — the plugin now registers signal at plugin scope."""
    ok, out = _claude(["mcp", "get", "signal"], timeout=15)
    if ok and "nsls-builder-toolkit" in out:
        _claude(["mcp", "remove", "signal", "-s", "user"], timeout=15)
        return True
    return False


def _stage_b():
    """Retire the shims now that the plugin is live."""
    if sys.platform == "win32":
        # The plugin's hooks.json invokes python3/bash, which is unverified on
        # Windows. Until parity is proven, Windows keeps the settings-based
        # shims (its plugin hooks fail silently, so nothing double-fires).
        return
    # CLI calls first: the claude CLI may normalize/rewrite settings.json as a
    # side effect (observed live: it rewrote a model alias during `mcp get`),
    # so our own settings edit must come after every CLI invocation.
    signal_moved = _remove_user_scope_signal()
    hooks_removed = _remove_settings_hooks()
    stubs_removed = _remove_org_stubs()
    if hooks_removed or stubs_removed or signal_moved:
        _announce(
            "NSLS Builder Toolkit plugin migration complete (step 2 of 2): "
            f"removed {stubs_removed} legacy skill pointers, {hooks_removed} "
            "legacy hook entries"
            + (", and moved the signal MCP server to plugin scope"
               if signal_moved else "")
            + ". Org skills now load as nsls-builder-toolkit:<name> — if a "
            "bare skill name fails this session, use the prefixed form. "
            "Rollback, if ever needed: restore "
            "~/.claude/settings.json.pre-plugin-migration and run "
            "`claude plugin uninstall nsls-builder-toolkit@nsls-toolkit`."
        )


def _acquire_lock():
    try:
        if _LOCK.exists() and time.time() - _LOCK.stat().st_mtime > _LOCK_STALE_SECS:
            _LOCK.unlink()
        fd = os.open(str(_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except Exception:
        return False


def run_migration():
    if os.environ.get("NSLS_NO_PLUGIN_MIGRATION"):
        return
    if not _acquire_lock():
        return
    try:
        if not _plugin_installed():
            _stage_a()
        elif _plugin_disabled_by_user():
            return
        elif _shims_present():
            _stage_b()
    except Exception:
        pass  # fail-open: shims still work; retry next session
    finally:
        try:
            _LOCK.unlink()
        except OSError:
            pass


run_migration()
