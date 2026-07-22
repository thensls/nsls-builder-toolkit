---
name: setup
description: >-
  Onboarding for the NSLS Builder Toolkit. Confirms the builder email so the
  tracker can credit work, connects org tools one at a time (Slack, Google
  Drive, Google Calendar, Gmail, Fathom), verifies plugins, registers Windows
  hooks, checks GCP/gws access, and offers personal productivity setup.
  Use when first setting up, or when a tool connection seems broken.
---

# NSLS Builder Toolkit — Setup

Walk the new builder through getting connected. **This is a guided, hand-held
experience, not a checklist you hand them.** Golden rules for the whole skill:

- **One thing at a time.** Ask one question, wait for the answer, then move on.
  Never print a wall of steps for the builder to execute themselves.
- **Open or link the exact page.** Never say "go to settings → MCP Servers."
  Instead, tell them precisely what to click, or (better) send them to the exact
  Connectors panel and wait.
- **Plain words, no jargon.** "the long code on that page," not "the OAuth
  bearer token." Describe what they'll see on screen.
- **Detect first, ask second.** If something is already done, say so and skip it.

Show the roadmap upfront so the builder knows the shape:

```
Welcome to the NSLS Builder Toolkit! Let's get you set up.

This takes about 5 minutes, and I'll do it with you one step at a time:
  1. Confirm your builder email (so the tracker can credit your work)
  2. Connect your tools — Slack, Google Drive, Calendar, Gmail, Fathom
  3. Check your plugins are working
  4. Register Windows hooks (Windows only — skipped on Mac/Linux)
  5. Personal productivity skills (optional, your call)

Ready?
```

## Step 1: Confirm Your Builder Email (~15 sec)

The session-start hook (daily session points + PR credit) and the skill-use
hook both read `BUILDER_EMAIL` from
`~/.claude/local-plugins/nsls-personal-toolkit/.env`. Without it, your work
shows up as "unknown" in the Automation Tracker and you don't get credit.

**Don't make the builder type their email.** You already know the email of the
signed-in Claude account from this session's context — propose it and ask only
to confirm:

```
I'll credit your work to <signed-in account email>. Sound right? (yes / or paste a different email)
```

Only fall back to free-text entry if they say the signed-in address is wrong
(e.g. they use an alias). If `/personal-setup` already set BUILDER_EMAIL, this
is a no-op — check first:

```bash
ENV_FILE="$HOME/.claude/local-plugins/nsls-personal-toolkit/.env"
if [ -f "$ENV_FILE" ] && grep -q "^BUILDER_EMAIL=" "$ENV_FILE"; then
  echo "ALREADY_SET: $(grep '^BUILDER_EMAIL=' "$ENV_FILE" | cut -d= -f2-)"
fi
```

If not set (or they gave a different one), write it — preserving any other env
vars in the file (JSONB-style merge; never clobber the file):

```bash
ENV_FILE="$HOME/.claude/local-plugins/nsls-personal-toolkit/.env"
mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
{ grep -v "^BUILDER_EMAIL=" "$ENV_FILE" || true; } > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
echo "BUILDER_EMAIL=<confirmed email>" >> "$ENV_FILE"
```

Confirm, and be transparent about the one bit of tracking so it never feels
hidden: "Got it — your work is now credited to <email>. Heads up: each time you
use a skill, the toolkit fires a tiny one-line ping to our NSLS tracker so you
get credit for it — just the skill name and your email, nothing about what you
were doing. You'll see it noted in the status line as it runs. That's the only
thing it phones home about." (If a permission prompt for `skill-event.sh` ever
appears, that's this same harmless ping — safe to approve; the installer
allowlists it so it shouldn't recur.)

### Step 1.5: Reconcile early events (automatic, silent — no question)

The installer fires an install event (and skill events can fire) **before**
`/setup` runs, attributed to a fallback identity (git email → `$USER@host`).
Now that the real BUILDER_EMAIL is set, tell the tracker to merge those early
events onto the right builder. Recompute the *previous* identity by re-running
the same fallback chain the early events used, then POST the reconcile. Skip
silently if they match, and never block setup on it:

