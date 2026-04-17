# NSLS Knowledge Base + Personal Library

**Date**: 2026-04-17
**Author**: Kevin Prentiss
**Status**: Approved

## Problem

NSLS has rich institutional knowledge locked in SLT meeting transcripts (7,800+ tagged topic mentions across 30 categories), but no persistent, navigable map of "what does NSLS know about X?" Leadership context lives in people's heads and scattered across Fathom recordings, Airtable records, and Slack threads. Meanwhile, personal learning resources (articles, videos, docs) have no home — the `/learn` skill creates learning paths but doesn't persist the resources themselves.

## Solution

Three interconnected layers in Obsidian, each with a clear audience and purpose.

### Layer 1: NSLS Knowledge (`60-nsls-knowledge/`)

**What**: Institutional knowledge map — what NSLS collectively knows and has decided about key topics. Hierarchical, with parent-child relationships expressed via frontmatter links.

**Audience**: SLT only (6 people). May expand later.

**Repo**: `thensls/nsls-knowledge` (private GitHub). SLT members clone it into their Obsidian vault as `60-nsls-knowledge/`. Auto-pull on Claude Code session start via the same SessionStart hook pattern as the builder toolkit.

**NOT bundled with the builder toolkit.** Separate install, offered during SLT-specific onboarding. If a broader audience needs institutional context later, a read-only subset can be exported to the builder toolkit's `_shared/context/` (same pattern as org chart and LOPs).

#### Topic File Format

Flat directory — no folder nesting. Hierarchy via frontmatter.

`60-nsls-knowledge/chapter-health.md`:
```yaml
---
type: knowledge
category: customer-segment
parent: "[[retention]]"
related:
  - "[[client-services]]"
  - "[[college-partners]]"
owner: "[[Ashleigh Smith]]"
airtable-tag-id: recXXXXXX
last-updated: 2026-04-17
---

# Chapter Health

How healthy our on-campus chapters are — open rates, advisor engagement,
stale chapter recovery, event participation.

## What We Know
- 211 SLT meeting topics tagged to this area
- Key metric: chapter open rate (currently tracked in Snowflake)
- Stale chapters defined as: no events in 2+ semesters

## Current State
[Brief summary — what's working, what's not]

## Key Decisions
- YYYY-MM-DD: [Decision made and context]

## Open Questions
- [Unresolved threads]
```

#### Categories

Mirror the three Airtable Topic Tag types:
- `customer-segment`: Active Members, Alumni, Chapters, College Partners, GPA-Qualified Prospects, Non-GPA Students, Parents, Board, Employers
- `functional-domain`: Client Services / Member Experience, Executive / Strategy, Marketing & Growth, Product & Engineering, Finance / Operations, People / HR
- `strategic-theme`: AI / Personalization, Revenue Strategy, Data & Analytics, Tech Debt / Modernization, Risk Management, Compensation & Incentives, Legal & Compliance, Events & Gatherings, Process Debt, Brand / Positioning, Data Infrastructure, Product-Led Growth, Organizational Change, Hiring & Talent

#### Hierarchy

Expressed via `parent:` and `related:` in frontmatter:
- `parent:` — strict hierarchy ("Chapter Health" is a child of "Retention")
- `related:` — lateral connections ("Chapter Health" relates to "Client Services")
- Both render as connections in Obsidian's graph view
- A topic can have one parent and multiple related links
- Top-level topics (no parent) are the category anchors

#### Initial Seed

A script pulls the 30 Topic Tags from the SLT Airtable base (`appHDEHQA4bvlWwQq`, table `tbljhFMlpOUgbXwQq`). For each tag:
- Create a file named `{slugified-tag-name}.md`
- Populate `category` from the Airtable `category` field
- Populate `description` from the Airtable `description` field → becomes the intro paragraph
- Populate "What We Know" with the topic mention count
- `parent:` and `related:` start empty — Kevin defines the hierarchy manually (this is a design decision, not data entry)
- `owner:` starts empty — populated as Kevin assigns topic ownership

