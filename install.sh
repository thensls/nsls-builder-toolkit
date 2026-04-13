#!/bin/bash
# NSLS Builder Toolkit — one-command installer
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.sh | bash
#
# What this does:
#   1. Installs the NSLS org skills (local plugin)
#   2. Installs superpowers + compound-engineering plugins (marketplace)
#   3. Tells you to run /setup to connect your tools

set -euo pipefail

PLUGIN_DIR="$HOME/.claude/local-plugins/nsls-builder-toolkit"
REPO_URL="https://github.com/thensls/nsls-builder-toolkit.git"

echo ""
echo "=== NSLS Builder Toolkit ==="
echo ""

# --- Prerequisites ---

if ! command -v git &>/dev/null; then
  echo "Error: git is not installed."
  echo "  macOS: Run 'xcode-select --install' first."
  exit 1
fi

if [ ! -d "$HOME/.claude" ]; then
  echo "Error: Claude Code doesn't appear to be set up (~/.claude/ not found)."
  echo "  Install Claude Code first, then re-run this script."
  exit 1
fi

# --- Step 1: Install the org toolkit ---

echo "Step 1: Installing org skills..."
mkdir -p "$HOME/.claude/local-plugins"

if [ -d "$PLUGIN_DIR" ]; then
  echo "  Updating existing installation..."
  git -C "$PLUGIN_DIR" fetch origin main --quiet 2>/dev/null
  git -C "$PLUGIN_DIR" reset --hard origin/main --quiet 2>/dev/null
else
  echo "  Cloning plugin..."
  git clone "$REPO_URL" "$PLUGIN_DIR" --quiet
fi
echo "  Done."

# --- Step 2: Enable the local plugin and register the auto-update hook in settings.json ---

SETTINGS="$HOME/.claude/settings.json"
HOOK_CMD='python3 -c "exec(open(__import__('"'"'pathlib'"'"').Path.home() / '"'"'.claude/local-plugins/nsls-builder-toolkit/hooks/session-start.py'"'"').read())"'

if [ -f "$SETTINGS" ]; then
  python3 -c "
import json, sys

HOOK_CMD = 'python3 -c \"exec(open(__import__(\'pathlib\').Path.home() / \'.claude/local-plugins/nsls-builder-toolkit/hooks/session-start.py\').read())\"'
HOOK_ENTRY = {
    'type': 'command',
    'command': HOOK_CMD,
    'timeout': 15,
    'statusMessage': 'Syncing builder toolkit...'
}
MARKER = 'nsls-builder-toolkit/hooks/session-start.py'

with open('$SETTINGS') as f: cfg = json.load(f)

# Enable plugin
ep = cfg.setdefault('enabledPlugins', {})
if not ep.get('nsls-builder-toolkit@local'):
    ep['nsls-builder-toolkit@local'] = True
    print('  Enabled nsls-builder-toolkit in settings.json')
else:
    print('  Plugin already enabled')

# Register auto-update hook (idempotent)
hooks = cfg.setdefault('hooks', {})
session_start = hooks.setdefault('SessionStart', [])

# Find or create the startup matcher entry
startup_entry = None
for entry in session_start:
    if entry.get('matcher', '').startswith('startup'):
        startup_entry = entry
        break
if startup_entry is None:
    startup_entry = {'matcher': 'startup', 'hooks': []}
    session_start.insert(0, startup_entry)

hook_list = startup_entry.setdefault('hooks', [])
already = any(MARKER in h.get('command', '') for h in hook_list)
if not already:
    hook_list.insert(0, HOOK_ENTRY)
    print('  Registered session auto-update hook')
else:
    print('  Auto-update hook already registered')

with open('$SETTINGS', 'w') as f: json.dump(cfg, f, indent=2)
" 2>/dev/null || echo "  Note: Could not update settings.json — add the hook manually"
else
  echo "  Note: No settings.json found — the plugin will be enabled on first use"
fi

# --- Step 3: Install marketplace plugins ---

echo ""
echo "Step 2: Installing recommended plugins..."

# Find the claude CLI — curl|bash may not inherit the full PATH
CLAUDE_BIN=""
for candidate in \
  "$(command -v claude 2>/dev/null)" \
  "$HOME/.local/bin/claude" \
  "/usr/local/bin/claude" \
  "$HOME/.claude/bin/claude"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    CLAUDE_BIN="$candidate"
    break
  fi
