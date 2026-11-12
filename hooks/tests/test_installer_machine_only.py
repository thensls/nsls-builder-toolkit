#!/usr/bin/env python3
"""`install.sh --machine-only` and `install.ps1 -MachineOnly` set up the computer and nothing else.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_installer_machine_only.py`.

When the toolkit arrives as a Claude plugin, nothing needs cloning or wiring
into Claude's settings. What a computer still lacks is the tools the skills
call: the gws CLI, the Python libraries and nsls-python launcher for the
document skills, a Node.js check (and on a PC, Git for Windows and Python). The
installers already provision exactly those, so they gained a mode that runs
those steps alone. /nsls-setmeup and the document skills' repair step run it
from the plugin's own folder, on a machine with no GitHub access.

What this pins:

1. Machine-only never runs git, never creates the toolkit folder, never
   touches Claude's settings, and never calls the claude CLI.
2. It still runs the three machine steps, survives every one of them failing
   (no network here), and exits 0.
3. The default path is byte-for-byte what it was: the only lines added sit
   outside every step, and the skipped block opens and closes where it says.
4. The Windows installer stops after its prerequisite report and before the
   clone, with a real exit code under -File.

The real install, on a fresh Mac and a fresh PC, is the install-check workflow.
"""

import collector_off  # noqa: F401  (first: no test may install the real collector)
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SH = REPO / "install.sh"
PS1 = REPO / "install.ps1"
WINDOWS = os.name == "nt"

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


sh = SH.read_text(encoding="utf-8")
ps1 = PS1.read_text(encoding="utf-8")

print("install.sh: where the mode opens and closes")
open_at = sh.index('if [ "$MACHINE_ONLY" != "1" ]; then\n\n# --- Prerequisites ---')
close_at = sh.index("fi   # end of the toolkit-itself steps (skipped by --machine-only)")
stop_at = sh.index('if [ "$MACHINE_ONLY" = "1" ]; then\n  echo ""\n  echo "==============================="')
check("the skipped block opens before the git check and the clone",
      open_at < sh.index("# --- Prerequisites ---") < sh.index("# --- Step 1: Install the org toolkit ---"))
check("and closes right before the gws step",
      close_at < sh.index("# --- Step 3.7: Install the gws CLI") and
      sh[close_at:sh.index("# --- Step 3.7: Install the gws CLI")].count("\n") <= 2)
check("every toolkit-itself step sits inside it",
      all(open_at < sh.index(marker) < close_at for marker in (
          "# --- Step 1: Install the org toolkit ---",
          "# --- Step 2: Enable the local plugin",
          "# --- Step 2.5: Fire an install event",
          "# --- Step 3: Install marketplace plugins ---",
          "# --- Step 3.5: Register bundled MCP servers")))
check("the three machine steps sit outside it, before the stop",
      all(close_at < sh.index(marker) < stop_at for marker in (
          "# --- Step 3.7: Install the gws CLI",
          "# --- Step 3.75: Python libraries for the document skills ---",
          "# --- Step 3.8: Node.js check")))
check("machine-only stops before pointers and the shell shortcut",
      stop_at < sh.index("# --- Step 4: Create slash-command pointer skills ---") < sh.index("# --- Step 5: Add 'cc' shortcut ---"))
check("with exit 0", "  exit 0\nfi\n\n# --- Step 4:" in sh)
check("the flag is parsed beside --test", "--machine-only) MACHINE_ONLY=1 ;;" in sh)
check("and defaults to off", "MACHINE_ONLY=0\nfor arg in" in sh)

