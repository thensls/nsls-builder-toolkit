#!/usr/bin/env python3
"""Every skill says where it works, and one that needs Claude Code tells the person so.

Usage: python3 .github/scripts/check_skill_surfaces.py [--fix] [<repo root>]

NSLS delivers this toolkit to every Claude seat, and a delivered skill is
listed in Claude Code, in an ordinary Claude chat and in Cowork alike. Most
skills only work in Claude Code on the person's own computer: they run a
script, use the toolkit's own folder, or read Claude Code's files. Opened
anywhere else such a skill used to fail halfway. Now it says one plain
sentence and stops.

_shared/references/skill-surfaces.json is the one place that holds:
  - the two groups, `anywhere` and `claude_code_only`, each skill folder in
    exactly one of them;
  - the note a `claude_code_only` skill carries at the top of its SKILL.md,
    and the sentence the person sees;
  - the few words its description starts with, so Claude is less likely to
    pick the skill outside Claude Code in the first place.

This check fails when:
  - a folder in skills/ is in neither group, or in both;
  - a listed skill has no SKILL.md;
  - a `claude_code_only` skill lacks the note, carries it anywhere but the top,
    or carries different words;
  - a `claude_code_only` skill's description does not start with the tag;
  - an `anywhere` skill carries the note or the tag.

`--fix` puts the note and the tag where the lists say they belong and takes
them off where they don't. It changes nothing else in a SKILL.md. Sorting a
skill into a group stays a person's decision: read the skill first.

A damaged note (an opening or closing marker line with no partner, as a bad
merge can leave) is reported and left alone. `--fix` cannot tell where such a
note ends, so removing it could take the skill's own text with it, and adding
a second note beside it would never pass. A person deletes what is left.

Tests: test/test_check_skill_surfaces.py
"""

import json
import re
import sys
from pathlib import Path

DATA = Path("_shared") / "references" / "skill-surfaces.json"
GROUPS = ("anywhere", "claude_code_only")
START = "<!-- claude-code-only:start"
END = "<!-- claude-code-only:end -->"
# One note, with the blank lines around it. Non-greedy, so two notes are two matches.
NOTE_RE = re.compile(r"\n*" + re.escape(START) + r".*?" + re.escape(END) + r"\n*", re.DOTALL)
# `description: >-`, `description: |` and friends: the text starts on the next line.
BLOCK_RE = re.compile(r"^[>|][+-]?[0-9]?$|^[>|][0-9]?[+-]?$")
# Words the person must never be shown: this sentence is read by non-technical staff.
NOT_FOR_STAFF = ("plugin", "sandbox", "/", "\\", "~", "`", "$")
HOW_TO_FIX = "python3 .github/scripts/check_skill_surfaces.py --fix"


class Unreadable(Exception):
    pass


def load(root):
    """The lists and the shared wording, checked for shape."""
    path = root / DATA
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        raise Unreadable(f"{DATA.as_posix()}: can't read it as JSON ({e})")
    for key in GROUPS:
        if not isinstance(data.get(key), dict):
            raise Unreadable(f'{DATA.as_posix()}: "{key}" must be a list of skill folder: reason')
    for key in ("description_tag", "person_sees"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise Unreadable(f'{DATA.as_posix()}: "{key}" must be a line of text')
    lines = data.get("guard")
    if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines) or len(lines) < 3:
        raise Unreadable(f'{DATA.as_posix()}: "guard" must be a list of lines')
    if not lines[0].startswith(START) or lines[-1] != END:
        raise Unreadable(f'{DATA.as_posix()}: "guard" must open with {START} … and close with {END}')
    if sum(x.count("{person_sees}") for x in lines) != 1:
        raise Unreadable(f'{DATA.as_posix()}: "guard" must hold {{person_sees}} exactly once')
    if any(START in x or END in x for x in lines[1:-1]):
        raise Unreadable(f'{DATA.as_posix()}: the markers belong on the first and last lines of "guard" only')
    sentence = data["person_sees"]
    shown = [w for w in NOT_FOR_STAFF if w in sentence.lower()]
    if shown:
        raise Unreadable(
            f'{DATA.as_posix()}: "person_sees" is read by staff, so keep it plain: take out {", ".join(repr(w) for w in shown)}'
        )
    if "\n" in sentence or len(re.findall(r"[.!?](?:\s|$)", sentence)) != 1:
        raise Unreadable(f'{DATA.as_posix()}: "person_sees" must be one sentence')
    return data


