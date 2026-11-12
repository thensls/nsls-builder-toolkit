#!/usr/bin/env python3
# windows-ci: python | The Personal Toolkit folder follows the copy Claude delivers, and never overwrites its owner's changes
"""The Personal Toolkit folder is kept current from the copy NSLS delivers through Claude.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_personal_delivery.py`.

Once NSLS's repository is private, a computer with no GitHub sign-in cannot
pull the Personal Toolkit. NSLS's Claude organization can deliver it as a
plugin, and hooks/personal_delivery.py copies that into the folder everything
already points at. What this pins, in order of how much it would hurt:

1. With nothing delivered, NOTHING changes: no file, no setting, no git call.
   That is every computer today.
2. A file its owner changed is never overwritten or removed without their yes,
   and with their yes it is moved aside first, never deleted.
3. A fork, a checkout with the owner's own work, and a checkout that is newer
   than the delivered copy are left exactly as they are.
4. A checkout holding nothing of its owner's is taken over: its .git is kept
   under another name, the installers' update entries leave settings.json, and
   git can no longer act on the folder or climb past it.
5. A folder that follows the delivered copy picks up each new version, and a
   file NSLS stopped shipping goes only on the second look.

Real git, real files, temporary folders. No network: the "GitHub" remote is a
URL nothing ever fetches.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
PLUGIN = "nsls-personal-toolkit"
ORG = "11111111-2222-3333-4444-555555555555"
ACCT = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OTHER = "99999999-8888-7777-6666-555555555555"
NSLS_URL = "https://github.com/thensls/nsls-personal-toolkit.git"
WINDOWS = os.name == "nt"

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


# git must behave the same on every machine that runs this: no system or
# personal configuration (a global hooks path, autocrlf, a default branch).
_EMPTY = tempfile.NamedTemporaryFile(prefix="gitconfig-", delete=False)
_EMPTY.close()
os.environ["GIT_CONFIG_GLOBAL"] = _EMPTY.name
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"


def git(where, *args):
    r = subprocess.run(["git", "-C", str(where), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        *args], capture_output=True, text=True)
    return r.returncode, (r.stdout or "").strip()


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def toolkit_files(version, extra=None):
    files = {
        ".claude-plugin/plugin.json": json.dumps({"name": PLUGIN, "version": version}) + "\n",
        ".gitignore": ".env\ncompanion/.venv/\nnotes.local\n",
        "skills/open-day/SKILL.md": f"---\nname: open-day\ndescription: plan the day\n---\nopen day {version}\n",
        "skills/close-day/SKILL.md": "---\nname: close-day\ndescription: close the day\n---\nclose day\n",
        "skills/old-skill/SKILL.md": "---\nname: old-skill\ndescription: retired later\n---\nold\n",
        "companion/ensure-companion.sh": "#!/usr/bin/env bash\necho companion\n",
        "hooks/session-start.py": "#!/usr/bin/env python3\nprint('personal hook')\n",
        "README.md": f"Personal Toolkit {version}\n",
    }
    files.update(extra or {})
    return files


def lay(root, files):
    for rel, text in files.items():
        write(Path(root) / rel, text)


class Machine:
    """A throwaway Claude config directory, signed in to the NSLS account."""

    def __init__(self, tmp):
        self.cfg = Path(tmp) / "home" / ".claude"
        self.cfg.mkdir(parents=True)
        write(self.cfg / ".claude.json", json.dumps(
            {"oauthAccount": {"organizationUuid": ORG, "accountUuid": ACCT}}))
        self.folder = self.cfg / "local-plugins" / PLUGIN
        self.copy = self.cfg / "plugins" / "synced" / f"{ORG}_{ACCT}" / PLUGIN
        self.upstream = Path(tmp) / "upstream"
        self.ss = None

    def deliver(self, version, extra=None, account=None, drop=()):
        """Put (or replace) the copy Claude delivers."""
        copy = self.copy if account is None else (
            self.cfg / "plugins" / "synced" / f"{ORG}_{account}" / PLUGIN)
        files = toolkit_files(version, extra)
        for rel in drop:
            files.pop(rel, None)
            if (copy / rel).exists():
                (copy / rel).unlink()
                parent = (copy / rel).parent
                while parent != copy and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
        lay(copy, files)
        return copy

    def checkout(self, version, url=NSLS_URL):
        """The folder as install.sh leaves it: a clone of NSLS's repository."""
        if not self.upstream.exists():
            self.upstream.mkdir(parents=True)
            git(self.upstream, "init", "-q", "-b", "main")
        lay(self.upstream, toolkit_files(version))
        git(self.upstream, "add", "-A")
        git(self.upstream, "commit", "-q", "-m", f"release {version}")
        self.folder.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(self.upstream), str(self.folder)],
                       capture_output=True, text=True)
        git(self.folder, "remote", "set-url", "origin", url)
        # What every real folder holds that git ignores: the person's own.
        write(self.folder / ".env", "SECRET=1\n")
        write(self.folder / "companion/.venv/pyvenv.cfg", "home = somewhere\n")

    def settings(self, hooks=None, **extra):
        data = dict(extra)
        if hooks is not None:
            data["hooks"] = {"SessionStart": hooks}
        write(self.cfg / "settings.json", json.dumps(data, indent=2))

    def load(self):
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.cfg)
        os.environ["NSLS_NO_PLUGIN_MIGRATION"] = "1"
        spec = importlib.util.spec_from_file_location(f"ss_{time.time_ns()}", HOOKS / "session-start.py")
        self.ss = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.ss)
        self.ss._personal_delivery().SETTLE_SECONDS = 0
        return self.ss

    def run(self, request=None):
        """One pass, as a session start (or a request) makes it. (result, stdout)."""
        if self.ss is None:
            self.load()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            res = self.ss.deliver_personal_toolkit(request=request)
        return res, out.getvalue()

    def text(self, rel):
        return (self.folder / rel).read_text(encoding="utf-8")

    def marker(self):
        try:
            return json.loads((self.folder / ".delivered-by-claude.json").read_text(encoding="utf-8"))
        except Exception:
            return None


