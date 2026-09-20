#!/usr/bin/env python3
"""Probe the session hook's fork-check lock from a real Windows Python.

Driven by lock-smoke.ps1; also fine by hand:
    python lock-probe.py <session-start.py> <lock-file> try|hold|probe [<old-lock-file>]
  try    claim once, print "held" or "refused", release, exit.
  hold   claim, print "held" (then "second-refused" when a second claim through
         another descriptor in this same process is refused), keep the lock
         until a line arrives on stdin, then release.
  probe  do NOT claim through the hook; instead report each step the hook's
         claim would take (open, lock, size and mtime age of the lock file, and
         of the old protocol's file) as one JSON line, so a failing check names
         the step that behaved unexpectedly on this machine.
The optional fourth argument is where the previous protocol's token file lives
for this run; the hook reads that path and never writes it.
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

hook_path, lock, mode = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
legacy = Path(sys.argv[4]) if len(sys.argv) > 4 else None
spec = importlib.util.spec_from_file_location("session_start_hook", hook_path)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)
if legacy is not None:
    hook.PERSONAL_UPSTREAM_LEGACY_LOCK = legacy

if mode == "probe":
    info = {"python": sys.version.split()[0]}
    fd = None
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o644)
        info["open"] = "ok"
    except OSError as e:
        info["open"] = f"err errno={e.errno} winerror={getattr(e, 'winerror', None)} {e.strerror}"
    now = time.time()
    if fd is not None:
        try:
            hook._lock_exclusive(fd)
            info["lock"] = "ok"
        except OSError as e:
            info["lock"] = f"err errno={e.errno} winerror={getattr(e, 'winerror', None)} {e.strerror}"
        st = os.fstat(fd)
        info.update(size=st.st_size, age=round(now - st.st_mtime, 3))
        os.close(fd)
    if legacy is not None and legacy.exists():
        ls = legacy.stat()
        info.update(old_size=ls.st_size, old_age=round(now - ls.st_mtime, 3))
    print(json.dumps(info), flush=True)
    sys.exit(0)

fd = hook._claim_lock(lock)
print("held" if fd is not None else "refused", flush=True)
if fd is not None and mode == "hold":
    again = hook._claim_lock(lock)
    if again is None:
        print("second-refused", flush=True)
    else:
        print("second-held", flush=True)
        hook._release_lock(again)
    sys.stdin.readline()
if fd is not None:
    hook._release_lock(fd)