```bash
NEW_EMAIL="<confirmed email>"
PREV_EMAIL=$(git config user.email 2>/dev/null || true)
[ -z "$PREV_EMAIL" ] && PREV_EMAIL="${USER:-unknown}@$(hostname -s 2>/dev/null || echo unknown)"
if [ -n "$NEW_EMAIL" ] && [ "$PREV_EMAIL" != "$NEW_EMAIL" ]; then
  # Contract matches the tracker service's handler (POST /reconcile-builder,
  # body {previous_email,new_email}). Server-side it's idempotent and no-ops when
  # the emails match or no provisional row exists, so this is safe to re-run.
  # Best-effort — a 404/timeout must never block setup.
  curl -s --max-time 40 -X POST \
    ${NSLS_TRACKER_URL:-https://web-production-6281e.up.railway.app}/reconcile-builder \
    -H 'Content-Type: application/json' \
    -d "{\"previous_email\":\"$PREV_EMAIL\",\"new_email\":\"$NEW_EMAIL\"}" \
    >/dev/null 2>&1 || true
fi
```

Don't mention this to the builder unless they ask — it's plumbing.

## Step 2: Connect Your Tools (~2 min) — guided, one at a time

This is the most important step and the one builders stall on. **Do NOT dump a
list of settings paths.** Connect the recommended starter bundle **one connector
at a time**, each a connect-now-or-defer choice. For each: say one line on *why*,
send them to the exact Connectors panel, wait, then verify with a live read call
and confirm before moving to the next.

All five are **one-click "Authorize" connectors** in the desktop app — no API
keys, no tokens to paste. The bundle, in order:

1. **Slack** — team channels, standups, searches
2. **Google Drive** — read/write docs and files
3. **Google Calendar** — powers `/open-day`'s daily schedule
4. **Gmail** — draft and triage email
5. **Fathom** — meeting recordings and transcripts (`/close-day`, `person-intelligence`)

> **Do not rely on a programmatic MCP-registry probe to decide what's
> available** — a probe has missed Fathom even though its connector exists
> (user-verified 2026-07-21). Always send the builder to the Connectors panel
> and confirm by an actual read call, not by a registry lookup.

For each connector, run this loop:

1. **One line on why**, then ask: "Want to connect **<tool>** now? (yes / skip)"
   - If skip: "No problem — you can add it anytime by running /setup again." Move on.
2. **If yes, send them to the exact panel** (don't name a settings path — tell
   them what to click):
   ```
   In the desktop app, open Settings → Connectors, find <tool>, and click
   Authorize. A browser window opens for you to sign in — approve it, and you're done.
   ```
3. **⚠️ Home-tab gotcha — print this every time:**
   ```
   Heads up: after you authorize, the app often drops you back on the Home tab
   and it looks like you lost this chat. You didn't — just click **Code** (top
   left) to come back here, and tell me when you're back.
   ```
4. **Wait** for them to confirm they're back.
5. **Verify with a live read call** (not a registry probe). Examples:
   - Slack: read your own identity from the Slack MCP tool descriptions
     ("Current logged in user's Slack user_id is U…").
   - Google Drive: a minimal Drive search/list call.
   - Google Calendar: `list_calendars`.
   - Gmail: `list_labels` (or a minimal thread search).
   - Fathom: `get_identity` / `list_meetings` (via the `api.fathom.ai` path).
6. **Confirm result**, then next:
   - Works: "✓ <tool> is connected — you're [name/detail]."
   - Still not showing: "Not seeing <tool> yet — that usually means the
     Authorize window didn't finish. Want to try once more, or skip for now?"

After the loop, a short summary:

```
Connected: [the ones that verified]
Skipped:   [the ones deferred] — run /setup anytime to add these.
```

Don't block on skipped tools — org skills that don't need them work right now.

**API keys are the fallback only for vendors with no connector.** If you ever
hit a key path for Fathom, note the old `fathom.video/settings/api` deep link
404s — say "open fathom.video → Settings → API Access" instead, and validate the
key with a live `api.fathom.ai` call.

## Step 3: Verify Plugins (~30 sec)

Check that superpowers is installed by looking for its skills (e.g.,
`verification-before-completion`, `brainstorming`).

