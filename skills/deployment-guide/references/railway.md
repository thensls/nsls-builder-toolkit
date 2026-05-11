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

Never commit secrets to the repo. Set them in Railway instead.

In the service dashboard, go to **Variables** and add each key/value pair. Reference them in code as normal environment variables (`os.environ.get('KEY')` in Python, `process.env.KEY` in Node).

For secrets shared across multiple services (like a shared Airtable token), add them once at the project level under **Shared Variables**.

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