def tree(root):
    """Every file under root with its bytes: proof that nothing changed."""
    found = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def pull_entry(folder):
    return {"type": "command", "timeout": 20,
            "command": f'unset GIT_DIR GIT_WORK_TREE; git -C "{folder}" pull --ff-only --quiet'}


def sync_entry(folder):
    return {"type": "command", "timeout": 20,
            "command": f'"/usr/bin/python3" "{folder}/hooks/session-start.py" --no-pull'}


BUILDER_HOOK = {"type": "command", "command": 'bash "/x/nsls-builder-toolkit/hooks/run-hook.sh" session-start'}


def outcome(res):
    return None if res is None else res.get("outcome")


saved_env = dict(os.environ)

print("1. nothing delivered: nothing changes")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.settings([{"matcher": "startup|resume", "hooks": [pull_entry(m.folder), sync_entry(m.folder)]}])
    before, settings_before = tree(m.folder), (m.cfg / "settings.json").read_bytes()
    res, said = m.run()
    check("no delivered copy: the pass returns nothing", res is None, str(res))
    check("the folder is byte for byte what it was, .git included", tree(m.folder) == before)
    check("settings.json is untouched", (m.cfg / "settings.json").read_bytes() == settings_before)
    check("and nothing is said", said == "", said)

    m.deliver("2.0.0", account=OTHER)
    res, said = m.load() and m.run()
    check("a copy delivered to ANOTHER account is not this account's", res is None and tree(m.folder) == before)

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("2.0.0")
    before = tree(m.folder)
    m.settings(enabledPlugins={f"{PLUGIN}@synced": False})
    res, _ = m.run()
    check("a delivered copy this computer switched off changes nothing", res is None and tree(m.folder) == before)
    m.settings(syncClaudeAiPlugins=False)
    res, _ = m.load() and m.run()
    check("and neither does one behind the all-plugins switch", res is None and tree(m.folder) == before)

