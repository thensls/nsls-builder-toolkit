---
name: setup
description: >-
  Onboarding for the NSLS Builder Toolkit. Verifies org tool connections
  (Slack, Asana, Google Calendar), installs superpowers and compound-engineering
  plugins if missing, and optionally installs personal productivity skills.
  Use when first setting up, or when a tool connection seems broken.
---

# NSLS Builder Toolkit — Setup

Walk the new builder through getting their tools connected. Detect what's already working and only ask about what's missing. Keep it friendly and fast.

## Phase 1: Check Plugin Health

Check that the three plugin sources are installed and enabled:

1. **NSLS Builder Toolkit** (this plugin) — should be working if they're running /setup
2. **Superpowers** — check if available by looking for superpowers skills (e.g., `verification-before-completion`, `brainstorming`)
3. **Compound Engineering** — check if available by looking for compound-engineering skills (e.g., `ce:brainstorm`, `ce:plan`, `ce:review`)

If superpowers or compound-engineering skills aren't showing up, tell the user:

```
It looks like [plugin] isn't installed yet. Run this in your terminal:

  claude plugins install superpowers

  # For compound-engineering:
  claude plugins marketplace add https://github.com/EveryInc/compound-engineering-plugin.git
  claude plugins install compound-engineering@every-marketplace

Then restart Claude Code and run /setup again.
```

If all three are present, confirm:
```
Your plugins are all set:
  NSLS Builder Toolkit — org skills for building, deploying, presenting
  Superpowers — planning, debugging, verification workflows
  Compound Engineering — brainstorm → plan → build → review pipeline
```

## Phase 2: Check Tool Connections

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

### Google Cloud Platform (GCP)

Check if the builder has GCP project creation access. This is needed for automations that use Google APIs (OAuth, Apps Script, service accounts).

Ask the user:
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

If no or skip: move on — this doesn't block any other setup.

### Summary

After checking all tools, show a summary:

```
Tool Status:
  [check or x] Slack
  [check or x] Asana
  [check or x] Google Calendar
  [check or x] GCP Access (if requested)

[If any missing]: You can add these anytime in Claude Code settings.
The org skills that don't need these tools will work fine right now.

[If all connected]: All tools connected. You're ready to build.
```

Don't block on missing tools — most org skills work without them. Just let the user know what they'll need for specific skills.

## Phase 3: Offer Personal Productivity Skills

After the org setup is complete, ask:

```
One more thing — would you like to set up personal productivity skills too?

These are separate from the org toolkit. They're Kevin's personal workflow
template — daily planning, end-of-day summaries, weekly reviews, project
logging, and relationship tracking.

They're yours to customize. Edit anything, delete what you don't use,
or resync with Kevin's template later if he adds something useful.

Skills included:
  /open-day            — Morning planning (calendar, tasks, priorities)
  /close-day           — End-of-day summary (what happened, what's next)
  /close-week          — Friday weekly roll-up
  /log                 — Log session progress to project notes
  /familiar            — Recall past screen activity
  /person-intelligence — Relationship profiles and 1:1 context
  /obsidian-setup      — Set up an Obsidian knowledge base

Want to install these? (You can always do this later by running the
personal toolkit installer separately.)
```

### If yes:

Install the personal toolkit by running:
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

After installing, run the personal toolkit configuration inline — don't make them restart. Follow the same flow as the personal toolkit's `/personal-setup` skill:

1. **Slack User ID** — already detected in Phase 2, reuse it
2. **Asana GIDs** — already detected in Phase 2, reuse them
3. **Fathom API key** — ask the user:
   ```
   Do you use Fathom (fathom.video) for meeting recording?

   If yes, your API key lets /close-day pull today's meeting summaries
   and /person-intelligence pull 1:1 transcripts.

   To get your key:
   1. Go to https://fathom.video/settings/api
   2. Copy your API key
   3. Paste it here

   Or skip this — /close-day works without it (just won't have meeting summaries).
   ```

   If provided, validate with a test call:
   ```bash
   curl -s -H "X-Api-Key: <key>" "https://api.fathom.ai/external/v1/meetings?created_after=$(date +%Y-%m-%d)T00:00:00Z" | head -c 100
   ```

4. **Airtable API key** — ask the user:
   ```
   Your Airtable API key is only needed for /person-intelligence (relationship profiles).

   To create one:
   1. Go to airtable.com/create/tokens
   2. Create a token with scopes: data.records:read, data.records:write, schema.bases:read
   3. Add access to the People Ops base
   4. Paste it here (starts with "pat...")

   Or skip this — you can add it later by running /personal-setup.
   ```

5. Write the `.env` file to `~/.claude/local-plugins/nsls-personal-toolkit/.env`

6. Confirm:
   ```
   Personal productivity skills installed and configured!

   Try it out:
     "open my day" — morning planning
     "close my day" — end-of-day summary

   These skills live in ~/.claude/local-plugins/nsls-personal-toolkit/
   Edit anything — they're yours. To pull Kevin's latest template changes:
     cd ~/.claude/local-plugins/nsls-personal-toolkit
     git remote add upstream https://github.com/thensls/nsls-personal-toolkit.git
     git fetch upstream && git diff upstream/main

   You'll need to restart Claude Code for the new skills to appear.
   ```

### If no:

```
No problem. The org toolkit is fully set up — you're ready to build.

If you change your mind later, install the personal toolkit with:
  curl -fsSL https://raw.githubusercontent.com/thensls/nsls-personal-toolkit/main/install.sh | bash
```

## Phase 4: Wrap Up

```
Setup complete! Here's what you can do now:

ORG SKILLS (always available):
  /register-automation  — Track your builds in the Automation Tracker
  /product-design       — UX guardrail with DESIGN.md and focus groups
  /nsls-focus-group     — Test ideas with simulated employee panels
  /nsls-slides          — Branded NSLS/Society presentations
  /deployment-guide     — How to deploy to Railway, Airtable, GAS, etc.
  /web-research         — Structured web research
  /gws                  — Google Workspace operations
  ... and more — type / to see all available skills

WORKFLOW PLUGINS:
  Superpowers gives you: /brainstorm, /debug, /verify, /plan
  Compound Engineering gives you: /ce:brainstorm, /ce:plan, /ce:review

Start building something and use /register-automation to track it!
```

## Edge Cases

- **User runs /setup again after everything is configured**: Check state, confirm everything is good, offer to reconfigure the personal toolkit .env if needed.
- **Git clone fails (network/permissions)**: Show the error, suggest they clone manually and point to the GitHub repo URL.
- **User isn't an NSLS employee**: The org toolkit still works — skip NSLS-specific Airtable base IDs and note that some skills reference NSLS-specific resources.
- **Personal toolkit already installed**: Skip the clone, just offer to reconfigure the .env.
