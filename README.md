# NSLS Builder Toolkit

Organization skills for every NSLS builder — building, tracking, deploying, presenting, and researching. Install once, get updates automatically.

Also installs **Superpowers** (planning, debugging, verification) and **Compound Engineering** (brainstorm, plan, review, git) plugins.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.sh | bash
```

Then open Claude Code and say `/setup` to connect your tools and optionally install personal productivity skills.

## Org Skills

| Skill | What it does |
|-------|-------------|
| **/setup** | Onboarding — connect tools, install personal skills |
| **/register-automation** | Track your work in the NSLS Automation Tracker |
| **/product-design** | UX guardrail — DESIGN.md, reviews, focus groups |
| **/nsls-focus-group** | Test ideas with simulated employee panels |
| **/nsls-slides** | Branded NSLS/Society presentations |
| **/frontend-slides** | Build HTML presentations |
| **/google-drive** | Google Drive file management |
| **/google-slides-api** | Edit existing Google Slides via API |
| **/gws** | Google Workspace Sheets CLI |
| **/netlify-deploy** | Deploy and preview static pages |
| **/deployment-guide** | How to deploy to Railway, Airtable, GAS, Cloudflare |
| **/pydoc-pipeline** | Generate documentation from Python code |
| **/web-research** | Structured web research |
| **/interrogate** | Deep-dive investigation skill |

## Bundled Plugins

These are installed automatically by the install script:

| Plugin | What it gives you |
|--------|-------------------|
| **Superpowers** | `/brainstorm`, `/debug`, `/verify`, `/plan`, `/tdd` |
| **Compound Engineering** | `/ce:brainstorm`, `/ce:plan`, `/ce:work`, `/ce:review`, `/git-commit` |

## Personal Productivity Skills (Optional)

During `/setup`, you can optionally install personal productivity skills — daily planning, weekly reviews, project logging, relationship tracking. These are Kevin's personal template — fork them, edit them, make them yours. They live in a [separate repo](https://github.com/thensls/nsls-personal-toolkit).

## Updates

Skills auto-update when you start a Claude Code session. To update manually:

```bash
cd ~/.claude/local-plugins/nsls-builder-toolkit && git pull
```

## Request a Skill

Open a [GitHub issue](https://github.com/thensls/nsls-builder-toolkit/issues) or message Kevin in Slack.
