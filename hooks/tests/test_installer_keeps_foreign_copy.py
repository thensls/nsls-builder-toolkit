#!/usr/bin/env python3
"""install.sh never "updates" a toolkit copy from somewhere other than NSLS.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_installer_keeps_foreign_copy.py`.

A builder's Mac (2026-11) had the toolkit folder cloned from the builder's own
fork, made to contribute a skill in August, sitting on a feature branch. Nothing
updated it. The fix for a silent machine is to run the installer again, and the
installer updated an existing copy from that copy's own `origin`: here the fork,
708 commits behind NSLS. It would have reset the folder onto the fork's main and
printed "installed!". Now a copy whose origin is not NSLS is moved aside,
untouched, and a fresh copy cloned.

This runs the installer's own Step 1, cut from the real install.sh, against
local repositories in a temp folder. git runs with an isolated config so a
builder's own settings cannot change the fixture. Nothing is downloaded.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SH = (REPO / "install.sh").read_text(encoding="utf-8")
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + ("" if cond else f"  {detail}"))
    if not cond:
        failures.append(name)


def cut(start, end):
    a = SH.index(start)
    return SH[a:SH.index(end, a)]


STEP1 = cut("# --- Step 1: Install the org toolkit ---", "# --- Step 2:")
REPO_KEY = cut("repo_key() {", "\n}\n") + "\n}\n"
BANNER = SH[SH.index("# --- Done ---"):]
ISO = Path(tempfile.mkdtemp(prefix="keeps-foreign-iso-"))
(ISO / "nohooks").mkdir()
(ISO / "gitconfig").write_text(
    "[user]\n\tname = T\n\temail = t@t.test\n[commit]\n\tgpgsign = false\n"
    "[init]\n\tdefaultBranch = main\n[protocol \"file\"]\n\tallow = always\n"
    f"[core]\n\thooksPath = {ISO / 'nohooks'}\n")
ENV = {k: v for k, v in os.environ.items()
       if not k.startswith(("GIT_", "NSLS_TOOLKIT_", "CLAUDE_CONFIG_DIR"))}
ENV.update(GIT_CONFIG_GLOBAL=str(ISO / "gitconfig"), GIT_CONFIG_NOSYSTEM="1",
           GIT_TERMINAL_PROMPT="0")


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                          text=True, env=ENV).stdout.strip()


def commit(repo, name, text):
    (repo / name).write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "--quiet", "-m", f"add {name}")


def world(tmp):
    """NSLS (bare), a builder's fork of it (bare, behind), and a config dir."""
    tmp = Path(tmp)
    seed = tmp / "seed"
    seed.mkdir()
    git(seed, "init", "--quiet")
    commit(seed, "skill.md", "v1\n")
    fork = tmp / "fork.git"
    git(tmp, "clone", "--quiet", "--bare", str(seed), str(fork))
    commit(seed, "skill.md", "v2, released by NSLS after the fork\n")
    nsls = tmp / "nsls.git"
    git(tmp, "clone", "--quiet", "--bare", str(seed), str(nsls))
    cfg = tmp / ".claude"
    (cfg / "local-plugins").mkdir(parents=True)
    return nsls, fork, cfg, cfg / "local-plugins" / "nsls-builder-toolkit"


def step1(cfg, plugin, repo_url):
    script = ("set -euo pipefail\n"
              f'CONFIG_DIR="{cfg}"\nPLUGIN_DIR="{plugin}"\n'
              f'REPO_URL="{repo_url}"\nREPO_BRANCH="main"\n' + STEP1 + "\n")
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=ENV, timeout=120)
    return r.returncode, r.stdout + r.stderr


def kept(cfg):
    return sorted((cfg / "local-plugins").glob("nsls-builder-toolkit.kept-*"))


print("a copy cloned from the builder's fork (the Mac of 2026-11)")
with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(fork), str(plugin))
    git(plugin, "checkout", "--quiet", "-b", "add-my-skill")
    commit(plugin, "mine.md", "the builder's own skill\n")
    (plugin / "skill.md").write_text("an edit the builder never committed\n")
    rc, out = step1(cfg, plugin, nsls)
    copies = kept(cfg)
    check("the installer finishes", rc == 0, out[-400:])
    check("the toolkit folder is now a fresh copy of NSLS, on main",
          git(plugin, "remote", "get-url", "origin") == str(nsls)
          and git(plugin, "rev-parse", "HEAD") == git(nsls, "rev-parse", "main")
          and git(plugin, "rev-parse", "--abbrev-ref", "HEAD") == "main", out[-400:])
    check("the old copy is kept beside it", len(copies) == 1, str(copies))
    if copies:
        old = copies[0]
        check("with its branch and the builder's commit",
              git(old, "rev-parse", "--abbrev-ref", "HEAD") == "add-my-skill"
              and git(old, "log", "-1", "--format=%s") == "add mine.md")
        check("and the uncommitted edit, untouched",
              (old / "skill.md").read_text() == "an edit the builder never committed\n")
        check("and it still follows the fork", git(old, "remote", "get-url", "origin") == str(fork))
        check("the installer says where it went, and why", str(old) in out and str(fork) in out
              and "never got NSLS's releases" in out, out[-400:])
    check("no half-finished download is left behind",
          not list((cfg / "local-plugins").glob("nsls-builder-toolkit.new-*")))

print("\ncopies that must be updated in place, never moved")
with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(fork), str(plugin))
    git(plugin, "remote", "set-url", "origin", str(nsls))
    rc, out = step1(cfg, plugin, nsls)
    check("a copy that follows NSLS is updated in place",
          rc == 0 and kept(cfg) == [] and git(plugin, "rev-parse", "HEAD") == git(nsls, "rev-parse", "main"), out[-400:])

