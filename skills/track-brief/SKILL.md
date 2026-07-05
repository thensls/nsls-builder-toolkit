---
name: track-brief
description: >-
  Use when someone has an idea for a Society (ignite-next) learning track and
  needs to shape it into something buildable — before any track is authored.
  Turns a raw idea into a Creative Content Brief + Track Template Brief (one
  Google Doc) and lands it in the Track Studio Backlog. For anyone with an idea,
  no curriculum expertise assumed; it feeds track-design, it does not replace it.
  Triggers: "I have an idea for a track", "brief a track", "track idea",
  "backlog a track idea", "shape this track idea", "we should build a track
  that…", "add a track to the backlog", "creative content brief", "track
  template brief".
---

# track-brief

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** — reading existing tracks, the Studio board, prior briefs, the
   member-personas panel (in the sibling `track-design` skill), and this skill's
   references. Free.
2. **Configuration / new-content** — building a new Google Doc draft via
   `gdoc-build`. OK by default; say what's being created and where.
3. **Write to shared systems** — creating the Studio Backlog row in Airtable
   (base `appzDWu6GowvnACtv`). This is a shared, leadership-visible board.
   **Confirm the field values with the user before writing.** If no write token
   is available, print the fields for manual entry rather than failing.

## Purpose

Authoring today starts at `track-design`, which already assumes a fairly-formed
idea. There's no home for *ideas that aren't tracks yet* and no guided way for
someone without curriculum expertise to shape one. track-brief is that front
door: it asks plain questions, turns the answers into two disciplined artifacts —
a **Creative Content Brief** (the why/what, human-readable, backlog-visible) and
a **Track Template Brief** (the how-it's-structured, which `track-design`
consumes) — and drops the idea into the Studio Backlog so leadership sees the
idea funnel. It makes a good brief the path of least resistance, so ideas arrive
buildable instead of as one-liners.

## When to use

- Someone has a track idea and it needs shaping before build — **the upstream
  step before `track-design`.**
