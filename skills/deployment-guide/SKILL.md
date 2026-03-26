---
name: deployment-guide
description: >-
  Guide for deploying NSLS automations to company-managed services. This skill
  should be used when the user says "deploy", "how do I deploy", "ship this",
  "put this in production", "Railway", "Airtable API", "Google Apps Script",
  "GAS", "Cloudflare Workers", or needs to choose where to host their
  automation. Covers service selection, access requests, and step-by-step
  deployment for each platform.
---

# Deployment Guide

## Service Decision Matrix

Pick the platform that matches what you're building:

| What you're building | Use |
|---|---|
| Slack bot, web API, long-running process | Railway |
| Data storage, structured records | Airtable API |
| Spreadsheet automation, email triggers | Google Apps Script |
| Edge worker, lightweight API | Cloudflare Workers |
| Static HTML page, presentation | netlify-deploy skill (no company account needed) |

When in doubt: if it needs to run on a schedule or respond to requests 24/7, use Railway. If it reads/writes structured data, use Airtable. If it lives in a Google Sheet, use GAS.

## Company Accounts

All deployments use NSLS company accounts, not personal ones.

NSLS runs company accounts for Railway, Airtable, Google Workspace, and Cloudflare. Do not create personal accounts for work automations — you won't be able to transfer ownership later and it creates a support gap when you're unavailable.

If you don't have access, message Kevin in Slack: "I need access to [service] to deploy [what you're building]."

## After Deploying

Register your automation so the team knows it exists and who owns it. Say "register this automation" to track it in the automation registry.

## Reference Files

Detailed instructions for each platform:

- **Railway** — `references/railway.md`: creating services, env vars, Procfile, Socket Mode, logs
- **Airtable API** — `references/airtable-api.md`: tokens, common patterns, rate limits, gotchas
- **Google Apps Script** — `references/google-apps-script.md`: bound vs. standalone scripts, triggers, web apps
- **Cloudflare Workers** — `references/cloudflare-workers.md`: Wrangler CLI, secrets, KV storage
