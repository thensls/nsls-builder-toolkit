---
name: provision-builder
description: >-
  Use when a builder needs their app put on shared NSLS infrastructure (Railway +
  Doppler) — "provision a builder", "set up [name] on Railway", "onboard [name]'s
  app", "get [name] able to deploy", "add [name] to Railway and Doppler", when a
  builder reports they "can't deploy" or hit "only the GitHub owner can do this" in
  Railway, or /provision-builder.
---

# /provision-builder — onboard a builder's app to Railway + Doppler

## Safety — what this skill may do

1. **Read-only (no friction):** check GitHub org membership and repo access, read
   Railway projects (`railway list`), read Doppler projects (`doppler projects`),
   look up the builder in Slack. Run these freely to build the picture.
2. **Configuration (confirm first):** create a Railway project + GitHub-connected
   service, create a Doppler project. Show the full plan and get a yes before
   creating anything. These make real resources in the NSLS workspaces.
3. **External / human-in-the-loop (never automatic):** inviting the builder to the
   Railway team or Doppler workplace, granting Doppler project access, and sending
   the builder a Slack message. The skill **prepares** these — a printed checklist
   and a Slack *draft* — but a human completes them. Never invite via API, never
   auto-send the Slack message.

## Purpose

Getting a builder's app onto shared infra used to mean re-deriving a playbook under
a misleading error. This skill turns that into a guided ~10-minute flow: it knows
the GitHub side is usually already fine, it knows which steps the CLIs can do and
which are dashboard-only, and it knows the one failure that masquerades as a
permissions problem. It does the mechanical creation itself and hands the human a
tight checklist for the parts that genuinely require a click.

## The one thing to understand first

When a builder hits **"only the GitHub owner can do this"** in Railway, it is almost
never a GitHub problem. The Railway GitHub App is already installed org-wide on
`thensls` with access to **all** repos, and builders already have repo access. The
real cause: the builder is acting in a Railway account/team that does not hold the
org's GitHub connection. **The fix is to create the service under the NSLS Railway
team (which holds the connection) and add the builder to that team** — not to grant
anything on GitHub.

## Inputs (gather interactively, heartbeat each)

- **Builder:** name + **GitHub username** + **work email**. Resolve email/Slack with
  `slack_search_users "<name>"` and confirm; don't guess an address you'll invite.
- **Repo(s):** one or more `thensls/...`. If they give an app name, find matches with
  `gh repo list thensls --limit 200 | grep -i <name>` and confirm.
- **Confirm the plan** before any write:
  `Provisioning Josh Hrala (jhrala) → 2 apps (NSLS-Alumni-Tracker, invite-email-simulator) on Railway + Doppler under the NSLS team. Proceed?`

## Preflight — pick the mode

Check the runner's own access and **say what you found** (heartbeat):

```bash
ME=$(gh api /user --jq .login)
gh api /orgs/thensls/memberships/$ME --jq .role     # owner/admin vs member
railway whoami                                       # logged in? (Kevin/Jenna = NSLS)
doppler me                                           # logged in? workplace = NSLS?
```

- If any CLI isn't authenticated, stop and point to `railway login` / `gh auth login` /
  `doppler login` (or `/connect`). Resume after.
- **Execute mode** — runner is an org admin and the Railway/Doppler CLIs work: do the
  CLI creation below, then print the dashboard checklist + Slack draft.
- **Request mode** — runner is *not* an admin (e.g. Josh onboarding a new builder), or
  an execute-mode CLI call fails with a permission error: **create nothing.** Emit a
  clean *Provisioning request* — repos, services to create, Doppler projects, and the
  invites needed with access levels — and offer to drop it as a Slack draft to an admin
  (Kevin or Jenna). Don't thrash against a permission wall; hand it off.

## Execute-mode steps (idempotent — safe to re-run)

### 1. Verify GitHub access (prerequisite, not something to grant)

```bash
gh api /orgs/thensls/memberships/<user> --jq .role          # must exist (member/admin)
gh api /repos/thensls/<REPO>/collaborators --jq '.[]|select(.login=="<user>")|.role_name'
```

The builder must be a `thensls` org member with at least `write` on each repo. If not,
**flag it** — that's a separate access grant, don't silently add them. (Context, if
asked: `gh api /orgs/thensls/installations --jq '.installations[]|select(.app_slug=="railway-app")|.repository_selection'` returns `all` — Railway already sees every repo.)

### 2. Railway — one GitHub-connected service per repo

Check first; skip-and-heartbeat if it already exists (a re-run after a timeout must not
double-create):

```bash
railway list        # does a project for this app already exist? say so if it does.
```

Otherwise, **work from a temp dir** so no Railway link files land in the runner's home:

