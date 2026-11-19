"""No test sees the claude CLI that runs the developer's own session.

session-start.py's _find_claude tries the CLI running the session first, found
from CLAUDE_PID. A test run from inside Claude Code inherits that variable, so
the developer's real CLI won over every fake CLI a test set up: eight test
files failed that way, and only when run from a Claude session, never in CI.
Importing this takes the variable out of this process and every child it
starts. test_running_claude.py sets it on purpose, per check.
"""

import os

os.environ.pop("CLAUDE_PID", None)
