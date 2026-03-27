#!/bin/bash
set -euo pipefail

PLUGIN_DIR="$HOME/.claude/local-plugins/nsls-builder-toolkit"
REPO_URL="https://github.com/thensls/nsls-builder-toolkit.git"

echo "Installing NSLS Builder Toolkit..."

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

mkdir -p "$HOME/.claude/local-plugins"

if [ -d "$PLUGIN_DIR" ]; then
  echo "Updating existing installation..."
  cd "$PLUGIN_DIR"
  git reset --hard origin/main --quiet 2>/dev/null
  git pull origin main --quiet
else
  echo "Cloning plugin..."
  git clone "$REPO_URL" "$PLUGIN_DIR" --quiet
fi

## Enable plugin in settings.json if not already enabled
SETTINGS="$HOME/.claude/settings.json"
PLUGIN_KEY="nsls-builder-toolkit@local"

if [ -f "$SETTINGS" ]; then
  if grep -q "$PLUGIN_KEY" "$SETTINGS" 2>/dev/null; then
    echo "  Plugin already enabled in settings.json"
  else
    python3 -c "
import json
with open('$SETTINGS') as f: cfg = json.load(f)
cfg.setdefault('enabledPlugins', {})['$PLUGIN_KEY'] = True
with open('$SETTINGS', 'w') as f: json.dump(cfg, f, indent=2)
    " && echo "  Plugin enabled in settings.json" \
      || echo "  Note: Manually add '\"$PLUGIN_KEY\": true' to enabledPlugins in ~/.claude/settings.json"
  fi
else
  echo "  Note: No settings.json found — plugin will be enabled on first use"
fi

## Create slash-command pointer skills in ~/.claude/skills/
## Local plugins don't surface commands in autocomplete — pointer skills fix this.
## Each pointer tells Claude to read the full skill from the plugin directory.
echo "  Creating slash-command pointers..."
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"

for skill_dir in "$PLUGIN_DIR/skills"/*/; do
  skill=$(basename "$skill_dir")
  dest="$SKILLS_DIR/$skill"

  # Skip if user already has a custom skill with this name
  if [ -d "$dest" ] && ! grep -q "local-plugins/nsls-builder-toolkit" "$dest/SKILL.md" 2>/dev/null; then
    continue
  fi

  # Extract name and description from plugin SKILL.md frontmatter
  src="$skill_dir/SKILL.md"
  [ -f "$src" ] || continue

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
done

echo "  $(ls "$PLUGIN_DIR/skills/" | wc -l | tr -d ' ') slash commands created"

echo ""
echo "NSLS Builder Toolkit installed!"
echo ""
echo "Skills included:"
ls "$PLUGIN_DIR/skills/" | sed 's/^/  \//'
echo ""
echo "Start a new Claude Code session to use the skills."
echo "Type /<skill-name> to use any skill (e.g., /log, /close-day, /nsls-slides)."
echo ""
echo "The toolkit auto-updates at the start of each session."
echo "Do not edit files in $PLUGIN_DIR — changes are managed via GitHub."
