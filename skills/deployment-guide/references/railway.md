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

Railway redeploys automatically on every push to the default branch. To deploy a specific branch, change the source branch in the service settings.

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
