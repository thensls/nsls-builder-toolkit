# Builder Onboarding Redesign + Org Context Sync

**Date**: 2026-04-13
**Author**: Kevin Prentiss
**Status**: Approved

## Problem

The current builder onboarding has three issues:

1. **Too much in one pass.** `/setup` tries to do org tools, plugin health, and personal productivity in a single flow. New builders hit decision fatigue before they reach the payoff.
2. **Compound Engineering install is flaky.** The two-step marketplace-add-then-install flow breaks often enough that it shouldn't be in the critical path.
3. **Org context requires individual API keys.** Builders who want org chart, LOPs, or strategy context need an Airtable API key provisioned by Kevin. The People Ops base contains sensitive data (journals, quick notes), so keys can't be freely distributed. This bottleneck gets worse as the builder program grows (55 builders today).

## Solution

Two changes, shipped together:

### Part 1: Org Context Sync

Sync org data from Airtable and Google Docs into markdown files committed to the builder toolkit repo. Builders get current org context automatically via the existing SessionStart auto-pull. No API keys, no setup, no permissions requests.

#### Files

| File | Location | Source | Refresh Schedule |
|------|----------|--------|-----------------|
| `org-chart.md` | `_shared/context/org-chart.md` | People Ops Airtable — Employees table | Weekly (Sunday night cron) |
| `lops.md` | `_shared/context/lops.md` | People Ops Airtable — L2 Goals + L2 Goal Updates tables | Biweekly (matches LOP update cycle) |
| `strategy.md` | `_shared/context/strategy.md` | Google Doc `1EOOTdKLV0j1MnpHV_hwNx4hbcOiHTjjKdo5h7UCZBYo` | Manual trigger (quarterly, after SLT approval) |

#### Org Chart Format

```markdown
# NSLS Org Chart
_Last synced: 2026-04-13_

## Marketing
| Name | Title | Manager | Email | Slack |
|------|-------|---------|-------|-------|
| Jane Doe | Director of Marketing | Gary Tuerack | jdoe@nsls.org | U0ABC123 |
| ... | ... | ... | ... | ... |

## Product
...
```

Grouped by department. Sorted by manager hierarchy within each department.

#### LOPs Format

```markdown
# Lines of Priority (LOPs)
_Last synced: 2026-04-13_

## L1: Core Program Revenue
**Owner**: [Name] | **Health**: Green
> Latest update: On track for $35.2M. Q1 actuals at $8.9M.

## L2: Ignite Adoption
**Owner**: [Name] | **Health**: Yellow
> Latest update: Profile completion at 22%, below 25% target. New onboarding flow shipping next week.

...
```

#### Strategy Format

```markdown
# NSLS 2025-2026 Strategy
_Last synced: 2026-04-13_
_Source: [Google Doc](https://docs.google.com/document/d/1EOOTdKLV0j1MnpHV_hwNx4hbcOiHTjjKdo5h7UCZBYo/edit)_

> For Internal Use Only. This document is the private intellectual property of NSLS and must not be shared outside the organization.

[Full strategy content as markdown]
```

#### GitHub Action

File: `.github/workflows/sync-org-context.yml`

**Triggers**:
- `schedule`: Weekly (Sunday 11 PM ET) for org chart, biweekly for LOPs
- `workflow_dispatch`: Manual trigger for strategy sync (with input to select which file to sync)

**Secrets needed**:
- `AIRTABLE_API_KEY` — Kevin's key, scoped to People Ops read-only
- No secret needed for Google Docs — uses the gws CLI or a service account

**Sync script**: Python script at `_shared/scripts/sync_org_context.py` that:
1. Fetches data from Airtable (org chart, LOPs) or Google Docs (strategy)
2. Renders markdown using the formats above
3. Writes to `_shared/context/`
4. Script is called by the GitHub Action; can also be run locally

**Commit behavior**: The action commits only if files changed. Commit message: `sync: org-chart 2026-04-13` (or `lops` or `strategy`). This gives free change-over-time tracking in git history.

#### What This Replaces

- Airtable API key is **no longer needed** for reading org context. Removed from `/personal-setup` as a required or suggested step.
- Person-intelligence and any skill that needs org data reads from `_shared/context/` instead of making live Airtable API calls.
- Airtable API key is still available as an optional config for builders who need to **write** to Airtable (rare).

### Part 2: Onboarding Redesign

Split the monolithic `/setup` into two focused flows with clear sequencing and time estimates.

#### Install Script Changes

