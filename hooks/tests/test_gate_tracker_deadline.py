#!/usr/bin/env python3
# windows-ci: python | The gate's tracker lookup outlasts a slow tracker and still fits the hook
"""The gate's tracker lookup must wait out a slow tracker and still fit the hook.

Plain stdlib, no pytest: run with `python3 hooks/tests/test_gate_tracker_deadline.py`.

Gates 2 and 4 look a repo up with GET /automations. A reply that misses the
limit is "unknown", and both gates then allow the command: the check is skipped
and nothing says so.

The limit was urllib's 3s timeout, which bounds each socket operation, not the
lookup. So the check was skipped whenever the tracker itself took over 3s to
answer, and a reply that kept trickling bytes was read for as long as it
trickled, past the hook's own 10s, where the harness kills the hook
mid-decision. Timed live on 2026-10-24 (181 rows, two Airtable pages), the
tracker took up to 3.2s to answer and whole calls up to 5.9s; every further
100 registrations adds a page, about 0.5s.

The lookup now gets whatever is left of an 8s budget counted from when the gate
starts, on the clock.

A local server stands in for the tracker; each case says how slowly it answers.
"""

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
failures = []

# Never route the local stand-in through a system proxy.
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"

BODY = json.dumps({"success": True, "count": 1, "records": [
    {"name": "my-service", "scope": "Company-wide", "reviewer": ["recREVIEWER"]}]}).encode()

# How the stand-in answers the next request: ("delay", seconds) sends the whole
# reply after a pause; ("trickle", seconds) sends the headers at once, then the
# body one byte at a time for that long, so no single read ever waits.
behaviour = {"mode": ("delay", 0.0)}
requests_seen = []


class Tracker(BaseHTTPRequestHandler):
    def do_GET(self):
        requests_seen.append(self.path)
        kind, seconds = behaviour["mode"]
        try:
            if kind == "delay":
                time.sleep(seconds)
                self._headers(len(BODY))
                self.wfile.write(BODY)
            else:
                pad = b" " * int(seconds / 0.1)
                self._headers(len(pad) + len(BODY))
                for ch in pad:
                    self.wfile.write(bytes([ch]))
                    self.wfile.flush()
                    time.sleep(0.1)
                self.wfile.write(BODY)
        except Exception:
            pass  # the gate gave up and hung up, which is the point of some cases

    def _headers(self, length):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(length))
        self.end_headers()

    def log_message(self, *a):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), Tracker)
server.daemon_threads = True
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{server.server_address[1]}"


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def load_gate():
    """A fresh gate with an empty cache, pointed at the stand-in."""
    os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
    os.environ["NSLS_TRACKER_URL"] = URL
    spec = importlib.util.spec_from_file_location(
        f"gate_{time.monotonic_ns()}", HOOKS / "guardrail-gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def timed_lookup(gate, mode):
    behaviour["mode"] = mode
    started = time.monotonic()
    status = gate.tracker_lookup("my-service")[0]
    return status, time.monotonic() - started


print("a slow tracker is waited for, not skipped")
gate = load_gate()
status, took = timed_lookup(gate, ("delay", 0.0))
check("control: a prompt reply is found", status == "found", f"got {status}")

gate = load_gate()
status, took = timed_lookup(gate, ("delay", 4.0))
check("a reply 4s late is still read (it was skipped at 3s)",
      status == "found", f"got {status} after {took:.1f}s")

def budget_left(gate, seconds):
    """Pretend the gate has already spent all but `seconds` of its budget."""
    deadline = getattr(gate, "LOOKUP_DEADLINE", 8)
    gate._STARTED = time.monotonic() - (deadline - seconds)


print("\nthe limit covers the whole lookup, not each read")
gate = load_gate()
budget_left(gate, 1.5)
status, took = timed_lookup(gate, ("trickle", 5.0))
check("a reply still trickling at the limit is abandoned", status == "unknown",
      f"got {status}")
check("... at the limit, not when the trickle ends", took < 2.5, f"took {took:.1f}s")

print("\ntime already spent comes out of the tracker's allowance")
gate = load_gate()
budget_left(gate, 1.0)
status, took = timed_lookup(gate, ("delay", 2.5))
check("a gate that started late waits only for what is left",
      status == "unknown" and took < 2.0, f"got {status} after {took:.1f}s")

gate = load_gate()
budget_left(gate, -1.0)
before = len(requests_seen)
status, took = timed_lookup(gate, ("delay", 0.0))
check("a gate with no budget left does not call the tracker at all",
      status == "unknown" and len(requests_seen) == before,
      f"got {status}, {len(requests_seen) - before} request(s)")

print("\nthe arithmetic fits the hook's own timeout")
gate = load_gate()
hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))
hook_timeout = next(
    h.get("timeout") for entries in hooks["hooks"].values() for m in entries
    for h in m["hooks"] if h.get("command", "").rstrip().endswith(" gate"))
deadline = getattr(gate, "LOOKUP_DEADLINE", None)
check("the lookup ends 2s before the harness would kill the hook",
      deadline is not None and deadline + 2 <= hook_timeout,
      f"deadline {deadline}, hook {hook_timeout}")
# The slowest whole call timed live was 5.9s.
check("after a git lookup at its full timeout, the tracker still gets 6s",
      deadline is not None and deadline - gate.GIT_TIMEOUT >= 6,
      f"deadline {deadline}, git {gate.GIT_TIMEOUT}")

server.shutdown()
print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'all passed'}")
sys.exit(1 if failures else 0)
