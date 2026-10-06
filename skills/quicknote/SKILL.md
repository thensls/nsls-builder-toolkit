---
name: quicknote
description: >-
  Draft your weekly Signal quick note from what you actually did — your Claude
  Code sessions first, plus whichever of Google Calendar, Slack, Fathom, Asana
  and daily notes you choose. Works whether or not you use open-day/close-day.
  Use when someone says "quicknote", "quick note", "draft my quick note",
  "weekly notes", "Signal notes", "what did I do this week", "what did I work
  on", or is answering Signal's Friday "Take some quick notes on your week"
  message. First run asks which sources to include and remembers the answer;
  "change my quicknote sources" asks again.
---

# Quicknote

Every Friday, Signal asks: *what did you work on, what moved forward, any wins, what
was a grind, did anything click, and what tool or skill do you wish you'd had?* This
skill drafts that answer from evidence, so nobody has to rebuild the week from memory.
It only ever drafts. **The person pastes it into Signal themselves — never send it.**

Talk to the person plainly. No file paths, script names or tool names in what you say
to them unless something breaks and they need it to get unstuck.

## Step 0 — Sources (first run, or "change my quicknote sources")

Settings live in `~/.config/nsls/quicknote.json`. If the file exists and the person
didn't ask to change it, read it and skip to Step 1.

Otherwise ask with **AskUserQuestion**, two multi-select questions in one call:

1. *"Where does your work show up?"* — **Claude Code sessions (Recommended)** · Google
   Calendar · Slack · Asana
2. *"Any of these as well?"* — Fathom meeting notes · Daily notes (Obsidian, including
   open-day and close-day)

If they pick Google Calendar, use **only their work calendar** — the one on their
@nsls.org address. Never read a personal calendar unless they name it themselves: a
personal appointment is not work, and it has no place in a note their manager reads.

If they pick Daily notes, find the vault: the `OBSIDIAN_VAULT_PATH` environment
variable, else the personal toolkit's `.env`, else ask once. Save:

```json
{"sources": ["claude_sessions", "calendar", "slack"], "calendars": ["name@nsls.org"], "vault": null, "created": "YYYY-MM-DD"}
```

Say in one line what you saved and that "change my quicknote sources" redoes it.

## Step 1 — The week

Signal's week is **Monday to Friday**. Run on Thursday through Sunday → this week.
Run Monday through Wednesday → last week (the one Signal is still asking about).
State the dates in one line; the person can say "this week", "last week" or give dates.

## Step 2 — Sweep only the chosen sources

Run each chosen source. If one isn't connected, say so in one line — "Slack isn't
connected, so I skipped it (say /connect to add it)" — and carry on. At the end, list
which sources actually ran.

- **Claude Code sessions** — the richest source for most builders. Run
  `python3 scripts/sweep_sessions.py --start YYYY-MM-DD --end YYYY-MM-DD` from this
  skill's folder (use `python` if `python3` isn't found). It reads the transcripts on
  this computer and returns each session's title, active days, a few of the person's
  asks and Claude's last reply. Each real session is a candidate work item. The script
  already removes runs a scheduled task started where the person never typed anything.
  A session marked `started_by_schedule` began as a routine but the person typed in it
  that week — judge it by those asks and keep any real work. Drop one-off questions,
  setup and housekeeping, and anything personal.
- **Google Calendar** — read only the calendars saved in settings (the person's
  @nsls.org work calendar unless they named another). Meetings held with other people
  in the window; skip declined events, focus blocks and anything personal.
- **Slack** — messages the person sent in the window. Look for decisions, things they
  unblocked, thanks they received, and their last quick note to Signal (so finished
  wins aren't repeated and percentages move on instead of restarting).
- **Fathom** — meetings in the window that the person attended or recorded (the list
  also returns colleagues' calls they weren't in — skip those); read at most five
  summaries. Decisions and commitments beat attendance.
- **Asana** — tasks the person completed or moved forward in the window.
- **Daily notes** — the vault's dated notes for the window (commonly `01-daily/`).
  These include what open-day and close-day wrote, if the person uses them.

## Step 3 — Screen the evidence before writing

The note goes to the person's manager and into their Work Journal, and the session
excerpts are raw. Before drafting, drop anything about:

- another person's performance, HR matters, health, pay or personal life
- legal or contract matters, and anything marked confidential or not-for-sharing
- student or member records, credentials, keys and access details
- the person's own personal life, side projects or non-NSLS work

If you're not sure whether something belongs in a note their manager will read, leave
it out and ask about it in one line under the draft. Never quote a session's raw text
into the note — summarise the work in your own words.

## Step 4 — Write the note

Signal sorts every note into **work items, wins, challenges and growth moments**, and
builds each person's Work Journal from it. Write in that shape, in Slack formatting:

```
Sep 21 – Sep 25 quick note:
• *Project or piece of work* (60%) — what moved this week, ten to fifteen words
• *Another item* (30% BLOCKED) — what it's waiting on, and on whom
WIN: an outcome that landed — what, for whom, and what it unblocks
WIN: another one, naming the people involved
CHALLENGE: a grind or time suck, stated plainly
GROWTH: something that clicked
WISH: a tool or skill that would have made the week faster, including anything you wish Claude could do
```

Rules:

- **A bullet or a win, never both.** Is there meaningful work left? Yes → a bullet with
  a percentage (rounded to 10; `BLOCKED` when waiting on someone). No → a `WIN:` line.
- **One `WIN:` per line, two to five of them.** Signal counts each `WIN:` line as one
  win; a heading with bullets under it is read as a single win.
- **Outcomes, not activity.** "Shipped X so Y can stop doing Z" beats "worked on X".
- **Name the people.** Signal readers respond to names. Only the person's own wins.
- **Never state hours or time spent**, in any form.
- **Leave out** admin, housekeeping, tool setup, access requests, one-off messages,
  anything personal, and anything confidential.
- **Leave out empty sections.** No invented challenges, growth or wishes.
- **Five to eight bullets.** Merge related sessions into one item rather than listing
  every session; a busy week still reads in thirty seconds.
- Lead with what matters most. No headers, no emojis, no sign-off.

## Step 5 — Hand it over

Show the note in one code block, ready to paste. Under it, not in the block, add a short
*where each line came from* list (one line per bullet or win: the session title,
meeting or message behind it) so they can check it and cut anything that shouldn't go.

Then say, in one sentence: *paste it as a reply to Signal's Friday message.* Offer to
adjust anything. Never post it for them.
