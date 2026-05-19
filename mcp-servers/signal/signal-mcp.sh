#!/bin/sh
# Wrapper that reads the Signal API token from the user's config file and
# launches the bundled MCP server. Builders set this up once via /signal-setup
# instead of editing ~/.zshrc or ~/.claude.json.
#
# Token file: $XDG_CONFIG_HOME/nsls/signal-token (default ~/.config/nsls/signal-token)
# Permissions: should be mode 600.

set -e

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/nsls"
TOKEN_FILE="$CONFIG_DIR/signal-token"

if [ ! -f "$TOKEN_FILE" ]; then
  echo "signal-mcp: token not found at $TOKEN_FILE" >&2
  echo "  Run /signal-setup in Claude Code to configure it." >&2
  exit 1
fi

TOKEN=$(tr -d '[:space:]' < "$TOKEN_FILE")
if [ -z "$TOKEN" ]; then
  echo "signal-mcp: token file at $TOKEN_FILE is empty" >&2
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
exec env SIGNAL_API_TOKEN="$TOKEN" node "$SCRIPT_DIR/signal-mcp.js"
