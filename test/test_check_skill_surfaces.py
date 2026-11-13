#!/usr/bin/env python3
"""Every skill says where it works, and a skill that needs Claude Code tells the person so.

Plain stdlib, no pytest: run with `python3 test/test_check_skill_surfaces.py`.

Why it exists: NSLS delivers this toolkit to every Claude seat, so its skills
are listed in an ordinary Claude chat and in Cowork as well as in Claude Code.
Most of them only work in Claude Code on the person's own computer. Opened
anywhere else, such a skill says one plain sentence and stops; see
.github/scripts/check_skill_surfaces.py. The first block below runs that
check on the real skills/ folder, so a new skill cannot be added without
saying where it works. The rest proves the check catches each way of
skipping it, and that `--fix` changes nothing but the note and the tag.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "check_skill_surfaces.py"
DATA = ROOT / "_shared" / "references" / "skill-surfaces.json"

spec = importlib.util.spec_from_file_location("check_skill_surfaces", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

REAL = json.loads(DATA.read_text(encoding="utf-8"))
NOTE = m.note(REAL)
TAG = REAL["description_tag"]
SENTENCE = REAL["person_sees"]

failures = []


def check(label, cond):
    print(f"{'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        failures.append(label)


def run(root, *flags):
    r = subprocess.run([sys.executable, str(SCRIPT), *flags, str(root)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


BODY = "\n# A skill\n\nStep one.\n\n```bash\necho hi\n```\n"
FOLDED = "name: {n}\ndescription: >-\n  Does a thing on the computer. Use when\n  someone asks for the thing."
QUOTED = 'name: {n}\ndescription: "Does a thing: quickly. Use when asked."\nargument-hint: "[what]"'
PLAIN = "name: {n}\ndescription: Does a thing on the computer. Use when asked."


def tree(tmp, skills, anywhere=(), code_only=(), data=None):
    """A minimal toolkit: the lists, and one SKILL.md per (name, frontmatter, body)."""
    root = Path(tmp)
    (root / "_shared" / "references").mkdir(parents=True, exist_ok=True)
    spec_ = dict(REAL)
    spec_["anywhere"] = {n: "test" for n in anywhere}
    spec_["claude_code_only"] = {n: "test" for n in code_only}
    spec_.update(data or {})
    (root / "_shared" / "references" / "skill-surfaces.json").write_text(json.dumps(spec_), encoding="utf-8")
    for name, front, body in skills:
        d = root / "skills" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"---\n{front.format(n=name)}\n---\n{body}", encoding="utf-8", newline="\n")
    return root


def skill_text(root, name):
    return (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


print("\nthe toolkit's own skills")
code, out = run(ROOT)
check(f"every skill in skills/ is listed once, and each Claude Code skill carries the note ({out.strip().splitlines()[-1][:70]})", code == 0)
listed = set(REAL["anywhere"]) | set(REAL["claude_code_only"])
check("the lists name exactly the folders in skills/", listed == set(m.skill_dirs(ROOT)))
check("no skill is in both groups", not set(REAL["anywhere"]) & set(REAL["claude_code_only"]))
check("every listed skill gives a reason", all(isinstance(v, str) and v.strip() for g in m.GROUPS for v in REAL[g].values()))
check("ai-level-up, written to run in chat, works anywhere", "ai-level-up" in REAL["anywhere"])
check("the setup skills need Claude Code", {"nsls-setmeup", "setup", "update-toolkit"} <= set(REAL["claude_code_only"]))

print("\nthe words")
check("the note holds the sentence the person sees, whole and on one line", f'> "{SENTENCE}"' in NOTE.split("\n"))
check("the sentence is one sentence", SENTENCE.count(".") == 1 and SENTENCE.endswith(".") and "\n" not in SENTENCE)
check("the sentence names Claude Code and the person's computer", "Claude Code" in SENTENCE and "your computer" in SENTENCE)
check(
    "the sentence shows staff no path and no technical word",
    not any(w in SENTENCE.lower() for w in ("plugin", "sandbox", "/", "\\", "~", "`", "$", "session", "terminal")),
)
check("the note leaves Claude Code alone", "In **Claude Code**" in NOTE and "skip this\n> note" in NOTE)
check("unsure defaults to Claude Code, never to stopping", "any other\n> answer, blank included, is Claude Code" in NOTE)
check("the note names chat and Cowork", "ordinary Claude chat or a Cowork task" in NOTE)
for name in sorted(REAL["claude_code_only"]):
    text = skill_text(ROOT, name)
    if text.count(NOTE) != 1 or text.count(m.START) != 1:
        check(f"{name} carries the shared note exactly once", False)
check("all Claude Code skills carry the same note, once each", not any("carries the shared note" in f for f in failures))

print("\na skill that skips it is caught")
with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("new-skill", FOLDED, BODY), ("old", FOLDED, BODY)], anywhere=["old"])
    code, out = run(root)
    check("a skill in neither group fails, by name", code == 1 and "skills/new-skill: not listed" in out)
    check("the failure says what to do next", "--fix" in out and '"anywhere"' in out and '"claude_code_only"' in out)
    check("--fix does not sort an unlisted skill by itself", run(root, "--fix")[0] == 1 and skill_text(root, "new-skill") == f"---\n{FOLDED.format(n='new-skill')}\n---\n{BODY}")

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("needs-mac", FOLDED, BODY)], code_only=["needs-mac"])
    code, out = run(root)
    check("a Claude Code skill without the note fails", code == 1 and "the note that says so is missing" in out)
    check("a Claude Code skill without the tag fails", f'the description must start with "{TAG}"' in out)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("both", FOLDED, BODY)], anywhere=["both"], code_only=["both"])
    code, out = run(root)
    check("a skill in both groups fails", code == 1 and "both: listed in both groups" in out)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("here", FOLDED, BODY)], anywhere=["here", "gone"])
    code, out = run(root)
    check("a listed skill with no SKILL.md fails", code == 1 and "gone: listed" in out)

with tempfile.TemporaryDirectory() as tmp:
    reworded = NOTE.replace("reply with only this sentence", "tell them something like")
    root = tree(tmp, [("mine", FOLDED.replace(">-\n  ", f">-\n  {TAG}\n  "), f"\n{reworded}\n{BODY}")], code_only=["mine"])
    code, out = run(root)
    check("a note with its own wording fails", code == 1 and "differ from the shared ones" in out)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("low", FOLDED.replace(">-\n  ", f">-\n  {TAG}\n  "), f"{BODY}\n{NOTE}\n")], code_only=["low"])
    code, out = run(root)
    check("a note below the skill's own text fails: it must come first", code == 1 and "not the first thing after the frontmatter" in out)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("chatty", FOLDED, f"\n{NOTE}\n{BODY}")], anywhere=["chatty"])
    code, out = run(root)
    check("a works-anywhere skill carrying the note fails", code == 1 and "listed as working anywhere" in out)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("nofm", "", BODY)], code_only=["nofm"])
    (root / "skills" / "nofm" / "SKILL.md").write_text("# No frontmatter\n", encoding="utf-8")
    code, out = run(root)
    check("a SKILL.md with no frontmatter fails rather than passing unread", code == 1 and "no frontmatter" in out)

print("\nthe shared wording is checked too")
for label, change, expect in (
    ("a sentence that shows staff a path", {"person_sees": "Open ~/.claude and run it there."}, "keep it plain"),
    ("a sentence that says plugin", {"person_sees": "This plugin needs Claude Code."}, "keep it plain"),
    ("two sentences", {"person_sees": "This needs Claude Code. Switch to it."}, "one sentence"),
    ("a note without the sentence", {"guard": [m.START + " -->", "> stop", m.END]}, "{person_sees} exactly once"),
    ("a note without its markers", {"guard": ["> stop", '> "{person_sees}"', "> end"]}, "must open with"),
    ("a missing group", {"anywhere": None}, '"anywhere" must be'),
):
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(tmp, [], data=change)
        code, out = run(root)
        check(f"{label} is refused", code == 2 and expect in out)

print("\n--fix adds the note and the tag, and nothing else")
for label, front in (("a folded description", FOLDED), ("a quoted description", QUOTED), ("a one-line description", PLAIN)):
    with tempfile.TemporaryDirectory() as tmp:
        root = tree(tmp, [("s", front, BODY)], code_only=["s"])
        code, out = run(root, "--fix")
        text = skill_text(root, "s")
        parts = m.split(text)
        check(f"{label}: fixed tree passes", code == 0 and "updated skills/s/SKILL.md" in out)
        check(f"{label}: the note is the first thing after the frontmatter", parts[1].startswith(f"\n{NOTE}\n\n# A skill"))
        check(f"{label}: the skill's own text is untouched", parts[1] == f"\n{NOTE}\n{BODY}")
        check(f"{label}: the description starts with the tag", m.has_tag(parts[0], TAG))
        check(
            f"{label}: taking the tag off gives back the frontmatter as written",
            "\n".join(m.remove_tag(parts[0], TAG)) == front.format(n="s"),
        )
        check(f"{label}: a second --fix changes nothing", run(root, "--fix") == (0, run(root)[1]) and skill_text(root, "s") == text)

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("q", QUOTED, BODY)], code_only=["q"])
    run(root, "--fix")
    line = [l for l in skill_text(root, "q").split("\n") if l.startswith("description:")][0]
    check("a quoted description keeps its quotes", line == f'description: "{TAG} Does a thing: quickly. Use when asked."')

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("s", FOLDED, BODY)], code_only=["s"])
    run(root, "--fix")
    spec_path = root / "_shared" / "references" / "skill-surfaces.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    data["person_sees"] = "This skill needs Claude Code on your computer, so open Claude Code and run it there."
    spec_path.write_text(json.dumps(data), encoding="utf-8")
    check("changing the shared sentence makes every copy stale", run(root)[0] == 1)
    code, _ = run(root, "--fix")
    text = skill_text(root, "s")
    check("--fix rewrites the note in place: one copy, new words", code == 0 and text.count(m.START) == 1 and data["person_sees"] in text)
    check("and still leaves the skill's own text alone", m.split(text)[1].endswith(BODY))

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("s", FOLDED, BODY)], code_only=["s"])
    run(root, "--fix")
    spec_path = root / "_shared" / "references" / "skill-surfaces.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    data["anywhere"], data["claude_code_only"] = {"s": "now works in chat"}, {}
    spec_path.write_text(json.dumps(data), encoding="utf-8")
    code, _ = run(root, "--fix")
    check(
        "moving a skill to works-anywhere takes the note and tag off, back to the file as written",
        code == 0 and skill_text(root, "s") == f"---\n{FOLDED.format(n='s')}\n---\n{BODY}",
    )

with tempfile.TemporaryDirectory() as tmp:
    root = tree(tmp, [("win", FOLDED, BODY)], code_only=["win"])
    run(root, "--fix")
    p = root / "skills" / "win" / "SKILL.md"
    p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
    check("a Windows checkout (CRLF line endings) still passes", run(root)[0] == 0)

if failures:
    print(f"\n{len(failures)} FAILED")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("\nall passed")
