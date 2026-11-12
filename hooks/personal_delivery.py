#!/usr/bin/env python3
"""personal_delivery.py - keep the Personal Toolkit folder in step with the copy
NSLS delivers through Claude.

The Personal Toolkit lives in a folder on each computer,
<config>/local-plugins/nsls-personal-toolkit. Its skills, the companion and the
scheduled sweeps all point at that folder, and each person's own settings
(.env, the companion's Python environment, their update history) live inside
it. Until now the folder was a git checkout that pulled from GitHub with no
sign-in. Once the repository is private, that pull fails on every computer
with no GitHub sign-in, and says nothing.

NSLS's Claude organization can deliver the same toolkit as a plugin: Claude
Code downloads it by itself to

    <config>/plugins/synced/<organizationUuid>_<accountUuid>/nsls-personal-toolkit/

and replaces it when NSLS publishes. That copy is not somewhere a person's own
files can live (it is replaced whole), and nothing in the toolkit points at it.
So the folder stays, and this module copies the delivered files into it:

* no folder yet            -> the folder is made from the delivered copy;
* a folder this module set
  up or took over          -> brought to the delivered version, file by file;
* a git checkout of NSLS's
  repository holding
  nothing of its owner's   -> taken over: its .git is kept under another name,
                              and from then on the folder follows the delivered
                              copy (session-start.py decides whether a checkout
                              qualifies; this module knows nothing about git);
* anything else (a fork, a
  checkout or folder with
  the owner's own work)    -> never touched, unless its owner asks.

The rule that matters: a file its owner changed is never overwritten or removed
without being asked. A folder holding such a file is left exactly as it is and
the caller is told which files, so Claude can offer the choice. When the owner
says yes, every file replaced is first moved to .set-aside/ inside the folder.

With nothing delivered for the signed-in account, offer() returns None and no
function here does anything: every computer behaves as it did before.

Never raises. Plain stdlib.
"""

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

PLUGIN = "nsls-personal-toolkit"
# What a delivered copy must hold to count as whole enough to copy from.
NEEDS = ("skills",)

# Written into the folder once it follows the delivered copy. Holds what was
# delivered, file by file, so the next pass can tell NSLS's files from changes
# their owner made.
MARKER = ".delivered-by-claude.json"
# A checkout's own .git, kept under this name when the folder is taken over.
KEPT_GIT = ".git.before-claude-delivery"
# Where a file is copied before it is replaced at its owner's request.
SET_ASIDE = ".set-aside"
# An empty file with this name keeps a checkout on GitHub for good.
KEEP_ON_GITHUB = ".keep-on-github"
# What stands where a checkout's .git was, or would be. A folder with no .git
# at all is not safe: git climbs to the nearest parent repository, so the
# Windows session hook (which runs `git -C <folder> fetch` and a fast-forward
# on every toolkit folder that exists) and any old `git -C <folder> pull` still
# registered somewhere would update a person's dotfiles repository in ~/.claude
# or ~ instead. A .git FILE naming a folder that does not exist makes every git
# command stop here at once, with no network and no climbing.
TOMBSTONE = "gitdir: .git.delivered-by-claude\n"

SCHEMA = 1
# Claude's own limits for a delivered plugin are 5,000 files and 200 MB. A
# "copy" beyond them is not one this module will read.
MAX_FILES = 6000
MAX_BYTES = 250 * 1024 * 1024
# Claude Code refreshes the delivered copy in the background while the session
# hooks run. Before anything is copied from it, the copy is listed twice, this
# far apart: a listing that moved is a copy being written, left for the next
# session. (Not "no file newer than N seconds": if Claude rewrites the copy at
# every start, that would never be true at session start, and the folder would
# never update.)
SETTLE_SECONDS = 0.3

_SKIP_NAMES = {".git", MARKER, KEPT_GIT, SET_ASIDE, KEEP_ON_GITHUB,
               ".DS_Store", "Thumbs.db", "desktop.ini"}
_SKIP_DIRS = {"__pycache__"}
_VERSION = re.compile(r"^\d{1,5}\.\d{1,5}\.\d{1,5}\Z")


