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

# --- Step 2: Enable the local plugin in settings.json ---

SETTINGS="$HOME/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  python3 -c "
import json
with open('$SETTINGS') as f: cfg = json.load(f)
ep = cfg.setdefault('enabledPlugins', {})
if 'nsls-builder-toolkit@local' not in ep or not ep['nsls-builder-toolkit@local']:
    ep['nsls-builder-toolkit@local'] = True
    with open('$SETTINGS', 'w') as f: json.dump(cfg, f, indent=2)
    print('  Enabled nsls-builder-toolkit in settings.json')
else:
    print('  Already enabled in settings.json')
" 2>/dev/null || echo "  Note: Could not update settings.json — enable the plugin manually in Claude Code"
else
  echo "  Note: No settings.json found — the plugin will be enabled on first use"
fi

# --- Step 3: Install marketplace plugins ---

echo ""
echo "Step 2: Installing recommended plugins..."

# Find the claude CLI — it may not be in PATH for curl|bash
CLAUDE_BIN=""
if command -v claude &>/dev/null; then
  CLAUDE_BIN="claude"
elif [ -x "/usr/local/bin/claude" ]; then
  CLAUDE_BIN="/usr/local/bin/claude"
elif [ -x "$HOME/.claude/bin/claude" ]; then
  CLAUDE_BIN="$HOME/.claude/bin/claude"
fi

if [ -n "$CLAUDE_BIN" ]; then
  # Superpowers (official marketplace — planning, debugging, verification workflows)
  if "$CLAUDE_BIN" plugins list 2>/dev/null | grep -q "superpowers"; then
    echo "  superpowers: already installed"
  else
    echo "  Installing superpowers..."
    "$CLAUDE_BIN" plugins install superpowers 2>&1 | tail -1 || true
  fi

  # Compound Engineering (Every marketplace — brainstorm, plan, review, git workflows)
  if "$CLAUDE_BIN" plugins list 2>/dev/null | grep -q "compound-engineering"; then
    echo "  compound-engineering: already installed"
  else
    echo "  Adding Every marketplace..."
    "$CLAUDE_BIN" plugins marketplace add https://github.com/EveryInc/compound-engineering-plugin.git 2>&1 | tail -1 || true
    echo "  Installing compound-engineering..."
    "$CLAUDE_BIN" plugins install compound-engineering@every-marketplace 2>&1 | tail -1 || true
  fi
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
echo "    compound-eng.    — brainstorm, plan, review, git workflows"
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
