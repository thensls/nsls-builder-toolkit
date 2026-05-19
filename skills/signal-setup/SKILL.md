---
name: signal-setup
description: >-
  Configure the Signal MCP server so Claude Code can query Quick Notes,
  wins, friction signals, and team summaries for any team you're allowed
  to see. Use when the user says "set up Signal", "signal mcp", "signal
  setup", "/signal-setup", asks why `signal_*` tools aren't available,
  or wants to rotate their Signal API token. For managers and execs only —
  builders without direct reports will hit 403 on every endpoint.
---

# /signal-setup — Connect Claude Code to Signal

## What this does

Signal (the people-ops bot powering Quick Notes, wins, and friction signals) exposes a read-only HTTP API at `https://employee-profiles-production.up.railway.app/api/mcp/*`. This skill writes your personal bearer token to `~/.config/nsls/signal-token` so the bundled MCP server can authenticate. Scope follows the token — execs see org-wide on cross-team endpoints, managers see their reporting subtree.

After setup you'll have six new tools in Claude Code: `signal_team_summary`, `signal_wins`, `signal_friction`, `signal_person`, `signal_person_history`, `signal_person_goals`.

## Who can use this

- **Executives** (people.app_role = 'executive'): org-wide on `wins`, `friction`, `person/*`. `team_summary` returns your own direct reports unless you pass `manager_slug`.
- **Managers** (anyone with direct reports): your reporting subtree.
- **Everyone else**: every endpoint will 403. Don't bother setting this up.

If you're not sure, run setup anyway — the first tool call will tell you.

## Setup flow

When the user invokes /signal-setup:

### Step 1 — Check existing state

```sh
test -f ~/.config/nsls/signal-token && echo "token exists" || echo "no token"
```

If a token exists, ask whether to rotate or just verify the existing one.

### Step 2 — Mint the token

Tell the user to:

1. Open `https://employee-profiles-production.up.railway.app/team` in a browser. Sign in with their NSLS Google account.
2. Click **"Generate MCP token"** at the top of the page.
3. Copy the token (starts with `signal_` followed by 64 hex chars). It's shown once; if they dismiss the popup they need to regenerate.

Then prompt them to paste it into Claude Code.

### Step 3 — Write the token file

Use Bash to write the token with strict permissions. The token file lives at `~/.config/nsls/signal-token`:

```sh
mkdir -p ~/.config/nsls
umask 077  # so the file is created mode 600
printf '%s' '<TOKEN>' > ~/.config/nsls/signal-token
chmod 600 ~/.config/nsls/signal-token
```

Never echo the token back in chat output. Don't include it in commit messages, summaries, or anywhere else it could be persisted.

### Step 4 — Verify

```sh
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $(cat ~/.config/nsls/signal-token)" \
  https://employee-profiles-production.up.railway.app/api/mcp/wins?weeks=1
```

- `200` — working. They'll see results once they restart.
- `401` — token rejected. Likely typo or trailing whitespace; have them re-paste.
- `403` — token works but they're a `standard` role. Tell them this skill isn't for them.

### Step 5 — Tell them to restart

Claude Code only registers MCP servers at session start. Tell the user:

> "Quit and reopen Claude Code (or `exit` and start a new session). After restart you'll have `signal_team_summary`, `signal_wins`, `signal_friction`, `signal_person`, `signal_person_history`, `signal_person_goals` available."

## Rotating

If a token is compromised or the user just wants a fresh one:

1. Click "Generate MCP token" again on `/team`. The old token stops working the instant the new one is minted (the `app_api_token` column is unique).
2. Re-run /signal-setup.

## Common failures

**`signal-mcp: token not found at ...`** in MCP server logs → the wrapper script can't find the token file. Confirm it exists at `~/.config/nsls/signal-token` and is readable.

**`401 unknown token`** → the token was rotated somewhere else (e.g. the user clicked the button again from a different browser). Re-mint and re-run setup.

**`403 token owner has no team access`** → the user's `app_role` is `standard` and they have no direct reports. Either Airtable isn't reflecting their team, or they genuinely don't manage anyone yet.

**Tools still missing after restart** → run `/mcp` in Claude Code to see if the `signal` server is listed. If it's not, the `nsls-builder-toolkit` plugin might not be enabled. Run `/setup` to check plugin state.

## Why not just an env var

The MCP server runs whenever Claude Code spawns it — it doesn't inherit the user's interactive shell env. Putting `SIGNAL_API_TOKEN=...` in `~/.zshrc` works only if Claude Code is launched from a shell that has sourced it. The file-based approach avoids that footgun: the wrapper reads the token at every spawn, regardless of how Claude Code was launched.
