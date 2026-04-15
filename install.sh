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
  "$HOME/.claude/bin/claude" \
  "/usr/local/bin/claude" \
  "/opt/homebrew/bin/claude" \
  "$HOME/.npm-global/bin/claude" \
  "$HOME/.nvm/versions/node/*/bin/claude"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    CLAUDE_BIN="$candidate"
    break
  fi
done

# Retry with PATH refresh if not found (native installer may need a moment)
if [ -z "$CLAUDE_BIN" ]; then
  eval "$(cat ~/.zshrc 2>/dev/null | grep -E 'export PATH|path=')" 2>/dev/null || true
  eval "$(cat ~/.bashrc 2>/dev/null | grep -E 'export PATH|path=')" 2>/dev/null || true
  CLAUDE_BIN="$(command -v claude 2>/dev/null)"
fi

install_plugin() {
  local name="$1"
  local install_cmd="$2"
  local marketplace_url="$3"

  if "$CLAUDE_BIN" plugin list 2>/dev/null | grep -q "$name"; then
    echo "  $name: already installed"
  else
    if [ -n "$marketplace_url" ]; then
      echo "  Adding $name marketplace..."
      "$CLAUDE_BIN" plugin marketplace add "$marketplace_url" 2>&1 | tail -1 || true
    fi
    echo "  Installing $name..."
    "$CLAUDE_BIN" plugin install "$install_cmd" 2>&1 | tail -1 || true
  fi
}

if [ -n "$CLAUDE_BIN" ]; then
  install_plugin "superpowers" "superpowers" ""
  install_plugin "compound-engineering" "compound-engineering@every-marketplace" \
    "https://github.com/EveryInc/compound-engineering-plugin.git"
else
  echo ""
  echo "  Could not find the 'claude' CLI in PATH."
  echo "  After your next Claude Code session, run /setup — it will detect"
  echo "  missing plugins and give you the install commands."
  echo ""
  echo "  Or run these manually:"
  echo "    claude plugin install superpowers"
  echo "    claude plugin marketplace add https://github.com/EveryInc/compound-engineering-plugin.git"
  echo "    claude plugin install compound-engineering@every-marketplace"
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

# --- Step 5: Add 'cc' shortcut ---

echo ""
echo "Step 4: Adding 'cc' shortcut..."

# Detect shell config file
SHELL_RC=""
if [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
  SHELL_RC="$HOME/.bash_profile"
fi

if [ -n "$SHELL_RC" ]; then
  if grep -q "alias cc=" "$SHELL_RC" 2>/dev/null; then
    echo "  cc shortcut: already configured"
  else
    echo "" >> "$SHELL_RC"
    echo "# Claude Code shortcut" >> "$SHELL_RC"
    echo "alias cc='claude'" >> "$SHELL_RC"
    echo "  Added 'cc' shortcut to $(basename "$SHELL_RC") — type cc to launch Claude Code"
    echo "  (takes effect in new terminal windows, or run: source $SHELL_RC)"
  fi
else
  echo "  Could not find shell config (.zshrc, .bashrc, .bash_profile)"
  echo "  Add this manually: alias cc='claude'"
fi

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
echo "    superpowers              — planning, debugging, verification workflows"
echo "    compound-engineering     — brainstorm, plan, build, review pipeline"
echo ""
echo "  SHORTCUT:"
echo "    cc                       — type 'cc' in any terminal to launch Claude Code"
echo ""
echo "=== NEXT STEP ==="
echo ""
echo "  1. Open a new terminal window (so the 'cc' shortcut loads)"
echo ""
echo "  2. Type:  cc"
echo ""
echo "  3. Say:  /setup"
echo "     This connects your tools (Slack, Asana, etc.) and optionally"
echo "     installs personal productivity skills (daily planning, weekly"
echo "     reviews, project logging — yours to customize)."
echo ""
