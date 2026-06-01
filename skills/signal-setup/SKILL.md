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

**Works on macOS, Linux, and Windows.** The MCP server is launched directly as `node signal-mcp.js` (no shell wrapper), so it runs identically on every OS. The only host requirement is **Node.js 18+ on the PATH** — the server is a Node program. Each step below gives a macOS/Linux (`sh`) form and a Windows (PowerShell) form; use whichever matches the builder's machine.

## Who can use this

- **Executives** (people.app_role = 'executive'): org-wide on `wins`, `friction`, `person/*`. `team_summary` returns your own direct reports unless you pass `manager_slug`.
- **Managers** (anyone with direct reports): your reporting subtree.
- **Everyone else**: every endpoint will 403. Don't bother setting this up.

If you're not sure, run setup anyway — the first tool call will tell you.

## Setup flow

When the user invokes /signal-setup:

### Step 0 — Confirm Node.js is installed

The MCP server runs as `node signal-mcp.js`, so Node must be on the PATH. Check first — a missing Node is the most common Windows failure, and it shows up as "tools never appear" with no error.

```sh
node --version   # works on macOS, Linux, and Windows (PowerShell or cmd)
```

If this prints a version ≥ v18, continue. If it errors (`command not found` / `not recognized`), the builder must install Node first:
- **macOS**: `brew install node` (or download from nodejs.org)
- **Windows**: download the LTS installer from https://nodejs.org and re-open Claude Code afterward so the new PATH is picked up.

### Step 1 — Check existing state

macOS/Linux:
```sh
test -f ~/.config/nsls/signal-token && echo "token exists" || echo "no token"
```

Windows (PowerShell):
```powershell
if (Test-Path "$HOME\.config\nsls\signal-token") { "token exists" } else { "no token" }
```

If a token exists, ask whether to rotate or just verify the existing one.

### Step 2 — Mint the token

Tell the user to:

1. Open `https://employee-profiles-production.up.railway.app/team` in a browser. Sign in with their NSLS Google account.
2. Click **"Generate MCP token"** at the top of the page.
3. Copy the token (starts with `signal_` followed by 64 hex chars). It's shown once; if they dismiss the popup they need to regenerate.

Then prompt them to paste it into Claude Code.

### Step 3 — Write the token file

Write the token to `~/.config/nsls/signal-token` (the server reads this exact path on every OS via `os.homedir()`).

macOS/Linux — strict permissions via umask:
```sh
mkdir -p ~/.config/nsls
umask 077  # so the file is created mode 600
printf '%s' '<TOKEN>' > ~/.config/nsls/signal-token
chmod 600 ~/.config/nsls/signal-token
```

Windows (PowerShell) — `chmod`/`umask` don't exist; create the dir and write the file without a trailing newline:
```powershell
$dir = "$HOME\.config\nsls"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
[IO.File]::WriteAllText("$dir\signal-token", '<TOKEN>')
```
(NTFS file permissions already restrict the file to the user profile; no explicit chmod needed.)

Never echo the token back in chat output. Don't include it in commit messages, summaries, or anywhere else it could be persisted.

### Step 4 — Verify

The most reliable cross-platform check is the server's own self-test — it confirms Node can launch the bundled server on this machine (no token needed):

macOS/Linux:
```sh
node "$CLAUDE_PLUGIN_ROOT/mcp-servers/signal/signal-mcp.js" --selftest
# expect: signal-mcp: selftest OK — 6 tools registered, <platform>, node <version>
```

Windows (PowerShell — note `$env:` prefix and backslashes):
```powershell
node "$env:CLAUDE_PLUGIN_ROOT\mcp-servers\signal\signal-mcp.js" --selftest
# expect: signal-mcp: selftest OK — 6 tools registered, <platform>, node <version>
```

Then confirm the token is accepted by the API.

macOS/Linux:
```sh
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $(cat ~/.config/nsls/signal-token)" \
  https://employee-profiles-production.up.railway.app/api/mcp/wins?weeks=1
```

Windows (PowerShell — works on the default 5.1; `-SkipHttpErrorCheck` is 7+ only, so catch the 401/403 instead):
```powershell
$tok = (Get-Content "$HOME\.config\nsls\signal-token" -Raw).Trim()
$uri = "https://employee-profiles-production.up.railway.app/api/mcp/wins?weeks=1"
try {
  (Invoke-WebRequest -UseBasicParsing -Uri $uri -Headers @{ Authorization = "Bearer $tok" }).StatusCode
} catch {
  $_.Exception.Response.StatusCode.value__   # prints 401 / 403 on a rejected token
}
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

**`signal-mcp: no token found ...`** in MCP server logs → the server couldn't find a token. Confirm the file exists at `~/.config/nsls/signal-token` and is readable. (The server resolves this path with `os.homedir()`, so it's the same location on every OS.)

**`node: command not found` / `'node' is not recognized`, or the `signal` server silently never appears** → Node isn't installed or isn't on the PATH. This is the #1 Windows failure. Re-run Step 0; on Windows, install Node from nodejs.org and fully restart Claude Code so the PATH refreshes.

**`401 unknown token`** → the token was rotated somewhere else (e.g. the user clicked the button again from a different browser). Re-mint and re-run setup.

**`403 token owner has no team access`** → the user's `app_role` is `standard` and they have no direct reports. Either Airtable isn't reflecting their team, or they genuinely don't manage anyone yet.

**Tools still missing after restart** → run `/mcp` in Claude Code to see if the `signal` server is listed. If it's listed but errored, run the `--selftest` from Step 4 to see the failure. If it's not listed at all, the `nsls-builder-toolkit` plugin might not be enabled — run `/setup` to check plugin state.

## Why a token file (not an env var, not a shell wrapper)

The MCP server runs whenever Claude Code spawns it — it doesn't inherit the user's interactive shell env. Putting `SIGNAL_API_TOKEN=...` in `~/.zshrc` works only if Claude Code is launched from a shell that has sourced it. The file-based approach avoids that footgun: the server reads the token at every spawn, regardless of how Claude Code was launched.

Earlier versions used a POSIX shell wrapper (`signal-mcp.sh`) to read the token and `exec node`. That broke on Windows, which can't launch a `.sh` as a command — the server failed to start with no visible error. The token-reading now lives inside the Node server (`loadToken()`), and `.mcp.json` invokes `node` directly, so there's no OS-specific glue left.
