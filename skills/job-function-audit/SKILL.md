---
name: job-function-audit
description: >-
  Use whenever someone wants to inventory or document the full scope of what
  they (or a direct report) actually do: every responsibility, task, and
  workstream, especially to justify a decision like making the case for a new
  hire, deciding what to delegate/automate/offload, building a RACI or
  current-vs-target ownership map, clarifying a role, or prepping for a reorg.
  Reach for this skill even when the user does not say "audit" or name a skill;
  phrases like "document everything I do," "where does my time actually go,"
  "spreadsheet of all my responsibilities with time and criticality," "what
  should I hand off," or "map my scope before I talk to my manager" all mean
  this. It mines the person's calls (Fathom), Slack, email, and tasks (Asana)
  into a scored, evidence-backed Google Sheet with a current-to-target ownership
  model. Not for profiling someone else, a single one-off delegation, calendar
  or meeting-time math, org charts, or weekly-accomplishment recaps.
---

# /job-function-audit: Map What a Person Actually Does

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (default, no friction): searching Fathom meetings, Slack, Gmail, and Asana; reading existing Google Sheets/Docs. All discovery is read-only. Subagents launched for the source sweep MUST be told read-only.
2. **Configuration / output** (ask, then proceed): creating or updating the audit Google Sheet in the subject's Drive. This is the deliverable, so it's expected, but say what you're creating before the first write, and never silently overwrite cells the subject has edited.
3. **External sharing** (never proactive): sharing the sheet with anyone else (a manager, SLT), or sending it anywhere. Always confirm the recipient and access level (commenter vs editor) first. Sharing publishes the person's workload data, treat it as sensitive.

## Purpose

Turns the scattered reality of a person's work, calls, Slack threads, email, and tasks, into one honest, evidence-backed map of what they actually do and what should come off their plate. The intelligence here is the cross-source synthesis: no single system knows the whole job. Fathom shows the meetings and commitments, Asana shows the ticket volume, Slack shows the interrupt-driven asks, Gmail shows the external threads. Stitched together and scored (time, criticality, keep/delegate/automate, current->target owner), the result is the thing a delegation, hiring, or reorg conversation actually needs: not a list of tasks, but a defensible case for where the time goes and what to offload.

## When this runs

- "Document everything I work on" / "what do I actually do all day"
- Building a delegation or hiring business case (the keep-vs-offload split IS the case)
- A RACI / ownership map across someone's tools and responsibilities
- Role-clarity, reorg, or "should this move to another team" conversations
- A manager auditing a direct report's scope before a 1:1 or headcount ask

Works for a self-audit or for auditing a direct report. The subject is whoever's work is being mapped.

## Connections required

This skill orchestrates several systems. If tools aren't available, run `/connect`.
- **Fathom** (meetings/action items), **Slack**, **Gmail**, **Asana**, the four evidence sources.
- **Google Sheets** for output. `gws` is typically not configured here; use a `gcloud auth print-access-token` against the Sheets REST API (see "Building the sheet"). Related: `/gws`, `/google-drive`.
- For cross-system intelligence beyond one person, see `/data-intel`. For a person's relationships/history, `/person-intelligence` is complementary.

## The process

### Phase 1: Scope (ask up front, don't assume)
Pin down before mining:
- **Subject + identity handles**: email, Slack user ID, Asana user. (Slack `from:<@U…>` and Fathom `recorded_by` need these.)
- **Audience + purpose**: who reads the sheet (a manager? SLT?) and what decision it drives. This sets the output framing.
- **Exclusions**: ask if any tooling or work should NOT be attributed to them. People often disown work that lands on them but isn't theirs, honor it, and don't re-surface it even if it shows up in source data.
- **Output**: Google Sheet (default; shareable) vs. a doc. Sheet wins for a manager audience.

