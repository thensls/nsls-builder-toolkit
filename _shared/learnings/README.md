# Shared Learnings

Greppable, PR-gated bucket for things NSLS builders discover while doing the work. Written by `/kw:compound`, read by `knowledge-researcher` as part of tier 1.

## What belongs here

Four types of compoundable learning:

| Type | Signals | Example |
|------|---------|---------|
| **insight** | "We discovered X", counter-intuitive finding, surprising data | Extended trials increase conversion but delay revenue recognition |
| **playbook** | Repeatable process that worked, step-by-step | How to onboard a new chapter success specialist |
| **correction** | Wrong assumption fixed, data source clarified, definition updated | `filterByFormula` uses field names, not field IDs |
| **pattern** | Recurring phenomenon, systemic observation | Mobile release freezes push non-critical work two weeks |

## What does NOT belong here

- **Project status / in-flight work** → project docs or Obsidian `20-projects/`
- **SLT-confidential decisions** → `60-nsls-knowledge/` (SLT-only repo)
- **Personal preferences / ways of working** → your Obsidian operating memo
- **API credentials, secrets, PII** → never here, never anywhere in a repo
- **Stale learnings that have been superseded** → remove, or update the existing entry

## File format

One learning per file. Filename: `{type}-{descriptive-slug}.md`.

```markdown
---
type: insight | playbook | correction | pattern
tags: [relevant, keywords, for, grep, and, retrieval]
confidence: high | medium | low
created: YYYY-MM-DD
source: "Brief description of what triggered this — a project, a bug, a meeting"
owner: "Name (optional, for playbooks the author wants to own updates for)"
---

# [Learning title — one sentence, imperative if it's a playbook]

[2–4 sentences explaining the learning. Specific enough that someone reading this in 3 months understands what happened and why it matters.]

## Context

[What you were doing when you discovered this.]

## Implication

[How this should change future work. Be concrete: "When doing X, always check Y first."]
```

## Conventions

- **Filename** — lowercase, hyphen-separated, starts with the type. Examples: `correction-airtable-filter-formulas.md`, `playbook-onboarding-new-cs-specialist.md`.
- **Tags** — 3–7 keywords. Think: "what future question would this answer?" Tags are for `/kw:brainstorm` and `/kw:plan` grep, so choose terms the searcher will actually type.
- **Confidence** — `high` if verified across multiple sessions or with data. `low` if based on one data point; note the caveat in the body.
- **Never duplicate.** Before adding a new file, grep existing entries for the same topic. Update the existing entry if one exists.
- **Quality over quantity.** A folder of 50 sharp learnings beats 200 vague ones. `/kw:compound` enforces 1–3 learnings per session — respect that.

## Retrieval

`knowledge-researcher` includes this folder in its tier 1 read. `/kw:brainstorm` and `/kw:plan` surface relevant entries automatically.

Manual retrieval:

```bash
# grep by keyword
grep -rli "airtable" _shared/learnings/

# grep by tag (YAML frontmatter)
grep -l "tags:.*airtable" _shared/learnings/

# list by type
ls _shared/learnings/correction-*.md
```

## PR flow

Changes land through PRs like the rest of the builder toolkit. Treat this as institutional memory — you're writing for the team and for future-you.
