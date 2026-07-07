---
name: setup
description: >-
  Onboarding for the NSLS Builder Toolkit. Sets the builder email so the
  tracker hooks can attribute work, registers the PowerShell hooks on
  Windows, connects org tools (Slack, Asana, Google Calendar), verifies
  plugins, checks GCP access, and offers personal productivity setup.
  Use when first setting up, or when a tool connection seems broken.
---

# NSLS Builder Toolkit — Setup

Walk the new builder through getting their tools connected. Detect what's already working and only ask about what's missing. Keep it friendly and fast.

Show the roadmap upfront so the builder knows the shape:

```
Welcome to the NSLS Builder Toolkit! Let's get you set up.

This takes about 5 minutes:
  1. Set your builder email (so the tracker can credit your work)
  2. Connect your tools (Slack, Asana, Google Calendar)
  3. Verify plugins are working
  4. Register Windows hooks (Windows only — auto-skipped on Mac/Linux)
  5. Check GCP access (if you need it)
  6. Done — here's what you can do now

Ready?
```

## Step 1: Set Your Builder Email (~30 sec)

The session-start hook (daily session points + PR credit) and the PreToolUse skill hook (per-skill-use tracking) both read `BUILDER_EMAIL` from `~/.claude/local-plugins/nsls-personal-toolkit/.env`. Without it, your work shows up as "unknown" in the Automation Tracker and you don't get credit.

`/personal-setup` also sets this — so if the builder has already run that, this step is a no-op. Check first:

```bash
ENV_FILE="$HOME/.claude/local-plugins/nsls-personal-toolkit/.env"
if [ -f "$ENV_FILE" ] && grep -q "^BUILDER_EMAIL=" "$ENV_FILE"; then
  echo "BUILDER_EMAIL already set — skipping."
fi
```

If not set, ask:

```
What's your NSLS email? (e.g., you@nsls.org)
```

Then write it (preserves any other env vars in the file, creates parent dir if needed):

```bash
ENV_FILE="$HOME/.claude/local-plugins/nsls-personal-toolkit/.env"
mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"
# Strip any existing BUILDER_EMAIL line, then append the new one.
{ grep -v "^BUILDER_EMAIL=" "$ENV_FILE" || true; } > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE"
echo "BUILDER_EMAIL=<email>" >> "$ENV_FILE"
```

Confirm to the builder: "BUILDER_EMAIL set. Your skill use and session pings will now be attributed correctly."

## Step 2: Connect Your Tools (~2 min)

Check which MCP integrations are available. Try each one — if it works, check it off. If it fails, note it as missing.

### Slack
Try to detect the user's Slack identity from the Slack MCP tools. The tool descriptions usually include "Current logged in user's Slack user_id is U...".

- **Connected**: "Slack is connected — you're [name/ID]"
- **Not connected**: "Slack isn't connected. You can add it in Claude Code settings → MCP Servers → Slack. This is needed for /standup and channel searches."

### Asana
Try calling the Asana MCP to get the user's info:
```
mcp__claude_ai_Asana__get_me()
```

- **Connected**: "Asana is connected — you're [name] in [workspace]"
- **Not connected**: "Asana isn't connected. Add it in Claude Code settings → MCP Servers → Asana. Needed for task tracking in /open-day and /close-day."

### Google Calendar
Try calling:
```
mcp__claude_ai_Google_Calendar__gcal_list_calendars()
```

- **Connected**: "Google Calendar is connected"
- **Not connected**: "Google Calendar isn't connected. Add it in Claude Code settings → MCP Servers → Google Calendar. Used by /open-day for daily schedule."

Show a quick summary after checking:

```
Tool Status:
  [check or x] Slack
  [check or x] Asana
  [check or x] Google Calendar

[If any missing]: You can add these anytime in Claude Code settings.
The org skills that don't need these tools will work fine right now.
```

Don't block on missing tools — most org skills work without them.

## Step 3: Verify Plugins (~1 min)

Check that superpowers is installed by looking for its skills (e.g., `verification-before-completion`, `brainstorming`).

- **Installed**: "Superpowers plugin is working — you have /brainstorm, /debug, /verify, /plan"
- **Not installed**:
  ```
  Superpowers plugin isn't installed. Run this in your terminal:

    claude plugins install superpowers

  Then restart Claude Code and run /setup again.
  ```

Do NOT check for compound-engineering — it's an optional power-up, not required.

## Step 4: Register Windows Hooks (Windows only, ~10 sec)

The canonical `hooks/hooks.json` uses `python3` (SessionStart) and `bash` (PreToolUse skill logging) — neither runs natively on Windows. There's an `install.ps1` script in the toolkit root that registers the PowerShell equivalents (`session-start.ps1` and `skill-event.ps1`) in `~/.claude/settings.json`.

Detect platform first. The simplest check:

```bash
case "$OSTYPE" in
  msys*|cygwin*|win32*) echo "windows" ;;
  *) echo "not-windows" ;;
esac
```

Or from inside Claude Code's tooling, use whichever platform detection is handy — the script's idempotent, so a false positive run on Mac/Linux is harmless (it'd just print "Registered..." and not affect anything because settings.json on those platforms doesn't use these hook entries).

**If macOS or Linux**: Skip silently — the bash hooks in `hooks/hooks.json` work natively.

**If Windows**: Run the installer:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.claude\local-plugins\nsls-builder-toolkit\install.ps1"
```

Tell the builder:

```
Windows hooks registered:
  SessionStart → session-start.ps1 (pull + sync + ping)
  PreToolUse(Skill) → skill-event.ps1 (per-skill-use tracking)