def _umask():
    try:
        mask = os.umask(0)
        os.umask(mask)
        return mask
    except Exception:
        return 0o022


_UMASK = _umask()


def _synced_copy():
    """The synced_copy module beside this file (it knows where Claude keeps the
    signed-in account's delivered plugins), or None."""
    try:
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        import synced_copy

        return synced_copy
    except Exception:
        return None


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def folder(cfg) -> Path:
    return Path(cfg) / "local-plugins" / PLUGIN


def version_of(root):
    """The toolkit version a folder carries (X.Y.Z), or None."""
    try:
        value = _read_json(Path(root) / ".claude-plugin" / "plugin.json").get("version")
        return value if isinstance(value, str) and _VERSION.match(value) else None
    except Exception:
        return None


def _version_tuple(text):
    try:
        return tuple(int(part) for part in str(text).split("."))
    except Exception:
        return None


def older(a, b) -> bool:
    """True when version `a` is known to be older than version `b`."""
    ta, tb = _version_tuple(a), _version_tuple(b)
    return ta is not None and tb is not None and ta < tb


def _sha(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plain_file(path) -> bool:
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except OSError:
        return False


def _there(path) -> bool:
    try:
        os.lstat(path)
        return True
    except OSError:
        return False


class Offer:
    """What NSLS delivers here: the copy's files, read once.

    `files` maps each path inside the copy (forward slashes) to the file.
    `signature` changes whenever any file's size or time does, and costs only a
    directory listing. `hashes` reads every file, so it is worked out only when
    the signature says something changed.
    """

    def __init__(self, root, files, stats):
        self.root = Path(root)
        self.files = files
        self.version = version_of(root)
        self._stats = stats
        self._hashes = None

    @property
    def signature(self) -> str:
        digest = hashlib.sha256()
        for rel in sorted(self._stats):
            size, mtime = self._stats[rel]
            digest.update(f"{rel}\0{size}\0{mtime}\n".encode("utf-8", "surrogateescape"))
        return digest.hexdigest()

    @property
    def hashes(self) -> dict:
        if self._hashes is None:
            self._hashes = {rel: _sha(path) for rel, path in self.files.items()}
        return self._hashes

    def settled(self) -> bool:
        """False while the copy is being written: a second listing, taken a
        moment later, differs from the first."""
        try:
            if SETTLE_SECONDS > 0:
                time.sleep(SETTLE_SECONDS)
            again = _listing(self.root)
            return bool(again) and again[1] == self._stats
        except Exception:
            return False


def _listing(root):
    """({path: file}, {path: (size, mtime_ns)}) for every regular file in a
    delivered copy, or None when it cannot be read whole. Links are never
    followed and never copied."""
    files, stats, total = {}, {}, 0
    root = Path(root)
    for here, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs
                         if d not in _SKIP_NAMES and d not in _SKIP_DIRS
                         and not os.path.islink(os.path.join(here, d)))
        for name in sorted(names):
            if name in _SKIP_NAMES or name.endswith(".pyc"):
                continue
            path = Path(here) / name
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                continue
            rel = path.relative_to(root).as_posix()
            files[rel] = path
            stats[rel] = (info.st_size, info.st_mtime_ns)
            total += info.st_size
            if len(files) > MAX_FILES or total > MAX_BYTES:
                return None
    return files, stats


def offer(cfg):
    """The copy NSLS delivers to the signed-in account, or None.

    None when there is none, when it belongs to another account, when this
    computer's settings switch it off, or when it cannot be read whole. None
    means: do nothing, exactly as before delivery existed.
    """
    try:
        sc = _synced_copy()
        if sc is None:
            return None
        root = sc.live_root(cfg, PLUGIN, NEEDS)
        if root is None or sc.switched_off(cfg, root, PLUGIN):
            return None
        listed = _listing(root)
        if not listed or not listed[0]:
            return None
        found = Offer(root, *listed)
        return found if found.version else None
    except Exception:
        return None


