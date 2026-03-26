---
name: obsidian-setup
description: >-
  Set up a new Obsidian knowledge base matching the NSLS builder pattern. This
  skill should be used when the user says "set up Obsidian", "create a vault",
  "obsidian setup", "start my knowledge base", "I want to use Obsidian", or
  mentions wanting a project tracking system like Kevin's. Walks through
  vault creation, folder structure, templates, plugins, and configuration.
---

# Obsidian Setup

Set up a new Obsidian vault for an NSLS builder with project tracking, daily notes, people notes, and dataview queries. Claude automates everything it can via the filesystem, then provides a short manual checklist for steps that require the Obsidian app.

## Prerequisites

Obsidian must be installed first. If not installed:

> Download Obsidian (free) from https://obsidian.md and install it. Then come back here.

## Step 1: Create the Vault

Ask the builder:
1. **Where should the vault live?** Recommend `~/Obsidian/KP/` for local, or iCloud for cross-device sync:
   - Local: `~/Obsidian/[initials]/`
   - iCloud: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/[initials]/`
2. **What are your initials?** (Used as the vault folder name)

Create the vault directory:
```bash
mkdir -p [vault_path]
```

## Step 2: Create Folder Structure

```bash
mkdir -p [vault_path]/{_templates,00-inbox,00-inbox/attachments,01-daily,02-weekly,03-journal,10-slt,20-projects,30-people,40-learning,50-reference}
```

### What each folder is for:

| Folder | Purpose |
|--------|---------|
| `_templates` | Templater templates — daily notes, project homes, person notes |
| `00-inbox` | Default location for new notes. Triage later. |
| `01-daily` | Daily notes (auto-created by Calendar plugin) |
| `02-weekly` | Weekly review notes |
| `03-journal` | Personal journal entries (optional, can be encrypted) |
| `10-slt` | SLT meeting notes (skip if not SLT-adjacent) |
| `20-projects` | One subfolder per project with a home note and sessions folder |
| `30-people` | One note per person — relationship context, 1:1 notes |
| `40-learning` | Notes from reading, courses, ideas |
| `50-reference` | Stable reference material — schemas, docs, policies |

## Step 3: Create Templates

Create these 5 template files in `[vault_path]/_templates/`. Read `references/templates/` for the full content of each template.

| Template | Purpose |
|----------|---------|
| `daily-note.md` | Morning check-in, active projects dataview, work log, end-of-day dump |
| `weekly-review.md` | Portfolio review, projects touched/not touched, next week priorities |
| `project-home.md` | YAML frontmatter (status, priority, collaborators), current state, decisions, open questions |
| `person.md` | Role, org, shared projects dataview, 1:1 notes, background |
| `journal-entry.md` | Freeform reflection — what happened, how you feel, what you're carrying |

## Step 4: Configure Obsidian Settings

Create `[vault_path]/.obsidian/app.json`:
```json
{
  "newFileLocation": "folder",
  "newFileFolderPath": "00-inbox",
  "attachmentFolderPath": "00-inbox/attachments",
  "useMarkdownLinks": true,
  "showLineNumber": false,
  "spellcheck": false,
  "strictLineBreaks": false,
  "alwaysUpdateLinks": true
}
```

This sets:
- New notes go to the inbox by default
- Attachments go to `00-inbox/attachments`
- Use `[[wikilinks]]` style (Obsidian's strength)

## Step 5: Configure Plugin List

Create `[vault_path]/.obsidian/community-plugins.json`:
```json
[
  "templater-obsidian",
  "calendar",
  "dataview",
  "table-editor-obsidian",
  "obsidian-kanban",
  "omnisearch",
  "smart-connections",
  "obsidian-tasks-plugin"
]
```

## Step 6: Configure Templater

Create `[vault_path]/.obsidian/plugins/templater-obsidian/` directory and `data.json`:
```json
{
  "command_timeout": 5,
  "templates_folder": "",
  "templates_pairs": [["", ""]],
  "trigger_on_file_creation": true,
  "auto_jump_to_cursor": false,
  "enable_system_commands": false,
  "shell_path": "",
  "user_scripts_folder": "",
  "enable_folder_templates": true,
  "folder_templates": [
    {
      "folder": "01-daily",
      "template": "_templates/daily-note.md"
    }
  ],
  "syntax_highlighting": true,
  "syntax_highlighting_mobile": false,
  "enabled_templates_hotkeys": [["", ""]],
  "startup_templates": [""]
}
```

This auto-applies the daily note template when a note is created in `01-daily/`.

## Step 7: Manual Steps Checklist

After creating all files, present this checklist to the builder:

> I've set up your vault structure, templates, and configuration files. Now open Obsidian and do these steps:
>
> 1. **Open the vault** — Launch Obsidian > "Open folder as vault" > select `[vault_path]`
> 2. **Enable community plugins** — Settings (gear icon) > Community Plugins > Turn on community plugins > click "Turn on"
> 3. **Install plugins** — Settings > Community Plugins > Browse. Install these 8 plugins:
>    - **Templater** — template engine with date/logic support
>    - **Calendar** — calendar sidebar, click a date to create daily notes
>    - **Dataview** — query your notes like a database (powers the project dashboards)
>    - **Table Editor** — edit markdown tables visually
>    - **Kanban** — drag-and-drop kanban boards from markdown
>    - **Omnisearch** — fast full-text search across your vault
>    - **Smart Connections** — AI-powered related notes (needs API key)
>    - **Tasks** — checkbox task tracking with due dates and queries
> 4. **Enable each plugin** — After installing, go back to Community Plugins and toggle each one on
> 5. **Restart Obsidian** — Close and reopen to pick up the Templater config
> 6. **Test** — Click today's date in the Calendar sidebar. It should create a daily note in `01-daily/` with the template applied.
>
> **Optional:**
> - Smart Connections needs an API key (OpenAI or Anthropic) — set it in Settings > Smart Connections if you want AI-related notes
> - Meld Encrypt — install if you want to encrypt sensitive journal entries

## Step 8: Create First Project

After the builder confirms the manual steps are done, offer to create their first project:

> Want to create your first project? Tell me:
> - What's the project name?
> - One sentence — what is it?
> - Who else is involved?

Then create:
- `[vault_path]/20-projects/[slug]/[slug].md` using the project-home template
- `[vault_path]/20-projects/[slug]/sessions/` directory

## Customization Notes

Tell the builder:

> This is a starting point, not a prescription. Common customizations:
> - **Don't need SLT folders?** Delete `10-slt/` and remove the SLT-specific sections from the daily note template.
> - **Don't do weekly reviews?** Delete `02-weekly/` and the weekly-review template.
> - **Want different daily note sections?** Edit `_templates/daily-note.md` to match your workflow.
> - **Prefer a different folder structure?** Rename or reorganize. The templates use relative paths that adapt.
> - **Don't want journaling?** Delete `03-journal/` and the journal-entry template.

The only thing that matters is that `20-projects/` follows the convention (one subfolder per project with a home note) so the `log` and `close-day` skills can find your projects.
