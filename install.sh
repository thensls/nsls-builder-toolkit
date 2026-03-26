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
