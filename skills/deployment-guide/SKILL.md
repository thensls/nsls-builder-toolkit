---
name: deployment-guide
description: >-
  Guide for deploying NSLS automations to company-managed services. This skill
  should be used when the user says "deploy", "how do I deploy", "ship this",
  "put this in production", "Railway", "Airtable API", "Google Apps Script",
  "GAS", "Cloudflare Workers", "Val Town", or needs to choose where to host
  their automation. Covers service selection, access requests, and step-by-step
  deployment for each platform.
---

# Deployment Guide

## Service Decision Matrix

Pick the platform that matches what you're building:

| What you're building | Use | Why |
|---|---|---|
| Slack bot, web API, long-running process | Railway | Persistent containers, WebSocket support, any language |
| Quick webhook, cron job, small API (JS/TS only) | Val Town | Zero config, save and it's live in 100ms, built-in SQLite and cron |
| Data storage, structured records | Airtable API | Already used for most NSLS data |
| Spreadsheet automation, email triggers | Google Apps Script | Runs in Google Workspace, no infra needed |
| Edge worker, latency-sensitive global API | Cloudflare Workers | 300+ edge locations, ultra-low latency |
| Static HTML page, presentation | netlify-deploy skill | No company account needed |

**How to choose between Railway, Val Town, and Cloudflare Workers:**
- Need a long-running process, WebSockets, or Python/Go? → **Railway**
- Need a quick JS/TS function, webhook, cron, or prototype with zero setup? → **Val Town**
- Need global edge distribution or ultra-low latency? → **Cloudflare Workers**
- Just need a serverless function and don't care about edge? → **Val Town** (simplest path)

## Company Accounts

All deployments use NSLS company accounts, not personal ones.

NSLS runs company accounts for Railway, Val Town, Airtable, Google Workspace, and Cloudflare. Do not create personal accounts for work automations — you won't be able to transfer ownership later and it creates a support gap when you're unavailable.

If you don't have access, message Kevin in Slack: "I need access to [service] to deploy [what you're building]."

## After Deploying

Register your automation so the team knows it exists and who owns it. Say "register this automation" to track it in the automation registry.

## Reference Files

Detailed instructions for each platform:

- **Railway** — `references/railway.md`: creating services, env vars, Procfile, Socket Mode, logs
- **Airtable API** — `references/airtable-api.md`: tokens, common patterns, rate limits, gotchas
- **Google Apps Script** — `references/google-apps-script.md`: bound vs. standalone scripts, triggers, web apps
- **Val Town** — `references/val-town.md`: web editor, CLI, cron, SQLite, blob storage, secrets
- **Cloudflare Workers** — `references/cloudflare-workers.md`: Wrangler CLI, secrets, KV storage
