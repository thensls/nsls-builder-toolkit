#!/usr/bin/env python3
"""Syntax-check every inline <script> in a mock-up with node --check.

  python3 check_js.py page.html

Why: an unescaped apostrophe inside a JS string ("Society's") silently kills the
whole flow. The page still renders, but no button does anything. Run this after every copy edit.
"""
import os, re, subprocess, sys, tempfile

src = open(sys.argv[1], encoding="utf-8").read()
blocks = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", src, re.S)
blocks = [b for b in blocks if b.strip()]
if not blocks:
    sys.exit("no inline scripts found")
fd, tmp = tempfile.mkstemp(suffix=".js")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write("\n;\n".join(blocks))
r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
os.remove(tmp)
if r.returncode:
    print(r.stderr.strip())
    sys.exit(1)
print("scripts OK (%d block%s)" % (len(blocks), "" if len(blocks) == 1 else "s"))
