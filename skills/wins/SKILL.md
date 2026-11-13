---
name: wins
description: Claude Code only. Use when someone wants encouragement, a confidence boost, or proof they're doing well, drawn from what real colleagues actually said to them on recorded calls and in Slack. Triggers on "wins", "/wins", "pat on the back", "I need a pick-me-up", "remind me what's going well", "positive feedback from my calls", "what did people say about me this week", "hype me up", "I feel like I'm failing", "brag doc", "what went well this week", or before a review, 1:1, or self-assessment when they need receipts. Not for coaching on weaknesses (use meeting-analyzer), not for profiling someone else, not for a neutral weekly recap.
---

<!-- claude-code-only:start (same words in every skill that has this note; change them in _shared/references/skill-surfaces.json) -->
> **Claude Code only.** This skill needs the person's own computer, so check
> where you are first, going by what your own instructions say you are running in.
> In **Claude Code** (a terminal, or the Code tab in the Claude app), skip this
> note. In **an ordinary Claude chat or a Cowork task** (its files live in a
> sandbox such as `/sessions/...`, not on their computer), stop and follow
> nothing else in this skill. If the person asked for this skill, or what they
> want can't be done here without it, reply with only this sentence:
> "This skill only works in Claude Code on your computer, so switch to Claude Code (the Code tab in the Claude app) and run it there."
> Otherwise don't mention this skill; help the way you would without it.
> Unsure which? Run `echo "$CLAUDE_CODE_ENTRYPOINT"` (PowerShell:
> `$env:CLAUDE_CODE_ENTRYPOINT`): `local-agent` is Cowork, and any other
> answer, blank included, is Claude Code. No way to run a command means chat.
<!-- claude-code-only:end -->

# /wins: Real Praise From Real Conversations

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (default, no friction): listing Fathom meetings, reading summaries and transcripts, running `scripts/find_wins.py` on saved results in the scratchpad, and searching or reading Slack messages, threads, and DMs the user can already see. All of `/wins` runs here. Never react to, reply to, or mark anything in Slack.
2. **Configuration** (ask first): saving the wins list as a file in the user's folders, a doc, or an Obsidian note. Say what will be written and where.
3. **External** (never proactive): sending, posting, or sharing the wins anywhere (Slack, email, a manager, a review form). These are colleagues' words, often from meetings and private DMs. If the user asks, confirm the destination and remind them that the quotes are other people's words. Never repost a DM quote into a channel.

## Purpose

When someone is running on empty, generic encouragement bounces off. What lands is evidence: a leader thanking them by name for taking something on, a teammate saying "you're doing a great job" at the exact moment they apologized for not being prepared. That evidence already exists, scattered across hours of recorded calls nobody re-watches and Slack DMs that scrolled away. Some of the best praise is second-hand: a colleague posting in a group DM that a stakeholder "felt really listened to." `/wins` mines the user's own Fathom calls and Slack for what real people actually said to and about them, checks every quote in context so nothing is inflated or misattributed, and hands back a short, scannable list they can re-read when they need it. The intelligence is the verification: anyone can grep for "great job." This skill makes sure the "great job" was meant for *them*.

## Quick Start

1. Window: default **this week (Monday 00:00 local → now)**. Accept "today", "last two weeks", "this month", or dates.
2. Identity: Fathom `get_identity` (or ask). Collect every name variant the user appears under (see Gotchas).
3. Pull: Fathom `list_meetings` with `created_after`, `include_transcript: true`, `include_summary: true`. Follow `next_cursor` until it is empty. Each page will overflow and save to a file; that's expected.
4. Extract: `python3 -I <skill>/scripts/find_wins.py --out <scratchpad>/wins --name "<First>" [--name "<Variant>"] <page1> <page2> ...`
5. Verify: read `candidates.txt`. For every `>>` line, read the context and decide **to whom** and **about what**. Drop anything not aimed at the user.
6. Shipped work: grep each meeting's summary (top of each file in `meetings/`) for the user's name: approvals, completed requirements, things they demoed or delivered.
7. Slack: run the searches in "Slack sweep" below, in parallel. Read every hit in full before using it.
8. Write the output (template below). Every quote is verbatim, attributed, dated, and tagged 🎙️ (call) or 💬 (Slack).

