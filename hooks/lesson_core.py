"""The lesson check's shared state: on/off, the check log, and skill backups.

Used by lesson-check.py (the helper Claude runs) and by the end-of-turn hook
that offers the check. Plain stdlib, fails open everywhere.

WHY A LESSON CHECK. The compound skill saves a lesson so the builder never has
to repeat a correction to Claude. Nothing ever triggered it: on the machine it
was tested on, it ran 0 times in 30 days while the builder corrected Claude
about twice per long session. The hook offers the check after a stretch of
corrections; compound turns it into at most two proposed lessons, and nothing
is saved until the builder says yes.

ON BY DEFAULT, ONE SWITCH. "Turn off lesson checks" writes enabled=false here;
NSLS_LESSON_CHECK=off does the same for one shell. Both are read on every check.

BACKUPS BEFORE PATCHES. A lesson can change one of the builder's own skills.
The backup is taken by this helper, not by Claude copying a file, and it
refuses skills the builder does not own: toolkit and plugin skills (an edit is
overwritten at the next update), pointer skills the toolkit writes, and skills
synced from claude.ai.
"""
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

LOG_KEEP = 500  # newest log lines kept; the log is for status, not history


def config_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def home():
    return config_dir() / ".nsls-lesson-check"


def _config_path():
    return home() / "config.json"


def log_path():
    return home() / "log.jsonl"


def backups_dir():
    return home() / "backups"


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ── on / off ────────────────────────────────────────────────────────────────

def enabled():
    if os.environ.get("NSLS_LESSON_CHECK", "").strip().lower() in ("off", "0", "false", "no"):
        return False
    try:
        return json.loads(_config_path().read_text(encoding="utf-8")).get("enabled", True) is not False
    except Exception:
        return True


def set_enabled(value):
    try:
        data = json.loads(_config_path().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
    data["enabled"] = bool(value)
    home().mkdir(parents=True, exist_ok=True)
    tmp = _config_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, _config_path())


# ── log ─────────────────────────────────────────────────────────────────────

def append_log(entry):
    try:
        home().mkdir(parents=True, exist_ok=True)
        with open(log_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": now_iso(), **entry}) + "\n")
        _trim_log()
    except Exception:
        pass


def _trim_log():
    p = log_path()
    if p.stat().st_size < 256 * 1024:
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_KEEP:]
    tmp = p.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def read_log():
    out = []
    try:
        for line in log_path().read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    out.append(row)
            except Exception:
                continue
    except Exception:
        pass
    return out


# ── whose skill is it ───────────────────────────────────────────────────────

_POINTER = re.compile(r"read and follow the full skill at", re.I)
_pointer_check = []


def is_toolkit_pointer(text, skill):
    """True only for a pointer exactly as the toolkit writes it, by the one
    shared definition (is_own_pointer in session-start.py, also used by
    install.sh and sync-pointers.sh). A builder's own skill that merely
    mentions a toolkit skill, or a pointer they have added notes to, is theirs.
    If that definition cannot be loaded, treat a pointer-looking file as a
    pointer: refusing a backup is safe, overwriting a pointer is not."""
    if not _pointer_check:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "nsls_session_start_for_lesson", str(Path(__file__).resolve().with_name("session-start.py")))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _pointer_check.append(mod.is_own_pointer)
        except Exception:
            _pointer_check.append(None)
    check = _pointer_check[0]
    if check is None:
        return bool(_POINTER.search(text[:2000]))
    try:
        return bool(check(text, skill))
    except Exception:
        return bool(_POINTER.search(text[:2000]))


