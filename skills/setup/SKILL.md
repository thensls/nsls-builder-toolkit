---
name: setup
description: >-
  Onboarding for the NSLS Builder Toolkit. Connects org tools (Slack, Asana,
  Google Calendar), verifies plugins, checks GCP access, and offers personal
  productivity setup. Use when first setting up, or when a tool connection
  seems broken.
---

# NSLS Builder Toolkit — Setup

Walk the new builder through getting their tools connected. Detect what's already working and only ask about what's missing. Keep it friendly and fast.

Show the roadmap upfront so the builder knows the shape:

```
Welcome to the NSLS Builder Toolkit! Let's get you set up.

This takes about 5 minutes:
  1. Connect your tools (Slack, Asana, Google Calendar)
  2. Verify plugins are working
  3. Check GCP access (if you need it)
  4. Done — here's what you can do now

Ready?
```

## Step 1: Connect Your Tools (~2 min)

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

## Step 2: Verify Plugins (~1 min)

Check that superpowers is installed by looking for its skills (e.g., `verification-before-completion`, `brainstorming`).

- **Installed**: "Superpowers plugin is working — you have /brainstorm, /debug, /verify, /plan"
- **Not installed**:
  ```
  Superpowers plugin isn't installed. Run this in your terminal:

    claude plugins install superpowers

  Then restart Claude Code and run /setup again.
  ```

Do NOT check for compound-engineering — it's an optional power-up, not required.

## Step 3: Check GCP Access (~1 min)

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

## Step 4: Wrap Up + Pitch Personal Productivity

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
  (/ce:brainstorm, /ce:plan, /ce:review). Ask me how to install it.

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

- **User runs /setup again after everything is configured**: Check state, confirm everything is good, offer to run /personal-setup if they want to reconfigure.
- **Git clone fails (network/permissions)**: Show the error, suggest they clone manually and point to the GitHub repo URL.
- **User isn't an NSLS employee**: The org toolkit still works — skip NSLS-specific references and note that some skills reference NSLS-specific resources.
- **Personal toolkit already installed**: Skip the clone, just offer /personal-setup.