done

if [ -n "$CLAUDE_BIN" ]; then
  # Superpowers (official marketplace — planning, debugging, verification workflows)
  if "$CLAUDE_BIN" plugins list 2>/dev/null | grep -q "superpowers"; then
    echo "  superpowers: already installed"
  else
    echo "  Installing superpowers..."
    "$CLAUDE_BIN" plugins install superpowers 2>&1 | tail -1 || true
  fi

  # Compound Engineering is available as an optional power-up.
  # Install manually if you want advanced planning/review workflows:
  #   claude plugins marketplace add https://github.com/EveryInc/compound-engineering-plugin.git
  #   claude plugins install compound-engineering@every-marketplace
else
  echo ""
  echo "  Could not find the 'claude' CLI."
  echo "  After your next Claude Code session, run /setup — it will detect"
  echo "  missing plugins and give you the install commands."
  echo ""
  echo "  Or run these manually:"
  echo "    claude plugins install superpowers"
  echo "    claude plugins marketplace add https://github.com/EveryInc/compound-engineering-plugin.git"
  echo "    claude plugins install compound-engineering@every-marketplace"
fi

# --- Step 4: Create slash-command pointer skills ---

echo ""
echo "Step 3: Creating slash-command pointers..."
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"

count=0
for skill_dir in "$PLUGIN_DIR/skills"/*/; do
  skill=$(basename "$skill_dir")
  dest="$SKILLS_DIR/$skill"
  src="$skill_dir/SKILL.md"
  [ -f "$src" ] || continue

  # Skip if user already has a custom (non-pointer) skill with this name
  if [ -d "$dest" ] && [ -f "$dest/SKILL.md" ]; then
    grep -q "local-plugins/nsls-builder-toolkit" "$dest/SKILL.md" 2>/dev/null || continue
  fi

  # Extract name from frontmatter
  name=$(grep "^name:" "$src" | head -1 | sed 's/name: *//')
  [ -z "$name" ] && continue

  # Extract description (handles >- multiline format)
  desc=$(python3 -c "
import re, sys
with open('$src') as f: content = f.read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if not fm: sys.exit(0)
m = re.search(r'description:\s*>-?\s*\n((?:\s+.+\n)*)', fm.group(1))
if m: print(' '.join(l.strip() for l in m.group(1).strip().split('\n')))
else:
    m = re.search(r'description:\s*(.+)', fm.group(1), re.MULTILINE)
    if m: print(m.group(1).strip())
" 2>/dev/null)
  [ -z "$desc" ] && desc="NSLS Builder Toolkit skill: $skill"

  mkdir -p "$dest"
  cat > "$dest/SKILL.md" << POINTER
---
name: $name
description: >-
  $desc
---

Read and follow the full skill at \`~/.claude/local-plugins/nsls-builder-toolkit/skills/$skill/SKILL.md\`.
POINTER
  count=$((count + 1))
done

echo "  $count skill pointers synced"

# --- Done ---

echo ""
echo "==============================="
echo "  NSLS Builder Toolkit installed!"
echo "==============================="
echo ""
echo "What you got:"
echo ""
echo "  ORG SKILLS (13 skills for building, tracking, deploying):"
ls "$PLUGIN_DIR/skills/" | sed 's/^/    \//'
echo ""
echo "  PLUGINS:"
echo "    superpowers      — planning, debugging, verification workflows"
echo ""
echo "  OPTIONAL POWER-UPS:"
echo "    compound-engineering — advanced planning/review workflows"
echo "    Install: claude plugins marketplace add https://github.com/EveryInc/compound-engineering-plugin.git"
echo "             claude plugins install compound-engineering@every-marketplace"
echo ""
echo "=== NEXT STEP ==="
echo ""
echo "  1. Start a new Claude Code session (or restart if one is open)"
echo "     Skills won't appear until the session loads the new plugins."
echo ""
echo "  2. Say:  /setup"
echo "     This connects your tools (Slack, Asana, etc.) and optionally"
echo "     installs personal productivity skills (daily planning, weekly"
echo "     reviews, project logging — yours to customize)."
echo ""