These take effect after your next Claude Code restart. Until then, your
skill use won't show up in the Automation Tracker.
```

The script is **idempotent** — re-running replaces only the NSLS entries in settings.json, preserving everything else. Safe to run any time the hooks seem broken (e.g., `signal_*` MCP tools won't fire either if the SessionStart hook isn't pulling updates).

## Step 5: Check GCP Access (~1 min)

Ask the builder:
```
Do you need to create Google Cloud projects for your automations?

This is needed if you're building anything that uses Google APIs — OAuth flows,
Apps Script triggers, service accounts, etc. If you're just using Claude Code
with Slack/Asana/Airtable, you can skip this.
```

If yes:
```
To create GCP projects, you need to be in the gcp-builders@nsls.org group.
Ask Kevin (or any group owner) to add you — it's one command:

  gcloud identity groups memberships add \
    --group-email="gcp-builders@nsls.org" \
    --member-email="YOUR_EMAIL@nsls.org" \
    --roles=MEMBER

Once added, go to console.cloud.google.com/projectcreate and select
the "Builder Projects" folder as your parent resource. That's where
you have permission to create projects.

Personal automations (email triage, personal workflows) → your own project.
Org-owned automations → use the shared nsls-automations project.
```

If no or skip: move on.

## Step 6: Wrap Up + Pitch Personal Productivity

```
You're set up! Here's what you can do:

ORG SKILLS:
  /register-automation  — Track your builds in the Automation Tracker
  /product-design       — UX guardrail with DESIGN.md and focus groups
  /nsls-slides          — Branded NSLS/Society presentations
  /gws                  — Google Workspace operations
  /web-research         — Structured web research
  ... type / to see all available skills

WORKFLOW:
  Superpowers gives you /brainstorm, /debug, /verify, /plan

OPTIONAL POWER-UPS:
  Compound Engineering adds advanced planning/review workflows
  (/ce-brainstorm, /ce-plan, /ce-code-review, /ce-doc-review). Ask me how to install it.

ORG CONTEXT:
  Your toolkit includes current org chart, LOPs, and company strategy.
  Skills can reference these automatically — no setup needed.
  See: _shared/context/ in the toolkit repo.
```

Then pitch personal productivity:

```
One more thing — the builders who get the most out of this toolkit
use the personal productivity skills. They turn Claude into a daily
co-pilot: morning planning, end-of-day summaries, weekly reviews.

Think of it as making work fun again — bringing ease to your day.

It takes about 10 minutes to set up. Want to do it now?
Say /personal-setup anytime if you'd rather do it later.
```

### If yes and personal toolkit is already installed:
Invoke `/personal-setup` inline — don't make them restart.

### If yes and personal toolkit is NOT installed:
Install the personal toolkit:
```bash
bash -c 'PLUGIN_DIR="$HOME/.claude/local-plugins/nsls-personal-toolkit"; \
  REPO_URL="https://github.com/thensls/nsls-personal-toolkit.git"; \
  if [ -d "$PLUGIN_DIR" ]; then \
    git -C "$PLUGIN_DIR" pull --ff-only 2>/dev/null || true; \
    echo "Personal toolkit updated."; \
  else \
    mkdir -p "$(dirname "$PLUGIN_DIR")"; \
    git clone "$REPO_URL" "$PLUGIN_DIR" --quiet; \
    echo "Personal toolkit installed."; \
  fi'
```

Then enable it in settings.json:
```bash
python3 -c "
import json, os
settings_path = os.path.expanduser('~/.claude/settings.json')
with open(settings_path) as f: cfg = json.load(f)
ep = cfg.setdefault('enabledPlugins', {})
ep['nsls-personal-toolkit@local'] = True
with open(settings_path, 'w') as f: json.dump(cfg, f, indent=2)
print('Enabled nsls-personal-toolkit in settings.json')
"
```

Then tell the builder:

```
Personal toolkit installed! You'll need to start a new Claude Code
session for the skills to load. When you're back, say /personal-setup
to finish configuration (~10 min).
```

There is currently no way to reload skills without restarting the session. If Claude Code adds a reload command in the future, use that instead.

### If no:

```
No problem. The org toolkit is fully set up — you're ready to build.

If you change your mind later, install the personal toolkit with:
  curl -fsSL https://raw.githubusercontent.com/thensls/nsls-personal-toolkit/main/install.sh | bash
```

## Edge Cases

- **User runs /setup again after everything is configured**: Check state, confirm everything is good, offer to run /personal-setup if they want to reconfigure. Re-running Step 1 (email) and Step 4 (Windows hooks) is idempotent — both detect existing state and skip / no-op.
- **Git clone fails (network/permissions)**: Show the error, suggest they clone manually and point to the GitHub repo URL.
- **User isn't an NSLS employee**: The org toolkit still works — skip NSLS-specific references and note that some skills reference NSLS-specific resources. The Automation Tracker won't have a record for them, so Step 1's email is moot — set it anyway in case they get one later; the hooks degrade gracefully.
- **Personal toolkit already installed**: Skip the clone, just offer /personal-setup.
- **Windows builder skipped Step 4 by accident**: They'll have zero session pings and zero skill_used events in the tracker. Symptoms: their dashboard counters stay at 0, their stage never advances. Re-run /setup, or directly: `powershell -NoProfile -ExecutionPolicy Bypass -File "$HOME\.claude\local-plugins\nsls-builder-toolkit\install.ps1"`
