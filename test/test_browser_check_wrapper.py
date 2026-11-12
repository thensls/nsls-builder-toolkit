#!/usr/bin/env python3
"""The /browser-check wrapper's two promises: vendor telemetry can't leave, and a
run that loaded browser cookies fails loudly.

Plain stdlib, no network: run with `python3 test/test_browser_check_wrapper.py`.
Needs bash, git and node on PATH. A fake `npx` stands in for expect-cli and writes
the same session log line the real 0.1.3 writes, so the after-run cookie check
is exercised end to end.

Exists because both promises were found broken on 2026-11-12 before this
wrapper: NO_TELEMETRY=1 left Expect's Axiom traces flowing, and an
`echo | grep -q` under pipefail let a cookie-carrying session pass the check.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "browser-check" / "scripts"
WRAPPER = SCRIPTS / "browser-check.sh"
BLOCKER = SCRIPTS / "block-telemetry.cjs"

FAILED = []


def check(label, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if not ok:
        FAILED.append(f"{label} {detail}".strip())


def session_line(cookies, external):
    # Same shape as expect-cli 0.1.3's .expect/logs.md entry.
    return ('timestamp=2026-11-12T21:18:00.447Z level=Info fiber=#20 '
            'message="\\"MCP browser session opened\\"" message="{\\"source\\":\\"mcp_open\\",'
            '\\"browser_type\\":\\"chromium\\",\\"browser_mode\\":\\"headless\\",'
            f'\\"connection_mode\\":\\"launched\\",\\"is_external_browser\\":{external},'
            f'\\"cookie_count\\":{cookies}}}"')


def fake_repo(tmp, lines_to_log, record_env=False):
    repo = pathlib.Path(tmp) / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    bindir = pathlib.Path(tmp) / "bin"
    bindir.mkdir()
    log_body = "\n".join(f"echo '{l}' >> .expect/logs.md" for l in lines_to_log)
    env_dump = f'env > "{tmp}/env.txt"; printf "%s\\n" "$@" > "{tmp}/args.txt"' if record_env else ""
    (bindir / "npx").write_text(
        "#!/usr/bin/env bash\n"
        "mkdir -p .expect\n"
        f"{log_body}\n{env_dump}\n"
        "echo '{\"status\": \"passed\"}'\n"
    )
    (bindir / "npx").chmod(0o755)
    env = dict(os.environ, PATH=f"{bindir}{os.pathsep}{os.environ['PATH']}",
               EXPECT_PROFILE="Default", EXPECT_COOKIE_BROWSERS="chrome")
    return repo, env


def run_wrapper(repo, env, *extra):
    return subprocess.run(["bash", str(WRAPPER), "--url", "http://localhost:1", "--message", "m", *extra],
                          cwd=repo, env=env, capture_output=True, text=True)


print("\nthe telemetry blocker refuses vendor hosts and nothing else")
probe = r"""
const dns=require('dns');
const hosts=['us.i.posthog.com','api.axiom.co','expect.dev','www.expect.dev','localhost'];
let n=hosts.length;
for (const h of hosts) dns.lookup(h,(e)=>{console.log(h+' '+(e?'BLOCKED':'ok')); if(--n===0) process.exit(0)});
"""
r = subprocess.run(["node", "-e", probe], capture_output=True, text=True,
                   env=dict(os.environ, NODE_OPTIONS=f'--require "{BLOCKER}"'))
out = dict(line.split(" ", 1) for line in r.stdout.split("\n") if line)
for h in ("us.i.posthog.com", "api.axiom.co", "expect.dev", "www.expect.dev"):
    check(f"{h} blocked", out.get(h) == "BLOCKED", repr(r.stdout + r.stderr))
check("localhost still resolves", out.get("localhost") == "ok", repr(r.stdout + r.stderr))

print("\nthe wrapper refuses anything that could reach a real browser session")
with tempfile.TemporaryDirectory() as tmp:
    repo, env = fake_repo(tmp, [])
    for flag in (["--profile", "Default"], ["--cdp", "ws://x"], ["--cookies"], ["--browser-mode", "headed"]):
        r = run_wrapper(repo, env, *flag)
        check(f"{flag[0]} refused (exit 2)", r.returncode == 2, repr(r.stderr))

print("\nwhat the wrapper hands expect-cli")
with tempfile.TemporaryDirectory() as tmp:
    repo, env = fake_repo(tmp, [session_line(0, "false")], record_env=True)
    r = run_wrapper(repo, env)
    envtxt = (pathlib.Path(tmp) / "env.txt").read_text()
    args = (pathlib.Path(tmp) / "args.txt").read_text().split("\n")
    check("NO_TELEMETRY=1", "NO_TELEMETRY=1" in envtxt.split("\n"))
    check("blocker preloaded via NODE_OPTIONS", "block-telemetry.cjs" in envtxt)
    check("caller's EXPECT_PROFILE removed", "EXPECT_PROFILE=" not in envtxt)
    check("caller's EXPECT_COOKIE_BROWSERS removed", "EXPECT_COOKIE_BROWSERS=" not in envtxt)
    check("--ci passed (the flag that actually drops cookies)", "--ci" in args)
    check("version pinned", any(a.startswith("expect-cli@0.") for a in args), repr(args))

print("\nthe after-run cookie check")
cases = [
    ("clean session passes", [session_line(0, "false")], 0),
    ("cookies loaded fails (exit 3)", [session_line(12, "false")], 3),
    ("real browser attached fails (exit 3)", [session_line(0, "true")], 3),
    ("one bad session among clean ones fails (exit 3)",
     [session_line(0, "false"), session_line(0, "false"), session_line(5, "false")], 3),
]
for label, lines, want in cases:
    with tempfile.TemporaryDirectory() as tmp:
        repo, env = fake_repo(tmp, lines)
        r = run_wrapper(repo, env)
        check(label, r.returncode == want, f"got exit {r.returncode}: {r.stderr[-300:]!r}")

with tempfile.TemporaryDirectory() as tmp:
    repo, env = fake_repo(tmp, [])
    r = run_wrapper(repo, env)
    check("no session logged warns, never claims safe", "WARNING" in r.stderr and "passed" not in r.stderr,
          repr(r.stderr))

if FAILED:
    print("\nFAILED:\n  " + "\n  ".join(FAILED))
    sys.exit(1)
print("\nall ok")
