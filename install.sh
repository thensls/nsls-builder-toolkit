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

echo ""
echo "NSLS Builder Toolkit installed!"
echo ""
echo "Skills included:"
ls "$PLUGIN_DIR/skills/" | sed 's/^/  - /'
echo ""
echo "Start a new Claude Code session to use the skills."
echo "The toolkit auto-updates at the start of each session."
echo ""
echo "Do not edit files in $PLUGIN_DIR — changes are managed via GitHub."