def read_marker(target):
    """The record of what was delivered into a folder, or None."""
    try:
        data = _read_json(Path(target) / MARKER)
        if (isinstance(data, dict) and data.get("plugin") == PLUGIN
                and isinstance(data.get("files"), dict)):
            return data
    except Exception:
        pass
    return None


def _write_marker(target, data):
    target = Path(target)
    fd, tmp = tempfile.mkstemp(prefix=".delivered-", dir=str(target))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=1, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, str(target / MARKER))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def state(target) -> str:
    """What sits where the Personal Toolkit folder should be.

    "none"       nothing, or a shell holding no toolkit (a pre-written .env)
    "delivered"  a folder that follows the delivered copy
    "taking"     a checkout whose take-over was interrupted before .git moved
    "checkout"   a git checkout
    "copy"       toolkit files with no git and no record: a copy from somewhere
    """
    target = Path(target)
    git = target / ".git"
    marked = read_marker(target) is not None
    if git.is_dir():
        return "taking" if marked else "checkout"
    if marked:
        return "delivered"
    if _plain_file(git):
        try:
            if git.read_text(encoding="utf-8", errors="replace") != TOMBSTONE:
                return "checkout"  # a linked worktree or submodule: still git's
        except Exception:
            return "checkout"
    if (target / "skills").is_dir() or (target / ".claude-plugin" / "plugin.json").is_file():
        return "copy"
    return "none"


def is_delivered(target) -> bool:
    return state(target) == "delivered"


def owner_changes(target, baseline, incoming) -> list:
    """Paths in the folder that are their owner's, not NSLS's.

    `baseline` is what NSLS last put there ({path: sha256}); `incoming` is what
    NSLS delivers now. A file is NSLS's while it still matches either (matching
    the incoming one covers a copy that was interrupted half way). Everything
    else is its owner's: a delivered file they edited, replaced or removed, and
    a file of their own sitting where NSLS now ships one.
    """
    target = Path(target)
    changed = []
    for rel, was in baseline.items():
        path = target / rel
        wanted = incoming.get(rel)
        if _plain_file(path):
            if _sha(path) not in (was, wanted):
                changed.append(rel)
        elif _there(path):
            changed.append(rel)          # a folder or link where a file was
        elif wanted is not None:
            changed.append(rel)          # they removed a file NSLS still ships
    for rel, wanted in incoming.items():
        if rel in baseline:
            continue
        path = target / rel
        if _plain_file(path):
            if _sha(path) != wanted:
                changed.append(rel)
        elif _there(path):
            changed.append(rel)
    return sorted(changed)


def standing_in_the_way(cfg, found, tracked=()) -> list:
    """Files of the owner's that stop a take-over nobody asked for: anything in
    the folder that is neither a file git tracks (`tracked`, each still as NSLS
    shipped it) nor identical to what NSLS delivers, sitting where a delivered
    file goes. Reads only. Asked BEFORE anything is changed, settings included,
    so a folder that will not be taken over is left exactly as it is."""
    try:
        return owner_changes(folder(cfg), _as_shipped(folder(cfg), tracked), found.hashes)
    except Exception:
        return ["?"]


def _as_shipped(target, tracked) -> dict:
    """{path: sha256} of each tracked file as it is on disk right now."""
    shipped = {}
    for rel in tracked:
        path = Path(target) / rel
        if _plain_file(path):
            shipped[rel] = _sha(path)
    return shipped


def forget_unfinished(target) -> None:
    """Drop the record a take-over wrote before it moved .git, when the folder
    turns out not to be one to take over after all. The folder is then an
    ordinary checkout again."""
    try:
        if state(target) == "taking":
            (Path(target) / MARKER).unlink()
    except Exception:
        pass


def _starts_with_shebang(path) -> bool:
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == b"#!"
    except OSError:
        return False


