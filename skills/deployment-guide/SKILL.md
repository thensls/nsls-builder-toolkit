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

## Windows gotchas

For Python scripts and scheduled jobs that run on a Windows PC. Field notes from Anish Patel, checked against the Python and Microsoft docs.

- **Printing an arrow or an emoji can crash the script.** On Python 3.14 and earlier, output that is piped or redirected (a hook, a captured subprocess, `> log.txt`) is encoded in the Windows code page (CP1252 on a US-English PC), and a character outside it raises `UnicodeEncodeError`. The same script prints fine in a terminal window, so it passes a hand test and fails once automated. Fix it at the top of the script:

  ```python
  import sys
  sys.stdout.reconfigure(encoding="utf-8", errors="replace")
  ```

  For a child Python process, set `PYTHONIOENCODING=utf-8` in its environment and read its output as UTF-8 (example below).

- **Pass `encoding="utf-8"` on every file read and write.** Those Python versions use the code page for files too, so non-ASCII text comes back garbled or raises `UnicodeDecodeError`. Write `path.read_text(encoding="utf-8")`. Use `"utf-8-sig"` for a file that may start with a byte-order mark, which Windows PowerShell 5.1 adds when it saves UTF-8.

- **`env=` replaces the child's environment; it doesn't add to it.** `subprocess.run(cmd, env={"KEY": "val"})` starts the child without `PATH`, `APPDATA` or `SystemRoot`, which a Windows program can need just to start. Merge with `os.environ`:

  ```python
  subprocess.run(cmd, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                 capture_output=True, encoding="utf-8")
  ```

- **Task Scheduler, when registering a task from PowerShell:**
  - Name the account in full, as `domain\user`: `-UserId "$env:USERDOMAIN\$env:USERNAME"`. A bare username didn't work in the field; Microsoft's docs don't specify the format.
  - Use `-LogonType Interactive` for a script that needs the network (IMAP, an OAuth refresh). It runs only while that person is signed in. The `S4U` type runs signed out, but Microsoft documents it as having no access to the network or to encrypted files.
  - Add `-StartWhenAvailable` to the task settings, so a run missed while the laptop was asleep starts afterwards instead of being skipped.

Python 3.15 and later default to UTF-8, so the first two items apply to 3.14 and earlier.

## After Deploying

Register your automation so the team knows it exists and who owns it. Say "register this automation" to track it in the automation registry.

## Reference Files

Detailed instructions for each platform:

- **Railway** — `references/railway.md`: creating services, env vars, Procfile, Socket Mode, logs
- **Airtable API** — `references/airtable-api.md`: tokens, common patterns, rate limits, gotchas
- **Google Apps Script** — `references/google-apps-script.md`: bound vs. standalone scripts, triggers, web apps
- **Val Town** — `references/val-town.md`: web editor, CLI, cron, SQLite, blob storage, secrets
- **Cloudflare Workers** — `references/cloudflare-workers.md`: Wrangler CLI, secrets, KV storage
