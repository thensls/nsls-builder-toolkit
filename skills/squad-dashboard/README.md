# squad-dashboard

A Claude Code skill that builds a squad's own outcome / SLT / status dashboard — a clean,
filterable web page of *your* KPIs, campaigns, workstreams, experiments, or metrics — and
deploys it to Netlify. Each squad declares its own data sources, KPIs, sections, and L3/LOP
goals; nothing is hard-coded to one team.

Born from the enrollment Test Outcomes gallery; generalized so any squad gets the same craft
and reliability without an engineer building a bespoke page.

## What's here

| Path | What it is |
|------|-----------|
| `SKILL.md` | The skill — modes (setup / refresh / edit), pull-and-confirm, deploy, safety, diagnostics |
| `presets/shop.json` | Real, tested Shop config (revenue + email + campaigns + workstreams) |
| `presets/enrollment.json` | Experiment-shaped config (the reference design) |
| `sections/section-patterns.html` | The generic section primitives (copy-and-adapt blocks) |
| `shell/base.css` | Shared stylesheet (NSLS + Society themes) |
| `deploy.sh` | Netlify deploy helper (`--no-build`, optional SSO-gate verify) |
| `references/data-sources.md` | How to pull from Sheets / PostHog / HubSpot / Hex / Slack |
| `docs/specs/` | The design spec |

## Before you start (prerequisites)

- **NSLS Netlify access** — the dashboard publishes to the shared NSLS Netlify team. **Contact
  Kevin to be added**, then `netlify login`. (Required for the deploy step.)
- **Source connectors** — if your data lives in a system Claude can't reach yet, run `/connect`.
  No connector for your tool (Looker/Tableau/Snowflake/vendor)? Export the figures to a Google
  Sheet, or enter them manually — the skill supports both.
- **`gws`** for Google Sheets.

Status: **v1 pilot.** Verified end-to-end on Google Sheets + PostHog (the Shop squad,
`shop-squad-dashboard-demo.netlify.app`). Other source types are documented but not yet
battle-tested — expect rough edges and report them (see Feedback).

## Install

Copy or clone this directory into your Claude skills folder:

```bash
cp -R squad-dashboard-skill ~/.claude/skills/squad-dashboard
```

Then in Claude Code: "build our squad's dashboard" (or `/squad-dashboard`).

## Customize (the point)

This is a starting point, not a locked tool. Make it yours:
- **Add a section primitive** — drop a new block in `sections/section-patterns.html` + its CSS
  in `shell/base.css`. That's the unit of growth; the rest doesn't change.
- **Add a preset** — copy `presets/shop.json`, swap in your sources/KPIs/sections/LOPs.
- **Add a classification scheme** — vocabulary that fits your work (Won/Lost, Met/Missed,
  Shipped/Blocked…). Objective vs-goal ones auto-derive; judgment ones stay human.
- **Theme** — `body class="society"` for the Society palette, or edit `:root` in `base.css`.

## Two rules that make it reliable (please keep)

1. **Pull-and-confirm** — numbers are pulled from declared sources and confirmed by the squad
   before publish, with provenance shown.
2. **Human text is sacred** — the narrative "read", operational statuses, and judgment calls
   are written by the squad, never AI-concluded, and a refresh never overwrites them.

Optional: gate the page behind "Sign in with NSLS" — see `/nsls-auth`.

## Feedback

This is a piloted v1. If a data source won't pull, the setup stalls, or the output isn't right,
report it (Slack to Julia, or a comment on the toolkit PR) so the rough edges get fixed for the
next squad. The source list in `references/data-sources.md` marks which pulls are verified vs
documented-but-untested.