### Phase 2: Fan out the source sweep (parallel, read-only)
Launch one general-purpose subagent per source IN A SINGLE MESSAGE so they run concurrently. Ready-to-use prompt templates for all four sources plus the completeness sweep are in `references/source-agent-prompts.md`, read that and fill the placeholders rather than reinventing them. Each gets: the subject's identity, the current row list (if iterating), and instructions to return **Confirmed / New candidates / Possibly stale / Volume notes**, every item tied to evidence (dates, links, counts, names). Time window ~30-60 days for Slack/Asana, since-last-quarter for Fathom.
- **Asana agent**: open + recently-completed tasks assigned to/created by the subject; group into themes; cross-check the live project boards (see gotcha, the "assigned to me" search is unreliable).
- **Gmail agent**: sent + received work mail; what they're driving vs. cc'd on.
- **Slack agent**: messages from the subject + asks directed at them; which channels; who routes work to them.
- **Fathom agent**: meetings in the window with action items owed by the subject; recurring meeting series (these validate the "meetings & squads" row).

### Phase 3: Completeness sweep (the step that's easy to skip)
After the first pass, do a dedicated sweep that reads the **full** action-item set and the **live** task boards, not just the highlights. The biggest failure mode is under-elevation: the data contains a workstream but the first synthesis buries it inside a generic row. Explicitly ask "what discrete workstream is in the evidence but NOT yet its own row?" Confirm any items the subject names; characterize each as its own row vs. a fold-in, with evidence.

### Phase 4: Build the sheet (see "Building the sheet" + "Column schema")

