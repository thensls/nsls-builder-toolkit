#!/usr/bin/env python3
"""Turn Fathom list_meetings dumps into per-meeting text files plus a
praise-candidate file for the /wins skill.

Usage:
  python3 -I find_wins.py --out DIR --name "First" [--name "Alt Full Name"] DUMP.json [DUMP2.json ...]

DUMP files are the saved results of Fathom `list_meetings` called with
include_transcript=true and include_summary=true (one file per page).

Writes:
  DIR/meetings/<start>_<recording_id>.txt   summary + full transcript, one per meeting the user SPOKE in
  DIR/candidates.txt                        lines that look like praise, with context (see markers below)
  stdout                                    which meetings were kept, skipped, or deduped

Candidates are leads, not findings. Every one must be checked in context
before it is reported (praise is often aimed at someone else).
Markers: ">>" another speaker said it; "?>" Fathom labels it as the user,
so check who really said it (often a colleague's line, mislabeled).
Keyword candidates miss praise without a praise word; read full transcripts too.
"""
import argparse
import json
import os
import re
from datetime import datetime

PRAISE = re.compile(
    r"\b(great job|good job|nice job|great work|good work|well done|crushing it|killing it|nailed it|"
    r"you rock|kudos|shout ?out|proud of|thank you so much|thanks so much|thank you for|"
    r"appreciate (you|it|that|all|your)|we appreciate|grateful|"
    r"amazing|awesome|incredible|fantastic|excellent|brilliant|impressive|impressed|"
    r"so helpful|really helpful|super helpful|so clear|really clear|very clear|"
    r"great idea|good idea|smart move|great point|great question|"
    r"love (this|that|it|how|what|the)|feel (so )?(good|great) (about|in)|leading the charge|"
    r"run with it|you decide|your call|trust you|"
    r"doing a great|doing great|great start|important work|good handle|right direction)\b",
    re.I,
)
# Thanks or credit that names the user ("Thanks, Ann", "this came out of Ann's work").
NAMED = re.compile(r"\b(thanks?|thank you|appreciate|great|good|love|work|credit)\b", re.I)
# Bare filler that matches praise words but almost never is praise.
FILLER = re.compile(r"^(okay,? )?(that|it|this) makes( perfect)? sense\.?$|^(perfect|awesome|amazing|great)[.!]?$", re.I)


def load_items(paths):
    for p in paths:
        with open(p) as fh:
            data = json.load(fh)
        if isinstance(data, dict) and "items" not in data and "result" in data:
            data = data["result"]
        for m in data.get("items", []):
            yield m


def speaker(line):
    return ((line.get("speaker") or {}).get("display_name") or "").strip()


def mentions(text, variants):
    """True when the text names the user (first-name variants as whole words)."""
    return is_user(text, [v.split()[0] for v in variants if v.strip()])


def is_user(name, variants):
    """Match each variant as whole name words, so "Ann" never matches "Joanne"."""
    n = name.lower()
    return any(re.search(rf"(?<!\w){re.escape(v.lower().strip())}(?!\w)", n) for v in variants if v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", action="append", required=True,
                    help="name variants for the user as Fathom shows them; repeatable")
    ap.add_argument("--context", type=int, default=6, help="lines of context before each candidate")
    ap.add_argument("dumps", nargs="+")
    a = ap.parse_args()

    mdir = os.path.join(a.out, "meetings")
    os.makedirs(mdir, exist_ok=True)
    # Clear files from earlier runs so only this run's meetings can be read.
    for fname in os.listdir(mdir):
        fpath = os.path.join(mdir, fname)
        if os.path.isfile(fpath) and fname.endswith(".txt"):
            os.remove(fpath)

    seen_ids, kept = set(), []
    for m in load_items(a.dumps):
        rid = m.get("recording_id")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        t = m.get("transcript") or []
        title = (m.get("title") or m.get("meeting_title") or "").strip()
        start = m.get("recording_start_time") or m.get("created_at") or ""
        if not any(is_user(speaker(x), a.name) for x in t):
            print(f"skip (user did not speak): {start[:16]}  {title}")
            continue
        # Same meeting recorded by two people: same title, starts within 10 minutes. Keep the longer one.
        try:
            st = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            st = None
        dup = None
        for k in kept:
            if k["title"].lower() == title.lower() and st and k["st"] and abs((k["st"] - st).total_seconds()) < 600:
                dup = k
                break
        rec = {"m": m, "title": title, "start": start, "st": st, "t": t}
        if dup:
            if len(t) > len(dup["t"]):
                kept[kept.index(dup)] = rec
            print(f"dedupe (duplicate recording): {start[:16]}  {title}")
            continue
        kept.append(rec)

    kept.sort(key=lambda r: r["start"])
    with open(os.path.join(a.out, "candidates.txt"), "w") as cand:
        for r in kept:
            m, t = r["m"], r["t"]
            share = m.get("share_url") or m.get("url") or ""
            fn = os.path.join(mdir, f"{r['start'][:16].replace(':', '')}_{m.get('recording_id')}.txt")
            with open(fn, "w") as o:
                o.write(f"# {r['title']} | {r['start']} | {share}\n")
                o.write(((m.get("default_summary") or {}).get("markdown_formatted") or "") + "\n\n## TRANSCRIPT\n")
                for x in t:
                    o.write(f"[{x.get('timestamp')}] {speaker(x)}: {x.get('text')}\n")
            print(f"keep: {r['start'][:16]}  {r['title']}  ({len(t)} lines)")

            hits = {}
            for i, x in enumerate(t):
                who, text = speaker(x), (x.get("text") or "").strip()
                named = mentions(text, a.name) and NAMED.search(text)
                if FILLER.match(text) or not (PRAISE.search(text) or named):
                    continue
                # Fathom often puts other people's lines under the user's name
                # (a colleague's "Good job" or "Thanks, <user>"), so keep user-labeled
                # praise too, flagged for a speaker check instead of dropped.
                hits[i] = "?>" if is_user(who, a.name) else ">>"
            if not hits:
                continue
            cand.write(f"\n===== {r['title']} | {r['start'][:16]} | {share}\n")
            for i in hits:
                lo = max(0, i - a.context)
                cand.write("  ---\n")
                for j in range(lo, min(len(t), i + 3)):
                    mark = hits[i] if j == i else "  "
                    cand.write(f"  {mark} [{t[j].get('timestamp')}] {speaker(t[j])}: {(t[j].get('text') or '')[:400]}\n")
    print(f"\n{len(kept)} meetings kept. Candidates: {os.path.join(a.out, 'candidates.txt')}")


if __name__ == "__main__":
    main()
