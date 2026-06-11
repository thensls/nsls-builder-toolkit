---
name: signal-setup
description: >-
  Configure the Signal MCP server so Claude Code can query Quick Notes,
  wins, friction signals, and team summaries for any team you're allowed
  to see. Use when the user says "set up Signal", "signal mcp", "signal
  setup", "/signal-setup", asks why `signal_*` tools aren't available,
  or wants to rotate their Signal API token. For everyone: managers and
  execs get team/org scope; everyone else gets self scope — your own
  Quick Notes history and goals (powers /role-coach), nobody else's.
---

# /signal-setup — Connect Claude Code to Signal

## What this does

Signal (the people-ops bot powering Quick Notes, wins, and friction signals) exposes a read-only HTTP API at `https://employee-profiles-production.up.railway.app/api/mcp/*`. This skill writes your personal bearer token to `~/.config/nsls/signal-token` so the bundled MCP server can authenticate. Scope follows the token — execs see org-wide on cross-team endpoints, managers see their reporting subtree.

After setup you'll have six new tools in Claude Code: `signal_team_summary`, `signal_wins`, `signal_friction`, `signal_person`, `signal_person_history`, `signal_person_goals`.

**Works on macOS, Linux, and Windows.** The MCP server is launched directly as `node signal-mcp.js` (no shell wrapper), so it runs identically on every OS. The only host requirement is **Node.js 20+ on the PATH** — the bundle is built for Node 20 (and CI tests on it), so older majors may hit unsupported syntax. Each step below gives a macOS/Linux (`sh`) form and a Windows (PowerShell) form; use whichever matches the builder's machine.

## Who can use this

- **Executives** (people.app_role = 'executive'): org-wide on `wins`, `friction`, `person/*`. `team_summary` returns your own direct reports unless you pass `manager_slug`.
- **Managers** (anyone with direct reports): your reporting subtree.
- **Everyone else (self scope)**: `signal_person`, `signal_person_history`, and `signal_person_goals` work for **your own slug only** — your Quick Notes history and goal updates, with sentiment excluded server-side. Every other slug and every team endpoint returns 403. This is what powers `/role-coach` for individual contributors.

If you're not sure, run setup anyway — the first tool call will tell you your scope.

## Setup flow

When the user invokes /signal-setup:

### Step 0 — Confirm Node.js is installed

The MCP server runs as `node signal-mcp.js`, so Node must be on the PATH. Check first — a missing Node is the most common Windows failure, and it shows up as "tools never appear" with no error.

```sh
node --version   # works on macOS, Linux, and Windows (PowerShell or cmd)
```

If this prints a version ≥ v20, continue. If it errors (`command not found` / `not recognized`), the builder must install Node first:
- **macOS**: `brew install node` (or download from nodejs.org)
- **Windows**: download the LTS installer from https://nodejs.org and re-open Claude Code afterward so the new PATH is picked up.

### Step 1 — Register the MCP server (the part that's silently missing)

This is the #1 reason `signal_*` tools never appear even when Node and the token are perfect. The toolkit is *locally enabled* (an `enabledPlugins` entry), not marketplace-installed. Local enable loads skills/commands/hooks but does **not** register a plugin's bundled `.mcp.json` MCP server — so `signal` is absent from `/mcp` and `claude mcp list`, not failed, just never loaded.

Fix it by registering the server explicitly at user scope, pointing at the absolute path of this plugin (the directory this skill loaded from — `$CLAUDE_PLUGIN_ROOT`, e.g. `~/.claude/local-plugins/nsls-builder-toolkit`). Substitute the real path; don't rely on `$CLAUDE_PLUGIN_ROOT` being exported into a plain terminal (it usually isn't). `claude mcp add` is idempotent — if it's already registered it prints "already exists" and changes nothing, so it's always safe to run.

First check whether it's already there:

```sh
claude mcp get signal     # "No MCP server found" → register it below; otherwise skip to Step 2
```

macOS/Linux — register (replace `<PLUGIN_ROOT>` with the real absolute path):
```sh
claude mcp add signal --scope user \
  --env CLAUDE_PLUGIN_ROOT="<PLUGIN_ROOT>" \
  -- node "<PLUGIN_ROOT>/mcp-servers/signal/signal-mcp.js"
```

Windows (PowerShell) — same command, backslashes, real path substituted:
```powershell
claude mcp add signal --scope user `
  --env CLAUDE_PLUGIN_ROOT="<PLUGIN_ROOT>" `
  -- node "<PLUGIN_ROOT>\mcp-servers\signal\signal-mcp.js"
```

This writes to `~/.claude.json`. Verify with `claude mcp get signal` (expect `Scope: User config`). Reversible with `claude mcp remove signal -s user`. The server points at the same local-plugins path the auto-update hook git-pulls, so future updates to `signal-mcp.js` flow through on the next session. Tools bind at session start, so they appear after the restart in the final step — not immediately.

> New installs already do this automatically (`install.sh` registers every server in `.mcp.json`). This step is the self-heal for anyone who installed before that landed, or whose registration got removed.