print("2. no folder yet: it is made from the delivered copy")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    res, said = m.run()
    check("the folder is created", outcome(res) == "created", str(res))
    check("with the delivered files", m.text("skills/open-day/SKILL.md").endswith("open day 2.0.0\n"))
    check("and a record of what was delivered", (m.marker() or {}).get("complete") is True
          and (m.marker() or {}).get("version") == "2.0.0")
    check("a new folder is not news: nothing is said", said == "", said)
    check("it counts as following the delivered copy", m.ss._follows_delivered_copy(m.folder))
    if not WINDOWS:
        check("a script stays runnable", os.access(m.folder / "companion/ensure-companion.sh", os.X_OK))
    rc, _ = git(m.folder, "rev-parse", "--show-toplevel")
    check("git refuses to act on it", rc != 0)
    res, said = m.run()
    check("a second pass finds it current", outcome(res) == "current" and said == "", str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    write(m.folder / ".env", "BUILDER_EMAIL=someone@example.invalid\n")   # /nsls-setmeup wrote it first
    res, _ = m.run()
    check("a folder holding only a pre-written .env is filled in", outcome(res) == "created", str(res))
    check("and the .env is kept", m.text(".env") == "BUILDER_EMAIL=someone@example.invalid\n")

print("3. a folder that follows the delivered copy picks up each version")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    write(m.folder / ".env", "SECRET=1\n")
    write(m.folder / "companion/.venv/pyvenv.cfg", "home = somewhere\n")
    write(m.folder / "skills/my-own/SKILL.md", "mine\n")
    stamp = (m.folder / "skills/close-day/SKILL.md").stat().st_mtime_ns
    m.deliver("2.1.0", extra={"skills/new-skill/SKILL.md": "new\n"}, drop=("skills/old-skill/SKILL.md",))
    res, said = m.load() and m.run()
    check("the new version is applied", outcome(res) == "updated" and m.text("README.md") == "Personal Toolkit 2.1.0\n", str(res))
    check("a new file arrives", m.text("skills/new-skill/SKILL.md") == "new\n")
    check("an unchanged file is not rewritten", (m.folder / "skills/close-day/SKILL.md").stat().st_mtime_ns == stamp)
    check("their own files are untouched", m.text(".env") == "SECRET=1\n" and m.text("skills/my-own/SKILL.md") == "mine\n"
          and m.text("companion/.venv/pyvenv.cfg") == "home = somewhere\n")
    check("an update is not news either", said == "", said)
    check("a file NSLS stopped shipping stays for one more look", (m.folder / "skills/old-skill/SKILL.md").exists()
          and (m.marker() or {}).get("pending") == ["skills/old-skill/SKILL.md"])
    res, _ = m.run()
    check("and is removed on the second look", outcome(res) == "updated" and not (m.folder / "skills/old-skill").exists(), str(res))
    res, _ = m.run()
    check("then the folder is current", outcome(res) == "current" and (m.marker() or {}).get("pending") == [])

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    m.deliver("2.1.0", drop=("skills/old-skill/SKILL.md",))
    m.load() and m.run()                       # old-skill is now waiting for its second look
    m.deliver("2.1.1")                         # ...and NSLS ships it again (the first look was a half-written copy)
    res, _ = m.load() and m.run()
    check("a file missing from one look and back at the next is never deleted",
          outcome(res) == "updated" and (m.folder / "skills/old-skill/SKILL.md").exists()
          and (m.marker() or {}).get("pending") == [], str(res))

print("4. a file its owner changed is never replaced without their yes")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    write(m.folder / "skills/open-day/SKILL.md", "MY OWN open day\n")
    res, said = m.run()
    check("their edit alone, with nothing new from NSLS, is not a problem", outcome(res) == "current" and said == "", str(res))
    m.deliver("2.1.0")
    before = tree(m.folder)
    res, said = m.load() and m.run()
    check("a new version does not overwrite it: updates pause", outcome(res) == "paused"
          and res.get("changed") == ["skills/open-day/SKILL.md"], str(res))
    check("nothing in the folder changed", tree(m.folder) == before)
    check("Claude is told which file, and how to take NSLS's version",
          "paused" in said and "skills/open-day/SKILL.md" in said and "personal-delivery adopt" in said
          and "NEVER hand them a command" in said, said)
    res, said = m.run()
    check("and told once a day, not every session", outcome(res) == "paused" and said == "", said)
    res, _ = m.run(request="adopt")
    aside = Path(res.get("set_aside", "missing"))
    check("with their yes, NSLS's version is written", outcome(res) == "updated"
          and m.text("skills/open-day/SKILL.md").endswith("open day 2.1.0\n"), str(res))
    check("and their version was moved aside, not deleted",
          (aside / "skills/open-day/SKILL.md").read_text(encoding="utf-8") == "MY OWN open day\n"
          if aside.exists() else False, str(res))
    check("the set-aside folder sits inside the toolkit folder", m.folder in aside.parents)
    res, _ = m.run()
    check("after that the folder is current again", outcome(res) == "current", str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    (m.folder / "skills/close-day/SKILL.md").unlink()      # "delete what you don't use"
    m.deliver("2.1.0")
    res, _ = m.load() and m.run()
    check("a file they removed is not put back behind their back", outcome(res) == "paused"
          and res.get("changed") == ["skills/close-day/SKILL.md"] and not (m.folder / "skills/close-day/SKILL.md").exists(), str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    write(m.folder / "notes.local", "my notes\n")           # their file, where NSLS later ships one
    m.deliver("2.1.0", extra={"notes.local": "NSLS notes\n"})
    res, _ = m.load() and m.run()
    check("a file of theirs sitting where NSLS now ships one is theirs", outcome(res) == "paused"
          and res.get("changed") == ["notes.local"] and m.text("notes.local") == "my notes\n", str(res))

print("5. a copy that stops half way finishes at the next session")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    m.deliver("2.1.0", extra={"skills/new-skill/SKILL.md": "new\n"})
    ss = m.load()
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        res = ss.deliver_personal_toolkit(deadline=time.monotonic() - 1)
    check("out of time: the pass says so", outcome(res) == "retry" and (m.marker() or {}).get("complete") is False, str(res))
    res, _ = m.run()
    check("and the next one finishes it, without mistaking its own half-copy for the owner's edits",
          outcome(res) == "updated" and m.text("skills/new-skill/SKILL.md") == "new\n"
          and (m.marker() or {}).get("complete") is True, str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    ss = m.load()
    pd = ss._personal_delivery()
    real = pd._listing
    looks = []

    def moving(root):
        files, stats = real(root)
        looks.append(1)
        if len(looks) > 1:                      # the copy changed between two looks
            stats = dict(stats, **{"README.md": (1, 1)})
        return files, stats

    pd._listing = moving
    try:
        res, _ = m.run()
    finally:
        pd._listing = real
    check("a delivered copy still being written is left for the next session",
          outcome(res) == "retry" and not (m.folder / "skills").exists(), str(res))

print("6. a checkout holding nothing of its owner's is taken over")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    git(tmp, "init", "-q", "-b", "main")        # the home directory is itself a repository (dotfiles)
    m.checkout("1.9.0")
    m.deliver("2.0.0", extra={"skills/new-skill/SKILL.md": "new\n"})
    m.settings([{"matcher": "startup|resume", "hooks": [BUILDER_HOOK]},
                {"matcher": "startup|resume", "hooks": [pull_entry(m.folder), sync_entry(m.folder)]}])
    res, said = m.run()
    check("first the installers' update entries leave settings.json", outcome(res) == "entries" and said == "", str(res))
    left = json.loads((m.cfg / "settings.json").read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    check("only those: the Builder Toolkit's hook stays", left == [{"matcher": "startup|resume", "hooks": [BUILDER_HOOK]}], str(left))
    check("settings.json as it was is kept beside it", (m.cfg / "settings.json.pre-personal-delivery").exists())
    check("the checkout itself is not touched yet", (m.folder / ".git").is_dir() and m.marker() is None)
    res, said = m.run()
    check("at the next session the folder is taken over", outcome(res) == "converted", str(res))
    check("it carries the delivered version", m.text("skills/open-day/SKILL.md").endswith("open day 2.0.0\n")
          and m.text("skills/new-skill/SKILL.md") == "new\n")
    check("its .git is kept under another name, whole", (m.folder / ".git.before-claude-delivery" / "HEAD").is_file())
    check(".git is now a placeholder file", (m.folder / ".git").is_file())
    rc, top = git(m.folder, "rev-parse", "--show-toplevel")
    check("so git stops there and never climbs to the repository above", rc != 0, top)
    check("their own ignored files are untouched", m.text(".env") == "SECRET=1\n"
          and m.text("companion/.venv/pyvenv.cfg") == "home = somewhere\n")
    check("Claude is told once, with nothing for the builder to do",
          "now follows the copy NSLS delivers through Claude" in said and "nothing for the builder to do" in said, said)
    check("the record says where it came from", (m.marker() or {}).get("from", {}).get("kind") == "checkout"
          and len((m.marker() or {}).get("from", {}).get("head", "")) == 40)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        m.ss.git_pull(deadline=time.monotonic() + 5)
        m.ss.report_personal_fork_drift(deadline=time.monotonic() + 5)
    check("the hook's own pull and fork check leave it alone, silently", out.getvalue() == "", out.getvalue())
    res, said = m.run()
    check("from then on it is simply current", outcome(res) == "current" and said == "", str(res))
    m.deliver("2.1.0")
    res, _ = m.load() and m.run()
    check("and the next version arrives with no GitHub involved", outcome(res) == "updated"
          and m.text("README.md") == "Personal Toolkit 2.1.0\n", str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("1.9.0")
    res, _ = m.run()
    check("with no update entries registered it is taken over at once", outcome(res) == "converted", str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("2.0.0")
    ss = m.load()
    pd = ss._personal_delivery()
    calls = []
    real_update = ss._update_checkout
    ss._update_checkout = lambda plugin_dir, deadline: (calls.append(Path(plugin_dir).name), (None, ""))[1]
    with pd._Lock(m.cfg) as held:               # another session's hook is mid take-over
        res, _ = m.run()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ss.git_pull(deadline=time.monotonic() + 5)
    ss._update_checkout = real_update
    check("while another session takes the folder over, this one waits its turn",
          held and outcome(res) == "retry" and res.get("why") == "busy" and (m.folder / ".git").is_dir(), str(res))
    check("and keeps its own git pull out of that folder for this run", PLUGIN not in calls, str(calls))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("2.0.0")
    pd = m.load()._personal_delivery()
    write(m.folder / ".delivered-by-claude.json", json.dumps(
        {"schema": 1, "plugin": PLUGIN, "files": {}, "complete": False}))   # stopped before .git moved
    check("a take-over interrupted before .git moved is still a checkout to everything else",
          pd.state(m.folder) == "taking" and not m.ss._follows_delivered_copy(m.folder))
    res, _ = m.run()
    check("and is finished at the next session", outcome(res) == "converted" and (m.folder / ".git").is_file(), str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("2.0.0")
    pd = m.load()._personal_delivery()
    write(m.folder / ".delivered-by-claude.json", json.dumps(
        {"schema": 1, "plugin": PLUGIN, "files": {}, "complete": False}))
    write(m.folder / "README.md", "edited since\n")
    res, _ = m.run()
    check("an interrupted take-over of a folder its owner has since edited is dropped, not finished",
          outcome(res) == "kept" and pd.state(m.folder) == "checkout" and m.text("README.md") == "edited since\n", str(res))

print("7. anything of the owner's keeps the checkout on GitHub, untouched")


def kept_case(name, prepare, why, version="2.0.0", url=NSLS_URL, expect_notice=None):
    with tempfile.TemporaryDirectory() as tmp:
        m = Machine(tmp)
        m.checkout("1.9.0", url=url)
        m.deliver(version)
        m.settings([{"matcher": "startup|resume", "hooks": [pull_entry(m.folder)]}])
        prepare(m)
        before, settings_before = tree(m.folder), (m.cfg / "settings.json").read_bytes()
        res, said = m.run()
        ok = (outcome(res) == "kept" and res.get("why") == why and tree(m.folder) == before
              and (m.cfg / "settings.json").read_bytes() == settings_before)
        check(f"{name}: left exactly as it is", ok, f"{res} said={said!r}")
        if expect_notice is True:
            check(f"{name}: Claude is told, with the choice", "holds work of their own" in said
                  and "stay on GitHub" in said and "personal-delivery adopt" in said, said)
        elif expect_notice is False:
            check(f"{name}: nothing is said", said == "", said)
        return m


def commit_ahead(m):
    write(m.folder / "skills/open-day/SKILL.md", "my committed change\n")
    git(m.folder, "commit", "-q", "-am", "mine")


def stashed(m):
    write(m.folder / "README.md", "stashed\n")
    git(m.folder, "stash", "-q")


kept_case("an edited file", lambda m: write(m.folder / "README.md", "edited\n"), "own-changes", expect_notice=True)
kept_case("an edited file, with the folder already on the delivered version",
          lambda m: write(m.folder / "README.md", "edited\n"), "own-changes", version="1.9.0", expect_notice=False)
kept_case("a new file of their own", lambda m: write(m.folder / "skills/mine/SKILL.md", "mine\n"), "own-changes")
kept_case("a commit NSLS does not have", commit_ahead, "own-changes")
kept_case("a second branch", lambda m: git(m.folder, "branch", "experiment"), "own-changes")
kept_case("a stash", stashed, "own-changes")
kept_case("a linked worktree (what /unblock sets up)",
          lambda m: git(m.folder, "worktree", "add", "-q", str(m.cfg / "elsewhere"), "-b", "wt"), "own-changes")
kept_case("their own fork", lambda m: None, "fork", url="https://github.com/someone/nsls-personal-toolkit.git", expect_notice=False)
kept_case("the keep-on-GitHub file", lambda m: write(m.folder / ".keep-on-github", ""), "opt-out", expect_notice=False)
kept_case("a checkout newer than the delivered copy", lambda m: None, "older", version="1.8.0", expect_notice=False)
kept_case("an ignored file of theirs where NSLS now ships one",
          lambda m: (write(m.folder / "notes.local", "mine\n"), m.deliver("2.0.0", extra={"notes.local": "NSLS\n"})),
          "own-changes")
kept_case("an update entry they edited by hand",
          lambda m: m.settings([{"hooks": [{"type": "command",
                                            "command": f'cd /tmp; git -C "{m.folder}" pull --rebase'}]}]),
          "edited-entry", expect_notice=False)

print("8. with their yes, a checkout with their own work is switched, and nothing is lost")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0")
    m.deliver("2.0.0")
    m.settings([{"matcher": "startup|resume", "hooks": [pull_entry(m.folder)]}])
    write(m.folder / "skills/open-day/SKILL.md", "MY edited open day\n")
    write(m.folder / "skills/mine/SKILL.md", "my own skill\n")
    res, _ = m.run(request="adopt")
    aside = Path(res.get("set_aside", "missing"))
    check("the folder is switched in one go", outcome(res) == "adopted" and (m.folder / ".git").is_file(), str(res))
    check("NSLS's version is in place", m.text("skills/open-day/SKILL.md").endswith("open day 2.0.0\n"))
    check("their edited file was moved aside", aside.exists()
          and (aside / "skills/open-day/SKILL.md").read_text(encoding="utf-8") == "MY edited open day\n", str(res))
    check("a skill of their own that NSLS does not ship stays where it was", m.text("skills/mine/SKILL.md") == "my own skill\n")
    check("the git history is kept", (m.folder / ".git.before-claude-delivery" / "HEAD").is_file())
    check("the update entry is gone", "pull" not in (m.cfg / "settings.json").read_text(encoding="utf-8"))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.checkout("1.9.0", url="https://github.com/someone/nsls-personal-toolkit.git")
    m.deliver("2.0.0")
    res, _ = m.run(request="adopt")
    check("a fork's owner can point their computer back at the standard copy the same way",
          outcome(res) == "adopted" and m.text("README.md") == "Personal Toolkit 2.0.0\n"
          and (m.marker() or {}).get("from", {}).get("kind") == "adopted", str(res))

print("9. a plain copy with no git")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    lay(m.folder, toolkit_files("2.0.0"))
    m.deliver("2.0.0")
    res, said = m.run()
    check("identical to the delivered copy: it simply starts following it", outcome(res) == "converted", str(res))
    check("and what Claude is told claims no git history that never existed",
          "now follows the copy NSLS delivers through Claude." in said and "git" not in said, said)

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    lay(m.folder, toolkit_files("1.5.0"))
    m.deliver("2.0.0")
    before = tree(m.folder)
    res, said = m.run()
    check("different from it: nobody can say whose the differences are, so it is left alone",
          outcome(res) == "kept" and res.get("why") == "own-changes" and tree(m.folder) == before, str(res))
    check("and Claude is told, because it is behind, without any talk of GitHub",
          "plain copy with nothing keeping it current" in said and "personal-delivery adopt" in said
          and "GitHub" not in said, said)
    res, _ = m.run(request="adopt")
    check("with their yes it is switched, the old files moved aside", outcome(res) == "adopted"
          and m.text("README.md") == "Personal Toolkit 2.0.0\n"
          and (Path(res["set_aside"]) / "README.md").read_text(encoding="utf-8") == "Personal Toolkit 1.5.0\n", str(res))

print("10. every update entry an installer ever wrote is recognised, and nothing else")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    pd = m.load()._personal_delivery()
    names = "GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR"
    env_paths = ",".join("Env:" + n for n in names.split())
    posix, win = "/Users/a b/.claude/local-plugins/nsls-personal-toolkit", r"C:\Users\a b\.claude\local-plugins\nsls-personal-toolkit"
    ours = [
        f'git -C "{posix}" pull --ff-only --quiet',
        f'git -C "{win}" pull --ff-only --quiet',
        f'unset {names}; git -C "{posix}" pull --ff-only --quiet',
        f'Remove-Item {env_paths} -ErrorAction Ignore; git -C "{win}" pull --ff-only --quiet',
        f'unset {names}; GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS= git -C "{posix}" pull --ff-only --quiet',
        f"Remove-Item {env_paths} -ErrorAction Ignore; $env:GIT_TERMINAL_PROMPT='0'; $env:GCM_INTERACTIVE='never'; "
        f'git -C "{win}" pull --ff-only --quiet',
        f'"/opt/homebrew/bin/python3" "{posix}/hooks/session-start.py" --no-pull',
        f'"C:\\Python312\\python.exe" "/c/Users/a b/.claude/local-plugins/nsls-personal-toolkit/hooks/session-start.py" --no-pull',
    ]
    theirs = [
        BUILDER_HOOK["command"],
        'echo "nsls-personal-toolkit is great"',
        f'git -C "{posix}-experiments" pull --ff-only --quiet',
        f'git -C "{posix}" status',
        f'"/usr/bin/python3" "{posix}/hooks/session-start.py"',
    ]
    edited = f'cd /x && git -C "{posix}" pull --ff-only --quiet'
    for cmd in ours:
        check(f"ours: {cmd[:60]}...", pd._is_ours(cmd))
    for cmd in theirs + [edited]:
        check(f"not ours: {cmd[:60]}", not pd._is_ours(cmd))
    hooks = [{"matcher": "startup|resume", "hooks": [{"type": "command", "command": c} for c in ours[:4]]},
             {"matcher": "startup", "hooks": [{"type": "command", "command": theirs[0]},
                                              {"type": "command", "command": ours[6]}]},
             {"hooks": [{"type": "command", "command": c} for c in theirs[1:]]}]
    m.settings(hooks, model="opus", permissions={"allow": [f"Bash(git -C {posix} pull:*)"]})
    raw = (m.cfg / "settings.json").read_bytes()
    (m.cfg / "settings.json").write_bytes(b"\xef\xbb\xbf" + raw)       # as an old PowerShell installer left it
    check("counted: five of ours, none edited", pd.update_entries(m.cfg) == (5, 0), str(pd.update_entries(m.cfg)))
    check("removed", pd.remove_update_entries(m.cfg) is True and pd.update_entries(m.cfg) == (0, 0))
    after = json.loads((m.cfg / "settings.json").read_text(encoding="utf-8-sig"))
    check("every other hook, in its own group, is exactly as it was",
          after["hooks"]["SessionStart"] == [
              {"matcher": "startup", "hooks": [{"type": "command", "command": theirs[0]}]},
              {"hooks": [{"type": "command", "command": c} for c in theirs[1:]]}], str(after["hooks"]))
    check("and so is the rest of the file", after["model"] == "opus"
          and after["permissions"] == {"allow": [f"Bash(git -C {posix} pull:*)"]})
    m.settings([{"hooks": [{"type": "command", "command": edited}]}])
    still = json.loads((m.cfg / "settings.json").read_text(encoding="utf-8"))
    check("an entry someone edited is counted as theirs and never removed",
          pd.update_entries(m.cfg) == (0, 1) and pd.remove_update_entries(m.cfg) is True
          and json.loads((m.cfg / "settings.json").read_text(encoding="utf-8")) == still
          and still["hooks"]["SessionStart"][0]["hooks"][0]["command"] == edited)

print("11. NSLS reshapes the toolkit, the owner reshapes their folder, a copy stops half way")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0", extra={"notes": "a file\n", "refs/a.md": "a\n", "refs/b.md": "b\n"})
    m.run()
    m.deliver("2.1.0", extra={"notes/one.md": "one\n", "refs": "now a file\n"},
              drop=("notes", "refs/a.md", "refs/b.md"))
    res, _ = m.load() and m.run()
    check("a file NSLS turned into a folder is replaced in one pass, not retried for ever",
          outcome(res) == "updated" and m.text("notes/one.md") == "one\n", str(res))
    check("and so is a folder NSLS turned into a file", (m.folder / "refs").is_file() and m.text("refs") == "now a file\n")

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0", extra={"notes": "a file\n"})
    m.run()
    write(m.folder / "notes", "MY notes\n")
    m.deliver("2.1.0", extra={"notes/one.md": "one\n"}, drop=("notes",))
    res, _ = m.load() and m.run()
    check("but a file they edited, where NSLS now ships a folder, is theirs: updates pause",
          outcome(res) == "paused" and res.get("changed") == ["notes"] and m.text("notes") == "MY notes\n", str(res))
    res, _ = m.run(request="adopt")
    check("and with their yes it is moved aside before the folder is written",
          outcome(res) == "updated" and m.text("notes/one.md") == "one\n"
          and (Path(res.get("set_aside", "missing")) / "notes").read_text(encoding="utf-8") == "MY notes\n", str(res))

if not WINDOWS:   # making a link needs a privilege a Windows test run may not have
    with tempfile.TemporaryDirectory() as tmp:
        m = Machine(tmp)
        m.deliver("2.0.0")
        m.run()
        outside = Path(tmp) / "their-dotfiles" / "open-day"
        write(outside / "SKILL.md", "their own, kept somewhere else\n")
        shutil.rmtree(m.folder / "skills/open-day")
        os.symlink(outside, m.folder / "skills/open-day")
        m.deliver("2.1.0")
        res, _ = m.load() and m.run()
        check("a folder they replaced with a link is theirs: updates pause, and the link is what is named",
              outcome(res) == "paused" and res.get("changed") == ["skills/open-day"], str(res))
        check("nothing behind the link was read as the toolkit's or written to",
              (outside / "SKILL.md").read_text(encoding="utf-8") == "their own, kept somewhere else\n")
        res, _ = m.run(request="adopt")
        aside = Path(res.get("set_aside", "missing"))
        check("with their yes the link itself is moved aside and a real folder takes its place",
              outcome(res) == "updated" and not (m.folder / "skills/open-day").is_symlink()
              and m.text("skills/open-day/SKILL.md").endswith("open day 2.1.0\n")
              and (aside / "skills/open-day").is_symlink(), str(res))
        check("and the place it pointed at is still untouched",
              (outside / "SKILL.md").read_text(encoding="utf-8") == "their own, kept somewhere else\n")

    if os.geteuid() != 0:   # root reads anything, so there is nothing to prove
        with tempfile.TemporaryDirectory() as tmp:
            m = Machine(tmp)
            m.deliver("2.0.0")
            m.run()
            copy = m.deliver("2.1.0")
            before = tree(m.folder)
            os.chmod(copy / "skills/close-day", 0)
            try:
                first, _ = m.load() and m.run()
                second, _ = m.run()
            finally:
                os.chmod(copy / "skills/close-day", 0o755)
            check("a delivered copy with a folder that cannot be read is no copy at all: nothing is updated",
                  first is None and second is None and tree(m.folder) == before, f"{first} {second}")
            check("so a skill in that folder is never mistaken for one NSLS stopped shipping",
                  (m.folder / "skills/close-day/SKILL.md").exists())

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    write(m.folder / "skills/old-skill/SKILL.md", "MY version of the old skill\n")
    m.deliver("2.1.0", drop=("skills/old-skill/SKILL.md",))
    res, said = m.load() and m.run()
    check("a file they edited that NSLS then stops shipping does not hold updates back",
          outcome(res) == "updated" and said == "" and m.text("README.md") == "Personal Toolkit 2.1.0\n", str(res))
    check("it is simply theirs from then on: kept, and no longer tracked",
          m.text("skills/old-skill/SKILL.md") == "MY version of the old skill\n"
          and "skills/old-skill/SKILL.md" not in (m.marker() or {}).get("files", {"skills/old-skill/SKILL.md": 1})
          and (m.marker() or {}).get("pending") == [])
    res, _ = m.run()
    check("and the next pass has nothing left to ask about", outcome(res) == "current", str(res))

with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    m.deliver("2.0.0")
    m.run()
    m.deliver("2.1.0")
    pd = m.load()._personal_delivery()
    real, asked = pd._out_of_time, []
    pd._out_of_time = lambda deadline: (asked.append(1), len(asked) > 2)[1]   # stops after two files
    try:
        res, _ = m.run()
    finally:
        pd._out_of_time = real
    check("a copy stopped after its first files says so", outcome(res) == "retry"
          and '"version": "2.1.0"' in m.text(".claude-plugin/plugin.json")
          and m.text("README.md") == "Personal Toolkit 2.0.0\n", str(res))
    m.deliver("2.2.0")                                   # NSLS publishes again before the next session
    res, said = m.load() and m.run()
    check("and a NEWER delivery still finishes it: the files it had already written are not taken for the owner's edits",
          outcome(res) == "updated" and said == "" and m.text("README.md") == "Personal Toolkit 2.2.0\n", f"{res} {said}")

print("12. on request: the launcher's `personal-delivery` command")
with tempfile.TemporaryDirectory() as tmp:
    m = Machine(tmp)
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(m.cfg), NSLS_NO_PLUGIN_MIGRATION="1", PYTHONUTF8="1")
    env.pop("CLAUDE_PLUGIN_ROOT", None)

    def ask(*words):
        r = subprocess.run([sys.executable, str(HOOKS / "session-start.py"), "--personal-delivery", *words],
                           capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
        return r.stdout

    said = ask("now")
    check("nothing delivered: it says so and changes nothing",
          said.startswith("PERSONAL_TOOLKIT_NOT_DELIVERED") and not m.folder.exists(), said)
    m.deliver("2.0.0")
    said = ask("now")
    check("delivered: the folder is made and the answer is plain",
          said.startswith("PERSONAL_TOOLKIT_READY: version 2.0.0") and (m.folder / "skills/open-day/SKILL.md").exists(), said)
    check("and its skills are pointed at straight away, with no restart",
          (m.cfg / "skills" / "open-day" / "SKILL.md").exists())
    write(m.folder / "README.md", "mine now\n")
    m.deliver("2.1.0")
    said = ask("now")
    check("their change holds the update, and the answer names the way through",
          said.startswith("PERSONAL_TOOLKIT_PAUSED") and "personal-delivery adopt" in said, said)
    said = ask("adopt")
    check("`adopt` takes NSLS's version and says where their file went",
          said.startswith("PERSONAL_TOOLKIT_READY: version 2.1.0") and ".set-aside" in said, said)
    if not WINDOWS:
        r = subprocess.run(["bash", str(HOOKS / "run-hook.sh"), "personal-delivery", "now"],
                           capture_output=True, text=True, env=env, timeout=120)
        check("the launcher passes the command through", r.stdout.startswith("PERSONAL_TOOLKIT_READY"), r.stdout + r.stderr)

os.environ.clear()
os.environ.update(saved_env)
try:
    os.unlink(_EMPTY.name)
except OSError:
    pass

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
