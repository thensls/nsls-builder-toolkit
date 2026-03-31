# NSLS Builder Toolkit — Conventions

## What This Plugin Is

This plugin contains **organization-standard skills** for NSLS builders. These skills are maintained via GitHub PRs — do not edit them locally. Updates flow automatically when `main` is updated.

**Personal productivity skills** (open-day, close-day, close-week, plan-week, log, familiar, person-intelligence, obsidian-setup) are **not** in this plugin. They live in `~/.claude/skills/` and are fully yours to edit, delete, or replace. Kevin shares his as a starter template — fork the pattern, make it your own.

## Skill Routing by Complexity

You have skills from three sources: **NSLS Builder Toolkit** (organization skills), **Compound Engineering** (development workflows), and **Superpowers** (process discipline). Route tasks to the right one:

### Quick tasks (< 30 min, single-step)
- Use **Superpowers** skills: `systematic-debugging`, `verification-before-completion`, `test-driven-development`
- These are lightweight — find root cause, verify the fix, move on

### Feature work (multi-step, needs a plan)
- Use **Compound Engineering** pipeline: `ce:brainstorm` → `ce:plan` → `ce:work`
- Produces durable requirements docs and implementation plans
- Use `ce:review` for code review (parallel reviewer personas, structured findings)

### NSLS-specific tasks (always)
- Use **NSLS Builder Toolkit** skills for anything NSLS-domain: slides, automations, Google Workspace, focus groups, deployment, web research
- These override generic skills when the task is NSLS-related

### Git operations
- Use **Compound Engineering**: `git-commit`, `git-commit-push-pr`, `git-clean-gone-branches`

### Process discipline (always active)
- **Superpowers** `using-superpowers` fires every session — it ensures skills get checked before acting. Keep this active.
- `verification-before-completion` — always verify before claiming done
- `finishing-a-development-branch` — merge/PR decision guide (no compound equivalent)

## Automation Tracking

**Always register automations** with `/register-automation` when you build something new. This feeds the org-wide Automation Tracker so leadership has visibility into what's being built, by whom, and at what stage.

## Google Workspace
- **Always use `gws` for Google Docs, Sheets, Slides, Drive URLs** — never WebFetch, WebSearch, or Firecrawl for google.com URLs
- Use `google-drive` skill for file upload/download/sharing operations

## Presentations
- Always ask "NSLS branded or Society branded?" before creating slides
- **NSLS**: Lexend Deca + Avenir, navy/teal/gold
- **Society**: HW Cigars + Inter, cream/yellow