with tempfile.TemporaryDirectory() as tmp:
    # Davo's own layout: origin is NSLS, the fork is a second remote.
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(nsls), str(plugin))
    git(plugin, "remote", "add", "fork", str(fork))
    rc, out = step1(cfg, plugin, nsls)
    check("a fork kept as a second remote is fine: updated in place, remote untouched",
          rc == 0 and kept(cfg) == [] and git(plugin, "remote", "get-url", "fork") == str(fork), out[-400:])

with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(nsls), str(plugin))
    rc, out = step1(cfg, plugin, str(nsls) + "/")
    check("the same repository written another way is the same",
          rc == 0 and kept(cfg) == [], out[-400:])

print("\nnever left with no toolkit")
with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(fork), str(plugin))
    before = git(plugin, "rev-parse", "HEAD")
    rc, out = step1(cfg, plugin, Path(tmp) / "unreachable.git")
    left = sorted(p.name for p in (cfg / "local-plugins").iterdir())
    check("a fresh copy that cannot be downloaded: stops, and the old folder is exactly where it was",
          rc == 1 and "Nothing was changed" in out and left == ["nsls-builder-toolkit"]
          and git(plugin, "rev-parse", "HEAD") == before
          and git(plugin, "remote", "get-url", "origin") == str(fork), f"{left} {out[-400:]}")

print("\nthe other shapes")
with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    rc, out = step1(cfg, plugin, nsls)
    check("no copy yet: a plain fresh clone, nothing kept",
          rc == 0 and kept(cfg) == [] and git(plugin, "rev-parse", "HEAD") == git(nsls, "rev-parse", "main"), out[-400:])

with tempfile.TemporaryDirectory() as tmp:
    nsls, fork, cfg, plugin = world(tmp)
    git(cfg / "local-plugins", "clone", "--quiet", str(fork), str(plugin))
    git(plugin, "remote", "remove", "origin")
    rc, out = step1(cfg, plugin, nsls)
    check("a copy with no origin at all is kept aside too, and says 'nowhere'",
          rc == 0 and len(kept(cfg)) == 1 and "updates from nowhere" in out, out[-400:])

if hasattr(os, "geteuid") and os.geteuid() != 0:
    with tempfile.TemporaryDirectory() as tmp:
        nsls, fork, cfg, plugin = world(tmp)
        git(cfg / "local-plugins", "clone", "--quiet", str(fork), str(plugin))
        before = git(plugin, "rev-parse", "HEAD")
        (cfg / "local-plugins").chmod(0o555)
        try:
            rc, out = step1(cfg, plugin, nsls)
        finally:
            (cfg / "local-plugins").chmod(0o755)
        check("a folder where nothing can be written: stops, says so, changes nothing",
              rc == 1 and "Nothing was changed" in out
              and git(plugin, "rev-parse", "HEAD") == before
              and git(plugin, "remote", "get-url", "origin") == str(fork), out[-400:])

print("\nwhat counts as the same repository")
NSLS = "https://github.com/thensls/nsls-builder-toolkit.git"


def key(url):
    r = subprocess.run(["bash", "-c", REPO_KEY + 'repo_key "$1"', "_", url],
                       capture_output=True, text=True, timeout=20)
    return r.stdout


same = ["https://github.com/thensls/nsls-builder-toolkit",
        "git@github.com:thensls/nsls-builder-toolkit.git",
        "ssh://git@github.com/thensls/nsls-builder-toolkit",
        "https://x-access-token:abc123@github.com/thensls/nsls-builder-toolkit.git",
        "https://github.com/TheNSLS/nsls-builder-toolkit/"]
differ = ["https://github.com/nsls-royce/nsls-builder-toolkit.git",
          "git@github.com:bdoyer-nsls/nsls-builder-toolkit.git",
          "https://github.com/thensls/nsls-builder-toolkit-old.git", ""]
check("https, ssh, a sign-in, .git, capitals and a trailing slash are all NSLS",
      all(key(u) == key(NSLS) for u in same), str([(u, key(u)) for u in same if key(u) != key(NSLS)]))
check("a fork, another repository, or no origin are not",
      all(key(u) != key(NSLS) for u in differ), str([u for u in differ if key(u) == key(NSLS)]))

print("\nthe closing message")


def banner(**variables):
    cfg = Path(tempfile.mkdtemp(prefix="keeps-foreign-banner-"))
    (cfg / "settings.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"hooks": [{"type": "command", "command": "nsls-builder-toolkit/hooks/session-start.py"}]}]}}))
    names = {"TEST_MODE": "0", "CONFIG_DIR": str(cfg), "PLUGIN_DIR": str(REPO),
             "INSTALL_FAILED": "", "UPDATE_FAILED": "0", "CLAUDE_BIN": "/somewhere/claude", **variables}
    head = "set -euo pipefail\n" + "".join(f'{k}="{v}"\n' for k, v in names.items())
    r = subprocess.run(["bash", "-c", head + BANNER], capture_output=True, text=True, timeout=120, env=ENV)
    return r.stdout


out = banner(KEPT_COPY="/x/local-plugins/nsls-builder-toolkit.kept-20261113-120000",
             KEPT_FROM="https://github.com/nsls-royce/nsls-builder-toolkit.git")
check("a kept copy is named again at the end, with where it updated from",
      "YOUR OLD COPY IS KEPT" in out and "nsls-builder-toolkit.kept-20261113-120000" in out
      and "nsls-royce" in out, out[-600:])
check("and nothing is said when nothing was kept (and an unset name is not an error)",
      "YOUR OLD COPY IS KEPT" not in banner() and "NEXT STEP" in banner())

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