### Phase 5: Draft the decision columns, then hand off
Pre-fill Time %, Criticality, Keep?, and Fly-in as **drafts** (derive Keep? from each row's target owner: KEEP rows -> Y; rows targeted to someone else -> Delegate; alert/manual toil -> Automate). Tint those cells so the subject sees exactly what to confirm. These four columns are ultimately the subject's call, you draft, they correct.

### Phase 6: Confidence call
State plainly: which sources are verified, which aren't, and what's still the subject's to fill. Don't claim "perfect" while a source is unverified or the decision columns are blank.

## Column schema (what worked)

Decision signals first, prose last:

`Function | Task Type | Examples | Time % | Criticality | Keep? (Y/Delegate/Automate) | Fly-in | Current owner | Target owner (R) | Delegation path | Notes`

- A **legend row** above the header (Time % = draft; Keep? = Y/Delegate/Automate; Fly-in = occasional drop-in Y vs. ongoing ownership N).
- An **exec block at the very top**: time-allocation rollup by category + 3 headline findings. A manager reads this in 30 seconds.
- A **target-state block** at the bottom: the work the subject WANTS to shift toward (mark Keep = "Want to own", Time ~0% today). This is the counterweight to everything being offloaded.
- An **"Ask" block**: the hire/role the keep-vs-offload split justifies.
- Group rows by category (Admin / Enablement / RevOps / etc.). Keep the row count honest, completeness over brevity when the purpose is "everything I do," but collapse true duplicates.

## The ownership model (RACI): why it's the business case

For each function: **Current owner -> Target owner (R) -> Delegation path.** The subject keeps strategic/architecture work (Target = them, "KEEP"); daily admin and toil get a named target owner (a proposed hire, another team, automation). The count of Keep vs. Delegate/Automate, especially the **High-criticality AND Delegate** rows, is the single strongest argument for a headcount or reorg ask: high-stakes work currently pinned to one person that shouldn't be.

## Building the sheet (gcloud + Sheets REST API)

Use the bundled `scripts/build_sheet.py`, it takes a JSON spec (title, exec block, headers, rows, target-state block, ask block) and handles create + write + format + tint + verification in one shot, so the mechanical Sheets work isn't rewritten each run. Run it on a Python 3.10+ interpreter (system `python3` may be 3.9; `python3.13` works) with `requests` available. It prints a verification line (row count, Time % sum, category rollup, excluded-term scan), read it before telling the user the sheet is done. Fall back to raw REST calls only for edits the script doesn't cover:

`gws` is usually not configured; drive the Sheets API directly with a token:
- `TOKEN=$(gcloud auth print-access-token)` (has Drive/Sheets scope).
- Create: `POST https://sheets.googleapis.com/v4/spreadsheets` with `sheets[]` for tabs.
- Write values: `values:batchUpdate` (RAW). Format (bold header, freeze rows, column widths, wrap, cell tint): `:batchUpdate` with `repeatCell` / `updateDimensionProperties` / `updateSheetProperties`.
- Share (Phase tier 3, confirm first): `PATCH drive/v3/files/{id}/permissions` or the permissions endpoint.
- Do the work in a small Python script (`requests`); write it to `/tmp`, run it, and have it **print a verification** (e.g. Time % sum, row count, a scan for excluded terms) so you catch mistakes before telling the user it's done.

## Domain micro (hard-won, these will bite you)

- **No single source is complete; the synthesis is the product.** Gmail confirms little that Slack/Fathom didn't, but the one time it matters (an external thread) it's the only place it lives.
- **Under-elevation is the #1 quality failure.** The evidence will contain workstreams your first synthesis buries. Always run the completeness sweep over the FULL action-item set and live boards. When the subject says "did you include X?", X is almost always already in the data you pulled, you just didn't make it a row.
- **Fathom title search misses meetings.** A 1:1 may be titled "Royce / Jordan" not "Jordan Perry." Don't rely on `search_meetings` by person name, `list_meetings` over the date window and scan invitees/summaries.
- **Asana "assigned to me" caps and skews stale.** The assignee search hits ~100 results dominated by abandoned multi-year-old tasks (e.g. an "...- Old" project). Cross-check the live project boards (the intake queue, the active sprint board) for current work.
- **Slack #alerts channels are often inbox firehoses, not system health.** High message volume can be conversation/handoff notifications, not real alerts. Verify what's actually firing (and where, recurring bot DMs vs. the channel) before describing it. Don't repeat a claim like "the X workflow fires 3x/day" without confirming the specific workflow.
- **Anchor every claim to evidence; never inflate.** It's easy to call something "actively driving" when the evidence is "opened a discovery thread." The subject WILL catch overstatements and it costs trust. Down-rank to what the evidence literally shows.
- **Gmail OAuth connectors drop.** They silently invalidate between sessions ("connection invalidated, needs reconnect"). Reconnect via `/mcp` (or `/mcp` from Terminal.app if the IDE OAuth silently no-ops). A **live session cannot hot-reload a dropped MCP server**, even after reconnecting elsewhere, this session won't see it without a window reload. If reconnect is fiddly, finalize on the available sources and note the gap rather than blocking.
- **Time % must reconcile.** Draft estimates should sum to ~100 and the top-line rollup must match the row-level numbers. Have the build script print the sum; fix off-by-ones (one row that didn't get adjusted) before declaring done.
- **Tint the draft cells.** The owner-to-fill columns (Time/Criticality/Keep/Fly-in) should be visually distinct so the subject knows exactly what to confirm.
- **Honor exclusions absolutely.** If the subject says don't attribute a given tool/work to them, exclude it everywhere and scan the output to confirm it's gone, even though it appears in the source data.

## Diagnostic loop

TRY → OBSERVE → DIAGNOSE → ADAPT.
- Source connector down → reconnect via `/connect`/`/mcp`; if not quickly fixable, finalize on the other sources and footnote the gap. Never block the deliverable on one source.
- Person/topic search returns nothing → broaden: list by date window, scan invitees; try the collaborator's name; try the live board instead of the assignee search.
- "Did you include X?" → it's likely in the data already; re-run the completeness sweep rather than just adding the one item.
- Time % ≠ 100 / rollup mismatch → reprint the per-row sum, find the unadjusted row, rebalance.
- The subject disputes a row's framing → down-rank to literal evidence; show the quote/source.

## Output guidelines

- **Audience-first.** A manager wants the exec rollup + the keep/delegate split + the hire ask. Put those at the top; park dense evidence in Notes (last column).
- **Draft vs. owner-to-fill is explicit.** Tinted cells + a legend. Never present drafts as the subject's confirmed answers.
- **PII / sensitivity.** A workload audit names collaborators and volumes. Don't share it without confirming recipient and access. It's the person's professional data.
- **Confidence statement always.** End with what's verified, what's not (e.g. a source that was down), and what only the subject can fill.

## Related skills

- `/connect`, set up Fathom / Slack / Gmail / Asana / Google before running.
- `/data-intel`, cross-system intelligence beyond a single person.
- `/person-intelligence`, relationship/history profile of a person (complementary).
- `/gws`, `/google-drive`, Google Sheets/Docs/Drive operations.
- `/interrogate`, if the audit turns into scoping a new project or role.
