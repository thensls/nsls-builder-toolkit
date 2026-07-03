---
name: track-optimize
description: >-
  Use when a live Society (ignite-next) track needs improvement — members are
  dropping off, a step underperforms, or a track is flagged for optimization.
  Finds where members leave (real PostHog data), diagnoses why (focus-group),
  proposes a concrete change, and produces a new version that re-enters the
  score→gate loop. Triggers: "optimize a track", "improve a live track", "why
  are members dropping off", "fix the weak step", "this track underperforms",
  "optimize <track>", "track is losing people at step".
---

# track-optimize

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** — reading the live track's PostHog performance (Studio
   `PostHogActuals` + `/posthog`), its `track.json`, and its scores. Free.
2. **Configuration / new-content** — authoring a proposed new version
   (`track.json` edit) + previewing it in the demo. OK by default; say what changed.
3. **Ship** — a new version goes Live only through `track-prototype`'s score→gate
   and a human decision. **Never auto-ship an optimization.** The gate stays.

## Purpose

A live track is a hypothesis with real data attached. This skill closes the loop:
it reads where members actually leave, diagnoses why that step underperforms,
proposes a specific fix, and routes the fix back through the same quality gate a
new track passes — so optimization is evidence-driven, not opinion, and nothing
ships to members without clearing the bar. Signal says *where*; the focus-group
says *why*; the gate says *good enough*.

## When to use

- A track in the Studio's **Optimization** column, or any Live track a builder
  wants to improve.
- NOT for building a new track (that's `track-design`) or first-time scoring
  (that's `track-prototype`). This is the *live → better version* loop.

## Inputs

- The live track's **`track.json`** (the current shipped content).
- Its **live performance** — from the Studio `PostHogActuals` (base
  `appzDWu6GowvnACtv`), and `/posthog` for deeper funnels. See
  `references/reading-the-signal.md`.

## Process

### 0 — Flag it: move the card to Optimization
If the track is still in the **Live** column, flag the optimization work on the
board before digging in (heartbeat: report the transition):
```
AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=appzDWu6GowvnACtv \
  node <track-prototype>/scripts/set-stage.mjs <slug> optimization
```

### 1 — Signal: find where members leave (PostHog)
Read the track's `PostHogActuals`: **`step_to_step_continuation`** (the primary
live metric — average share continuing step→step), **`dropoff_by_step`** (the
per-step counts), and `step1_dropoff`. **Pick the row for the *current* live
version** — a track may have several rows across versions; use the one whose
`live_track_version` matches the shipped build (else the latest `period`), so
you're optimizing what's actually live. Identify the **weakest step** — the
largest single continuation drop. For depth or a fresh cut, use `/posthog` on the
track's events. Report the weak step with its numbers (real, sourced — never a
guessed figure).

### 2 — Diagnose: why that step underperforms (focus-group)
Run `track-prototype`'s synthetic focus-group panel **on the current live
content**, focused on the weak step. If the track has prerequisites, pass their
assumed tokens (the track's `--assume` / `--prereq` set, as in `track-design`
Phase 0 / the demo build) so the walk doesn't error on token ordering. Read the
panel's friction notes against the four dimensions (Value / Pacing / Copy / Fit).
The signal says a step loses people; the panel says which dimension is failing
and why.

### 3 — Propose: one concrete change
From the diagnosis, propose a specific change to the weak step — reword (Copy),
re-pace / split / cut (Pacing), sharpen the payoff or **add/adjust a value
moment** (Value, via `value-moment`), or re-target (Fit). One change tied to one
diagnosed cause, not a rewrite. State the hypothesis: *"continuation drops at
step N because X; this change should lift it because Y."*

### 4 — New version → re-enter the gate
Author the change as a **new version** of the `track.json`, preview it in the
demo (build-prototype, with the prompt-context note so the change is legible),
then hand to **`track-prototype`** to walk → focus-group → score → gate. On pass,
a human ships it — and at that ship moment, flip the board back yourself (nothing
else writes stage):
```
AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=appzDWu6GowvnACtv \
  node <track-prototype>/scripts/set-stage.mjs <slug> live --live-version <contentHash>
```
Do not bypass the gate.

## Guardrails

- **Ground the numbers.** Every drop-off / continuation figure comes from real
  PostHog data (Studio actuals or `/posthog`). No invented percentages — same
  faithfulness rule as `value-moment`.
- **One change at a time.** Optimization is causal: change the diagnosed step,
  re-measure. A scattershot rewrite can't teach you what worked.
- **The gate is non-negotiable.** A proposed version ships only after
  `track-prototype` clears it and a human approves.
- **Enough data first.** If `n_users` is small, say so — a drop on tiny N may be
  noise, not signal.

## Diagnostic loop

TRY (read the signal) → OBSERVE (weakest step + numbers) → DIAGNOSE (focus-group:
which dimension) → ADAPT (one targeted change) → RE-GATE (track-prototype) →
measure again once live. If the new version doesn't lift continuation, the
hypothesis was wrong — return to step 2 with that knowledge.

## Reference index
- `references/reading-the-signal.md` — the `PostHogActuals` fields + `/posthog` cut for the weak step.
- Hand-offs: `track-prototype` (focus-group + score→gate), `value-moment` (if the fix is a nugget), `track-design` (larger structural changes).
