---
name: open-day
description: Morning routine — pulls calendar, Asana tasks, overdue items, and yesterday's carry-overs to set daily priorities. Trigger phrases: open day, start day, morning, good morning, what's on my plate, what do I have today
---

# Open Day

Pull today's calendar, Asana tasks, overdue items, and yesterday's carry-overs to populate the Morning Check-in section of today's daily note.

## When to Run

Morning, before first meeting. Can also be triggered mid-day to reset priorities.

## Asana Reference

- **Workspace GID:** `657431271309846`
- **Kevin's user GID:** `1212312899409797`

## Step-by-step Execution

### Step 1: Determine today's date

```bash
date +%Y-%m-%d
```

### Step 2: Collect data (run in parallel)

**2a. Google Calendar — today's meetings**

```
gcal_list_events(
  timeMin="YYYY-MM-DDT00:00:00",
  timeMax="YYYY-MM-DDT23:59:59",
  timeZone="America/New_York",
  condenseEventDetails=false
)
```

Extract: meeting title, start/end time, attendees. Flag meetings that need prep (external attendees, board members, candidates).

**2b. Asana — what's due and overdue**

Two parallel calls:

```
mcp__claude_ai_Asana__get_my_tasks(
  completed_since="now",
  limit=100,
  opt_fields="name,due_on,projects.name,assignee_section.name"
)
```

```
mcp__claude_ai_asana__asana_search_tasks(
  assignee_any="me",
  completed=false,
  due_on_before="YYYY-MM-DD+1",  // include today
  sort_by="due_date",
  sort_ascending=true,
  opt_fields="name,due_on,projects.name",
  limit=50
)
```

Categorize:
- **Overdue** — due before today
- **Due today** — due today
- **Do today section** — tasks in "Do today" Asana section regardless of due date

Filter out auto-generated noise ("It's time to update your goal(s)").

**2c. Yesterday's carry-overs**

Read yesterday's daily note:
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/KP/01-daily/YYYY-MM-DD-1.md
```

Extract the `## Carrying Over` section. These are unfinished items from yesterday.

**2d. This week's plan (if it exists)**

Check for a weekly plan note:
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/KP/02-weekly/YYYY-[W]WW.md
```

If it exists, extract the `## Next Week Priorities` or `## This Week's Focus` section. These are the strategic priorities for the week.

### Step 3: Draft Morning Check-in

Present to Kevin:

```markdown
## Morning Check-in

### Today's Meetings ([count])
- **HH:MM** — [Title] (with [key attendees])
  - Prep: [if external/board/candidate, note what to prepare]
- **HH:MM** — [Title]

### Suggested Top 3
1. [P1 Asana task or carry-over — explain why it's #1]
2. [Next most important — from Asana, carry-over, or week plan]
3. [Third — balance strategic and tactical]

*Based on: [N] overdue Asana tasks, [N] carry-overs from yesterday, week plan priorities.*

### Overdue ([count])
- [ ] [Task] (due [date]) — [project]
- [ ] [Task] (due [date])

### Also on the plate
- [ ] [Due today tasks]
- [ ] [Do today section tasks]
- [ ] [Carry-overs not in top 3]
```

**Priority inference for Top 3:**
1. Anything with an external deadline today (meeting prep, deliverable due)
2. P1 Asana tasks that are overdue
3. Carry-overs that have been carrying for multiple days (check previous daily notes)
4. Week plan priorities that haven't gotten attention yet
5. Quick wins that unblock others

### Step 4: Kevin reviews and adjusts

Kevin sets his actual Top 3 and energy level. The suggestions are a starting point.

### Step 5: Write daily note

Check if `01-daily/YYYY-MM-DD.md` already exists:
- **Exists:** Update the Morning Check-in section only, preserve everything else
- **Doesn't exist:** Create from template with Morning Check-in populated

Write to:
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/KP/01-daily/YYYY-MM-DD.md
```

The daily note should include:
```markdown
# YYYY-MM-DD — [Day of Week]

## Morning Check-in
- Energy: [blank for Kevin]
- Top 3 priorities today:
  1. [Kevin's chosen or suggested #1]
  2. [#2]
  3. [#3]

## Today's Meetings
- **HH:MM** — [Title] (with [attendees])
- **HH:MM** — [Title]

## Asana
**Overdue:**
- [ ] [Task] (due [date])

**Due today:**
- [ ] [Task]
```

The `## Work Log`, `## Projects Touched`, `## Carrying Over`, and `## End of Day` sections are left empty — `/close-day` fills those in.

### Day-of-Week Additions

Include role-specific reminders based on the day:

- **Monday:** "Review topic submissions in Slack. Prepare weekly update + draft agenda. Check Airtable for open action items."
- **Tuesday:** Flag SLT meeting type (tactical or strategic based on week-of-month). "Pre-meeting: Finalize agenda. Post-meeting: Trigger assessment."
- **Friday:** "SLT topic request goes out at 3 PM ET. Run /close-week before quick notes."

## Edge Cases

- **Weekend:** Still generate if Kevin asks, but skip meeting prep and Asana overdue (he knows it's the weekend).
- **No carry-overs:** Skip that section.
- **Empty calendar:** Note "No meetings today — deep work day?" and suggest tackling overdue Asana items.
