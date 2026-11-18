#!/usr/bin/env python3
"""CI: installing a branch must install that branch, clone and plugin both.

Runs this PR's own installer in test mode twice, the way a tester's machine
sees it: first a plain install of main, then this PR's branch on top. Fails
unless the clone (the hooks) and the plugin (the skills) both end up on the
PR's head commit. Before 2026-10-10 the second install left the plugin on
main, and nothing said so.

Reads HEAD_REPO, HEAD_REF and HEAD_SHA from the workflow, and installs into
CLAUDE_KIT_TEST_DIR, a throwaway folder, the way a builder's test install does:
with no CLAUDE_CONFIG_DIR set, so the installer has to point the claude CLI
there itself. Fails if the plugin turns up in the real ~/.claude instead.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

HEAD_REPO = os.environ["HEAD_REPO"]
HEAD_REF = os.environ["HEAD_REF"]
HEAD_SHA = os.environ["HEAD_SHA"]
CONFIG = Path(os.environ["CLAUDE_KIT_TEST_DIR"])
REAL = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
WINDOWS = os.name == "nt"


def install(branch):
    env = dict(os.environ, NSLS_TOOLKIT_REPO=HEAD_REPO, NSLS_TOOLKIT_BRANCH=branch,
               PYTHONIOENCODING="utf-8")
    env.pop("CLAUDE_CONFIG_DIR", None)
    if WINDOWS:
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", "install.ps1", "-Test"]
    else:
        cmd = ["bash", "install.sh", "--test"]
    print(f"::group::install {branch}", flush=True)
    proc = subprocess.run(cmd, env=env, stdin=subprocess.DEVNULL, timeout=1500)
    print("::endgroup::", flush=True)
    print(f"installer exit code: {proc.returncode}")
    return proc.returncode


def installed():
    """(clone commit, plugin commit) as this machine has them now."""
    clone = subprocess.run(
        ["git", "-C", str(CONFIG / "local-plugins" / "nsls-builder-toolkit"), "rev-parse", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    plugin = None
    registry = CONFIG / "plugins" / "installed_plugins.json"
    if registry.exists():
        entries = json.loads(registry.read_text(encoding="utf-8")).get("plugins", {}).get(
            "nsls-builder-toolkit@nsls-toolkit", [])
        plugin = next((e["gitCommitSha"] for e in entries if e.get("gitCommitSha")), None)
    return clone, plugin


def in_real_config():
    """Whether the real ~/.claude has the toolkit plugin registered."""
    try:
        return "nsls-builder-toolkit@nsls-toolkit" in json.loads(
            REAL.read_text(encoding="utf-8")).get("plugins", {})
    except (OSError, ValueError):
        return False


CONFIG.mkdir(parents=True, exist_ok=True)
real_before = in_real_config()

if install("main") != 0:
    print("FAIL: the plain install of main reported a failure (see its banner).")
    sys.exit(1)
clone, plugin = installed()
print(f"after main:   clone {clone[:7] or '-'}   plugin {(plugin or '-')[:7]}")
if in_real_config() and not real_before:
    print(f"FAIL: the test install put the toolkit plugin into the real config ({REAL}).")
    sys.exit(1)
if not plugin:
    print("FAIL: the plain install left no toolkit plugin, so the branch step proves nothing.")
    sys.exit(1)

code = install(HEAD_REF)
clone, plugin = installed()
print(f"after branch: clone {clone[:7] or '-'}   plugin {(plugin or '-')[:7]}   want {HEAD_SHA[:7]}")

bad = [name for name, sha in (("clone (hooks)", clone), ("plugin (skills)", plugin)) if sha != HEAD_SHA]
if bad:
    print(f"FAIL: installing {HEAD_REF} left the {' and the '.join(bad)} on another commit.")
    sys.exit(1)
if code != 0:
    print(f"FAIL: the branch install landed, but the installer exited {code} (see its banner).")
    sys.exit(1)
print(f"ok: installing {HEAD_REF} put the clone and the plugin both on {HEAD_SHA[:7]}")