def note(data):
    """The note exactly as it sits in a SKILL.md."""
    return "\n".join(data["guard"]).replace("{person_sees}", data["person_sees"])


def split(text):
    """(frontmatter lines without the two --- lines, body after the closing ---), or None."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None


def join(front, body):
    return "\n".join(["---", *front, "---"]) + "\n" + body


def description(front):
    """(line number, how it is written, line number of its first words) or None.

    Three ways a description is written here: `>-` with the words on the lines
    below, one quoted line, or one plain line.
    """
    for i, line in enumerate(front):
        m = re.match(r"^description:[ \t]*(.*)$", line)
        if not m:
            continue
        rest = m.group(1).strip()
        if BLOCK_RE.match(rest):
            for j in range(i + 1, len(front)):
                if not front[j].strip():
                    continue
                if not front[j].startswith((" ", "\t")):
                    return None  # an empty block: nothing to tag
                return i, "block", j
            return None
        if not rest:
            return None
        return i, ("quoted" if rest[0] in "\"'" else "plain"), i
    return None


def _first_words(front, found):
    i, kind, j = found
    if kind == "block":
        return front[j].strip()
    rest = re.match(r"^description:[ \t]*(.*)$", front[i]).group(1)
    return rest[1:] if kind == "quoted" else rest


def has_tag(front, tag):
    found = description(front)
    if not found:
        return False
    words = _first_words(front, found)
    return words == tag or words.startswith(tag + " ")


def add_tag(front, tag):
    found = description(front)
    if not found or has_tag(front, tag):
        return front
    i, kind, j = found
    front = list(front)
    if kind == "block":
        indent = re.match(r"^[ \t]*", front[j]).group(0)
        front.insert(j, indent + tag)
        return front
    head, rest = re.match(r"^(description:[ \t]*)(.*)$", front[i]).groups()
    if kind == "quoted":
        front[i] = f"{head}{rest[0]}{tag} {rest[1:]}"
    else:
        front[i] = f"{head}{tag} {rest}"
    return front


def remove_tag(front, tag):
    found = description(front)
    if not found or not has_tag(front, tag):
        return front
    i, kind, j = found
    front = list(front)
    if kind == "block":
        if front[j].strip() == tag:
            del front[j]
        else:
            indent = re.match(r"^[ \t]*", front[j]).group(0)
            front[j] = indent + front[j].strip()[len(tag):].lstrip()
        return front
    head, rest = re.match(r"^(description:[ \t]*)(.*)$", front[i]).groups()
    if kind == "quoted":
        front[i] = f"{head}{rest[0]}{rest[1:][len(tag):].lstrip()}"
    else:
        front[i] = f"{head}{rest[len(tag):].lstrip()}"
    return front


MARKER_RE = re.compile(re.escape(START) + "|" + re.escape(END))


def damaged(body):
    """True when the note's marker lines don't pair up: start, end, start, end.

    Every other function here assumes whole notes. One marker without its
    partner is not a note `--fix` can move or remove, so callers check this
    first and leave such a file to a person.
    """
    expect = START
    for found in MARKER_RE.findall(body):
        if found != expect:
            return True
        expect = END if expect == START else START
    return expect == END


def without_note(body):
    """The body as it was before any note went in. Whole notes only: see damaged()."""
    if START not in body:
        return body
    at_top = body.lstrip("\n").startswith(START)
    rest = NOTE_RE.sub("\n\n", body)
    return "\n" + rest.lstrip("\n") if at_top else rest


def with_note(body, text):
    """The note first, one blank line each side, then the body untouched."""
    return "\n" + text + "\n\n" + without_note(body).lstrip("\n")


def skill_dirs(root):
    skills = root / "skills"
    if not skills.is_dir():
        return []
    return sorted(p.name for p in skills.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def problems(root):
    """Every reason the check fails, in words a skill author can act on."""
    root = Path(root)
    data = load(root)
    text, tag = note(data), data["description_tag"]
    anywhere, code_only = set(data["anywhere"]), set(data["claude_code_only"])
    found = set(skill_dirs(root))
    out = []

    for name in sorted(anywhere & code_only):
        out.append(f"{name}: listed in both groups in {DATA.as_posix()}. Keep it in one.")
    for name in sorted(found - anywhere - code_only):
        out.append(
            f"skills/{name}: not listed in {DATA.as_posix()}. Read the skill, then add it to "
            f'"anywhere" (it works in an ordinary Claude chat and in Cowork too) or to "claude_code_only" '
            f"(it needs the person's own computer: it runs a script or a command, uses the toolkit's folder, "
            f"or reads Claude Code's files). Then run: {HOW_TO_FIX}"
        )
    for name in sorted((anywhere | code_only) - found):
        out.append(f"{name}: listed in {DATA.as_posix()}, but skills/{name}/SKILL.md does not exist. Take it off the list.")

    for name in sorted(found & (anywhere | code_only) - (anywhere & code_only)):
        where = f"skills/{name}/SKILL.md"
        parts = split(read(root / "skills" / name / "SKILL.md"))
        if parts is None:
            out.append(f"{where}: no frontmatter (the block between two --- lines at the top).")
            continue
        front, body = parts
        if damaged(body):
            out.append(
                f"{where}: the Claude Code note is damaged: a line starting {START} or the line {END} "
                f"has no partner. --fix leaves it alone. Delete what is left of the note by hand, both "
                f"marker lines included"
                + (f", then run: {HOW_TO_FIX}" if name in code_only else ".")
            )
            continue
        if name in code_only:
            count = body.count(START)
            if count == 0:
                out.append(f"{where}: needs Claude Code, but the note that says so is missing. Run: {HOW_TO_FIX}")
            elif count > 1:
                out.append(f"{where}: carries the Claude Code note {count} times. Run: {HOW_TO_FIX}")
            elif not body.startswith("\n" + text + "\n"):
                out.append(
                    f"{where}: the Claude Code note is not the first thing after the frontmatter, or its words "
                    f"differ from the shared ones in {DATA.as_posix()}. Run: {HOW_TO_FIX}"
                )
            if description(front) is None:
                out.append(f"{where}: no description to mark as Claude Code only.")
            elif not has_tag(front, tag):
                out.append(f'{where}: the description must start with "{tag}" Run: {HOW_TO_FIX}')
        else:
            if START in body or END in body:
                out.append(
                    f'{where}: listed as working anywhere, but it carries the Claude Code note. Move it to '
                    f'"claude_code_only" in {DATA.as_posix()}, or run: {HOW_TO_FIX}'
                )
            if has_tag(front, tag):
                out.append(
                    f'{where}: listed as working anywhere, but its description starts with "{tag}" Move it to '
                    f'"claude_code_only" in {DATA.as_posix()}, or run: {HOW_TO_FIX}'
                )
    return out


def fix(root):
    """Put the note and the tag where the lists say. Returns the files changed."""
    root = Path(root)
    data = load(root)
    text, tag = note(data), data["description_tag"]
    anywhere, code_only = set(data["anywhere"]), set(data["claude_code_only"])
    changed = []
    for name in skill_dirs(root):
        if (name in anywhere) == (name in code_only):
            continue  # unlisted or listed twice: a person decides, not this script
        path = root / "skills" / name / "SKILL.md"
        before = read(path)
        parts = split(before)
        if parts is None:
            continue
        front, body = parts
        if damaged(body):
            continue  # problems() says how to repair it by hand
        if name in code_only:
            after = join(add_tag(front, tag), with_note(body, text))
        else:
            after = join(remove_tag(front, tag), without_note(body))
        if after != before:
            path.write_text(after, encoding="utf-8", newline="\n")
            changed.append(f"skills/{name}/SKILL.md")
    return changed


def main(argv):
    args = [a for a in argv if a != "--fix"]
    root = Path(args[0]) if args else Path(__file__).resolve().parents[2]
    try:
        if "--fix" in argv:
            for path in fix(root):
                print(f"updated {path}")
        found = problems(root)
        data = load(root)
    except Unreadable as e:
        print(f"FAIL {e}")
        return 2
    if found:
        print(f"FAIL {len(found)} problem(s) with where skills say they work:\n")
        for line in found:
            print(f"  - {line}\n")
        return 1
    print(
        f"ok: {len(data['anywhere'])} skills work anywhere, {len(data['claude_code_only'])} say they need Claude Code."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
