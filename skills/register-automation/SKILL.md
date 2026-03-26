---
name: register-automation
description: Register, update, or check an NSLS automation in the Automation Tracker Airtable base. Use when the user says "register automation", "register this", "track this automation", "update automation tracker", "check automation status", "list automations", or is working in an NSLS automation repo and wants to record it in the tracker.
---

# Register Automation

Register or update NSLS automations in the Automation Tracker Airtable base via a Railway proxy.

**Proxy URL**: `https://web-production-6281e.up.railway.app`

## What This Does

This skill connects to the NSLS Automation Tracker — an Airtable base that tracks all automations from idea to organizationally owned, plus a builder pipeline for employees learning to build.

**Two pipelines:**
- **Automations**: Submitted → Idea → Prototype → Production → Org-Owned → Retired
- **Builders**: Explorer → Maker → Builder → Architect → Steward

## Available Actions

### 1. Register a New Automation

POST to `/automation` with the automation details.

### 2. Update an Existing Automation

POST to `/automation` with `record_id` plus the fields to update.

### 3. Find an Automation

POST to `/find` with `{"name": "search term"}` to search by name.

### 4. List Automations

GET `/automations` to list all, or `/automations?stage=Production` or `/automations?department=People (HR)` to filter.

### 5. Register a Builder

POST to `/builder` with builder details.

### 6. Create an Assignment

POST to `/assignment` to link a builder to an automation.

## How to Use

### Auto-detect mode (when in a repo)

If the user is working inside a git repo, auto-detect as much as possible:

1. **Check for existing record**: POST `/find` with the repo name or a likely automation name
2. **Scan the repo** for org-owned checklist items:
   - `README.md` exists? → `readme: true`
   - `CLAUDE.md` exists? → `claude_md: true`
   - `docs/runbook.md` or `runbook.md` exists? → `runbook: true`
   - `docs/architecture.md` or `architecture.md` exists? → `architecture_doc: true`
   - `DESIGN.md` exists? → `design_intent: true`
   - Check `git remote -v` for GitHub URL → `github_repo_url`
   - Check for `.env` or `railway.toml` → hints about deployment
3. **Ask the user** only for fields you can't detect: name, description, department, scope, type, stage
4. **Register or update** via POST `/automation`

### Manual mode (from anywhere)

If not in a repo, ask the user for:
- **Required**: name, description
- **Recommended**: department, scope (Personal/Department/Company-wide/Customer Facing: Advisors/Customer Facing: Members), type (Bot/Claude Code Skill/Script/Scheduled Job/Integration), stage
- **Optional**: everything else — fill in what you know, skip what you don't

### Checking status

If the user asks "what automations do we have" or "show me the tracker":
- GET `/automations` to list all
- Present as a clean table with name, stage, department, type

## API Reference

### POST /automation

Register or update. Include `record_id` to update an existing record.

```json
{
  "record_id": "recXXX",           // optional — include to update
  "name": "Quick Notes Weekly Journal",
  "description": "Friday journal prompt...",
  "department": "People (HR)",      // Finance, Marketing, Product, People (HR), Client Services, Development, Logistics, Leadership (SLT)
  "scope": "Company-wide",          // Personal, Department, Company-wide, Customer Facing: Advisors, Customer Facing: Members
  "type": "Bot",                    // Bot, Claude Code Skill, Script, Scheduled Job, Integration
  "stage": "Production",            // Submitted, Idea, Prototype, Production, Org-Owned, Retired
  "submitted_by_name": "Kevin Knudsen",
  "submitted_by_email": "kknudsen@nsls.org",
  "roi_impact": "Large",            // Small, Medium, Large
  "effort": "Medium",               // Small, Medium, Large
  "time_saved": "~2 hrs/week across 60 employees",
  "money_impact": "$500/month",
  "people_affected": 60,
  "data_sources": ["Airtable", "Slack", "Google Docs", "Claude API"],
  "github_repo_url": "https://github.com/thensls/nsls-coach",
  "railway_service_url": "https://...",
  "gcp_project": "nsls-automations",
  "service_account_email": "hr-automation@nsls-automations.iam.gserviceaccount.com",
  "railway_monthly_spend": 5.00,
  "api_key_name": "People Ops Anthropic Key",
  "code_on_github": true,
  "readme": true,
  "claude_md": true,
  "runbook": true,
  "architecture_doc": true,
  "service_account_creds": true,
  "deployed_shared_infra": true,
  "env_vars_documented": true,
  "collaborators_on_repo": true,
  "handoff_guide_exists": true,
  "won_the_lottery": false,
  "design_intent": true,
  "related_lop_goal": "L1: Simplification/Efficiency",
  "high_level_kpi": ["Simplification", "Internal Alignment"],
  "parent_automation_id": "recXXX"
}
```

All fields except `name` are optional. Send only what you have.

### POST /find

```json
{"name": "NSLS Coach"}
```

Returns matching records with record_id, name, stage, department, type, scope, description.

### GET /automations

Query params: `?stage=Production` or `?department=People (HR)`

### POST /builder

```json
{
  "name": "Jane Smith",
  "email": "jsmith@nsls.org",
  "github_username": "jsmith-nsls",
  "department": "Product",
  "tools": ["Claude Code", "Python"],
  "interests": "Want to learn how to build Slack bots"
}
```

### POST /assignment

```json
{
  "assignment_name": "Jane Smith — NSLS Coach",
  "builder_id": "recXXX",
  "automation_id": "recYYY",
  "role": ["Developer", "Maintainer"],
  "status": "Active"
}
```

## Org-Owned Checklist

When updating an automation, scan the repo and check these boxes:

| Check | How to detect |
|-------|---------------|
| `code_on_github` | `git remote -v` returns a github.com URL |
| `readme` | `README.md` exists in repo root |
| `claude_md` | `CLAUDE.md` exists (root or `.claude/`) |
| `runbook` | `runbook.md` exists (root or `docs/`) |
| `architecture_doc` | `architecture.md` exists (root or `docs/`) |
| `service_account_creds` | Ask the user |
| `deployed_shared_infra` | `railway.toml` or `Procfile` exists |
| `env_vars_documented` | README or runbook mentions env vars |
| `collaborators_on_repo` | `gh api repos/{owner}/{repo}/collaborators --jq length` > 1 |
| `handoff_guide_exists` | Ask the user |
| `won_the_lottery` | Ask the user — "Would this still run if you disappeared tomorrow?" |
| `design_intent` | `DESIGN.md` exists in repo root |

### Scope Change Check

When updating an automation's scope to a higher level (e.g., Personal → Department, Department → Company-wide, or any → Customer Facing), check for `DESIGN.md`. If missing, recommend the builder run the `product-design` skill in Generate Mode before proceeding. This is required for Department+ scope automations.

## Example Conversation

**User**: register this automation
**Assistant**: *scans repo, finds README, CLAUDE.md, railway.toml, GitHub remote*

> I found this repo is `thensls/nsls-coach` on GitHub. Let me check if it's already in the tracker...
>
> Found it: **NSLS Coach** (Production, People (HR)). I can see the repo has:
> - ✓ README, CLAUDE.md, runbook, architecture doc
> - ✓ On GitHub with 3 collaborators
> - ✓ Railway deployment configured
>
> Want me to update the checklist? I'll also need to ask: does it use a service account (not personal creds), and are the env vars documented somewhere?
