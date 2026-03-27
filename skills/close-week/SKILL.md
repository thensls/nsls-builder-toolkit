---
name: close-week
description: Friday morning weekly roll-up — synthesizes Mon-Thu daily notes into achievements, learnings, project progress, time allocation, and priorities-vs-reality. Formatted for quick notes copy-paste. Trigger phrases: close week, weekly review, week summary, week roll up, friday summary, weekly wrap, end of week
---

# Close Week

Roll up the week's daily notes into a structured weekly review. Output is formatted for copy-paste into the NSLS Coach quick notes journal. Run Friday morning before 10 AM.

## When to Run

Friday morning, before Kevin's quick notes reminder fires. Output feeds directly into the weekly journal.

## Step-by-step Execution

### Step 0: Determine the week

Default to the current week (Monday through today). Kevin can override: `/close-week 2026-03-17` (uses that Monday as the start).

Calculate:
- Monday date = start of week
- Friday date = today (or target Friday)
- Date range string for display: "Mar 24 - Mar 28, 2026"

### Step 1: Collect data (run in parallel)

**1a. Read all daily notes for the week**

Read files from `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/KP/01-daily/`:
- `YYYY-MM-DD.md` for Monday through Thursday (Friday's may not exist yet)

Extract from each:
- `## Morning Check-in` → Top 3 priorities (especially Monday's — these are the week plan)
- `## Work Log` → all bullets
- `## Meetings` → count and key meetings
- `## Projects Touched` → project list
- `## Carrying Over` → what slipped each day
- `## Time Distribution` → capture counts by category

**1b. Familiar time data for the full week**

```bash
for d in Mon Tue Wed Thu Fri; do
  DATE=$(date -v-${offset}d +%Y-%m-%d)  # compute each day
  grep -h "^app:" $HOME/familiar/stills-markdown/session-${DATE}T*/*.md 2>/dev/null \
    | sort | uniq -c | sort -rn
done
```

And Chrome breakdown:
```bash
for d in Mon-Fri dates; do
  awk '/^app: Google Chrome/{found=1} found && /^window_title_raw:/{print; found=0}' \
    $HOME/familiar/stills-markdown/session-${DATE}T*/*.md 2>/dev/null
done | sort | uniq -c | sort -rn
```

Use the same categorization rules from `/close-day` (Gmail, YouTube, Airtable, etc.). Exclude personal finance. Compute weekly totals and percentages.

**1c. Asana tasks completed this week**

```
mcp__claude_ai_asana__asana_search_tasks(
  assignee_any="me",
  completed=true,
  completed_on_after="YYYY-MM-DD",  // Monday
  completed_on_before="YYYY-MM-DD",  // Saturday
  sort_by="completed_at",
  opt_fields="name,completed_at,projects.name",
  limit=100
)
```

**1d. Asana tasks still overdue**

```
mcp__claude_ai_asana__asana_search_tasks(
  assignee_any="me",
  completed=false,
  due_on_before="YYYY-MM-DD",  // today (Friday)
  sort_by="due_date",
  sort_ascending=true,
  opt_fields="name,due_on,projects.name",
  limit=50
)
```

### Step 2: Synthesize

**Achievements:** Scan all Work Log bullets across the week. Pick the 5-8 most impactful — things that shipped, decisions that moved the needle, external commitments met. Prefer concrete outcomes with numbers over activity descriptions.

**Learnings:** Look for:
- Patterns across meetings (Fathom themes)
- Things that failed or were harder than expected
- Insights from conversations (Slack, email)
- Process improvements discovered
- "I wish I had..." moments from carry-overs that piled up

**Project Progress:** For each project that appeared in any daily note's `## Projects Touched`, summarize the week's movement. Status = on-track (touched 2+ days or key milestone hit), needs-attention (touched but blocked), stalled (not touched despite being active).

**Time Allocation:** Aggregate Familiar data across all 5 days:
- Meetings (Google Meet + Zoom captures)
- Building (Warp + Claude web captures)
- Communication (Slack + Gmail captures)
- Deep work (Obsidian + Google Docs + Airtable captures)
- Content (YouTube + News captures)
- Other

Convert to hours (rough: total captures / captures-per-hour based on Familiar's capture interval, typically 1 capture per ~10-15 seconds, so ~240/hr).

**Priorities vs. Reality:** Pull Monday's Top 3 from the daily note. For each, assess:
- **Done** — clear evidence in Work Log
- **Partial** — worked on but not finished (note what remains)
- **Missed** — no evidence of progress (note why if detectable)

### Step 3: Generate two outputs

**Output A: Weekly Review note** (for Obsidian)

Write to: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/KP/02-weekly/YYYY-[W]WW.md`

Full format with Dataview queries for projects touched/not touched.

**Output B: Quick Notes format** (for copy-paste into NSLS Coach journal)

Present this in the conversation for Kevin to copy:

```
Achievements:
- [Concrete outcome — shipped, decided, or delivered]
- [Concrete outcome]
- [Concrete outcome]

Learnings:
- [What I'd do differently or insight gained]
- [Pattern noticed across the week]

Project Progress:
[Project]: [on-track/needs-attention/stalled] — [1-line summary]
[Project]: [status] — [1-line]

Time Allocation:
- Meetings: Xh (Y%)
- Building: Xh (Y%)
- Communication: Xh (Y%)
- Deep work: Xh (Y%)
- Content/learning: Xh (Y%)

Priorities vs. Reality:
1. [Monday priority] → [Done/Partial/Missed] — [1-line]
2. [Monday priority] → [Done/Partial/Missed]
3. [Monday priority] → [Done/Partial/Missed]
```

**Rules for quick notes format:**
- Keep it tight. This goes into a Slack bot journal — not a novel.
- Lead with achievements, not activities.
- Learnings should be genuine insights, not platitudes. "Discovered DDC IT overage is $15k/mo — need to renegotiate" not "Learned about vendor management."
- Project progress should flag what needs CEO attention, not just list updates.
- Time allocation should make Kevin think: "Am I spending time on what matters?"
- Priorities vs. Reality is the accountability moment — be honest.

### Step 4: Present to Kevin

Show both outputs. Ask:
- "Anything to add or adjust before I write the weekly note?"
- "Quick notes version ready to paste — want any edits?"

### Step 5: Write weekly note

Write Output A to `02-weekly/YYYY-[W]WW.md`.

### Step 6: Asana sync

Create any new tasks surfaced by the weekly review:
- Stalled projects that need CEO attention → P2 task for next week
- Carry-forward items that have been carrying all week → bump to P1
- Process improvements identified in Learnings → P3 tasks

Use the same Asana write-back pattern as `/close-day` — present plan, Kevin approves, then create.

## Edge Cases

- **Missing daily notes:** Some days may not have `/close-day` run. Use whatever exists — even partial daily notes have Morning Check-in priorities.
- **No Familiar data for a day:** Skip that day in time allocation, note the gap.
- **Short week (holiday, PTO):** Adjust date range. Still generate — even a 3-day week deserves a roll-up.
- **Kevin ran /close-week already this week:** Check if `02-weekly/YYYY-[W]WW.md` exists. If so, ask if he wants to regenerate or append.
