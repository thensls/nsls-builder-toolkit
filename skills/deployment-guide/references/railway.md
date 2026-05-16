# Railway

## What It Is

Railway is a cloud hosting platform. Use it for anything that needs to run continuously or respond to network requests: Slack bots, web APIs, scheduled jobs, and background workers.

Use Railway when:
- You're building a Slack bot (Socket Mode or HTTP)
- You need a persistent process (scheduler, queue worker)
- You need a web API that other services call

Don't use Railway for one-off scripts or things that only run when a spreadsheet changes — that's what Google Apps Script is for.

## Getting Access

Message Kevin in Slack: "I need access to Railway to deploy [what you're building]." He'll add you to the NSLS team.

## Creating a Service from a GitHub Repo

1. Go to [railway.app](https://railway.app) and open the NSLS project.
2. Click **New** → **GitHub Repo**.
3. Select the repo. Railway will detect the language and suggest a build command.
4. Set environment variables before deploying (see below).
5. Click **Deploy**.

Railway redeploys automatically on every push to the default branch — **but only when the service has a "repo trigger" wired**. Verify this BEFORE shipping the service (see next section). Three NSLS services have been quietly missing this and required manual `railway up` for every deploy until 2026-05-11.

## Verifying Auto-Deploy Is Actually Wired

A service connected via the "New → GitHub Repo" flow gets a `repoTrigger` automatically. Services created another way (CLI `railway up`, "deploy from image", duplicated from another service) often don't — and the silent failure mode is the worst kind: deployments look like they're working because manual deploys still succeed.

After creating a service, verify with the Railway CLI:

```bash
railway link --project <project-name>
railway service <service-name>
# Look for the GitHub icon in `railway status` or in the dashboard's
# Settings → Source pane. If "Source" says "image" or is empty, the
# trigger isn't wired.
```

Or with the Railway GraphQL API:

```bash
RAILWAY_TOKEN=$(python3 -c "import json; print(json.load(open('$HOME/.railway/config.json'))['user']['token'])")
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"query($id:String!){ service(id:$id){ name repoTriggers { edges { node { repository branch } } } } }","variables":{"id":"<SERVICE_ID>"}}'
```

`repoTriggers.edges` must contain an entry with the right `repository` and `branch`. Empty → no auto-deploy.

**Smoke test the wire** before assuming it works. From the repo:

```bash
git commit --allow-empty -m "chore: verify Railway auto-deploy is wired"
git push origin <default-branch>
```

Within ~30 seconds Railway should start a new deployment with `reason: "deploy"` (not `redeploy`). If nothing happens, the trigger is missing.

To wire a trigger when one is missing:

```bash
curl -s -X POST https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $RAILWAY_TOKEN" -H "Content-Type: application/json" \
  -d '{"query":"mutation($id:String!,$input:ServiceConnectInput!){ serviceConnect(id:$id, input:$input){ name repoTriggers { edges { node { repository branch } } } } }","variables":{"id":"<SERVICE_ID>","input":{"repo":"thensls/<repo-name>","branch":"<default-branch>"}}}'
```

Or use the dashboard: **Settings → Source → Connect Repo**, then pick the repo and branch.

There's a one-shot org-wide audit script at `automation-tracker/scripts/audit_railway_repo_triggers.py` that lists every service missing a trigger. Worth running after a flurry of new-service work.

## Environment Variables

**Use Doppler. Don't set production env vars directly in Railway.**

NSLS standard is to source all service secrets from Doppler and let the native Doppler↔Railway integration push them into Railway env vars automatically. This lets non-engineers (Chelsea, future ops owners) manage secrets without Railway admin access — they just need an invite to the Doppler project.

### Setup (one-time per service)

1. **Identify or create the Doppler project.** Check existing projects first — services that share infrastructure share a Doppler project. Example: the `slt-coach` Doppler project hosts secrets for both the SLT Coach bot and the agenda-render-service because they share `GOOGLE_SERVICE_ACCOUNT_JSON` and Airtable creds. Only create a new project if the service serves a genuinely different domain.

   ```bash
   doppler projects                          # list existing projects
   doppler projects create <name>            # create new if needed
   ```

2. **Add secrets to the `prd` config.** Use the same names as your `.env.example`.

   ```bash
   doppler secrets set --project <name> --config prd KEY=value
   ```

3. **Wire the integration.** In the Doppler dashboard: **Integrations → Railway → Connect**. Authorize, pick the Railway project and service. Doppler now pushes secrets into Railway env vars and keeps them in sync on every change.

4. **Invite the ops owner.** Doppler dashboard → **Project → Access**. Add the ops owner (Chelsea by default) with `Editor` role.

5. **Document the Doppler project name** in the service's CLAUDE.md under "Environment Variables." This is what an inheritor reads to know where to look.

### Local Development

```bash
# Run locally with dev-config secrets injected:
doppler run --project <name> --config dev -- python app.py

# Or download to a local .env for the session (don't commit it):
doppler secrets download --project <name> --config dev --no-file --format env > .env
```

### Don't

- **Don't set prod env vars directly in Railway.** They drift from Doppler and someone (probably you) will eventually rotate the wrong one.
- **Don't commit `.env` with real secrets.** Doppler is the only source of truth.
- **Don't share secrets via Slack, email, or DM.** Add the person to Doppler.
- **Don't create a new Doppler project for every new service.** Reuse when infrastructure overlaps.

### Existing NSLS Doppler Projects

- `slt-coach` — SLT Coach bot + agenda-render-service. Google service account, Airtable, Anthropic, Fathom, Slack tokens.
- `rippling-sync` — Rippling HRIS sync job
- `people-ops` — local dev for people-ops skills
- `nsls-builder-toolkit` / `nsls-personal-toolkit` — plugin dev

### Services Not Yet on Doppler

Signal (formerly NSLS Coach) and automation-tracker-proxy still use Railway env vars directly. Migrate one at a time when touching them.

### Code Side

Reference secrets as normal environment variables — your code doesn't know they came from Doppler. `os.environ.get('KEY')` in Python, `process.env.KEY` in Node. Doppler's push to Railway means the runtime env is identical to the "set in Railway dashboard" pattern.

## Procfile Format

If Railway can't detect how to start your app, add a `Procfile` at the repo root:

```
web: python app.py
worker: python worker.py
```

Use `web` for HTTP servers (Railway routes traffic to it automatically). Use `worker` for background processes that don't need inbound traffic.

## railway.toml Basics

For more control, add a `railway.toml` at the repo root:

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "python app.py"
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

Most projects don't need this — use it when you need a custom start command or restart policy.

## Socket Mode for Slack Bots

If your Slack bot uses Socket Mode (no public URL needed), your service type is `worker`, not `web`. Set these environment variables:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

The app token requires the `connections:write` scope. Generate it in the Slack app settings under **Socket Mode**.

Socket Mode bots don't need Railway to expose a port. Don't add a `PORT` variable — it's not needed and can cause confusion.

## Monitoring Logs

In the service dashboard, click **Deployments** → select a deployment → **View Logs**.

For live logs, install the Railway CLI:

```bash
npm install -g @railway/cli
railway login
railway logs --service your-service-name
```

## Restarting Services

From the dashboard: go to the deployment, click the three-dot menu → **Restart**.

From the CLI:

```bash
railway redeploy --service your-service-name
```

If a service keeps crashing, check the logs first. Common causes: missing environment variable, syntax error, dependency not in `requirements.txt`.

## Cost

Railway charges based on usage (CPU + memory + GB transferred). Kevin monitors the team dashboard. Most NSLS automations cost under $5/month. If your service is unexpectedly expensive, it's usually a runaway loop — check the logs.
