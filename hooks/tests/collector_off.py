"""No test may install the real NSLS usage collector. Import this first.

Session start (session-start.py main(), run-hook.sh session-start/update, and
session-start.ps1 on a PC) ends by installing the collector when it is
missing: it downloads the real installer from signal.nsls.org and runs it. The
collector's schedule is one per account (launchd's org.nsls.collector, the
"NSLS Collector" task), so an install from a test's scratch HOME re-points the
developer's real schedule at the scratch folder, and every run fails once the
folder is deleted. On 2026-10-24 that had silently stopped a developer's
collector for six days.

Importing this module opts every part of the test out, in one place:

  * os.environ gets NSLS_COLLECTOR_OPTOUT=1, so session start loaded in this
    process, and every child that inherits the environment, stands down;
  * every child started with an explicit env= gets it added too, so a test that
    builds a child's environment from scratch cannot drop it by accident.

test_no_test_installs_collector.py fails any test file that runs session start
or the bootstrap without importing this. (collector_bootstrap.py also refuses
to install from a home that is not the account's own; this is the first line,
that is the second.)
"""

import os
import subprocess

OPTOUT = "NSLS_COLLECTOR_OPTOUT"

os.environ[OPTOUT] = "1"

_popen_init = subprocess.Popen.__init__


def _init_without_collector(self, *args, **kwargs):
    env = kwargs.get("env")
    if env is not None and env.get(OPTOUT) != "1":
        kwargs["env"] = {**env, OPTOUT: "1"}
    _popen_init(self, *args, **kwargs)


if getattr(subprocess.Popen.__init__, "__name__", "") != _init_without_collector.__name__:
    subprocess.Popen.__init__ = _init_without_collector
