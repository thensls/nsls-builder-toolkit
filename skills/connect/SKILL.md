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

**What:** Team messaging, channels, search.
**Skills that use it:** `/slack`
**Prerequisite:** Slack workspace admin must create a Slack app. Non-admins cannot do this step — ask your admin.

#### Connection: stdio with bot token (VS Code / Cursor)
**MCP type:** stdio (npx)
**Auth:** Bot User OAuth Token (`xoxb-`)

1. Go to api.slack.com/apps → Create New App → From scratch
2. Name: `Claude Code MCP`, Workspace: select yours
3. OAuth & Permissions → Bot Token Scopes → add ALL read scopes available. Key ones: `channels:read`, `channels:history`, `groups:read`, `groups:history`, `im:read`, `im:history`, `mpim:read`, `mpim:history`, `users:read`, `users.profile:read`, `search:read`, `reactions:read`, `files:read`, `pins:read`, `bookmarks:read`, `links:read`, `metadata.message:read`, `reminders:read`, `team:read`, `usergroups:read`, `users:read.email`. Browse the full list — add any scope with "read" in the name. This is a starting point, not a ceiling.
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

No config file changes needed. But this approach is limited to claude.ai web sessions.

---

### Braintrust

**What:** AI evaluation and observability.
**Skills that use it:** `/braintrust-evals`

**Not an MCP integration.** Braintrust is an SDK — `braintrust` npm package — called directly by Claude Code. No MCP server, no config file entry, no `mcpServers` block.

To use: `npm install braintrust` in your project, set `BRAINTRUST_API_KEY` as an environment variable.

---

### Snowflake

**What:** Data warehouse.
**No seed yet.** If you have Snowflake access, help the `/connect` skill by trying available MCP packages and documenting what works.

---

### HubSpot

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
