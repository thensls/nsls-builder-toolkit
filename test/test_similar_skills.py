#!/usr/bin/env python3
"""The installed-skills duplicate check.

Run: python3 test/test_similar_skills.py

Exists because the registry check reported "no overlap" for a skill that was
sitting next to a near-identical one on the same machine (2026-09-19), and
nothing in the system could have noticed.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ss", ROOT / "hooks" / "similar-skills.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FAILED = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if not ok:
        FAILED.append(f"{label}: got {got!r}, wanted {want!r}")


def sc(qn, qd, cn, cd):
    return round(m.score(m.tokens(qn), m.tokens(qn + " " + qd),
                         m.tokens(cn), m.tokens(cn + " " + cd)), 2)


print("\nthe case this exists for — a shared distinctive name beats a diluted description")
s = sc("macroscope-watch", "Waits for the Macroscope review bot to finish on a PR",
       "macroscope", "Use when the Macroscope review bot has posted review comments on a pull request")
check(f"macroscope pair scores {s} (>= threshold)", s >= m.THRESHOLD, True)

print("\nunrelated work stays quiet")
s = sc("rippling sync", "Hourly sync of employee records from Rippling into Airtable",
       "macroscope", "Use when the Macroscope review bot has posted review comments")
check(f"rippling vs macroscope scores {s} (< threshold)", s < m.THRESHOLD, True)

print("\nstopwords and plural folding match the registry check exactly")
check("'skills'/'tools'/'automation' dropped", m.tokens("skills tools automation"), set())
check("plural folded to singular", m.tokens("dashboards") == m.tokens("dashboard"), True)
check("short tokens dropped", "to" not in m.tokens("to the pr"), True)

print("\noverlap coefficient, not Jaccard — a one-line query is not punished for a long description")
q, long_row = {"alpha", "beta"}, {"alpha", "beta"} | {f"w{i}" for i in range(30)}
check("full query coverage scores 1.0", m.similarity(q, long_row), 1.0)
check("empty set scores 0.0", m.similarity(set(), long_row), 0.0)

print("\ndiscovery is deduplicated across cached plugin versions")
names = list(m.installed_skills())
check("no duplicate skill names", len(names), len(set(names)))
check("found some skills at all", len(names) > 0, True)

print("\nit never raises — a crashing duplicate check must not stop a build")
try:
    m.main(["similar-skills.py"])
    m.main(["similar-skills.py", "", ""])
    check("degenerate input handled", True, True)
except Exception as e:
    check(f"degenerate input raised {e!r}", False, True)

print()
if FAILED:
    print("FAILURES:")
    for f in FAILED:
        print("  -", f)
    sys.exit(1)
print("all green — the skills check agrees with the registry check's arithmetic")
