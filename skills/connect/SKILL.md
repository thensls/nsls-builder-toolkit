---
name: connect
description: >-
  Connect Claude Code to the external systems you have credentials for.
  Use when a skill says its tools aren't available, when MCP tools aren't
  loading, or when you want to add a new system. Detects what's already
  connected, walks through setup for what's missing, and handles the
  failures that will happen along the way.
---

# /connect — Connect Your Systems

## SAFETY: READ-ONLY BY DEFAULT

Do NOT proactively suggest, offer, or present write/delete/modify operations as options. Do not surface them as next steps. They are never part of the default workflow.

If the user EXPLICITLY requests a write operation: explain the specific risks of that operation, confirm they understand what will be changed and that it cannot be undone (if applicable), confirm they have the necessary permissions in that service, and only then proceed if they still want to. This is behind several layers of guardrails — but it is ultimately the user's decision, not a flat refusal. Developers should not have to leave Claude Code to create a PostHog dashboard or update an Airtable record.

## What This Skill Does

You installed the NSLS Builder Toolkit. This skill connects Claude Code to the systems you already have credentials for — so the other skills can access your data.

Run it once per system. The connection persists across sessions. You never enter the token again.

**How persistence works:** Tokens and API keys are stored as environment variables in your Claude Code config files. Claude Code loads these on every startup and passes them to each MCP server automatically.

**Update resilience:** Claude Code auto-updates can occasionally reset or restructure settings. If your connections stop working after an update, check that your MCP configs are still in `settings.json` and that `"defaultMode": "auto"` is at the top level (not nested inside another object). Back up your `settings.json` periodically — the MCP configs and permission entries took significant effort to build and cannot be auto-reconstructed.

## Three-Tier Permission Model

Every operation falls into one of three tiers:

1. **Read-only** — runs without friction. No approval prompts, no extra steps. Querying PostHog, searching Airtable, reading Slack messages — this just happens. The `/connect` skill adds all read-only tools to `permissions.allow` IN THE SAME STEP as writing the MCP config. The user never sees a permission prompt for a read-only tool.

2. **Local configuration** — asks permission and explains WHY. Adding an MCP server to your config, writing permission entries, modifying Claude Code settings. These change YOUR setup, not external data. Claude explains what it's about to modify and waits for a yes. You may also see a system permission dialog from Claude Code itself — that's the tool confirming the config change, not Claude asking again. Approve it to continue.

3. **Write to external systems** — never proactively offered. But if the user explicitly requests it: explain the specific risks, confirm they understand, confirm they have permissions, then proceed. Behind several layers of guardrails, but ultimately the user's call.

## Before You Start: Environment Detection

Different Claude Code environments support different connection methods.

**Check where you're running:**
- **VS Code extension** → Use stdio (npx) or HTTP MCP servers configured in your config files. First-party `claude.ai *` connectors will NOT work (their OAuth only completes through claude.ai web).
- **Cursor** → Same as VS Code. First-party connectors don't work here either.
- **claude.ai web** → First-party connectors work here. Also supports stdio/HTTP.
- **CLI terminal** → stdio/HTTP servers work. First-party connectors may not.

**If you don't know:** Try running a tool. If it says "This is a claude.ai MCP connector" or shows "Completing authentication in browser..." and nothing happens — you're in VS Code/Cursor and need the stdio/HTTP approach instead.

## Step 1: Detect What's Connected

Read `~/.claude/settings.json` and `~/.claude.json` to check for existing MCP server entries. For each one found, attempt a read-only health check.

Report status for each system:
- ✅ **Connected** — MCP configured, tools available, health check passed
- ⚠️ **Configured but not responding** — MCP entry exists but tools aren't loading (check token, check env vars, try manual test in terminal)
- ❌ **Not set up** — No MCP entry found

## Step 2: Connect What's Missing

For each system the user wants to connect, follow the service-specific instructions below. Each system may have multiple viable connection methods (seeds). The skill recommends one, explains the tradeoffs, and helps discover what works for the user's specific setup.

