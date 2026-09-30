"""How the Windows hook reaches session-start.py's __guardrails__ block.

A file, not `python -c "<program>"`. Windows PowerShell 5.1, which is what runs
session-start.ps1 on every PC, does not escape double quotes inside an argument
it passes to a native program. The inline program arrived as
`run_name=__guardrails__`, a NameError, so the hook's whole Python step (the
guardrails context, plugin stage A, the freshness check) died on every PC from
the day it was added, and 2>$null hid it. PowerShell 7.3+ escapes the quotes,
which is why it never showed up there. A file path has no quotes to lose.

Usage: python guardrails_entry.py <path to session-start.py>
"""
import runpy
import sys

runpy.run_path(sys.argv[1], run_name="__guardrails__")