The `curl | bash` install script changes:
- **Keep**: Org toolkit clone + enable
- **Keep**: Superpowers install
- **Remove**: Compound Engineering auto-install (move to optional mention in wrap-up)
- **Keep**: Slash-command pointer sync
- **Keep**: "Start a new session and say `/setup`" (skills don't load until session restart — no workaround currently)

#### `/setup` — Org Tools (~5 min)

Streamlined to four steps, shown upfront:

```
Welcome to the NSLS Builder Toolkit! Let's get you set up.

This takes about 5 minutes:
  1. Connect your tools (Slack, Asana, Google Calendar)
  2. Verify plugins are working
  3. Check GCP access (if you need it)
  4. Done — here's what you can do now

Ready?
```

**Step 1: Connect tools**
Same as today — auto-detect Slack, Asana, Google Calendar via MCP. Show connected/not-connected status. Don't block on missing tools.

**Step 2: Verify plugins**
Check superpowers is installed. If not, give install command. Do NOT check compound-engineering — it's not in the critical path.

**Step 3: GCP access**
Same as current (added 2026-04-13). Ask if they need GCP project creation, point to `gcp-builders@nsls.org` group if yes.

**Step 4: Wrap up + pitch personal productivity**

```
You're set up! Here's what you can do:

ORG SKILLS:
  /register-automation  — Track your builds
  /product-design       — UX guardrail with DESIGN.md
  /nsls-slides          — Branded presentations
  /gws                  — Google Workspace operations
  ... type / to see all

WORKFLOW:
  Superpowers gives you /brainstorm, /debug, /verify, /plan

OPTIONAL POWER-UPS:
  Compound Engineering adds advanced workflows (/ce:brainstorm,
  /ce:plan, /ce:review). Ask me how to install it if you want it.

ORG CONTEXT:
  Your toolkit includes current org chart, LOPs, and strategy.
  Skills can reference these automatically — no setup needed.
```

Then pitch personal productivity:

```
One more thing — the builders who get the most out of this toolkit
use the personal productivity skills. They turn Claude into a daily
co-pilot: morning planning, end-of-day summaries, weekly reviews.

It takes about 10 minutes to set up. Want to do it now?
Say /personal-setup anytime if you'd rather do it later.
```

If yes and personal toolkit is already installed → invoke `/personal-setup` inline.
If yes and personal toolkit is NOT installed → install it, then tell the builder:

```
Personal toolkit installed! You'll need to start a new Claude Code session
for the skills to load. When you're back, say /personal-setup to finish
configuration (~10 min).
```

There is currently no way to reload skills without restarting the session. If Claude Code adds a `/reload-skills` or similar command in the future, use that instead of requiring a restart.

If no → done.

#### `/personal-setup` — Personal Productivity (~10 min)

Standalone skill (already exists, gets restructured). Four numbered steps:

```
Let's set up your personal productivity toolkit.

This takes about 10 minutes:
  1. Set up your knowledge base (Obsidian)        — 5 min
  2. Connect your accounts (mostly auto-detected)  — 2 min
  3. Optional integrations (Fathom meeting notes)  — 3 min
  4. Done — try "open my day" to see it in action
```

**Step 1: Knowledge base (Obsidian)**
- Auto-detect existing vaults
- If none found, offer `/obsidian-setup` to scaffold one
- This is the biggest piece and the most tangible payoff — "your notes, project logs, and daily plans all live here"

**Step 2: Connect accounts**
- Auto-detect Slack ID and Asana GIDs from MCP (same as today)
- Confirm and move on — fast step

**Step 3: Optional integrations**
- **Fathom API key** — for meeting summaries in `/close-day` and 1:1 transcripts in `/person-intelligence`. Clear skip option.
- **Airtable API key** — demoted to fully optional. Only needed for writing to Airtable (not for org context, which is now in the repo). Most builders skip this.

**Step 4: Write .env and confirm**
- Write config to `~/.claude/local-plugins/nsls-personal-toolkit/.env`
- Suggest "open my day" as first thing to try — this is the aha moment

#### Changes from Today

| Today | New |
|-------|-----|
| Compound Engineering auto-installed (flaky two-step) | Mentioned as optional power-up in wrap-up |
| Personal productivity buried in Phase 3 of `/setup` | Standalone `/personal-setup`, pitched as the aha moment |
| One monolithic `/setup` flow | Two focused flows: `/setup` (5 min) + `/personal-setup` (10 min) |
| Airtable API key needed for org context | Org chart + LOPs + strategy synced to repo, no key needed |
| No time estimates shown to builder | Clear "5 min" / "10 min" framing upfront |
| No org context available without keys | `_shared/context/` with org chart, LOPs, strategy available to all |
| Session restart needed but not always clear | Explicit callouts wherever a restart is required (install, personal toolkit add) |

## Files to Create or Modify

### New files
- `.github/workflows/sync-org-context.yml` — GitHub Action for scheduled sync
- `_shared/scripts/sync_org_context.py` — Python sync script (Airtable + Google Docs → markdown)
- `_shared/context/org-chart.md` — generated, committed by action
- `_shared/context/lops.md` — generated, committed by action
- `_shared/context/strategy.md` — generated, committed by action (manual trigger)

### Modified files
- `install.sh` — remove compound-engineering auto-install
- `skills/setup/SKILL.md` — restructure to 4-step flow, add time estimates, pitch personal productivity at end, mention org context
- Personal toolkit: `skills/personal-setup/SKILL.md` — restructure to 4-step flow, add time estimates, demote Airtable key to optional

## Data Sources

### Airtable (People Ops base `appnXPTu01esWWbrK`)

**Org chart fields needed from Employees table**:
- Name
- Title
- Department
- Manager (linked record)
- Email
- Slack ID

**LOP fields needed from L2 Goals table**:
- Goal name
- Owner
- Latest Update Health (lookup from L2 Goal Updates)
- Latest update comment (lookup from L2 Goal Updates)

### Google Docs

**Strategy doc**: `1EOOTdKLV0j1MnpHV_hwNx4hbcOiHTjjKdo5h7UCZBYo`
- Fetched via Google Docs API (gws or service account)
- Converted to markdown
- "For Internal Use Only" header preserved

## Security Considerations

- Org chart contains names, titles, emails, Slack IDs — not sensitive for a private repo that all builders already have access to
- LOP health and updates — operational data, appropriate for internal sharing
- Strategy doc — marked "For Internal Use Only", appropriate for private repo, not for public repos
- Airtable API key lives in GitHub repo secrets, not on builder machines
- Quick notes, work journals, and other sensitive People Ops data are NOT synced — only the fields listed above