if not WINDOWS:
    print("install.sh --machine-only, run for real with no network")

    # A git that says it was called; a curl that cannot download; a claude that says it was called.
    TATTLE = textwrap.dedent('''\
        #!/bin/sh
        echo "$(basename "$0") $*" >> "$TATTLE_LOG"
        exit 1
    ''')

    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        (home / ".claude").mkdir(parents=True)
        settings = home / ".claude" / "settings.json"
        settings.write_text(json.dumps({"hooks": {}, "mine": True}), encoding="utf-8")
        before = settings.read_bytes()
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        for name in ("git", "curl", "claude", "brew"):
            exe = bindir / name
            exe.write_text(TATTLE, encoding="utf-8")
            exe.chmod(0o755)
        log = Path(tmp) / "tattle.log"
        log.write_text("", encoding="utf-8")
        env = {
            "HOME": str(home), "PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "SHELL": "/bin/zsh",
            "TATTLE_LOG": str(log), "TMPDIR": tmp, "LANG": "C",
            # pip must fail fast instead of reaching the network.
            "PIP_INDEX_URL": "http://127.0.0.1:9/simple", "PIP_RETRIES": "0", "PIP_DEFAULT_TIMEOUT": "2",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1",
        }
        run = subprocess.run(["bash", str(SH), "--machine-only"], capture_output=True, text=True,
                             env=env, timeout=300, stdin=subprocess.DEVNULL)
        out = run.stdout + run.stderr
        called = [line for line in log.read_text(encoding="utf-8").splitlines() if line]
        check("it exits 0 even though every download failed", run.returncode == 0, f"rc={run.returncode}\n{out[-800:]}")
        check("git was never run", not [c for c in called if c.startswith("git ")], str(called))
        check("the claude CLI was never run", not [c for c in called if c.startswith("claude ")], str(called))
        check("the toolkit folder was not created", not (home / ".claude" / "local-plugins").exists())
        check("Claude's settings are byte-for-byte untouched", settings.read_bytes() == before)
        check("no pointer skills were written", not (home / ".claude" / "skills").exists())
        check("it did not say it was installing the toolkit",
              "Step 1: Installing org skills" not in out and "Cloning plugin" not in out
              and "NSLS Builder Toolkit installed!" not in out, out[-600:])
        check("the gws step ran", "Installing gws (Google Workspace CLI)..." in out)
        # A machine that already has gws on PATH (a developer's) skips the download.
        check("and either found gws or tried the download",
              "gws: already installed" in out or any(c.startswith("curl ") for c in called), str(called))
        check("the Python libraries step ran", "Installing Python libraries for the document skills..." in out)
        check("the Node.js check ran", "Node.js" in out)
        check("it ends by saying the computer is set up", "This computer is set up for the NSLS toolkit." in out)
        check("and nothing was written outside the throwaway home",
              all(str(p).startswith(str(home)) or str(p).startswith(tmp) for p in home.rglob("*")))

    print("install.sh with no flag still takes the full path")
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        # No git on this PATH at all: the full install must stop at its own git
        # check, which machine-only never reaches.
        keep = [d for d in os.environ["PATH"].split(os.pathsep)
                if d and not (Path(d) / "git").exists()]
        for tool in ("bash", "sh", "dirname", "basename", "mkdir", "cat", "sed", "awk", "uname", "env"):
            found = shutil.which(tool)
            if found:
                try:
                    (bindir / tool).symlink_to(found)
                except FileExistsError:
                    pass
        env = {"HOME": str(home), "PATH": os.pathsep.join([str(bindir)] + keep), "TMPDIR": tmp, "LANG": "C"}
        run = subprocess.run([str(bindir / "bash"), str(SH)], capture_output=True, text=True,
                             env=env, timeout=120, stdin=subprocess.DEVNULL)
        check("without git, the full install stops at its git check (as before)",
              run.returncode == 1 and "Error: git is not installed." in run.stdout, run.stdout[-300:] + run.stderr[-300:])
        run = subprocess.run([str(bindir / "bash"), str(SH), "--machine-only"], capture_output=True, text=True,
                             env={**env, "PIP_INDEX_URL": "http://127.0.0.1:9/simple", "PIP_RETRIES": "0",
                                  "PIP_DEFAULT_TIMEOUT": "2", "PIP_DISABLE_PIP_VERSION_CHECK": "1"},
                             timeout=300, stdin=subprocess.DEVNULL)
        check("machine-only on that same computer needs no git at all",
              run.returncode == 0 and "git is not installed" not in run.stdout, run.stdout[-300:] + run.stderr[-300:])

print("install.ps1: where the mode stops")
stop = ps1.index("if ($MachineOnly) {")
check("the switch is a parameter beside -Test", "param([switch]$Test, [switch]$MachineOnly)" in ps1)
check("it stops after the prerequisite report is built",
      ps1.index("# gws (verified last so the message can point back at the VC++ step)") < stop)
check("and before the clone", stop < ps1.index("# --- Step 1: Clone / update the org toolkit ---"))
check("with nothing between the stop and the clone but the clone's own header",
      ps1[stop:ps1.index("# --- Step 1: Clone / update the org toolkit ---")].count("git") == 0)
block = ps1[stop:ps1.index("# --- Step 1: Clone / update the org toolkit ---")]
check("it prints the prerequisite report", "$PrereqReport | ForEach-Object { Write-Host $_ }" in block)
check("it hands back a real exit code under -File and never closes a pasted window",
      "if ($RunningFromFile) { exit 0 } else { return }" in block)
check("Git for Windows and Step 0 still come first, so machine-only runs them",
      ps1.index("# --- Prerequisites ---") < ps1.index("# --- Step 0: Provision runtime prerequisites") < stop)
check("install.ps1 is ASCII-only", all(ord(c) < 128 for c in ps1))

print()
if failures:
    print(f"FAILED: {len(failures)}")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print("all checks passed")
