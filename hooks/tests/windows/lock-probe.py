#!/usr/bin/env python3
"""Probe the session hook's fork-check lock from a real Windows Python.

Driven by lock-smoke.ps1; also fine by hand:
    python lock-probe.py <session-start.py> <lock-file> try|hold|probe
  try    claim once, print "held" or "refused" (and, when held, the file's size
         after the claim), release, exit.
  hold   claim, print "held" (then "second-refused" when a second claim through
         another descriptor in this same process is refused), keep the lock
         until a line arrives on stdin, then release.
  probe  do NOT claim through the hook; instead report each step the hook's
         claim would take (open, lock, size, mtime age) as one JSON line, so a
         failing check says which step behaved unexpectedly on this machine.
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

hook_path, lock, mode = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
spec = importlib.util.spec_from_file_location("session_start_hook", hook_path)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

if mode == "probe":
    info = {"python": sys.version.split()[0], "utime_takes_fd": os.utime in os.supports_fd}
    fd = None
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o644)
        info["open"] = "ok"
    except OSError as e:
        info["open"] = f"err errno={e.errno} winerror={getattr(e, 'winerror', None)} {e.strerror}"
    if fd is not None:
        try:
            hook._lock_exclusive(fd)
            info["lock"] = "ok"
        except OSError as e:
            info["lock"] = f"err errno={e.errno} winerror={getattr(e, 'winerror', None)} {e.strerror}"
        st = os.fstat(fd)
        now = time.time()
        info.update(size=st.st_size, mtime=st.st_mtime, now=now, age=round(now - st.st_mtime, 3))
        os.close(fd)
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
    print(f"size={os.fstat(fd).st_size}", flush=True)
    hook._release_lock(fd)