- **Installed**: "Superpowers is working — you have /brainstorm, /debug, /verify, /plan."
- **Not installed** — offer to do it, don't hand them a terminal command to run
  blind:
  ```
  Superpowers isn't installed yet. I can install it for you — want me to?
  ```
  If yes, run `claude plugin install superpowers` for them, then tell them to
  restart Claude Code and run /setup again.

Do NOT check for compound-engineering — it's an optional power-up.

## Step 4: Register Windows Hooks (Windows only, ~10 sec)

On Windows the whole install runs through `install.ps1` (a full native
PowerShell installer mirroring `install.sh` — clone, enable, hooks, install-event,
MCP, pointers), because the bundled `hooks/hooks.json` uses `python3`/`bash`
which Windows lacks. A Windows builder installs with the PowerShell command
(see the guide), not `curl … | bash`. If they already installed but the hooks
seem missing, re-running `install.ps1` re-registers them idempotently.

Detect platform:

```bash
case "$OSTYPE" in
  msys*|cygwin*|win32*) echo "windows" ;;
  *) echo "not-windows" ;;
esac
```

**If macOS or Linux**: skip silently — the bash hooks work natively.

**If Windows**: run the installer for them:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.claude\local-plugins\nsls-builder-toolkit\install.ps1"
```

Then tell the builder (one message, not a checklist):

```
Windows hooks registered — your session pings and skill use will show up in the
tracker after your next Claude Code restart.
```

Idempotent — re-running replaces only the NSLS entries, preserving everything
else. Safe any time the hooks seem broken.

## Step 5: GCP + Google Docs access (optional)

Ask (one question):

```
Do you need to create Google Cloud projects for your automations? (yes / no)
```

If yes:
```
You'll need to be in the gcp-builders@nsls.org group. Ask Kevin (or any group
owner) to add you. Once you're in, create projects under the "Builder Projects"
folder at console.cloud.google.com/projectcreate.
```

If no: move on.

### Google Docs editing (gws auth) — optional

`/gdoc-edit` and `/gdoc-build` run on `gws` (installed by the toolkit installer).
They need a one-time `gws auth login`. Check state:

```bash
gws auth status 2>/dev/null | grep -q '"storage": "none"' && echo "gws NOT authed" || echo "gws authed (or missing)"
```

- **Already authed**: "Google Docs skills are ready."
- **Not authed** — don't run the OAuth flow for them (it mints *their* token).
  Point them at the setup doc and offer to walk them through it live:
  ```
  To edit/create Google Docs from Claude, there's a one-time sign-in. I can walk
  you through it now, or you can do it later — it's in the /gdoc-edit setup notes.
  ```

## Step 6: Personal productivity (optional)

Pitch it, then let them choose the depth. **Two tiers:**

```
Last thing — the builders who get the most out of this toolkit use the personal
productivity skills: morning planning, end-of-day summaries, weekly reviews.

There are two ways in:
  • Light (~3 min) — works immediately, just a notes folder. Recommended to start.
  • Advanced — full Obsidian vault + plugins + graph view. Great, but more setup;
    you can add it anytime.

Want to set up the light version now? (yes / later)
```

`/personal-setup` exists the moment the toolkit is installed (it ships as a thin
bootstrapper in this org kit), so **"say /personal-setup anytime later" is a
real, working command** — no "unknown command" trap for anyone who defers.

### If yes:
Invoke `/personal-setup` — it installs+enables the personal kit if needed, syncs
its pointer skills immediately, and runs the light config. If it needs the full
personal kit and a restart, tell them plainly and hand off.

### If later:
```
No problem. Say /personal-setup anytime — it works right now, no install needed
first.
```

## Edge Cases

- **Re-running /setup after everything is configured**: detect state, confirm
  it's all good, offer /personal-setup. Steps 1 and 4 are idempotent.
- **Personal-toolkit clone into a dir that already holds `.env`**: `/personal-setup`
  handles this by preserving the existing `.env` across the clone (Step 1 may
  have written BUILDER_EMAIL there before the toolkit was cloned). Never `git
  clone` into a non-empty dir and assume success.
- **User isn't an NSLS employee**: org toolkit still works; set the email anyway,
  hooks degrade gracefully.
- **Windows builder skipped Step 4**: zero pings / zero skill events, counters
  stuck at 0. Re-run /setup, or `install.ps1` directly.