**At every step: expect failure.** Silent failures, environment incompatibilities, expired tokens, wrong package names, missing env vars. When something doesn't work:
1. Diagnose what happened (don't guess — check the error)
2. Try the next approach
3. If tools don't appear after config change + restart, test the MCP server manually in terminal: run the npx command with env vars and read the error output
4. Keep going until it works

**After each successful connection:**
1. Write the MCP server config to the appropriate config file
2. Write ALL read-only tools to `permissions.allow` in `settings.json` (Tier 1 — zero friction)
3. Tell the user to restart: VS Code → `Shift+Cmd+P` → "Developer: Reload Window"
4. After restart, verify with a read-only query

---

## Service Registry

Each entry below is a seed — one path that worked. Your setup may need a different approach.

---

### PostHog

**What:** Product analytics across Society, FOL, and Shop.
**Skills that use it:** `/posthog`, `/data-intel`

#### Connection: HTTP with bearer token
**MCP type:** HTTP
**Auth:** Personal API key from PostHog
**Prerequisite:** PostHog account with project access

1. Go to PostHog → Settings → Personal API Keys → Create Key
2. Give it a descriptive name (e.g., "Claude Code MCP")
3. Scope: at minimum "Query Read" — add more read scopes as needed
4. Copy the key (starts with `phx_`)

**Config** (add to `~/.claude.json` under `mcpServers`):
```json
"posthog": {
  "type": "http",
  "url": "https://mcp.posthog.com/mcp",
  "headers": {
    "Authorization": "Bearer phx_YOUR_KEY_HERE"
  }
}
```

**Permissions** (add to `settings.json` `permissions.allow`):
All tools matching `mcp__posthog__*-get*`, `mcp__posthog__*-list*`, `mcp__posthog__*-retrieve`, `mcp__posthog__query-*`, `mcp__posthog__docs-search`, `mcp__posthog__entity-search`, `mcp__posthog__*-stats`. Enumerate the actual tool names after the server loads — they change as PostHog updates their MCP.

**Verify:** Search for an event definition or run a simple query.

**Known issues from setup:**
- Running `claude mcp add` inside Claude Code fails with "cannot be launched inside another session" — use `unset CLAUDECODE` first, or add config manually
- CLI argument ordering matters: name before URL
- ~80 tools available — add read-only ones to permissions.allow or you'll get prompted for each one

---

### Airtable

**What:** Shared databases for tracking work, roadmaps, content.
**Skills that use it:** `/airtable-guide`

#### Connection: stdio with Personal Access Token
**MCP type:** stdio (npx)
**Auth:** Personal Access Token (PAT)
**Prerequisite:** Airtable account with base access

1. Go to airtable.com/create/tokens → Create New Token
2. Add scopes: `data.records:read`, `schema.bases:read` — and any other read scopes available
3. Add access to the bases you need (or all bases)
4. Copy the token (starts with `pat`)

**Config** (add to `~/.claude/settings.json` under `mcpServers`):
```json
"airtable": {
  "command": "/usr/local/bin/npx",
  "args": ["-y", "airtable-mcp-server"],
  "env": {
    "AIRTABLE_API_KEY": "patYOUR_TOKEN_HERE"
  }
}
```

**Permissions:** `mcp__airtable__list_bases`, `mcp__airtable__list_tables`, `mcp__airtable__describe_table`, `mcp__airtable__list_records`, `mcp__airtable__search_records`, `mcp__airtable__get_record`, `mcp__airtable__list_comments`

**Verify:** `list_bases` should return your accessible bases.

**Known issues from setup:** None. This is the cleanest setup of all services — PAT auth, stdio transport, works on first try. The gold standard.

---

### n8n

**What:** Workflow automation platform.
**Skills that use it:** `/n8n`

#### Connection: stdio with API key
**MCP type:** stdio (npx)
**Auth:** n8n API key (JWT)
**Prerequisite:** n8n Cloud account or self-hosted instance with API access

1. Go to your n8n instance → Settings → API → Create API Key
2. Copy the key (JWT format, starts with `eyJ`)

**Config** (add to `~/.claude.json` under `mcpServers` — NOT just `settings.json`):
```json
"n8n": {
  "command": "/usr/local/bin/npx",
  "args": ["-y", "n8n-mcp@latest"],
  "env": {
    "N8N_API_URL": "https://YOUR_INSTANCE.app.n8n.cloud",
    "N8N_API_KEY": "eyJYOUR_KEY_HERE",
    "MCP_MODE": "stdio",
    "N8N_MCP_TELEMETRY_DISABLED": "true"
  }
}
```

**Important:** `N8N_MCP_TELEMETRY_DISABLED: "true"` suppresses a telemetry prompt that blocks stdio communication. Without it, the server hangs.

**Permissions:** `mcp__n8n__n8n_list_workflows`, `mcp__n8n__n8n_get_workflow`, `mcp__n8n__n8n_executions`, `mcp__n8n__n8n_health_check`, `mcp__n8n__search_nodes`, `mcp__n8n__get_node`, `mcp__n8n__tools_documentation`, `mcp__n8n__search_templates`, `mcp__n8n__get_template`, `mcp__n8n__validate_node`, `mcp__n8n__validate_workflow`, `mcp__n8n__n8n_validate_workflow`, `mcp__n8n__n8n_workflow_versions`

**Verify:** `n8n_list_workflows` should return your workflows.

**Known issues from setup:**
- Tool names have `n8n_` prefix — don't guess names, verify after server loads
- `better-sqlite3` module warning on startup is harmless — falls back to sql.js
- Config must be in `~/.claude.json` for VS Code/Cursor to find it (not just `settings.json`)
- Can't activate or execute workflows that only have Manual Trigger

---

### Customer.io

**What:** Email marketing and customer messaging.
**Skills that use it:** `/customerio`

#### Connection: HTTP with OAuth
**MCP type:** HTTP (remote server)
**Auth:** OAuth browser flow — managed by Claude Code
**Prerequisite:** Customer.io account. Account admin must enable "Customer.io AI" and "Customer.io MCP Server" in Settings → Privacy, Data, & AI.

**Config** (add to `~/.claude/settings.json` under `mcpServers`):
```json
"customerio": {
  "type": "http",
  "url": "https://mcp.customer.io/mcp"
}
```

**Permissions:** `mcp__customerio__*` (wildcard — the App API is read-only by design)

**Verify:** After the OAuth flow completes in your browser, try searching for a customer.

**Known issues from setup:**
- OAuth expires between sessions — tools silently disappear with no error. If Customer.io tools stop appearing, re-authenticate through the `/mcp` flow
- The OAuth flow opens a browser window. In VS Code, this should work (Customer.io's OAuth is not limited to claude.ai web like Slack's first-party connector is)
- Account admin must enable the MCP feature before any user can connect

---

### Slack

**What:** Team messaging, channels, DMs, search.
**Skills that use it:** `/slack`

#### Option A: First-party OAuth via Terminal (Recommended)
**MCP type:** HTTP (remote, managed by Claude Code)
**Auth:** OAuth browser flow, one-time setup
**Access level:** User-level — sees everything you can see: channels, DMs, group DMs, search

The first-party `claude.ai Slack` connector authenticates as YOUR Slack user (not a bot). This gives full read access to DMs, group DMs, and cross-workspace search. The OAuth flow doesn't work from inside VS Code/Cursor, but it DOES work from Terminal.app — and the token persists across all environments after that.

1. Open **Terminal.app** (the macOS terminal, NOT your IDE's integrated terminal)
2. Run `claude` to start a Claude Code session
3. Type `/mcp` → select "claude.ai Slack"
4. A browser window opens → complete the Slack OAuth consent
5. Back in Terminal, press Enter when prompted ("Press Enter after authenticating in your browser")
6. You should see "Authentication successful. Connected to claude.ai Slack."
7. Close the Terminal session — the token is stored on your claude.ai account permanently

**After authenticating — getting it working in Cursor/VS Code:**
Claude Code caches which connectors need auth. Even after a successful Terminal auth, your IDE may still show "Needs Auth." Fix:
1. Open `~/.claude/mcp-needs-auth-cache.json`
2. Delete the `"claude.ai Slack"` entry from the JSON
3. Reload your IDE (`Shift+Cmd+P` → "Developer: Reload Window")
4. The first-party Slack tools should now be available

**Permissions** (read-only tools to add to `permissions.allow`):
`mcp__claude_ai_Slack__slack_read_channel`, `mcp__claude_ai_Slack__slack_read_thread`, `mcp__claude_ai_Slack__slack_read_canvas`, `mcp__claude_ai_Slack__slack_read_user_profile`, `mcp__claude_ai_Slack__slack_search_public_and_private`, `mcp__claude_ai_Slack__slack_search_public`, `mcp__claude_ai_Slack__slack_search_users`, `mcp__claude_ai_Slack__slack_search_channels`

Do NOT add: `slack_send_message`, `slack_send_message_draft`, `slack_schedule_message`, `slack_create_canvas`, `slack_update_canvas` (Tier 3 — write operations, never proactively offered).

**Verify:** `slack_read_channel` with a known user_id as `channel_id` should return your DM history with that person. `slack_search_public_and_private` with a keyword should return results across channels and DMs.

**Tools available with this approach:**
- `slack_search_public_and_private` — search ALL messages (public, private, DMs, group DMs) with filters
- `slack_read_channel` — read channel history or DM history (pass user_id as channel_id for DMs)
- `slack_read_thread` — read thread replies
- `slack_search_users` — find users by name
- `slack_search_channels` — find channels by name
- `slack_read_user_profile` — full user profile with custom fields
- `slack_read_canvas` — read canvas content

#### Option B: Bot token via korotovsky (Fallback)
**MCP type:** stdio (npx)
**Auth:** Bot User OAuth Token (`xoxb-`)
**Access level:** Bot-scoped — only sees channels the bot is invited to. Cannot see DMs. Cannot search.
**Prerequisite:** Slack workspace admin must create a Slack app. Non-admins cannot do this step — ask your admin.

Use this when: Terminal.app isn't available, org prefers bot-scoped access, or first-party OAuth is broken.
**What:** Team messaging, channels, search.
**Skills that use it:** `/slack`
**Prerequisite:** Slack workspace admin must create a Slack app. Non-admins cannot do this step — ask your admin.

#### Connection: stdio with bot token (VS Code / Cursor)
**MCP type:** stdio (npx)
**Auth:** Bot User OAuth Token (`xoxb-`)

1. Go to api.slack.com/apps → Create New App → From scratch
2. Name: `Claude Code MCP`, Workspace: select yours
3. OAuth & Permissions → Bot Token Scopes → add ALL read scopes available. Key ones: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `im:read`, `im:history`, `mpim:read`, `mpim:history`, `users:read`, `users.profile:read`, `search:read`, `reactions:read`, `files:read`, `pins:read`, `bookmarks:read`, `links:read`, `metadata.message:read`, `reminders:read`, `team:read`, `usergroups:read`, `users:read.email`. Browse the full list — add any scope with "read" in the name. This is a starting point, not a ceiling.
4. Do NOT add User Token Scopes with `admin.*` prefix — these require Enterprise Grid and will block installation with "Apps with this feature are only available to Enterprise customers" or `team_not_authorized`.
5. Install to Workspace → click Allow
6. Copy the Bot User OAuth Token (starts with `xoxb-`)
7. Find your Team ID: open Slack in a browser → DevTools → Console → `JSON.parse(localStorage.getItem('localConfig_v2')).teams` → the key is your Team ID (format: `T0XXXXXXXX`)
4. Install to Workspace → click Allow
5. Copy the Bot User OAuth Token (starts with `xoxb-`)
6. Find your Team ID: open Slack in a browser → DevTools → Console → `JSON.parse(localStorage.getItem('localConfig_v2')).teams` → the key is your Team ID (format: `T0XXXXXXXX`)

**Config** (add to `~/.claude.json` under `mcpServers` — name it `slack-workspace`, NOT `slack`):
```json
"slack-workspace": {
  "command": "/usr/local/bin/npx",
  "args": ["-y", "slack-mcp-server"],
  "env": {
    "SLACK_MCP_XOXB_TOKEN": "xoxb-YOUR_TOKEN_HERE",
    "SLACK_TEAM_ID": "T0YOUR_TEAM_ID"
  }
}
```

**Why `slack-workspace` not `slack`?** A name conflict with the built-in `claude.ai Slack` connector prevents tools from loading. Use any name except `slack`.

**Permissions:** `mcp__slack-workspace__channels_list`, `mcp__slack-workspace__conversations_history`, `mcp__slack-workspace__conversations_replies`, `mcp__slack-workspace__usergroups_list`, `mcp__slack-workspace__usergroups_me`, `mcp__slack-workspace__users_search`

**Verify:** `channels_list` with `channel_types: "public_channel"` should return your workspace's channels.

#### Option C: First-party OAuth from claude.ai web
**MCP type:** HTTP (remote)
**Auth:** OAuth browser flow

This works natively from claude.ai/code web interface. In VS Code/Cursor, the OAuth flow silently does nothing — use Option A (Terminal) instead.
**Known issues from setup (9 failures documented):**
- First-party `claude.ai Slack` connector does NOT work in VS Code/Cursor — OAuth only completes through claude.ai web. If you see "Completing authentication in browser..." and nothing happens, you're in the wrong environment. Use the bot token approach instead.
- Browser tokens (`xoxc` + `xoxd`) extracted from DevTools don't work outside the browser — `invalid_auth`. Use a bot token.
- Naming the server `slack` conflicts with the first-party connector — name it `slack-workspace` or anything else.
- Both `SLACK_MCP_XOXB_TOKEN` AND `SLACK_TEAM_ID` are required. Missing either = silent crash, tools never appear.
- The env var must be `SLACK_MCP_XOXB_TOKEN` (not `SLACK_MCP_BOT_TOKEN` or `SLACK_BOT_TOKEN`). Wrong name = silent crash.
- Config must be in `~/.claude.json` global `mcpServers` (not `~/.claude/settings.json`).
- `channels_list` may not return private channels. Use `conversations_history` with `#channel-name` to access private channels directly.
- The bot only sees channels it's been invited to. For private channels: `/invite @Claude Code MCP` in the channel. Teammates will see a message: "[You] added an integration to this channel: Claude Code MCP."
- The bot can see: message text, senders, timestamps, reactions (emoji + counts), threads, file counts. It CANNOT see actual file content (images, videos) — only metadata.
- Adding scopes later requires clicking "Reinstall to Workspace" on the OAuth & Permissions page.
- The MCP server caches users and channels on startup. If you invite the bot to a new channel, restart Claude Code to refresh the cache.

#### Connection: First-party OAuth (claude.ai web only)
**MCP type:** HTTP (remote)
**Auth:** OAuth browser flow

This ONLY works from claude.ai web. In VS Code/Cursor, the OAuth flow silently does nothing.

1. Type `/mcp` in Claude Code chat → select "claude.ai Slack"
2. Complete the OAuth flow in your browser
3. Tools become available automatically

No config file changes needed. Same user-level access as Option A.

#### Known issues (11 failures documented across 2 setup sessions)
- **Silent OAuth in IDE:** First-party `claude.ai Slack` connector shows "Completing authentication in browser..." in VS Code/Cursor but the browser never opens. Use Terminal.app (Option A) or bot token (Option B) instead.
- **Auth cache stale across environments:** After authenticating from Terminal, Cursor may still show "Needs Auth" because `~/.claude/mcp-needs-auth-cache.json` caches the old state. Delete the `"claude.ai Slack"` entry from this file and reload.
- **Browser tokens don't persist:** `xoxc` + `xoxd` tokens extracted from DevTools are session-bound — `invalid_auth` outside the browser. Not viable for persistent connections.
- **User token scopes blocked:** Adding User Token Scopes (especially `admin.*` scopes) to a custom Slack app can trigger "Apps with this feature are only available to Enterprise customers" or `team_not_authorized`. Non-Enterprise Grid workspaces cannot install apps with admin-level user scopes. Remove all `admin.*` scopes before reinstalling.
- **Name conflict:** Naming a korotovsky server `slack` conflicts with the first-party connector — tools never load. Use `slack-workspace` or any other name.
- **Missing env vars = silent crash:** Both `SLACK_MCP_XOXB_TOKEN` AND `SLACK_TEAM_ID` are required for korotovsky. Missing either = server crashes on startup, tools never appear, no error shown.
- **Wrong env var name = silent crash:** Must be `SLACK_MCP_XOXB_TOKEN` (not `SLACK_MCP_BOT_TOKEN`). Run `npx -y slack-mcp-server` in terminal to see the exact expected env var names.
- **Config file location:** Some MCP servers only load from `~/.claude.json` global `mcpServers`, not `~/.claude/settings.json`. If tools don't appear after restart, try moving the config.
- **Bot can't see DMs:** Bot tokens (`xoxb-`) can only see channels the bot is invited to. DMs and search require user-level access (Option A or C).
- **Bot channel invitation visible:** When inviting the bot to a private channel via `/invite @Claude Code MCP`, everyone in the channel sees: "[You] added an integration to this channel: Claude Code MCP."
- **Bot sees metadata, not files:** The bot can see message text, senders, timestamps, reactions, threads, file counts. It CANNOT see actual file content (images, videos) — only metadata.
- **Cache refresh:** The korotovsky MCP server caches users and channels on startup. After inviting the bot to a new channel, restart Claude Code to refresh.
No config file changes needed. But this approach is limited to claude.ai web sessions.

---

### Braintrust

**What:** AI evaluation and observability.
**Skills that use it:** `/braintrust-evals`

**Not an MCP integration.** Braintrust is an SDK — `braintrust` npm package — called directly by Claude Code. No MCP server, no config file entry, no `mcpServers` block.

To use: `npm install braintrust` in your project, set `BRAINTRUST_API_KEY` as an environment variable.

---

### NSLS DNS Proxy

**What:** The scoped service that puts apps on branded `nsls.org` subdomains (e.g. `signal.nsls.org`). It can ONLY create/update/delete subdomain CNAME/A/AAAA records — it physically cannot touch email, the apex, `www`, or `auth`.
**Skills that use it:** `/add-domain`

**Not an MCP integration.** The `/add-domain` skill calls the proxy over plain HTTP with `curl`. It reads two values straight from your environment — no MCP server, no `mcpServers` block.

**Two env vars** (add to the top-level `env` block in `~/.claude/settings.json`):

```json
"env": {
  "NSLS_DNS_PROXY_URL": "https://nsls-dns-proxy-production.up.railway.app",
  "NSLS_DNS_PROXY_TOKEN": "<shared bearer token>"
}
```

- `NSLS_DNS_PROXY_URL` — public, fixed: `https://nsls-dns-proxy-production.up.railway.app`. (The bare `nsls-dns-proxy.up.railway.app` 404s — it must include `-production`.)
- `NSLS_DNS_PROXY_TOKEN` — a shared secret. It is NOT in any repo or `.env.example`. Get it from Kevin / the proxy owner; it's `PROXY_AUTH_TOKEN` in the Doppler project `nsls-dns-proxy`.

After adding them, restart Claude Code so the `env` block reloads.

**Verify:**
```bash
curl -s "$NSLS_DNS_PROXY_URL/health"   # expect {"ok":true,"service":"nsls-dns-proxy","railwayVerify":true}
```
A `200` with `"ok":true` means you're connected. A `404` ("Application not found") means the URL is wrong — check for the `-production` suffix.

**Known issues from setup:**
- The most common mistake is the URL: `nsls-dns-proxy.up.railway.app` (no `-production`) returns Railway's "Application not found." Use the `-production` host.
- A `401`/`403` from `/domains` means the token is missing or wrong — re-check `NSLS_DNS_PROXY_TOKEN`.
- These are plain env vars, not an MCP server, so nothing appears under `/mcp`. The only "connection" is the two vars being present in your shell — confirm with `echo "$NSLS_DNS_PROXY_URL"`.

---

### Snowflake

**What:** Data warehouse.
**No seed yet.** If you have Snowflake access, help the `/connect` skill by trying available MCP packages and documenting what works.

---

### HubSpot

**What:** CRM — 6.9M contacts, chapter management, enrollment pipeline, support tickets.
**Type:** claude.ai MCP connector (OAuth, not local MCP server)
**Setup:** Run `/mcp` → select "claude.ai HubSpot" → complete OAuth on HubSpot consent screen → select "View-only" for optional permissions → authorize.
**Post-setup:** If tools don't appear after auth, check `~/.claude/mcp-needs-auth-cache.json` — remove the HubSpot entry if the OAuth callback was interrupted, then restart Claude Code.
**Tools available after connection:** get_user_details, get_properties, get_crm_objects, search_crm_objects, search_properties, search_owners
**Skill:** `/hubspot`
**What:** CRM.
**No seed yet.** Found in PostHog CDP integrations. If you have HubSpot access, help the `/connect` skill by trying available MCP packages and documenting what works.

---

### Rippling

**What:** HR / ATS / People operations.
**No seed yet.** If you have Rippling access, help the `/connect` skill by trying available MCP packages and documenting what works.

---

## Step 3: Verify All Connections

After connecting everything, run a read-only health check on each service and report the final status card:

| System | Status | Tools Available |
|--------|--------|----------------|
| PostHog | ✅ / ⚠️ / ❌ | count |
| Airtable | ✅ / ⚠️ / ❌ | count |
| n8n | ✅ / ⚠️ / ❌ | count |
| Customer.io | ✅ / ⚠️ / ❌ | count |
| Slack | ✅ / ⚠️ / ❌ | count |

## When Things Go Wrong (Diagnostic Loop)

If tools don't appear after a config change + restart:

1. **Test the MCP server directly:** Run the npx command with the env vars set using Claude Code's Bash tool — NOT by asking the user to paste into their own terminal. Claude Code runs this itself and reads the error output. Claude Code hides MCP startup errors during normal operation — running the command directly surfaces them.
   ```bash
   SLACK_MCP_XOXB_TOKEN="xoxb-..." SLACK_TEAM_ID="T0..." npx -y slack-mcp-server
   ```
2. **Check the config file location.** VS Code/Cursor may read from `~/.claude.json`, not `~/.claude/settings.json`. Try moving the config.
3. **Check for name conflicts.** If a first-party `claude.ai *` connector exists for the same service, rename your server (e.g., `slack-workspace` not `slack`).
4. **Check env var names exactly.** One wrong character = silent crash. The error message from step 1 tells you the exact names expected.
5. **Check if auth expired.** OAuth-based services (Customer.io) lose auth between sessions. Re-authenticate.
6. **Try a different MCP package.** The one you tried may not support your environment. Search npm for alternatives.
7. **Restart Claude Code.** `Shift+Cmd+P` → "Developer: Reload Window". New MCP configs only load on restart. Channel/user caches only refresh on restart.

If none of this works, describe what you see (or don't see) and what you've tried. There is always a path through.