### Step 2 — Check existing state

macOS/Linux:
```sh
test -f ~/.config/nsls/signal-token && echo "token exists" || echo "no token"
```

Windows (PowerShell):
```powershell
if (Test-Path "$HOME\.config\nsls\signal-token") { "token exists" } else { "no token" }
```

If a token exists, ask whether to rotate or just verify the existing one.

### Step 3 — Mint the token

Tell the user to:

1. Open `https://employee-profiles-production.up.railway.app/me/mcp-token` in a browser (works for everyone; managers/execs can also use the button on `/team`). Sign in with their NSLS Google account.
2. Click **"Generate MCP token"**.
3. Copy the token (starts with `signal_` followed by 64 hex chars). It's shown once; if they dismiss the popup they need to regenerate.

Then prompt them to paste it into Claude Code.

### Step 4 — Write the token file

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

### Step 5 — Verify

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

`CLAUDE_PLUGIN_ROOT` is set inside the plugin's `.mcp.json`/hook context but is not guaranteed to be exported into a plain terminal. When running this by hand, substitute the real path — the `mcp-servers/signal/signal-mcp.js` inside the installed `nsls-builder-toolkit` plugin directory (the same folder this skill loaded from).

Then confirm the token is accepted by the API.

macOS/Linux:
```sh
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $(cat ~/.config/nsls/signal-token)" \
  "https://employee-profiles-production.up.railway.app/api/mcp/wins?weeks=1"
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

- `200` — working with team/org scope. They'll see results once they restart.
- `401` — token rejected. Likely typo or trailing whitespace; have them re-paste.
- `403` — the token is valid but carries **self scope** (`standard` role — no reports, not an exec). That's expected and fine: team endpoints like `wins` 403, but `signal_person`, `signal_person_history`, and `signal_person_goals` work for their own slug. Verify with their own profile slug instead (the lowercased `firstname-lastname` form of their name):

```sh
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $(cat ~/.config/nsls/signal-token)" \
  "https://employee-profiles-production.up.railway.app/api/mcp/person/<their-slug>"
```

`200` there = self scope working — exactly what /role-coach T1 needs.

### Step 6 — Tell them to restart

Claude Code only registers MCP servers at session start. Tell the user:

> "Quit and reopen Claude Code (or `exit` and start a new session). After restart you'll have `signal_team_summary`, `signal_wins`, `signal_friction`, `signal_person`, `signal_person_history`, `signal_person_goals` available."

## Rotating

If a token is compromised or the user just wants a fresh one:

1. Click "Generate MCP token" again on `/me/mcp-token` (or `/team` for managers/execs). The old token stops working the instant the new one is minted (the `app_api_token` column is unique).
2. Re-run /signal-setup.

## Common failures

**`signal-mcp: no token found ...`** in MCP server logs → the server couldn't find a token. Confirm the file exists at `~/.config/nsls/signal-token` and is readable. (The server resolves this path with `os.homedir()`, so it's the same location on every OS.)

**`node: command not found` / `'node' is not recognized`, or the `signal` server silently never appears** → Node isn't installed or isn't on the PATH. This is the #1 Windows failure. Re-run Step 0; on Windows, install Node from nodejs.org and fully restart Claude Code so the PATH refreshes.

**`401 unknown token`** → the token was rotated somewhere else (e.g. the user clicked the button again from a different browser). Re-mint and re-run setup.

**`403 token owner has no team access`** on team endpoints → the user's role is `standard` (no direct reports, not an exec). Their token still works in **self scope** on the three `person/*` endpoints for their own slug. If they believe they SHOULD have team scope, Airtable isn't reflecting their reports yet.

**`403 not your profile`** on a `person/<slug>` call → self-scope token reading a slug that isn't theirs (or a typo'd slug — the API deliberately doesn't distinguish). Have them check the slug spelling against their own name.

**Tools still missing after restart** → run `/mcp` (or `claude mcp list`) to see if the `signal` server is listed. If it's listed but errored, run the `--selftest` from Step 5 to see the failure. If it's **not listed at all**, the server was never registered — this is the local-enable gap from Step 1, *not* a disabled plugin. Don't re-run `/setup` or re-enable the plugin; that won't register the MCP server. Run the `claude mcp add` from Step 1 (`claude mcp get signal` first to confirm it's absent), then restart.

## Why a token file (not an env var, not a shell wrapper)

The MCP server runs whenever Claude Code spawns it — it doesn't inherit the user's interactive shell env. Putting `SIGNAL_API_TOKEN=...` in `~/.zshrc` works only if Claude Code is launched from a shell that has sourced it. The file-based approach avoids that footgun: the server reads the token at every spawn, regardless of how Claude Code was launched.

Earlier versions used a POSIX shell wrapper (`signal-mcp.sh`) to read the token and `exec node`. That broke on Windows, which can't launch a `.sh` as a command — the server failed to start with no visible error. The token-reading now lives inside the Node server (`loadToken()`), and `.mcp.json` invokes `node` directly, so there's no OS-specific glue left.