```bash
cd "$(mktemp -d)"
railway init -n "<Project Name>" -w NSLS --json          # capture .id
railway link -p <projectId>
railway add --repo thensls/<REPO> --service <service-name> --json
railway status --json | grep -E '"name"|"repo"'          # confirm source.repo is set
```

- Use `--repo` — it creates a **GitHub-connected** service that auto-deploys on push.
  `railway up` only uploads a local snapshot; that is not what we want.
- `railway init`/`add` may echo interactive prompts even with `--json`; they still
  complete. The real risk is a transient `operation timed out` from backboard — if that
  happens, re-run `railway list` to see whether the project was created before retrying.

### 3. Doppler — one project per app

```bash
doppler projects --json     # already exists? skip and heartbeat.
doppler projects create <slug> --description "Env/secrets for <App> (Railway). Owner: <Builder>."
```

Default configs `dev` / `stg` / `prd` are created automatically; the Railway production
environment will sync from `prd`.

### 4. Dashboard checklist — the CLIs cannot do these (print verbatim)

Neither the Railway CLI nor the Doppler CLI can invite members or grant access. Hand the
admin these exact steps:

- **Railway team:** railway.com → **NSLS** workspace → **Settings → Members → Invite** →
  `<builder email>`, role **Member**.
  ⚠️ **Blast radius:** Railway membership is team-wide, not per-project — the builder will
  see **every** NSLS project, not just their two. State this every run. (A per-builder
  Railway team is the tighter alternative; we deliberately default to the NSLS team.)
- **Doppler:** dashboard.doppler.com → **Workplace Settings → Team → Invite** →
  `<builder email>`. Then for **each** new project → **Access** → add the builder as
  **Admin** (so they manage their own secrets, scoped to just their projects).

### 5. Handoff — draft (never send) a Slack message to the builder

Look up the builder (`slack_search_users`), then `slack_send_message_draft` to their
user id. The draft tells them what's done and their remaining steps:
1. Accept the **Railway team invite** (else they can't see their Railway projects).
2. Accept the **Doppler invite**.
3. Put env vars in the **`prd`** config of each Doppler project.
4. Wire **Doppler → Railway** themselves (Doppler project → **Integrations → Railway** →
   point `prd` at the Railway service's production env — they have Admin).

Then: push deploys with secrets pulled from Doppler.

## Red flags — STOP

Each of these is a shortcut that breaks the skill. If you catch yourself doing it, stop:

| Rationalization | Reality |
|---|---|
| "It's a GitHub permissions wall — I'll grant access on GitHub." | It isn't. The app has `all` repos and the builder has write. Create the service under the NSLS team + add them to the team. |
| "I'll just send the builder the Slack message to finish the job." | Never auto-send. Create a **draft** only; the runner sends it. |
| "I'll invite them to Railway/Doppler via the API to save a click." | Don't. Invites and project-access grants stay human-in-the-loop — print the checklist. |
| "I'll create the Railway project / Doppler project now." | Check first (`railway list`, `doppler projects`). A re-run after a timeout must not double-create. |
| "The plan's obvious, I'll skip the confirm." | Confirm the plan before any create. These are real resources. |
| "The runner isn't an admin, but I'll push the CLI through." | Fall back to request mode and hand off. Don't thrash a permission wall. |
| "The builder lacks repo write — I'll just add them." | Flag it as a prerequisite gap. Don't silently grant org/repo access. |

## Diagnostic loop

- **"only the GitHub owner can do this" (the builder hit it):** not GitHub. Confirm the
  app is `repository_selection: all` and the builder has org membership + repo write
  (they will). The fix is creating the service under the NSLS team + adding them to the
  team — see top of skill.
- **`railway add` succeeds but nothing deploys:** the service is connected but has no
  build config / env vars yet. Expected until the builder adds `prd` vars and wires the
  Doppler→Railway sync. Not a provisioning bug.
- **Railway `operation timed out`:** transient backboard error. Re-run `railway list` to
  check whether the resource was created, then retry only the missing step.
- **Repo not visible to Railway:** verify the builder's org membership, not the GitHub
  App (the app already has `all`).
- **CLI permission error mid-execute:** the runner isn't sufficiently privileged for that
  step — fall back to request mode and hand the rest to an admin.

## Output

Close with a compact table — per app: Railway project/service ↔ repo, Doppler project,
and the access state — followed by the dashboard checklist and the Slack draft link.
Then the single next action ("builder accepts invites, adds prd vars, wires sync").

## Notes

- Setup of the runner's own connections lives in `/connect`, not here.
- Register the app(s) with `/register-automation` if they're org automations.
- Scope is Railway + Doppler. Vercel/Netlify provisioning is intentionally out.
