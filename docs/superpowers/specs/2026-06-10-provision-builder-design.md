# /provision-builder — design

**Date:** 2026-06-10
**Status:** Implemented (shipped PR #55)
**Author:** Kevin (with Claude)

> **Correction (2026-06-10):** The original design said the *builder* wires the
> Doppler→Railway sync themselves (since they get Doppler project-Admin). That's wrong —
> creating a Doppler *connection*/sync is a **workplace-admin** action; project-Admin can
> edit secrets but cannot add connections. The sync setup moved to the **admin**
> dashboard checklist (step 4). Surfaced when Josh hit "no permission to add a new
> connection." Fixed in a follow-up PR.

## Problem

Getting a builder's app onto shared NSLS infra (Railway + Doppler) is a recurring,
error-prone manual task. The first run (Josh Hrala — Alumni Tracker + Invite Email
Simulator, 2026-06-08) surfaced a misleading failure mode: Railway says *"only the
GitHub owner can do this,"* which reads like a GitHub permissions problem but is
actually a Railway-side issue (the builder is acting in a Railway account that
doesn't hold the org's GitHub connection). The fix has fixed CLI parts and fixed
dashboard-only parts. This skill encodes the playbook so each future builder is a
~10-minute guided flow, not a re-debug.

Users: Kevin, Jenna, Josh (and future admins).

## What it does

Takes a builder + one or more `thensls` repos from nothing to "ready to deploy with
secrets in Doppler," across **Railway and Doppler only**.

- **Home:** `nsls-builder-toolkit/skills/provision-builder/SKILL.md` (single file, org
  plugin, PR-gated). Jenna + Josh already have the plugin, so they get it on update.
- **Trigger phrases:** "provision a builder", "set up [name] on Railway/Doppler",
  "onboard a builder's app", "give [name] access to deploy", "/provision-builder".

## Scope

**In scope:** GitHub access verification, Railway GitHub-connected service creation
under the NSLS team, Doppler project creation, the dashboard-only invite checklist,
and a Slack-draft handoff to the builder.

**Out of scope (YAGNI, note as future):**
- Vercel / Netlify provisioning (Railway is the established pattern).
- Auto-inviting to Railway team or Doppler workplace via API (stays human-in-the-loop).
- Auto-sending the Slack message.
- Granting GitHub org membership or repo access (prerequisite the skill *checks*, not grants).

## Runner model: execute mode vs request mode

The skill relies on the **runner's own** `gh`, `railway`, and `doppler` CLI auth.
Preflight determines which mode applies and reports it as a heartbeat.

Preflight checks:
- `gh api /orgs/thensls/memberships/{me}` → role `admin` vs `member`; CLI logged in.
- `railway whoami` → logged in; NSLS workspace reachable.
- `doppler me` → logged in; workplace = NSLS.
- If any CLI isn't authed: point to `railway login` / `gh auth login` / `doppler login`
  or `/connect`, then stop.

**Execute mode** (runner is admin): runs the CLI work, then prints the dashboard
checklist + Slack draft.

**Request mode** (runner is not admin — e.g. Josh onboarding a *new* builder): creates
nothing. Emits a structured "Provisioning request" handoff — repos, services to create,
Doppler projects, who to invite where with what access level — and offers to drop it as
a Slack draft to an admin (Kevin/Jenna). Also the fallback when an execute-mode CLI call
fails with a permission error (fall back, don't thrash).

## Inputs (interactive, with heartbeats)

1. Builder name + **GitHub username** + **work email** (auto-resolve email/Slack via
   `slack_search_users`, confirm).
2. One or more repos (`thensls/...`); auto-suggest matches from an app name.
3. Confirm the plan before any action:
   *"Provisioning Josh Hrala (jhrala) → 2 apps on Railway+Doppler. Proceed?"*

## Execute-mode steps (idempotent — safe to re-run)

1. **GitHub check** — verify builder is a `thensls` org member and has `write` on each
   repo (`gh api /repos/thensls/REPO/collaborators`). If not, flag as a prerequisite gap;
   do not silently grant.
2. **Railway** (per repo) — check if a project/service already exists for the repo; if so,
   heartbeat "found existing, skipping." Else:
   `railway init -n "<Name>" -w NSLS` → `railway link -p <id>` →
   `railway add --repo thensls/REPO --service <name>` (creates a GitHub-connected service
   that auto-deploys on push). Run from a temp dir so no Railway link files land in the
   runner's home.
3. **Doppler** (per app) — `doppler projects create <slug>` if absent (default dev/stg/prd).
4. **Dashboard checklist** (CLIs cannot do these — always printed explicitly):
   - Railway: invite builder to the **NSLS team** (railway.com → workspace → Settings →
     Members).
   - Doppler: invite to workplace + grant **Admin on just their project(s)**
     (dashboard.doppler.com → Workplace Settings → Team; then project → Access).
5. **Handoff** — create (never auto-send) a Slack DM draft to the builder via
   `slack_send_message_draft`, summarizing what's done and their next steps: add env vars
   to the **prd** config, then wire Doppler→Railway themselves (project → Integrations →
   Railway → point prd at the service's production env — they have Admin).

## Guardrails

- **Confirm before creating** anything; show the plan first.
- **Idempotent**: detect-and-skip existing Railway/Doppler resources so a re-run after a
  timeout (hit during the Josh run) doesn't double-create.
- **Blast-radius warning** (every run): adding a builder to the NSLS Railway team grants
  them access to *all* NSLS projects (team-wide, not per-project). The skill states this
  plainly. **Decision: keep defaulting to the NSLS team**; mention the per-builder-team
  alternative exists but do not default to it.
- **Never** auto-send the Slack message or fire workplace/team invites via API.
- Relay CLI permission errors plainly; on failure, fall to request-mode output.
- Heartbeat every conditional/skip step (per toolkit convention — silent skips are
  indistinguishable from broken).

## Key facts to bake into the skill (from the Josh run)

- Railway GitHub App on `thensls` = `railway-app`, install id `118001364`, already
  `repository_selection: all` — so there is nothing to "select on GitHub." The
  "only the GitHub owner can do this" wall is Railway-side.
- Railway CLI **cannot** invite members; Doppler CLI **cannot** invite members or grant
  project access — both are dashboard-only.
- `railway add --repo` creates the GitHub-connected (auto-deploy) service; `railway up`
  only uploads a local snapshot — use `--repo`.
- One Doppler project per app (matches convention: nsls-dns-proxy, slt-coach, …).

## Reference

Playbook + first-run session: Obsidian `20-projects/builder-access-provisioning/`.

## Build process

Authoring uses the toolkit's 3-phase skill-creation cascade: `/skill-creation` →
`superpowers:writing-skills` → `compound-engineering:create-agent-skills`. Register with
`/register-automation` after merge. Ship via PR (Macroscope on the technical CLI claims).
