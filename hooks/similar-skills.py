#!/usr/bin/env python3
"""Is a skill like this one already installed?

The registry check (`POST /similar`) answers "has anyone REGISTERED something
like this". For a skill that is the wrong corpus twice over: most skills never
get their own registry row, and the thing a new skill most often duplicates is
another skill sitting on the same machine.

That gap cost real time on 2026-09-19 -- a macroscope-watch skill was checked
against the registry, came back clean, and only turned out to sit beside an
existing `macroscope` skill when a human said "check the toolkit too". The two
were complementary in the end, but nothing in the check knew that.

So this reads the skills actually installed and scores them the same way the
registry check scores rows: same stopwords, same one-character plural folding,
same overlap coefficient, same 0.5 threshold. Consistent numbers matter more
than clever ones -- a builder seeing 0.61 from one check and 0.34 from the other
for the same pair learns to trust neither.

    similar-skills.py "<name>" "<one sentence>"

Prints matches, highest first, or nothing at all. Silence is the same contract
the registry check keeps: no match is not evidence of no neighbour.
"""
import os
import re
import sys
from pathlib import Path

STOPWORDS = frozenset(
    "a an and are as at be but by for from has have in into is it its of on or "
    "that the this to was were will with we our your you nsls automation "
    "automations tool tools skill skills bot script app system data new "
    "use used using when claude code".split()
)
THRESHOLD = 0.5
TOP_N = 3


def tokens(text):
    words = re.split(r"[^a-z0-9]+", (text or "").lower())
    words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def similarity(query, row):
    """Overlap coefficient -- |intersection| / |smaller set|, as the proxy does."""
    if not query or not row:
        return 0.0
    return len(query & row) / min(len(query), len(row))


def skill_roots():
    """Every directory a SKILL.md can live in, deduplicated by real path.

    A plugin installed from the marketplace keeps one directory per cached
    version, so the same skill appears three or four times. Reporting "matched
    macroscope (x4)" would read as four neighbours instead of one.
    """
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))
    roots = [home / "skills"]
    roots += sorted((home / "local-plugins").glob("*/skills"))
    roots += sorted((home / "plugins" / "cache").glob("*/*/*/skills"))
    return [r for r in roots if r.is_dir()]


def installed_skills():
    """name -> (description, where it lives). Newest cached copy wins."""
    found = {}
    for root in skill_roots():
        for skill_md in sorted(root.glob("*/SKILL.md")):
            name = skill_md.parent.name
            if name in found:
                continue
            try:
                head = skill_md.read_text(errors="replace")[:4000]
            except OSError:
                continue
            # Frontmatter description, folded to one line. Deliberately naive:
            # a real YAML parse would pull in a dependency the toolkit ships
            # without, and every SKILL.md in this repo is a plain block scalar.
            desc = ""
            m = re.search(r"^description:\s*(.*?)(?=^\w+:|^---\s*$)",
                          head, re.M | re.S)
            if m:
                desc = " ".join(m.group(1).split())
                desc = desc.lstrip("|>-").strip()
            found[name] = (desc, str(skill_md.parent))
    return found


def score(query_name, query_all, cand_name, cand_all):
    """Best of two readings, because a skill's name carries more signal than its
    description.

    A SKILL.md description is a trigger-phrase blob -- "use when", "pull
    request", "review" -- words that any number of unrelated skills share. They
    dilute the overlap: macroscope-watch against the existing macroscope skill
    scored 0.44 on full text and slipped under the bar, even though the word
    macroscope was sitting in both names. Names are short and chosen to be
    distinctive, so overlap between them is the sharper instrument. Take
    whichever reading is more suspicious and let the human judge; the contract
    here is to mention a neighbour, never to block one.
    """
    return max(similarity(query_all, cand_all),
               similarity(query_name, cand_name))


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-3].strip(), file=sys.stderr)
        return 2
    q_name = tokens(argv[1])
    q_all = tokens(argv[1] + " " + (argv[2] if len(argv) > 2 else ""))
    hits = []
    for name, (desc, where) in installed_skills().items():
        if tokens(name) == q_name:
            continue  # the skill being described is not its own neighbour
        s = score(q_name, q_all, tokens(name), tokens(name + " " + desc))
        if s >= THRESHOLD:
            hits.append((s, name, desc, where))
    hits.sort(key=lambda h: (-h[0], h[1]))
    for s, name, desc, where in hits[:TOP_N]:
        print(f"{s:.2f}  {name}  ({where})")
        if desc:
            print(f"      {desc[:150]}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:
        # Same fail-open contract as every other guardrail hook: a duplicate
        # check that crashes must never be what stops someone building.
        sys.exit(0)
