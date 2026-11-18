#!/usr/bin/env python3
"""The lesson check's helper, run by Claude through run-hook.sh:

  bash run-hook.sh lesson on | off       turn lesson checks on or off (on by default)
  bash run-hook.sh lesson status         recent checks, whether it is on, skill backups
  bash run-hook.sh lesson backup <path>  back up one of the builder's own skills before a patch
  bash run-hook.sh lesson undo <id>      put a backed-up skill back

Everything prints one plain line or a short block for Claude to pass on. Exit
code is always 0 (run-hook.sh passes exit 2 through as "block", which no
helper may ever mean).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lesson_core as core  # noqa: E402

USAGE = "Usage: lesson on | off | status | backup <skill path> | undo <backup id>"


def status():
    rows = core.read_log()
    checks = [r for r in rows if r.get("event") == "check"]
    lines = [f"Lesson checks are {'ON' if core.enabled() else 'OFF'}."]
    if checks:
        lines.append(f"{len(checks)} lesson check(s) offered; most recent:")
        for r in checks[-5:]:
            lines.append(f"  {r.get('ts', '')[:16].replace('T', ' ')} · {r.get('summary', '')}")
    else:
        lines.append("No lesson check has been offered on this machine yet.")
    backups = core.backups()
    if backups:
        lines.append("Skill backups (newest last):")
        for b in backups[-5:]:
            lines.append(f"  {b['skill']} · {b['at'][:16].replace('T', ' ')} · undo id {b['id']}")
    return "\n".join(lines)


def main(argv):
    if not argv:
        return USAGE
    cmd, rest = argv[0], argv[1:]
    if cmd == "on":
        core.set_enabled(True)
        return "Lesson checks are on."
    if cmd == "off":
        core.set_enabled(False)
        return "Lesson checks are off. Say \"turn lesson checks back on\" to resume."
    if cmd == "status":
        return status()
    if cmd == "backup" and rest:
        bid, refusal = core.backup(" ".join(rest))
        if refusal:
            return refusal
        launcher = (Path(__file__).resolve().parent / "run-hook.sh").as_posix()
        return f"Backed up. To undo the change later: bash \"{launcher}\" lesson undo {bid}"
    if cmd == "undo" and rest:
        return core.undo(rest[0])
    return USAGE


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        print(main(sys.argv[1:]))
    except Exception as exc:  # never a traceback, never a non-zero exit
        print(f"Not done: the lesson helper hit an error ({type(exc).__name__}).")
    sys.exit(0)
