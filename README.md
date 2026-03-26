# NSLS Builder Toolkit

The NSLS Builder Toolkit gives every NSLS employee with Claude Code a set of skills for building, tracking, and deploying automations. Install once, get updates automatically.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.sh | bash
```

## Included Skills

| Skill | What it does |
|-------|-------------|
| **register-automation** | Track your work in the NSLS Automation Tracker |
| **product-design** | UX guardrail — generate DESIGN.md, review changes, run focus groups |
| **nsls-focus-group** | Test ideas with simulated employee panels |
| **nsls-slides** | Create branded NSLS/Society presentations |
| **frontend-slides** | Build HTML presentations |
| **google-docs** | Google Drive file management |
| **google-slides-api** | Edit existing Google Slides via API |
| **netlify-deploy** | Deploy and preview static pages |
| **log** | Log progress to Obsidian project files |
| **close-day** | End-of-day summary from calendar, Slack, email |
| **familiar** | Screen capture activity tracking (optional, opt-in) |
| **pydoc-pipeline** | Generate documentation from Python code |
| **gws** | Google Workspace Sheets CLI |
| **deployment-guide** | How to deploy to Railway, Airtable, GAS, Cloudflare |

## Updates

Skills auto-update when you start a Claude Code session. To update manually:

```bash
cd ~/.claude/local-plugins/nsls-builder-toolkit && git pull
```

## Request a Skill

Open a [GitHub issue](https://github.com/thensls/nsls-builder-toolkit/issues) or message Kevin in Slack.

## Automation Tracker

Track all NSLS automations: [Open in Airtable](https://airtable.com/appd5oK1wLVPYZeia)
