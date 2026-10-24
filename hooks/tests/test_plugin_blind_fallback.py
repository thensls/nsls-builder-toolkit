#!/usr/bin/env python3
"""A machine that can't read the published commit still updates, once a day.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_plugin_blind_fallback.py`.

Since 3.29.0 the session hook asks the marketplace clone's remote for its latest
commit (a 3-second `ls-remote`) and runs `claude plugin update` only when that
differs from the installed one. Before, it ran the update once a day whatever
GitHub said. Where the read keeps failing (a proxy, a slow link, a broken
remote), the new check returned early every time: the toolkit stopped updating
and nothing said so.

Now, after a day with no successful read, the hook runs the old unconditional
update once and waits another day. It never reinstalls on that path: with no
published commit there is no evidence of drift, and a reinstall starts by
uninstalling.

The marketplace clone's remote points at a folder that doesn't exist, so the
read fails the way it does offline. Every CLI call goes to a fake `claude` on
PATH that records what it was asked. No network, no real install touched.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from contextlib import redirect_stdout
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "session-start.py"
PLUGIN_KEY = "nsls-builder-toolkit@nsls-toolkit"
OLD = "58b5a0227d37a72f3baaf911226e7b318ef4c497"
DAY = 86400

failures = []


def check(label, cond, detail=""):
    print(f"{'ok  ' if cond else 'FAIL'} {label} {'' if cond else detail}")
    if not cond:
        failures.append(label)


FAKE_CLAUDE = textwrap.dedent('''\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    args = sys.argv[1:]
    Path(os.environ["FAKE_LOG"]).open("a").write(" ".join(args) + "\\n")
    if args[:2] == ["plugin", "update"]:
        if os.environ.get("FAKE_UPDATE_FAILS"):
            sys.exit(1)
        new_path = os.environ.get("FAKE_NEW_PATH")
        if new_path:
            for name in os.environ["FAKE_NEW_SKILLS"].split(","):
                d = Path(new_path) / "skills" / name
                d.mkdir(parents=True, exist_ok=True)
                (d / "SKILL.md").write_text(f"---\\nname: {name}\\n---\\n")
            reg = Path(os.environ["FAKE_REGISTRY"])
            d = json.loads(reg.read_text())
            d["plugins"]["nsls-builder-toolkit@nsls-toolkit"] = [{
                "scope": "user", "version": "3.7.0", "installPath": new_path,
                "gitCommitSha": "0" * 40}]
            reg.write_text(json.dumps(d))
    sys.exit(0)
''')


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   text=True, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})


class Machine:
    """A fake ~/.claude with 3.6.0 installed and a marketplace clone whose
    remote can't be read. `seen_ago`: seconds since the published commit was
    last read (None: never recorded)."""

    def __init__(self, tmp, seen_ago=None, reachable=False):
        self.root = Path(tmp)
        self.config = self.root / "claude-config"
        self.install_path = (self.config / "plugins" / "cache" / "nsls-toolkit"
                             / "nsls-builder-toolkit" / "3.6.0")
        for name in ("alpha", "beta"):
            d = self.install_path / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n")
        self.registry = self.config / "plugins" / "installed_plugins.json"
        self.registry.write_text(json.dumps({"version": 1, "plugins": {PLUGIN_KEY: [{
            "scope": "user", "version": "3.6.0", "installPath": str(self.install_path),
            "gitCommitSha": OLD}]}}))
        (self.config / "settings.json").write_text(json.dumps({"enabledPlugins": {PLUGIN_KEY: True}}))
        self.seen = self.config / ".nsls-plugin-published-seen"
        self.fresh = self.config / ".nsls-plugin-fresh-check"
        self.marker = self.config / ".nsls-plugin-update-check"
        if seen_ago is not None:
            self.seen.write_text(f"{int(time.time() - seen_ago)}\n")

        market = self.config / "plugins" / "marketplaces" / "nsls-toolkit"
        market.mkdir(parents=True)
        git(market, "init", "-q", "-b", "main")
        git(market, "config", "user.email", "t@example.test")
        git(market, "config", "user.name", "t")
        (market / "f").write_text("1")
        git(market, "add", "-A")
        git(market, "commit", "-q", "-m", "c")
        head = subprocess.run(["git", "-C", str(market), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        git(market, "remote", "add", "origin",
            str(market) if reachable else str(self.root / "no-such-remote"))
        if reachable:  # installed == published: the cheap check finds it level
            self.registry.write_text(self.registry.read_text().replace(OLD, head))

        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        (bin_dir / "claude").write_text(FAKE_CLAUDE)
        (bin_dir / "claude").chmod(0o755)
        self.log = self.root / "calls.log"
        self.log.write_text("")
        self.env = {
            "CLAUDE_CONFIG_DIR": str(self.config),
            "PATH": f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            "FAKE_LOG": str(self.log), "FAKE_REGISTRY": str(self.registry),
        }

    def calls(self):
        return [line for line in self.log.read_text().splitlines() if line]

    def seen_age(self):
        try:
            return time.time() - float(self.seen.read_text().strip())
        except Exception:
            return None

    def run(self, **kwargs):
        """A fresh copy of the hook, ensure_plugin_fresh, and what it printed.
        The 10-minute throttle is cleared first: each call is a new session."""
        self.fresh.unlink(missing_ok=True)
        saved = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        try:
            spec = importlib.util.spec_from_file_location("session_start_blind", HOOK)
            hook = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hook)
            buf = io.StringIO()
            with redirect_stdout(buf):
                hook.ensure_plugin_fresh(**kwargs)
            return buf.getvalue()
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


UPDATE = f"plugin update {PLUGIN_KEY}"

print("first failed read: the clock starts, nothing runs")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    out = m.run()
    check("no CLI call", m.calls() == [], m.calls())
    check("silent", out.strip() == "", out)
    check("the clock starts now", m.seen_age() is not None and m.seen_age() < 60, m.seen_age())

print("\nunder a day without a read: still waits")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY - 3600)
    m.run()
    check("no CLI call", m.calls() == [], m.calls())

print("\nover a day without a read: the old daily update runs once")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY + 3600)
    out = m.run()
    check("exactly one plugin update", m.calls() == [UPDATE], m.calls())
    check("no reinstall on a guess", not any("install" in c and "update" not in c for c in m.calls()))
    check("silent when nothing new arrived", out.strip() == "", out)
    check("the clock restarts", m.seen_age() is not None and m.seen_age() < 60, m.seen_age())
    check("the legacy daily marker is touched (the migration rescue stays quiet)", m.marker.exists())
    m.run()
    check("the next session that day runs nothing", m.calls() == [UPDATE], m.calls())

print("\nthe fallback update fails: tried again tomorrow, not every session")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY + 3600)
    m.env["FAKE_UPDATE_FAILS"] = "1"
    out = m.run()
    check("one attempt", m.calls() == [UPDATE], m.calls())
    check("silent", out.strip() == "", out)
    m.run()
    check("no second attempt the same day", m.calls() == [UPDATE], m.calls())

print("\nthe fallback brings new skills: they are announced")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY + 3600)
    m.env.update(FAKE_NEW_PATH=str(m.install_path.parent / "3.7.0"),
                 FAKE_NEW_SKILLS="alpha,beta,quicknote")
    out = m.run()
    check("names the new skill", "/quicknote" in out, out)
    check("names only the new one", "/alpha" not in out and "/beta" not in out, out)

print("\nshort of hook time: hands it to the next session")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY + 3600)
    m.env["NSLS_HOOK_STARTED_AT"] = str(int(time.time()) - 80)
    m.run()
    check("no CLI call", m.calls() == [], m.calls())
    check("the clock is left alone, so the next session tries",
          m.seen_age() is not None and m.seen_age() > DAY, m.seen_age())

print("\na stamp in the future (clock moved back): restart it, never act on it")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=-30 * DAY)
    m.run()
    check("no CLI call", m.calls() == [], m.calls())
    check("the clock restarts at now", m.seen_age() is not None and abs(m.seen_age()) < 60, m.seen_age())

print("\na successful read resets the clock")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp, seen_ago=DAY + 3600, reachable=True)
    m.run()
    check("level: no CLI call", m.calls() == [], m.calls())
    check("the read is recorded", m.seen_age() is not None and m.seen_age() < 60, m.seen_age())

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all passed")