**Enrichment priority**: Start with the top 5-10 topics by meeting mention count. Fill in "Current State", "Key Decisions", and "Open Questions" from memory and recent SLT meetings. The rest can stay sparse and grow organically.

#### Index File

`60-nsls-knowledge/_index.md`:
```markdown
# NSLS Knowledge Base

The institutional map of what we know, what we've decided, and what's unresolved.

## How to Use
- Browse topics in Obsidian's file explorer or graph view
- Filter graph: `path:60-nsls-knowledge` to see just the knowledge map
- Each topic links to people (owners), other topics (parent/related), and resources (_library/)
- Topics are enriched from SLT meetings — decisions and state changes get appended automatically

## Topic Map
### Customer Segments
- [[active-members]]
- [[alumni]]
- [[chapters]]
...

### Functional Domains
...

### Strategic Themes
...
```

### Layer 2: Institutional Library (`60-nsls-knowledge/_library/`)

**What**: Resources relevant to the whole SLT — industry reports, competitor analysis, research, articles. Self-contained with URLs and descriptions. Never links into personal vaults.

**Resource file format** (`_library/duolingo-retention-playbook.md`):
```yaml
---
type: resource
format: article
url: "https://example.com/duolingo-retention"
source: "First Round Review"
date-added: 2026-04-17
topics:
  - "[[retention]]"
  - "[[product-led-growth]]"
added-by: Kevin Prentiss
---

# Duolingo's Retention Playbook

[1-3 sentence summary of why this is useful to NSLS]

## Key Takeaways
- [bullets extracted from the article]
```

### Layer 3: Personal Library (`50-reference/`)

**What**: Personal bookmarks — articles, videos, podcasts, docs. Can link into `60-nsls-knowledge/` topics and `40-learning/` goals. Private to the individual.

**Same file format as institutional library**, plus an optional `learning-goal:` field:
```yaml
---
type: resource
format: article
url: "https://example.com/leadership-coaching"
source: "Harvard Business Review"
date-clipped: 2026-04-17
topics:
  - "[[retention]]"
learning-goal: "[[retention-strategy]]"
---
```

**Key boundary**: The shared repo (`60-nsls-knowledge/`) never points into personal vaults. Personal vaults can point into the shared repo. This means:
- `50-reference/article.md` can have `topics: ["[[retention]]"]` → links to `60-nsls-knowledge/retention.md`
- `60-nsls-knowledge/retention.md` does NOT link to anyone's `50-reference/` files

### Layer 4: Learning Goals (`40-learning/`)

**What**: Already exists. Personal learning paths managed by `/learn` skill.

**Change**: `/learn` skill should save resources to `50-reference/` and wikilink them from the learning goal, instead of embedding URLs inline. This connects learning resources to the broader graph.

## Ingest Paths

| Source | Destination | How |
|--------|------------|-----|
| Obsidian Web Clipper | `50-reference/` | Clip creates resource file. User tags with topics. If NSLS-relevant, user also creates a stub in `_library/` |
| `/learn` skill | `50-reference/` | Saves resource file, links from learning goal |
| Close-day (insight proposal) | `60-nsls-knowledge/` topic file | Claude surfaces specific insights from meetings/reading, user approves one-liner |
| Close-week | `60-nsls-knowledge/` topic file | Heavier pass — consolidates week's decisions, updates Current State if shifted |
| Manual | Either | Just create a file |
| SLT meeting seed script | `60-nsls-knowledge/` | Initial population from Airtable Topic Tags |

## Close-Day Knowledge Integration

The close-day skill gains a knowledge graph step after processing meetings and screen activity:

1. Match the day's meetings and reading to `60-nsls-knowledge/` topic files
2. For matched topics, look for: **debates, disagreements, surprising data points, changed positions, new frameworks** — signals of actual insight, not just "this was discussed"
3. Surface 0-3 candidates with specific evidence:
   > "You had a detailed exchange with Ashleigh about chapter health. She argued advisor turnover is the primary driver of stale chapters, citing UPhoenix and two other examples. This contradicts the assumption that it's event frequency. Capture this?"