- You want an idea captured in the Studio Backlog with a real brief attached.
- NOT for authoring the track itself (that's `track-design`), and NOT for
  non-ignite-next work (marketing pages, slides, Slack bots, automations).

## Quick Start

An idea goes → 2 brief artifacts (one Google Doc) → Studio Backlog through these
phases, in order:

**0 Frame** (lock the promise) → **1 Gather** (guided Q&A, no jargon) →
**2 Outcomes** (measurable outcome→evidence) → **3 Template Brief** (structure +
call `value-moment`) → **4 Build the doc** (`gdoc-build`, Society) → **5 Backlog
row** (Airtable, confirm first) → **6 Handoff**.

Keep a running scratchpad (frame → answers → outcomes → structure) in the
conversation — it's the resume point if the person stops partway.

## Operating rules

- **Ask, don't assume expertise.** The person may have never designed a track.
  Ask one plain question at a time, in their language. No curriculum jargon
  ("substep," "profile token," "value dimension") in questions — translate.
- **Run phases in order.** Skip only on explicit request, and record the skip by
  name in the Phase 6 handoff ("Skipped Phase 3 — idea is exploratory, no value
  moments yet"). Never skip silently.
- **Never author from memory.** Open the cited reference at its phase
  (`references/brief-template.md`, `references/backlog-airtable-write.md`), and
  invoke `value-moment` for the value moments — do not hand-wave them.
- **Outcomes must be measurable, grounded in evidence.** An outcome without an
  in-track artifact that proves it is not done (see Phase 2). This is the gate
  that makes a brief assessable instead of a wish list.

## Red flags — STOP

- Writing the brief *for* the person from your own assumptions instead of asking
  them. → Ask. It's their idea; your job is to draw it out and structure it.
- An outcome phrased as "understands X" / "feels more confident." → Not
  measurable. Rewrite as "can do / can produce X" with an in-track artifact as
  evidence (Phase 2).
- Skipping `value-moment` and writing a "Value moments" section yourself. → Use
  the sub-skill; its faithfulness rule exists for a reason.
- Inventing a statistic to make a value moment or a "why now" feel compelling. →
  Ground it or cut it. (See `value-moment`'s faithfulness rule — same rule
  applies to any number in the brief.)
- Writing the Airtable row without confirming the fields. → Tier-3 write. Confirm
  first.

**Violating the letter of these rules violates their spirit.**

## Phase 0 — Frame the idea

**Purpose:** lock the value promise before anything else.

Elicit, in plain words: *"When a member finishes this track, what will they have
or be able to do that they couldn't before?"* Push until it's concrete — a
deliverable, a clarity, a capability, not a feeling. This one sentence anchors
every later section. If the person can't answer it yet, stay here and help them
find it; don't proceed on a fuzzy promise.

## Phase 1 — Gather (guided Q&A)

**Purpose:** collect the raw material for the Creative Content Brief, one plain
question at a time. Optional: open the sibling `track-design` skill's
`references/member-personas.md` (the 7-persona panel) to pressure-test who the
audience really is — skip if it isn't installed alongside this skill.

Draw out, conversationally (not as a form dump):
- **Audience** — who is this for, and which member level(s) (Honor / Associate /
  Impact)? Translate levels if they don't know them.
- **Benefit** — why would *they* care? The felt payoff (this becomes the backlog
  card's one-liner).
- **Starting place** — where is the member when they begin (what they know,
  their situation, their mindset)?
- **Ending place** — what's different for them after?
- **What they'll learn** — the substance.
- **Prerequisites** — anything they should do first?
- **Made-something vs. built-a-habit** — does the member finish *holding
  something they keep* (a plan, a profile, a document) or *having built a habit /
  self-understanding*? (This is the artifact-track vs. practice-track
  classification `track-design` needs — ask it in plain words, don't use the
  jargon.)
- **Why now** — why does this idea earn development over others?

Reflect answers back in the scratchpad as you go.

## Phase 2 — Outcomes (measurable, outcome→evidence)

**Purpose:** turn "what they'll learn" into assessable outcomes.

**Read** `references/brief-template.md` (the outcome→evidence / WGU format). For
each outcome, produce a row: **competency** (verb-led, measurable — "can
articulate / produce / compare," never "understands") → **evidence** (the
in-track artifact that proves it — a saved statement, a plan, a ranked list) →
**alignment** (a Society capability / WGU power skill, optional).

**Gate:** every outcome must name an in-track artifact as its evidence. If it
can't, the outcome isn't measurable — fix it or add the step that would produce
the evidence. Do not leave this phase with vibes-outcomes.

## Phase 3 — Track Template Brief (structure + value moments)

**Purpose:** turn the brief into the build spec `track-design` will consume.

**Read** `references/brief-template.md` (Part 2). Draft, from the Phase 0–2
material: goals (from outcomes), where the member is, **what information will be
collected** (the fields, in rough order), what they'll learn (mapped to the
collected info), the **outcome→evidence map** (which step yields each outcome's
evidence), sequencing + level, and **track type + assumed context** (§8 —
artifact-track vs. practice-track from the Phase 1 answer, plus the profile
tokens inherited from prerequisites). §8 is what lets `track-design` start at its
Phase 0 without re-interviewing — don't skip it.

**Value moments — invoke `value-moment`.** Hand it the "what information will be
collected" list + the audience/promise. **REQUIRED SUB-SKILL:** use
`value-moment` — it proposes ranked, grounded insight-nugget candidates with
example outputs. Its output *is* this section. Do not write value moments freehand
(you'll skip the faithfulness rule and ship a fabricated stat).

## Phase 4 — Build the Google Doc

**Purpose:** produce the single deliverable doc.

**REQUIRED SUB-SKILL:** use `gdoc-build` (Society branding) to build **one**
Google Doc with both parts — Part 1 Creative Content Brief, Part 2 Track Template
Brief — per `references/brief-template.md`. Real headings and tables, not
markdown. Keep the URL; it's the `brief_doc_url`.

## Phase 5 — Create the Backlog row

**Purpose:** land the idea in the Studio Backlog.

**Prefer the Studio MCP tool** `create_brief_card` (`society-studio` server) — it
validates fields, rejects duplicate slugs against a FRESH board read, and needs
no Airtable PAT. Fallback when the MCP server isn't configured:

**Read** `references/backlog-airtable-write.md`. Confirm the field values with the
user (Tier-3 write), verify the slug is unique, then create the `Tracks` row with
`stage="backlog"` and `brief_doc_url` set. If no write token is available, print
the exact field values for the user to paste.

## Phase 6 — Handoff

Report: the Google Doc link, the Studio card (record id + `https://studio.nsls.org`),
and the next step in plain terms — *"When an owner picks this up, run
`track-design` on this brief to build the track."* Note any skipped phases by
name. `track-design` reads Part 2 of the same doc as its Phase-0 input.

## The pipeline (where this sits)

```
idea ──track-brief──▶ Creative Content Brief + Track Template Brief (1 gdoc)
                        └─ calls value-moment for the value moments
                      ──▶ Studio BACKLOG (stage=backlog, brief linked)
        owner picks up ──▶ track-design (brief = Phase-0 input) ──▶ IN DEVELOPMENT
                      ──▶ track-prototype (build→walk→score) ──ship-bar──▶ LIVE
```

- Upstream of: `track-design` (consumes Part 2).
- Calls: `value-moment` (Phase 3), `gdoc-build` (Phase 4).
- Writes to: Track Studio (the Backlog column built 2026-07-01).
- Token setup: see `/airtable` or `/connect` if the Airtable write fails.

## Rationalization table

| Excuse | Reality |
|---|---|
| "I know what they mean, I'll just write the brief." | It's their idea; assumptions produce a brief they won't recognize. Ask. |
| "'Understands the basics' is a fine outcome." | Not measurable. Name the in-track artifact that proves it. |
| "I'll write the value moments myself, faster than invoking value-moment." | You'll skip the faithfulness rule and ship a fabricated stat. Use the sub-skill. |
| "A quick stat in 'why now' makes the case stronger." | A fabricated stat makes it false. Ground it or cut it. |
| "Two docs / a markdown file is easier than one gdoc." | One gdoc, two parts, is the agreed shape — one link the Studio and track-design both use. |
| "I'll create the Airtable row without asking — it's obvious." | Tier-3 write to a shared board. Confirm the fields first. |
