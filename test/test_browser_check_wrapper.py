#!/usr/bin/env python3
"""The /browser-check wrapper's two promises: vendor telemetry can't leave, and a
run that loaded browser cookies fails loudly.

Plain stdlib, no network: run with `python3 test/test_browser_check_wrapper.py`.
Needs bash, git and node on PATH. A fake pre-installed expect-cli (in a temp cache) writes
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


# Same shape as expect-cli 0.1.3's cookie import (server-*.js and index.js), made callable:
# open({cookies: true}, false) reports whether addCookies ran.
COOKIE_CHUNK = ("export function open(t,s){let imported=false;const u={addCookies(){imported=true}};"
                "if(t.cookies&&!s){let r=Array.isArray(t.cookies)?t.cookies:[];u.addCookies(r)}return imported}\n")


def fake_repo(tmp, lines_to_log, record_env=False, skip_entry=None, cookie_chunk=COOKIE_CHUNK):
    """A git repo to run in, plus a fake pre-installed expect-cli in a temp cache
    (so the wrapper skips npm and patches these files instead)."""
    tmp = pathlib.Path(tmp)
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    pkg = tmp / "cache" / "nsls-browser-check" / "expect-cli-0.1.3" / "node_modules" / "expect-cli"
    dist = pkg / "dist"
    dist.mkdir(parents=True)
    (pkg / "package.json").write_text('{"type": "module"}')
    logs = "".join(f"fs.appendFileSync('.expect/logs.md', {l!r} + '\\n');\n" for l in lines_to_log)
    dump = (f"fs.writeFileSync({str(tmp / 'env.txt')!r}, Object.entries(process.env).map(([k,v])=>k+'='+v).join('\\n'));\n"
            f"fs.writeFileSync({str(tmp / 'args.txt')!r}, process.argv.slice(2).join('\\n'));\n") if record_env else ""
    (dist / "index.js").write_text(
        "#!/usr/bin/env node\nimport fs from 'node:fs';\n"
        "fs.mkdirSync('.expect', {recursive: true});\n" + logs + dump +
        "console.log(JSON.stringify({status: 'passed'}));\n")
    for name in ("browser-mcp.js", "browser-daemon.js"):
        if name != skip_entry:
            (dist / name).write_text("export {};\n")
    if cookie_chunk is not None:
        (dist / "server-Abc123.js").write_text(cookie_chunk)
    env = dict(os.environ, XDG_CACHE_HOME=str(tmp / "cache"),
               EXPECT_PROFILE="Default", EXPECT_COOKIE_BROWSERS="chrome")
    return repo, env, dist


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
    repo, env, _ = fake_repo(tmp, [])
    for flag in (["--profile", "Default"], ["--cdp", "ws://x"], ["--cookies"], ["--browser-mode", "headed"]):
        r = run_wrapper(repo, env, *flag)
        check(f"{flag[0]} refused (exit 2)", r.returncode == 2, repr(r.stderr))

print("\nthe blocker is wired into every Expect entry point, or nothing runs")
MARKER = 'import "./nsls-block-telemetry.cjs"; // nsls-browser-check'
with tempfile.TemporaryDirectory() as tmp:
    repo, env, dist = fake_repo(tmp, [session_line(0, "false")])
    r = run_wrapper(repo, env)
    check("run succeeds after patching", r.returncode == 0, repr(r.stderr[-300:]))
    for name in ("index.js", "browser-mcp.js", "browser-daemon.js"):
        check(f"{name} imports the blocker", MARKER in (dist / name).read_text())
    check("index.js keeps its shebang on line 1", (dist / "index.js").read_text().startswith("#!"))
    check("blocker copied beside them", (dist / "nsls-block-telemetry.cjs").is_file())
    r2 = run_wrapper(repo, env)
    check("patch applied once, not again on rerun",
          (dist / "browser-mcp.js").read_text().count(MARKER) == 1, repr(r2.stderr[-200:]))
with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, [session_line(0, "false")], skip_entry="browser-mcp.js")
    r = run_wrapper(repo, env)
    check("missing entry point refuses to run (exit 2)", r.returncode == 2, repr(r.stderr[-300:]))

print("\ncookie import is switched off in Expect's own code")
probe_open = "import(process.argv[1]).then(m=>console.log(m.open({cookies:true},false)))"
with tempfile.TemporaryDirectory() as tmp:
    repo, env, dist = fake_repo(tmp, [session_line(0, "false")])
    chunk = dist / "server-Abc123.js"
    before = subprocess.run(["node", "-e", probe_open, str(chunk)], capture_output=True, text=True).stdout.strip()
    check("unpatched chunk imports cookies when asked (the test is live)", before == "true", repr(before))
    r = run_wrapper(repo, env)
    check("run succeeds", r.returncode == 0, repr(r.stderr[-300:]))
    after = subprocess.run(["node", "-e", probe_open, str(chunk)], capture_output=True, text=True,
                           env=dict(os.environ, NODE_OPTIONS="")).stdout.strip()
    check("patched chunk imports nothing even with cookies:true", after == "false", repr(after))
    run_wrapper(repo, env)
    check("cookie patch applied once, not again on rerun", chunk.read_text().count("&&!1)") == 1)
with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, [session_line(0, "false")],
                             cookie_chunk="export const x=(u)=>u.addCookies([]);\n")
    r = run_wrapper(repo, env)
    check("addCookies in an unrecognised shape refuses to run (exit 2)", r.returncode == 2, repr(r.stderr[-300:]))
with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, [session_line(0, "false")], cookie_chunk=None)
    r = run_wrapper(repo, env)
    check("no cookie-import code found at all refuses to run (exit 2)", r.returncode == 2, repr(r.stderr[-300:]))

print("\nparallel runs never trip over each other's setup")
with tempfile.TemporaryDirectory() as tmp:
    repo, env, dist = fake_repo(tmp, [session_line(0, "false")])
    procs = [subprocess.Popen(["bash", str(WRAPPER), "--url", "http://localhost:1", "--message", "m"],
                              cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(6)]
    results = [(p.wait(), p.stderr.read()) for p in procs]
    check("6 simultaneous runs all succeed", all(rc == 0 for rc, _ in results),
          repr([(rc, e[-200:]) for rc, e in results if rc != 0]))
    for name in ("index.js", "browser-mcp.js", "browser-daemon.js"):
        check(f"{name} patched exactly once", (dist / name).read_text().count(MARKER) == 1)
    check("no staged temp files left behind", not any(".tmp" in p.name for p in dist.iterdir()),
          repr([p.name for p in dist.iterdir()]))
    check("setup lock released", not (dist.parent.parent.parent.with_name("expect-cli-0.1.3.lock")).exists())

print("\nwhat the wrapper hands expect-cli")
with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, [session_line(0, "false")], record_env=True)
    r = run_wrapper(repo, env)
    envtxt = (pathlib.Path(tmp) / "env.txt").read_text()
    args = (pathlib.Path(tmp) / "args.txt").read_text().split("\n")
    check("NO_TELEMETRY=1", "NO_TELEMETRY=1" in envtxt.split("\n"))
    check("blocker also preloaded via NODE_OPTIONS", "block-telemetry.cjs" in envtxt)
    check("caller's EXPECT_PROFILE removed", "EXPECT_PROFILE=" not in envtxt)
    check("caller's EXPECT_COOKIE_BROWSERS removed", "EXPECT_COOKIE_BROWSERS=" not in envtxt)
    check("--ci passed (the flag that actually drops cookies)", "--ci" in args, repr(args))
    check("headless", "headless" in args, repr(args))

print("\nthe after-run cookie check")
cases = [
    ("clean session passes", [session_line(0, "false")], 0),
    ("cookies the site set itself don't fail a headless run", [session_line(3, "false")], 0),
    ("real browser attached fails (exit 3)", [session_line(0, "true")], 3),
    ("one bad session among clean ones fails (exit 3)",
     [session_line(0, "false"), session_line(2, "false"), session_line(0, "true")], 3),
]
for label, lines, want in cases:
    with tempfile.TemporaryDirectory() as tmp:
        repo, env, _ = fake_repo(tmp, lines)
        r = run_wrapper(repo, env)
        check(label, r.returncode == want, f"got exit {r.returncode}: {r.stderr[-300:]!r}")

with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, [session_line(0, "true")])
    sub = repo / "web" / "src"
    sub.mkdir(parents=True)
    r = run_wrapper(sub, env)
    check("real-browser session fails (exit 3) when started from a subfolder", r.returncode == 3,
          f"got exit {r.returncode}: {r.stderr[-300:]!r}")
    check("Expect's log lands at the repo root, where it is audited",
          (repo / ".expect" / "logs.md").is_file() and not (sub / ".expect").exists())

with tempfile.TemporaryDirectory() as tmp:
    repo, env, dist = fake_repo(tmp, [])
    (dist / "index.js").write_text("#!/usr/bin/env node\nconsole.log('{}');\n")  # writes no log at all
    r = run_wrapper(repo, env)
    check("no log written at all fails (exit 3), never passes unaudited", r.returncode == 3,
          f"got exit {r.returncode}: {r.stderr[-300:]!r}")

with tempfile.TemporaryDirectory() as tmp:
    repo, env, _ = fake_repo(tmp, ['timestamp=2026-11-12T21:18:00.447Z level=Info message="plan ready"'])
    r = run_wrapper(repo, env)
    check("no session logged warns, never claims safe", "WARNING" in r.stderr and "passed" not in r.stderr,
          repr(r.stderr))

if FAILED:
    print("\nFAILED:\n  " + "\n  ".join(FAILED))
    sys.exit(1)
print("\nall ok")
