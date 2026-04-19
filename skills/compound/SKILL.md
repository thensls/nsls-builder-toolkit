---
name: kw:compound
description: "Extract and save learnings from a completed session so future work finds them. Routes each learning to the right tier — personal Obsidian, team-shareable _shared/learnings/, or SLT knowledge graph. Trigger phrases: compound this, save what we learned, what should we remember, kw:compound, /kw:compound, close the loop, extract learnings. Run at the end of meaningful work sessions — after a plan ships, after a bug is fixed with a surprising root cause, after a meeting that changed your mind."
---

# /kw:compound — Close the Loop

Extract 1–3 learnings from the current session and save them where future work will find them. This is how NSLS's institutional memory accretes instead of evaporating.

## When to Use

- After completing a plan, campaign, analysis, or strategy session
- After a data correction, process fix, or strategic insight
- After a bug fix with a surprising root cause
- At the end of any meaningful work session where something non-obvious was learned

**"Nothing to compound" is a valid outcome.** Most sessions don't produce compoundable learnings. Don't fabricate.

## The Three Destinations

| Destination | Audience | Location | When to use |
|-------------|----------|----------|-------------|
| **Personal** | You | `$OBSIDIAN_VAULT_PATH/40-learning/` (learning dashboards) or `20-projects/{name}.md` (project decisions) | Private insight about how you work, a project decision worth remembering |
| **Team** | All NSLS builders | `_shared/learnings/{type}-{slug}.md` (PR to `nsls-builder-toolkit`) | Reusable playbook, API gotcha, process correction, technical pattern |
| **Institutional** (SLT only) | SLT, via Obsidian | `$OBSIDIAN_VAULT_PATH/60-nsls-knowledge/{topic}.md` (PR to `thensls/nsls-knowledge`) | Strategic decision, changed position on a business topic, resolved open question from the knowledge graph |

**Rule:** if it's confidential to SLT, it does NOT go to `_shared/learnings/`. If it's about how you personally work, it does NOT go institutional. When in doubt, ask.

## Process

### Step 1: Identify candidate learnings

Scan the current session for signals:

| Type | Signals |
|------|---------|
| **Insight** | "We discovered...", surprising finding, counter-intuitive result, changed position |
| **Playbook** | Repeatable process that worked, step-by-step others could follow |
| **Correction** | Wrong assumption fixed, data source clarified, definition updated, silent-failure mode found |
| **Pattern** | Something that keeps recurring, systemic observation across multiple instances |

**Extract 1–3 learnings max.** If more feel worth saving, you're not filtering enough. If none feel worth saving, say so:

> "Nothing from this session looks worth saving as a standalone learning. The work is captured in the plan/deliverables/commit. Done."

For each candidate, draft:

```
**Learning:** [One sentence — what we now know]
**Type:** [insight | playbook | correction | pattern]
**Why it matters:** [One sentence — how this changes future work]
**Proposed destination:** [personal | team | institutional]
```

### Step 2: Get approval

Present the drafted learnings and ask:

> "Found [N] learnings worth saving. Review and approve?"

Show each with classification and destination. User can:
- Approve as-is
- Edit wording, type, or destination
- Skip individual learnings
- Add learnings you missed

**Do not save anything without approval.**

### Step 3: Check for duplicates

For each approved learning, grep existing destinations:

```bash
# Team tier
grep -rli "[keyword 1]" _shared/learnings/
grep -l "tags:.*[key-tag]" _shared/learnings/

# Personal tier (if going to Obsidian)
grep -rli "[keyword]" "$OBSIDIAN_VAULT_PATH/40-learning/" "$OBSIDIAN_VAULT_PATH/20-projects/"

# Institutional tier (SLT only)
grep -rli "[keyword]" "$OBSIDIAN_VAULT_PATH/60-nsls-knowledge/"
```

If a similar entry exists:
- Show the existing file
- Ask: "Update the existing entry, or save as new?"
- If updating, open the existing file, show the current body, and edit — don't create a parallel file

### Step 4: Check for stale / contradicted knowledge

Before saving, look for existing entries the new learning might **contradict**. Grep destinations for tag overlap. For each candidate contradiction, present:

> "This new learning may supersede:
> - **[existing file]** says [X].
> - The new learning says [Y].
>
> What should happen to the old entry?"
>
> Options: **Update** (merge into the new one) / **Remove** (it's wrong now) / **Keep both** (they address different contexts)

Only the user decides. Do not auto-modify.

### Step 5: Save

Based on destination:

**Team — `_shared/learnings/{type}-{slug}.md`:**

```markdown
---
type: insight | playbook | correction | pattern
tags: [3-7 keywords for grep and retrieval]
confidence: high | medium | low
created: YYYY-MM-DD
source: "Brief description of what triggered this"
owner: "Name (optional)"
---

# [Learning title]

[2–4 sentences explaining the learning. Specific enough to be useful in 3 months.]

## Context

[What you were doing when you discovered this.]

## Implication

[How this should change future work. Concrete: "When doing X, check Y first."]
```

After writing, stage and commit on a branch named `compound-{slug}`. Push and offer to open a PR.

**Personal — Obsidian:**
- Insight/pattern about how you work → append to `40-learning/{relevant-topic}.md` under a `## Learnings` section
- Project decision → append to `20-projects/{project}/{project}.md` under `## Key Decisions`
- Standalone insight with no existing home → new file at `40-learning/_insights/{slug}.md`

Use the same frontmatter schema as team tier (type, tags, confidence, created, source).

**Institutional — SLT knowledge graph (`60-nsls-knowledge/`):**
- Edit the matching topic file: append a dated one-liner to `## Key Decisions` or update `## Current State`
- Format: `- YYYY-MM-DD: [decision or state change — one line]`
- Stage, commit, push to `thensls/nsls-knowledge`, open a PR (this is a separate repo from the builder toolkit)

### Step 6: Confirm

```
## Compounded

**Saved:**
- [destination 1] — [path]
- [destination 2] — [path]

**This will surface in future /kw:brainstorm and /kw:plan calls** for topics tagged:
- [tag list]

[If team or institutional tier, link to the PR.]
```

Use AskUserQuestion for next steps:

**Question:** "Learnings saved. What next?"

**Options:**
1. **Run `/kw:plan`** — Start a new planning cycle (the new learnings will surface)
2. **Share in Slack** — Draft a brief post announcing the learning to the team
3. **Done** — Close the loop

## Important Rules

- **1–3 learnings max per session.** Filtering is the work.
- **Approval required.** Never auto-save. The user decides what's worth remembering.
- **Be specific.** "Use the right data source" is useless. "HubSpot counts are authoritative; PostHog person counts drift by ~8% due to anonymous user merging — use HubSpot for board numbers" is useful.
- **Tags are for retrieval.** Think "what future question would this answer?"
- **Confidence matters.** `low` if based on one data point — note the caveat in the body so readers calibrate.
- **Duplicates are waste.** Always check before creating. Update existing entries when possible.
- **Respect tier boundaries.** SLT-confidential insights never go to `_shared/learnings/`. Personal operating patterns never go institutional.
- **Contradictions need explicit resolution.** If a new learning supersedes an old one, update or remove the old one in the same session.

## Writing Style

Match Kevin's voice (plain language, numbers > adjectives, no corporate-speak). Every learning should pass the 3-month test: will someone reading this in 3 months understand what happened and why it matters without needing to ask?
