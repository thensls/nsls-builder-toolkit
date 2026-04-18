# NSLS Builder Toolkit — Conventions

## What This Plugin Is

This plugin contains **organization-standard skills** for NSLS builders. These skills are maintained via GitHub PRs — do not edit them locally. Updates flow automatically when `main` is updated.

**Personal productivity skills** (open-day, close-day, close-week, log, familiar, person-intelligence, obsidian-setup) are in a separate plugin: [nsls-personal-toolkit](https://github.com/thensls/nsls-personal-toolkit). Run `/setup` to install them — they're optional and fully yours to edit.

## What Gets Installed

The install script sets up three things:

1. **NSLS Builder Toolkit** (this plugin) — org skills for slides, automations, Google Workspace, focus groups, deployment, web research
2. **Superpowers** (marketplace plugin) — process discipline: planning, debugging, verification, TDD
3. **Compound Engineering** (marketplace plugin) — development pipeline: brainstorm, plan, work, review, git

## Skill Routing by Complexity

### Quick tasks (< 30 min, single-step)
- Use **Superpowers** skills: `systematic-debugging`, `verification-before-completion`, `test-driven-development`
- These are lightweight — find root cause, verify the fix, move on

### Feature work (multi-step, needs a plan)
- Use **Compound Engineering** pipeline: `ce:brainstorm` → `ce:plan` → `ce:work`
- Produces durable requirements docs and implementation plans
- Use `ce:review` for code review (parallel reviewer personas, structured findings)

### Data intelligence (any question about users, systems, or operations)
- If tools for a system aren't available, run `/connect` to set up the connection
- Use `/data-intel` for cross-system questions that span multiple services
- Use individual domain skills (`/posthog`, `/slack`, `/customerio`, `/n8n`, `/airtable`, `/braintrust-evals`) for deep single-system work
- `/connect` → provides connections. Domain skills → deep expertise. `/data-intel` → orchestrates across all of them.

### NSLS-specific tasks (always)
- Use **NSLS Builder Toolkit** skills for anything NSLS-domain: slides, automations, Google Workspace, focus groups, deployment, web research
- These override generic skills when the task is NSLS-related

### Git operations
- Use **Compound Engineering**: `git-commit`, `git-commit-push-pr`, `git-clean-gone-branches`

### Process discipline (always active)
- **Superpowers** `using-superpowers` fires every session — it ensures skills get checked before acting
- `verification-before-completion` — always verify before claiming done
- `finishing-a-development-branch` — merge/PR decision guide

## Automation Tracking

**Always register automations** with `/register-automation` when you build something new. This feeds the org-wide Automation Tracker so leadership has visibility into what's being built, by whom, and at what stage.

## Google Workspace
- **Always use `gws` for Google Docs, Sheets, Slides, Drive URLs** — never WebFetch, WebSearch, or Firecrawl for google.com URLs
- Use `google-drive` skill for file upload/download/sharing operations

## Skill Creation (3-phase cascade)
When building a new skill, use three tools in sequence. Each tests a different quality axis:
1. **`/skill-creation`** (this toolkit) — design rubric: purpose, safety, macro/micro, diagnostics, domain-specific gotchas
2. **`superpowers:writing-skills`** — pressure test: pure-trigger description, rationalization table, Red Flags list, TDD-for-documentation discipline
3. **`compound-engineering:create-agent-skills`** — spec audit: official frontmatter compliance, Quick Start, line count, writing style

**Optional Phase 4**: For broadly-released skills that need reliable auto-triggering across many sessions, add `skill-creator` plugin for quantitative eval. Skip for personal / time-boxed / Kevin-only skills.

See `/skill-creation` for the full cascade including a worked example (gary-meeting-prep build, 2026-04-18).

## Presentations
- Always ask "NSLS branded or Society branded?" before creating slides
- **NSLS**: Lexend Deca + Avenir, navy/teal/gold
- **Society**: HW Cigars + Inter, cream/yellow
