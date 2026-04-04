# NSLS Builder Toolkit

The NSLS Builder Toolkit gives every NSLS employee with Claude Code a set of skills for building, tracking, querying data, and deploying automations. Install once, get updates automatically.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.sh | bash
```

## First-Time Setup

After installing, run `/connect` in Claude Code to connect your data systems (PostHog, Airtable, Slack, Customer.io, n8n, and more). Each connection persists across sessions — you only do it once per system.

## Data Intelligence Skills

| Skill | What it does |
|-------|-------------|
| **connect** | Connect Claude Code to your external systems — PostHog, Airtable, Slack, and more |
| **data-intel** | Cross-system intelligence — query any connected system and cross-reference across all of them |
| **posthog** | Deep PostHog analytics — queries, dashboards, funnels, person lookup, error tracking |
| **slack** | Read and search NSLS Slack — channels, messages, threads, reactions |
| **customerio** | Customer.io campaign analytics and member lookup |
| **n8n** | Manage n8n automation workflows — create, validate, test, debug |
| **airtable** | Navigate 24+ NSLS Airtable bases — find data, query records, understand structure |
| **braintrust-evals** | LLM evaluation — run experiments, compare models, track quality |
| **skill-creation** | The rubric for building new skills that find their full shape |

## Builder Skills

| Skill | What it does |
|-------|-------------|
| **register-automation** | Track your work in the NSLS Automation Tracker |
| **product-design** | UX guardrail — generate DESIGN.md, review changes, run focus groups |
| **nsls-focus-group** | Test ideas with simulated employee panels |
| **nsls-slides** | Create branded NSLS/Society presentations |
| **frontend-slides** | Build HTML presentations |
| **google-drive** | Google Drive file management |
| **google-slides-api** | Edit existing Google Slides via API |
| **netlify-deploy** | Deploy and preview static pages |
| **pydoc-pipeline** | Generate documentation from Python code |
| **gws** | Google Workspace Sheets CLI |
| **deployment-guide** | How to deploy to Railway, Airtable, GAS, Cloudflare |
| **web-research** | Web research with AI overview extraction |
| **interrogate** | Scope a new project through structured conversation |

## Updates

Skills auto-update when you start a Claude Code session. To update manually:

```bash
cd ~/.claude/local-plugins/nsls-builder-toolkit && git pull
```

## Request a Skill

Open a [GitHub issue](https://github.com/thensls/nsls-builder-toolkit/issues) or message Kevin in Slack.

## Automation Tracker

Track all NSLS automations: [Open in Airtable](https://airtable.com/appd5oK1wLVPYZeia)
