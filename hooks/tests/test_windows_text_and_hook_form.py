#!/usr/bin/env python3
"""Two small Windows findings from the PC test of 2026-09-30.

Plain stdlib: `python3 hooks/tests/test_windows_text_and_hook_form.py`.

1. Hooks read git and claude CLI output with text=True and no encoding, which
   decodes in the platform's locale: cp1252 on a PC. Both tools write UTF-8, so
   the CLI's "Adding marketplace..." ellipsis and check mark came back as
   mojibake in the stuck-status detail, and a UTF-8 byte cp1252 does not define
   (0x81, 0x8D, 0x8F, 0x90, 0x9D) would raise instead, failing the call.
2. In the desktop app on that PC, a plugin hook whose command STARTS with a
   quoted "${CLAUDE_PLUGIN_ROOT}/..." ran with the variable unexpanded
   (superpowers' SessionStart, exit 127, every session). Ours start with a bare
   `bash` and ran fine. This pins that form so a later edit cannot lose it.
"""
import ast
import json
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
failures = []


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name} {'' if cond else detail}")
    if not cond:
        failures.append(name)


print("why the locale default is wrong on a PC")
cli = "Adding marketplace… √ Successfully installed".encode("utf-8")
check("cp1252 turns the CLI's UTF-8 into mojibake",
      cli.decode("cp1252", errors="replace") != cli.decode("utf-8"))
try:
    "с".encode("utf-8").decode("cp1252")   # Cyrillic s = D1 81
    raised = False
except UnicodeDecodeError:
    raised = True
check("and some UTF-8 cannot be decoded by cp1252 at all", raised)

print("\nevery text-mode subprocess call in the hooks names its encoding")
missing = []
for path in sorted(HOOKS.glob("*.py")):
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    for node in ast.walk(ast.parse(src)):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if name not in ("run", "Popen", "check_output"):
            continue
        kw = {k.arg: k.value for k in node.keywords}
        if "text" not in kw:
            continue
        enc = kw.get("encoding"); err = kw.get("errors")
        if not (isinstance(enc, ast.Constant) and enc.value == "utf-8"
                and isinstance(err, ast.Constant) and err.value == "replace"):
            missing.append(f"{path.name}:{node.lineno}")
check("every text-mode read is utf-8 with replacement", not missing, f"({missing})")
src_ss = (HOOKS / "session-start.py").read_text(encoding="utf-8")
check("the Python child is told to write UTF-8 too", '"PYTHONIOENCODING": "utf-8"' in src_ss)

print("\nplugin hook commands start with a bare bash")
hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
cmds = [h["command"] for groups in hooks.values() for g in groups for h in g["hooks"]]
check("there are hook commands to check", len(cmds) >= 3, f"({len(cmds)})")
for c in cmds:
    check(f"starts with `bash `, never a quoted variable: {c[:60]}",
          c.startswith("bash ") and not c.lstrip().startswith(('"$', "'$", "${", "$")))

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    sys.exit(1)
print("all checks passed")
