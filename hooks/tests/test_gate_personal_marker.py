#!/usr/bin/env python3
# windows-ci: python | A repo with a .personal-repo file is not blocked as NSLS work in a personal repo
"""A repo that declares itself personal is not blocked by gate 1.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_gate_personal_marker.py`.

Gate 1 reads any "nsls" in a repo's README as proof of NSLS work. On
2026-10-05 it blocked Davo's own codex-review-kit, whose README said it lived
outside the NSLS toolkits on purpose. And nothing remembered a repo Kevin had
authorized to stay put, so the next push was blocked again. A `.personal-repo`
file at the top of the repo now settles both. These checks pin down exactly
where that file counts: at the top level, as a file, wherever the push is run
from. Without it, the block stands and names the file as the way out.

Anyone who can write a file can write that one, Claude included. So a push the
file lets through is reported (one guardrail_proceeded row per repo per day),
and only when the file changed the outcome.

No network: NSLS_GUARDRAIL_EVENT_LOG redirects the event emitter to a file.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "hooks" / "guardrail-gate.py"
MARKER = ".personal-repo"

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def make_repo(parent, name):
    """Personal remote, NSLS fingerprints: the shape gate 1 exists to block."""
    repo = Path(parent) / name
    repo.mkdir()
    (repo / "README.md").write_text(
        "# Davo's review kit\nLives outside the NSLS toolkits on purpose.\n")
    run = lambda *a: subprocess.run(a, cwd=repo, capture_output=True, text=True)
    run("git", "init", "-q")
    run("git", "remote", "add", "origin",
        "https://github.com/someones-personal-account/review-kit.git")
    return repo


def gate(cwd, command, env):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run(
        [sys.executable, str(GATE)], input=json.dumps(payload),
        capture_output=True, text=True, cwd=cwd, env=env, timeout=30,
    )


def decision(result):
    try:
        out = json.loads(result.stdout or "{}")
    except Exception:
        return "unparseable", ""
    hso = out.get("hookSpecificOutput", {})
    return hso.get("permissionDecision") or "allow", hso.get("permissionDecisionReason", "")


def events(log):
    return log.read_text().count("\n") if log.exists() else 0


def event_rows(log):
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line]


with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ)
    env["CLAUDE_CONFIG_DIR"] = str(Path(tmp) / "claude")
    env.pop("NSLS_GUARDRAILS_DISABLED", None)
    (Path(tmp) / "claude").mkdir()
    PUSH = "git push origin main"

    print("without the file, gate 1 still blocks")
    repo = make_repo(tmp, "plain")
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(Path(tmp) / "plain.jsonl")
    verdict, reason = decision(gate(repo, PUSH, env))
    check("a push is denied", verdict == "deny", verdict)
    check("the block names the file that clears it", MARKER in reason, reason[-300:])
    check("one block event recorded", events(Path(tmp) / "plain.jsonl") == 1)

    print("\nwith the file at the top of the repo, the push goes through")
    repo = make_repo(tmp, "declared")
    (repo / MARKER).write_text("")
    log = Path(tmp) / "declared.jsonl"
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(log)
    r = gate(repo, PUSH, env)
    check("a push is allowed", decision(r)[0] == "allow", r.stdout[:200])
    check("the gate says nothing", r.stdout.strip() == "", r.stdout[:200])
    rows = event_rows(log)
    check("no block event recorded",
          not any(e["type"] == "guardrail_blocked" for e in rows), rows)
    # Claude can write the file as easily as the builder can, so the skip must
    # leave a row Kevin can see. Deduped: one row per repo per day, not per push.
    check("the skip is reported as one guardrail_proceeded event",
          [e["type"] for e in rows] == ["guardrail_proceeded"], rows)
    check("the event names the file and is deduped per day",
          rows and MARKER in rows[0]["description"] and rows[0]["dedupe"] is True
          and rows[0]["variant"] == "personal-repo-marker", rows)

    sub = repo / "skills"
    sub.mkdir()
    r = gate(sub, PUSH, env)
    check("a push run from a subfolder is allowed", decision(r)[0] == "allow",
          r.stdout[:200])

    elsewhere = Path(tmp) / "elsewhere"
    elsewhere.mkdir()
    r = gate(elsewhere, f"git -C '{repo.as_posix()}' push origin main", env)
    check("`git -C <repo> push` from another folder is allowed",
          decision(r)[0] == "allow", r.stdout[:200])

    print("\nthe skip is reported only when the file changed the outcome")
    plain = Path(tmp) / "weekend"
    plain.mkdir()
    (plain / "README.md").write_text("# Recipe scraper\n")
    subprocess.run(["git", "init", "-q"], cwd=plain, capture_output=True)
    subprocess.run(["git", "remote", "add", "origin",
                    "https://github.com/someones-personal-account/recipes.git"],
                   cwd=plain, capture_output=True)
    (plain / MARKER).write_text("")
    log = Path(tmp) / "weekend.jsonl"
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(log)
    r = gate(plain, PUSH, env)
    check("a non-NSLS personal repo with the file is allowed",
          decision(r)[0] == "allow", r.stdout[:200])
    check("...and reports nothing (gate 1 would have allowed it anyway)",
          events(log) == 0, event_rows(log))

    moved = make_repo(tmp, "moved")
    subprocess.run(["git", "remote", "set-url", "origin",
                    "https://github.com/thensls/review-kit.git"],
                   cwd=moved, capture_output=True)
    (moved / MARKER).write_text("")
    log = Path(tmp) / "moved.jsonl"
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(log)
    r = gate(moved, PUSH, env)
    check("a repo already on thensls with a leftover file is allowed",
          decision(r)[0] == "allow", r.stdout[:200])
    check("...and reports nothing", events(log) == 0, event_rows(log))

    print("\nthe file only counts at the top level, and only as a file")
    repo = make_repo(tmp, "nested")
    (repo / "notes").mkdir()
    (repo / "notes" / MARKER).write_text("")
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(Path(tmp) / "nested.jsonl")
    check("a marker in a subfolder does not count, even pushing from there",
          decision(gate(repo / "notes", PUSH, env))[0] == "deny")

    repo = make_repo(tmp, "folder-marker")
    (repo / MARKER).mkdir()
    env["NSLS_GUARDRAIL_EVENT_LOG"] = str(Path(tmp) / "folder.jsonl")
    check("a folder named .personal-repo does not count",
          decision(gate(repo, PUSH, env))[0] == "deny")

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