4. If approved, append a dated one-liner to the topic's `## Key Decisions` or `## Current State`
5. If nothing interesting — nothing surfaced. No noise.

**Bloat control**: 
- Decisions and state changes only — not "discussed X"
- 0 candidates most days
- One-liners, not paragraphs
- Close-week consolidates redundant entries

## Close-Week Knowledge Integration

Weekly pass with a broader lens:
- Review all knowledge graph entries from the week
- Consolidate any redundant one-liners
- Update `## Current State` if the overall picture on a topic shifted
- Flag topics with no activity that might need attention (optional, light touch)

## Repo Structure

```
thensls/nsls-knowledge/
  README.md              ← How to install, contribute, use
  CLAUDE.md              ← Conventions for Claude Code sessions
  60-nsls-knowledge/
    _index.md            ← Topic map overview
    _library/            ← Institutional resources
      duolingo-retention.md
      ...
    active-members.md    ← Topic files (flat, ~30 to start)
    alumni.md
    ai-personalization.md
    brand-positioning.md
    chapter-health.md
    chapters.md
    client-services.md
    college-partners.md
    compensation-incentives.md
    data-analytics.md
    data-infrastructure.md
    employers.md
    events-gatherings.md
    executive-strategy.md
    finance-operations.md
    gpa-qualified-prospects.md
    hiring-talent.md
    legal-compliance.md
    marketing-growth.md
    non-gpa-students.md
    organizational-change.md
    parents.md
    people-hr.md
    process-debt.md
    product-engineering.md
    product-led-growth.md
    retention.md          ← not in seed tags, but implied as a parent — create manually
    revenue-strategy.md
    risk-management.md
    tech-debt-modernization.md
    board.md
    ...
```

## Installation for SLT Members

Separate from builder toolkit. A simple script or manual clone:

```bash
git clone https://github.com/thensls/nsls-knowledge.git \
  "$OBSIDIAN_VAULT_PATH/60-nsls-knowledge"
```

The SessionStart hook (if builder toolkit is installed) can auto-pull this repo too. Otherwise, manual `git pull`.

**Not part of `/setup` or `/personal-setup`** — this is SLT-only and offered separately.

## Future Expansion

- **Broader audience**: Export a read-only subset (e.g., strategy, LOPs, topic summaries without meeting-level detail) to the builder toolkit's `_shared/context/`. Builders get institutional context without SLT-level detail.
- **Topic ownership**: Each topic gets an `owner:` who's responsible for keeping "Current State" accurate. Close-week could nudge: "3 topics you own haven't been updated in 4 weeks."
- **Hierarchy refinement**: Start with flat + frontmatter links. If the taxonomy grows past ~50 topics, consider Obsidian's folder structure for the top-level categories.
- **PR contributions from SLT**: Once the base is established, SLT members can submit PRs to update topics they own. Same PR-gated model as the builder toolkit.

## Files to Create or Modify

### New repo: `thensls/nsls-knowledge`
- `README.md`
- `CLAUDE.md`
- `60-nsls-knowledge/_index.md`
- `60-nsls-knowledge/_library/` (empty directory with .gitkeep)
- `60-nsls-knowledge/*.md` (~30 topic files from seed)

### Modified in `nsls-personal-toolkit`
- `skills/close-day/SKILL.md` — add knowledge graph insight proposal step
- `skills/close-week/SKILL.md` — add knowledge graph consolidation step
- `skills/learn/SKILL.md` — save resources to `50-reference/` instead of inline

### New in personal vault (not in any repo)
- `50-reference/` — populated by web clipper, `/learn`, and close-day over time

## Security Considerations

- Knowledge repo is private GitHub — only SLT members have access
- No sensitive data in topic files (meeting evidence is summarized, not quoted verbatim)
- `_library/` resources are links to external articles, not proprietary content
- Personal library (`50-reference/`) never leaves the individual's machine
- Future broader sharing would be a deliberate, curated export — not opening the repo