def skill_owner(path):
    """("own", skill_dir) when the builder may edit it, else (reason, None).

    Reasons: missing · plugin (toolkit or another plugin: an update overwrites
    the edit) · pointer (a stub the toolkit writes and refreshes) · synced (a
    skill synced from claude.ai: change it there) · elsewhere (not directly in
    the builder's skills folder) · linked (holds a link to a file elsewhere: a
    backup would save the link, not the text, so undo could not restore it).
    """
    p = Path(str(path)).expanduser()
    if p.name == "SKILL.md":
        p = p.parent
    if not (p / "SKILL.md").is_file():
        return "missing", None
    skills = config_dir() / "skills"
    try:
        real = p.resolve()
        skills_real = skills.resolve()
    except Exception:
        return "missing", None
    for root in (config_dir() / "plugins", config_dir() / "local-plugins"):
        try:
            real.relative_to(root.resolve())
            return "plugin", None
        except (ValueError, OSError):
            pass
    try:
        rel = real.relative_to(skills_real)
    except ValueError:
        return "elsewhere", None
    if rel.parts and rel.parts[0] == "synced":
        return "synced", None
    if len(rel.parts) != 1:  # Claude Code loads skills/<name>/SKILL.md, nothing deeper
        return "elsewhere", None
    text = (real / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    if is_toolkit_pointer(text, real.name):
        return "pointer", None
    if _holds_links(real):
        return "linked", None
    return "own", real


def _holds_links(folder):
    try:
        for dirpath, dirnames, filenames in os.walk(folder):
            for name in dirnames + filenames:
                if os.path.islink(os.path.join(dirpath, name)):
                    return True
    except OSError:
        return True
    return False


def _unique(name):
    """A sibling name no other run can pick: a second undo or backup started in
    the same second must never share (and then delete) this one's folder."""
    return f"{name}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


REFUSALS = {
    "missing": "Not backed up: there is no SKILL.md at that path.",
    "plugin": "Not backed up: this skill comes from the toolkit or another plugin, and its next update "
              "would overwrite the edit. Don't change it; offer to raise the change with its owner instead.",
    "pointer": "Not backed up: this is a pointer the toolkit keeps up to date, not the skill itself. "
               "Don't change it; offer to raise the change with the toolkit instead.",
    "synced": "Not backed up: this skill is synced from claude.ai, so a local edit may be overwritten. "
              "Suggest the builder change it in claude.ai instead.",
    "linked": "Not backed up: this skill links to files kept somewhere else, and a backup would save "
              "only the links. Don't change it here; offer to make the change where those files live.",
    "elsewhere": "Not backed up: this skill isn't directly in the builder's skills folder (often a link "
                 "into a repo). Don't change it here; offer to make the change where it lives instead.",
}


# ── backup / undo ───────────────────────────────────────────────────────────

def backup(path):
    """Copy the skill's folder aside. Returns (backup_id, None) or (None, refusal)."""
    owner, skill_dir = skill_owner(path)
    if owner != "own":
        return None, REFUSALS[owner]
    bid = _unique(time.strftime("%Y%m%d-%H%M%S") + "-" + re.sub(r"[^A-Za-z0-9_-]", "-", skill_dir.name)[:40])
    dest = backups_dir() / bid
    shutil.copytree(skill_dir, dest / "skill", symlinks=True)
    (dest / "meta.json").write_text(json.dumps({"path": str(skill_dir), "at": now_iso()}), encoding="utf-8")
    append_log({"event": "backup", "id": dest.name, "skill": skill_dir.name})
    return dest.name, None


def _own_skill_slot(target):
    """True when target is, or would be, a direct child of the builder's skills
    folder (outside synced/). Checked before undo touches anything, whether or
    not the folder exists yet: the path comes from a file on disk, and a file
    can be edited."""
    try:
        rel = Path(target).resolve().relative_to((config_dir() / "skills").resolve())
    except (ValueError, OSError):
        return False
    return len(rel.parts) == 1 and rel.parts[0] != "synced"


def undo(backup_id):
    """Put a backed-up skill back. Returns a one-line result.

    The backup is copied next to the skill first; only a complete copy is
    swapped in, and if the swap fails the skill is put back as it was."""
    bid = re.sub(r"[^A-Za-z0-9_-]", "", str(backup_id or ""))
    src = backups_dir() / bid
    try:
        meta = json.loads((src / "meta.json").read_text(encoding="utf-8"))
        target = Path(meta["path"])
    except Exception:
        return f"Not undone: no backup called {bid or '(blank)'}."
    if not (src / "skill" / "SKILL.md").is_file():
        return "Not undone: that backup is incomplete, so the skill was left as it is."
    if not _own_skill_slot(target):
        return "Not undone: that backup points outside the builder's own skills folder."
    if (target / "SKILL.md").exists() and skill_owner(target)[0] != "own":
        return "Not undone: that folder is no longer one of the builder's own skills."
    stamp = _unique(time.strftime("%Y%m%d-%H%M%S"))
    staged = target.with_name(f".{target.name}.restore-{stamp}")
    aside = target.with_name(f".{target.name}.undo-{stamp}")
    try:
        shutil.copytree(src / "skill", staged, symlinks=True)
    except Exception:
        shutil.rmtree(staged, ignore_errors=True)
        return "Not undone: the backup could not be copied, so the skill was left as it is."
    moved = False
    try:
        if target.exists() or target.is_symlink():
            os.replace(target, aside)
            moved = True
        os.replace(staged, target)
    except Exception:
        if moved and not target.exists():
            try:
                os.replace(aside, target)
            except Exception:
                return f"Not undone, and the skill is now at {aside.name} beside where it was. Move it back."
        shutil.rmtree(staged, ignore_errors=True)
        return "Not undone: the swap failed, so the skill was left as it was."
    if moved:
        shutil.rmtree(aside, ignore_errors=True)
    append_log({"event": "undo", "id": bid, "skill": target.name})
    return f"Undone: {target.name} is back to how it was at {meta.get('at', 'the backup')}."


def backups():
    out = []
    for meta in sorted(backups_dir().glob("*/meta.json")) if backups_dir().exists() else []:
        try:
            m = json.loads(meta.read_text(encoding="utf-8"))
            out.append({"id": meta.parent.name, "skill": Path(m["path"]).name, "at": m.get("at", "")})
        except Exception:
            continue
    return out