## Slack Sweep

The search tool's description shows the current user's Slack ID; use it as `<ME>`. Semantic search may be off, so these are keyword searches (keywords are AND'd, so use one praise word per search). Use `after:<window start, YYYY-MM-DD>` on all of them.

| Search | `keywords` | `filters` | Finds |
|---|---|---|---|
| Thanks in DMs/threads they're in | `thank` | `with:<@ME> after:…` | DMs and group DMs, where most praise lives |
| Same, other praise words | `appreciate`, `amazing`, `"well done"`, `kudos`, `love`, `"great job"`, `listened`, `happy` (one per search) | `after:…` (no `with:`) | Second-hand praise: people talking *about* the user to others |
| Name mentions | the user's first name | `after:…` | Praise that names them without an @-mention |
| @-mentions | `<@ME>` | `after:…`, `sort: timestamp` | Shout-outs, "can you take a look," and credit in announcements |

Then for each promising hit:
- Read it with `response_format: detailed` (or `slack_read_thread` for threads). **Concise results truncate long messages with "…", and the praise is often a bullet halfway down.** The best find of the first run was the 4th line of a long group-DM update.
- Keep the permalink for the output.
- Check who it's about: "thank you both" means the user shares the credit, so say who with.

## What Counts as a Win (four buckets)

| Bucket | What it is | Where it comes from |
|---|---|---|
| **Praise said to them** | Someone thanks, credits, or compliments the user directly or by name, including second-hand ("she felt really listened to") | Transcript candidates + Slack sweep, verified in context |
| **Moments they led** | Leadership handed them a decision ("run with it, you decide"), they held a position under pushback, they set a boundary, they coined a line others repeated | Transcript: read around the user's longer turns and any pushback |
| **Work they shipped** | Approvals, completed requirements, tickets released, demos, unblocked teams ("waiting for your tickets") | Fathom summaries + transcript |
| **How they show up** | Shared credit, thanked others, steadied the room | The user's own lines (the one place their own words count) |

## Gotchas (learned the hard way)

- **Praise aimed at someone else is the #1 error.** On the first real run: "Great job… you're crushing it" was addressed to three *other* people (the next line names them), and "great idea… love it" was about a colleague's process change. Always read the lines before and after. If the target is unclear, leave it out.
- **Fathom misattributes speakers.** In one call, a leader's praise appeared partly under another attendee's name, and lines jump between speakers mid-sentence. When attribution matters ("the CEO said…"), check the surrounding lines. If still unsure, write "said on the call" instead of naming someone.
- **The user appears under several names.** One person appeared under two different surnames in the same week (a legal name and a preferred name). Pass every variant with `--name`, or use first name only. Never infer a surname from an email address.
- **Filter by "spoke in it," not "was invited."** Calendar invitees miss calls the user joined from someone else's invite, and include calls they skipped. The script keeps only meetings where the user has transcript lines.
- **Duplicate recordings.** Two people recording the same meeting creates two items (same title, a couple of minutes apart). The script keeps the longer one. Different titles at different times (e.g., two back-to-back calls with the same title 20 min apart) are separate meetings.
- **`get_transcript` can 404 on same-day recordings** while `list_meetings` with `include_transcript: true` returns the text fine. Use `list_meetings`.
- **Payload size.** One week of calls with transcripts is around 4 MB across 3 pages. Never read the dump directly. Run the script on the saved files.
- **Filler isn't praise.** "That makes sense," "perfect," and "awesome" alone are mostly verbal tics. The script drops bare filler, but "okay, fantastic" still slips through and needs a judgment call.
- **Slack @-mentions are mostly work asks, not praise.** In a busy build channel, nearly all mentions are QA questions and "can you confirm." Don't read volume as appreciation; quote only actual praise. (Being the person everyone routes decisions to can go under "Moments they led" if framed honestly.)
- **Slack and Fathom use different display names** for the same person. Match on Slack user ID, not name.
- **Skip bots** (Jira, HubSpot, "Sent using Claude" agents). The search default `include_bots: false` handles most of it.
- **`has:reaction` on the user's own messages is weak.** Search results don't show which emoji or how many, so it mostly returns small talk. Use it only to find a big announcement, then open it with `slack_read_thread` (detailed) to see the reactions.
- **The user may paste a transcript.** If they do, it's the source of truth for that call. Use it instead of re-fetching.
- **Calibrate to the person's baseline.** If memory or prior context says the user tends to absorb pushback or avoid conflict, then holding a position and having leadership defer to them is a major win, even if it looks small. Read relevant user memories before writing the Leading section.

## Rationalizations to Refuse

| Tempting shortcut | Why it's wrong |
|---|---|
| "This praise is close enough, they were in the room" | Misattributed praise is worse than none. It breaks trust the first time they re-watch the clip. |
| "The week is thin, I'll round up 'thanks' into 'they loved your work'" | Inflation defeats the purpose. Quote exactly; if the week is thin, say so and offer a wider window. |
| "I'll paraphrase, it reads better" | The power is that real people said it. Quote verbatim; trim with an ellipsis, never reword. |
| "Summaries are enough, skip the transcript" | Summaries record what happened, not the warmth of what was said. Quotes come from transcripts only. |
| "I'll add a little 'areas to grow' for balance" | Not this skill. The user asked for the good. Coaching lives in meeting-analyzer. |
| "I'll include the user's own self-praise" | Their own words count only in "How they show up" (gratitude, credit-sharing), never as praise. |

## Red Flags (STOP and re-check)

- A quote you haven't read in its context window
- A Slack quote taken from a truncated ("…") search result instead of the full message
- A speaker name you haven't sanity-checked against surrounding lines
- Any sentence that starts "people felt…" or "the team loved…" without a quote behind it
- A "win" sourced from a meeting the user didn't speak in
- Output longer than about one screen per bucket

## Diagnostic Loop

TRY → OBSERVE → DIAGNOSE → ADAPT
- **No Fathom tools** → run `/connect` (Fathom). The `api.fathom.ai` key is under fathom.video → Settings → API Access.
- **No Slack tools, or DMs missing** → run `/connect` (Slack). Use the search that covers private channels and DMs. Public-only search misses most praise. If Slack is down, finish with Fathom and say Slack wasn't covered.
- **Slack search returns 0** → drop `with:`, try the first name as the keyword, then shorten the word (`thank` matches "thanks" and "thank you").
- **Zero meetings kept** → check the name variants (print distinct speaker names from one dump), then the window's timezone (use UTC `created_after` at local Monday midnight).
- **Few or no verified quotes** → widen the window (two weeks, a month), then lean on the "shipped" and "led" buckets from summaries. Say honestly that it was a quieter week for verbal praise. Don't manufacture.
- **Transcript missing on an item** (`transcript: null`) → still processing. Use its summary for "shipped," and tell the user that call has no quotes yet.
- **Too many candidates** (100+) → read per meeting, prioritizing leadership and cross-team calls. Stop when each bucket has its strongest 3–6 items.

## Output

Keep it concise: scannable, warm, no walls of text. Cards beat paragraphs.

```
## TL;DR
<2 sentences: the headline praise + the pattern across the week>
<one line on coverage: N calls + Slack, dates, anything not covered>

### 🏆 Said to you
**<Person>, 🎙️ <Meeting> (<Day>)**
- *"<verbatim quote>"*  [timestamp link]
**<Person>, 💬 <DM / #channel> (<Day>)**
- *"<verbatim quote>"*  [permalink]

### 🧭 Moments you led
- <what happened> → <their response, quoted>

### ✅ What you shipped
- **<Thing>:** <one line>, <who confirmed it>

### 🌱 How you show up
- <behavior>: *"<user's own words>"*

---
**One line to keep:** <the single most quotable, verified moment>
```

- Link timestamps as `<share_url>?timestamp=<seconds>` when available.
- Lead with the most senior or most specific praise.
- Keep per-quote context to a few words: why it mattered ("right after you apologized for not being prepared").
- End with the "one line to keep." Don't end with a question unless offering to save it, and then make the question the last line.

## Related

- `/connect`: Fathom and Slack setup
- `/slack`: deeper Slack search syntax and channel context
- `meeting-analyzer` (personal toolkit): the coaching counterpart, covering patterns to improve
- `/job-function-audit`: what a person does. `/wins`: how well it's landing.
- `person-intelligence`: relationship context for the people quoted