def _copy_file(src, dst):
    """Replace dst with src's bytes in one step, so nothing ever reads half a
    file. A script stays runnable: the mode is not trusted to survive delivery,
    so a file that was executable, is delivered executable, or starts with a
    shebang is written executable."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    runnable = _starts_with_shebang(src)
    for path in (src, dst):
        try:
            runnable = runnable or bool(os.lstat(path).st_mode & 0o111)
        except OSError:
            pass
    fd, tmp = tempfile.mkstemp(prefix=".nsls-copy-", dir=str(dst.parent))
    try:
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out)
        os.chmod(tmp, (0o777 if runnable else 0o666) & ~_UMASK)
        os.replace(tmp, str(dst))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _move_aside(path, aside, rel):
    dest = aside / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(dest))


def _prune_empty(target, path):
    """Remove folders a deleted file left empty, never the toolkit folder."""
    target = Path(target)
    parent = Path(path).parent
    while parent != target and target in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def _out_of_time(deadline) -> bool:
    return deadline is not None and time.monotonic() > deadline


def _mirror(target, found, record, deadline=None, aside=None):
    """Make the folder carry the delivered files. True when it finished.

    Writes only files that differ. A file NSLS stopped shipping is removed on
    the SECOND pass that finds it gone, and only while it is still exactly
    what NSLS delivered: one look at a copy Claude was in the middle of
    replacing must not delete anything. `record` is the marker being built; it
    is saved by the caller. With `aside`, a file that differs is moved there
    before its replacement is written.
    """
    target = Path(target)
    baseline = record["files"]
    waiting = set(record.get("pending") or [])
    hashes = found.hashes
    for rel in sorted(found.files):
        if _out_of_time(deadline):
            return False
        dst = target / rel
        if _plain_file(dst) and _sha(dst) == hashes[rel]:
            continue
        if _there(dst) and not _plain_file(dst):
            if aside is None:
                return False             # a folder where a file goes: theirs
            _move_aside(dst, aside, rel)
        elif aside is not None and _plain_file(dst):
            _move_aside(dst, aside, rel)
        _copy_file(found.files[rel], dst)

    files, pending = dict(hashes), []
    for rel, was in baseline.items():
        if rel in hashes:
            continue
        path = target / rel
        if not _plain_file(path):
            continue                     # already gone
        if rel in waiting and _sha(path) == was:
            path.unlink()
            _prune_empty(target, path)
            continue
        files[rel] = was                 # keep watching it for one more pass
        pending.append(rel)
    record["files"] = files
    record["pending"] = sorted(pending)
    return True


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _result(outcome, **extra):
    extra["outcome"] = outcome
    return extra


def _ensure_tombstone(target):
    git = Path(target) / ".git"
    if not _there(git):
        git.write_text(TOMBSTONE, encoding="utf-8")


class _Lock:
    """One pass at a time on this computer. Two sessions starting together
    would otherwise both copy into the same folder."""

    def __init__(self, cfg):
        self.path = Path(cfg) / ".nsls-personal-delivery.flock"
        self.fd = None

    def __enter__(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0), 0o644)
        except OSError:
            return False
        try:
            try:
                import fcntl
            except ImportError:
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, ImportError):
            os.close(fd)
            return False
        self.fd = fd
        return True

    def __exit__(self, *exc):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
        return False


def _aside_dir(target):
    return Path(target) / SET_ASIDE / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _finish(target, found, record, deadline, aside, done_as):
    """Copy, then save the record. The record is saved either way: a pass that
    ran out of time keeps `complete` false and its old signature, so the next
    session finishes it."""
    try:
        done = _mirror(target, found, record, deadline, aside)
    except Exception:
        done = False
    if done:
        record.update(complete=True, signature=found.signature,
                      version=found.version, updated=_now())
    else:
        record["complete"] = False
    try:
        _write_marker(target, record)
    except Exception:
        return _result("retry", why="record")
    if not done:
        return _result("retry", why="unfinished")
    extra = {"version": found.version}
    if aside is not None and aside.exists():
        extra["set_aside"] = str(aside)
    return _result(done_as, **extra)


def refresh(cfg, found, deadline=None, take_theirs=False):
    """Bring a folder that follows the delivered copy up to it, or make the
    folder when there is none.

    Outcomes: "current", "updated", "created", "paused" (the owner changed
    files; `changed` lists them, nothing was touched), "retry", and "kept" for
    anything that is not this function's to touch. `take_theirs` is the owner's
    yes: their changed files are moved to .set-aside/ and NSLS's are written.
    """
    try:
        target = folder(cfg)
        with _Lock(cfg) as held:
            if not held:
                return _result("retry", why="busy")
            kind = state(target)
            if kind not in ("none", "delivered"):
                return _result("kept", why=kind)
            record = read_marker(target) if kind == "delivered" else None
            # Nothing new, nothing unfinished, and no removed file still
            # waiting for its second look: the folder is where it should be.
            if (record and record.get("complete") and not take_theirs
                    and not record.get("pending")
                    and record.get("signature") == found.signature):
                _ensure_tombstone(target)
                return _result("current", version=record.get("version"))
            if not found.settled():
                return _result("retry", why="settling")
            baseline = record["files"] if record else {}
            changed = owner_changes(target, baseline, found.hashes)
            if changed and not take_theirs:
                return _result("paused", changed=changed, version=found.version,
                               have=(record or {}).get("version"))
            target.mkdir(parents=True, exist_ok=True)
            if record is None:
                record = {"schema": SCHEMA, "plugin": PLUGIN, "files": {}, "pending": [],
                          "complete": False, "signature": "", "version": None,
                          "from": {"kind": "new", "at": _now()}}
                _write_marker(target, record)
            _ensure_tombstone(target)
            aside = _aside_dir(target) if (take_theirs and changed) else None
            return _finish(target, found, record, deadline, aside,
                           "created" if kind == "none" else "updated")
    except Exception:
        return _result("retry", why="error")


def take_over(cfg, found, tracked=(), origin=None, deadline=None, take_theirs=False):
    """Switch a checkout (or a plain copy) to following the delivered copy.

    The caller has already decided this folder may be taken over: either git
    showed it holds nothing of its owner's (`tracked` is then every file git
    tracks there, each one still as NSLS shipped it), or its owner said yes
    (`take_theirs`: every file about to be replaced is moved to .set-aside/
    first). This function re-checks only what it can see without git: a file of
    the owner's sitting where NSLS ships one stops a take-over nobody asked for.

    .git is renamed, never removed, so the history, any branches and any
    stashes stay on the computer. Outcomes: "converted", "adopted", "kept"
    (with `changed`), "retry".
    """
    try:
        target = folder(cfg)
        with _Lock(cfg) as held:
            if not held:
                return _result("retry", why="busy")
            kind = state(target)
            if kind not in ("checkout", "taking", "copy"):
                return _result("kept", why=kind)
            if not found.settled():
                return _result("retry", why="settling")
            baseline = {}
            if not take_theirs:
                baseline = _as_shipped(target, tracked)
                changed = owner_changes(target, baseline, found.hashes)
                if changed:
                    return _result("kept", why="own-changes", changed=changed)
            git = target / ".git"
            if (git / "index.lock").exists():
                return _result("retry", why="git-busy")
            record = {"schema": SCHEMA, "plugin": PLUGIN, "files": baseline, "pending": [],
                      "complete": False, "signature": "", "version": version_of(target),
                      "from": dict(origin or {}, kind="adopted" if take_theirs else "checkout",
                                   at=_now())}
            _write_marker(target, record)
            if git.is_dir():
                kept = target / KEPT_GIT
                count = 1
                while _there(kept):
                    count += 1
                    kept = target / f"{KEPT_GIT}-{count}"
                try:
                    os.rename(str(git), str(kept))
                except OSError:
                    # Something holds the repository open (a git command, an
                    # indexer). Nothing has changed: forget the record and let
                    # the next session try.
                    try:
                        (target / MARKER).unlink()
                    except OSError:
                        pass
                    return _result("retry", why="git-held")
                record["from"]["kept_git"] = kept.name
            elif _plain_file(git):
                try:
                    git.unlink()             # a worktree pointer: the owner said yes
                except OSError:
                    pass
            _ensure_tombstone(target)
            aside = _aside_dir(target) if take_theirs else None
            return _finish(target, found, record, deadline, aside,
                           "adopted" if take_theirs else "converted")
    except Exception:
        return _result("retry", why="error")


# --- the update entries the Personal Toolkit's installers wrote ---------------
#
# install.sh and install.ps1 register the folder's own update in settings.json:
# a `git pull` of the folder, and (install.sh) the folder's session hook. Once
# the folder follows the delivered copy both are wrong: the pull has nothing to
# pull and would print a hook error at every session start, and with .git gone
# it could reach a parent repository. They are removed, and only they: every
# spelling an installer or an upgrade has ever written, matched whole. An entry
# its owner edited matches none of them and is left alone, and so is its folder.

_GIT_NAMES = r"[A-Z_]+"
_PULL = r'git -C "[^"\n]*[/\\]nsls-personal-toolkit" pull --ff-only --quiet'
_PULL_ENTRY = re.compile(
    r"(?:unset(?: " + _GIT_NAMES + r")+; "
    r"|Remove-Item Env:" + _GIT_NAMES + r"(?:,Env:" + _GIT_NAMES + r")* -ErrorAction Ignore; )?"
    r"(?:GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS= "
    r"|\$env:GIT_TERMINAL_PROMPT='0'; \$env:GCM_INTERACTIVE='never'; )?"
    + _PULL)
_SYNC_ENTRY = re.compile(
    r'"[^"\n]+" "[^"\n]*[/\\]nsls-personal-toolkit[/\\]hooks[/\\]session-start\.py" --no-pull')
# Any pull of the folder, however it is spelled.
_ANY_PULL = re.compile(r'nsls-personal-toolkit["\']?\s+pull\b')


def _is_ours(command) -> bool:
    return bool(_PULL_ENTRY.fullmatch(command) or _SYNC_ENTRY.fullmatch(command))


def _hook_lists(settings):
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    if not isinstance(hooks, dict):
        return
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            entries = group.get("hooks") if isinstance(group, dict) else None
            if isinstance(entries, list):
                yield event, group, entries


def update_entries(cfg):
    """(ours, edited): how many of the installers' own update entries are
    registered, and how many pulls of the folder someone has edited by hand.
    (0, 0) when settings cannot be read."""
    try:
        settings = _read_json(Path(cfg) / "settings.json")
    except Exception:
        return 0, 0
    ours = edited = 0
    for _event, _group, entries in _hook_lists(settings):
        for hook in entries:
            command = hook.get("command") if isinstance(hook, dict) else None
            if not isinstance(command, str):
                continue
            if _is_ours(command):
                ours += 1
            elif _ANY_PULL.search(command):
                edited += 1
    return ours, edited


def remove_update_entries(cfg) -> bool:
    """Take the installers' own update entries out of settings.json. True when
    none is left. Nothing else in the file changes meaning; a copy of the file
    as it was is kept beside it the first time."""
    try:
        path = Path(os.path.realpath(Path(cfg) / "settings.json"))
        before = path.read_bytes()
        settings = json.loads(before.decode("utf-8-sig"))
        removed = 0
        hooks = settings.get("hooks") if isinstance(settings, dict) else None
        for event, group, entries in list(_hook_lists(settings)):
            kept = [h for h in entries
                    if not (isinstance(h, dict) and isinstance(h.get("command"), str)
                            and _is_ours(h["command"]))]
            if len(kept) == len(entries):
                continue
            removed += len(entries) - len(kept)
            if kept:
                group["hooks"] = kept
            else:
                hooks[event] = [g for g in hooks[event] if g is not group]
                if not hooks[event]:
                    del hooks[event]
        if not removed:
            return True
        backup = path.with_name("settings.json.pre-personal-delivery")
        if not backup.exists():
            shutil.copy2(str(path), str(backup))
        fd, tmp = tempfile.mkstemp(prefix=".settings.json.", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(settings, fh, indent=2)
                fh.write("\n")
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
            # Whoever wrote settings.json since we read it wins: drop ours and
            # let the next session try again.
            if path.read_bytes() != before:
                raise OSError("settings.json changed")
            os.replace(tmp, str(path))
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            return False
        return update_entries(cfg)[0] == 0
    except Exception:
        return False
