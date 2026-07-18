---
name: bet-idea
description: >-
  Use when someone has a raw business idea for NSLS and it needs to become a
  full Lean Canvas + thesis, get its riskiest assumptions named out loud, get
  stress-tested, and — only if it earns it — get queued for research. The
  intake front door of the Strategy Studio pipeline; upstream of bet-research.
  Triggers: "I have a business idea", "new bet", "bet idea", "add a bet",
  "business model idea", "lean canvas this", "sketch a business", "should we
  sell X to Y", "capture this idea", "should we sell this thing we built",
  "we built this for ourselves — is it a product", "productize",
  "commercialize an internal tool".
---

# bet-idea

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** — `list_taxonomy`, `size_segment`, `get_bet` (resuming a
   partial capture). Free, no confirmation needed.
2. **Configuration / new-content** — `create_bet`, `update_section`,
   `upsert_assumption`, `score_rubric`. This bet belongs to nobody else yet;
   say out loud what's being written as you go (which field, what
   `evidence_tag`) but don't stop to confirm each individual call.
3. **Write to shared systems** — `upsert_taxonomy` (a new market/segment/
   buyer becomes visible to every other bet in the portfolio), `advance_stage`,
   `set_status`. **Confirm the exact values with the human before writing.**
   If no `STRATEGY_MCP_TOKEN` is available, print what WOULD be written and
   say so plainly — never fail silently, never fake a write.

Every write in every tier passes `via: "bet-idea"`.

## Purpose

Most business ideas at NSLS arrive as a sentence in a hallway or a Slack
message, and most of them die there — not because they're bad, but because
nobody ever forced them into a shape that could be argued with. `bet-idea` is
that forcing function: it drafts the full canvas and thesis in minutes so the
human is correcting instead of authoring, then spends the rest of the
conversation making the idea's weakest points visible — the assumption that
would collapse everything else if it's wrong, the box nobody can name a real
human for, the color that's red because the risk really is existential. It
ends with an honest, low-confidence score and an explicit ask: is this worth
one of our scarce research slots? Never assumed, always asked.

## When to use

- Someone has a business idea — a hallway pitch, a Slack message, a pasted
  doc — and it isn't a bet yet.
- **NOT** for an idea that's already a bet at Research stage or later (that's
  `bet-research` / `bet-plan` / `bet-review` / `bet-run` — route through
  `bet-studio` if unsure which).
- NOT for logging evidence against an existing bet, portfolio review, or
  experiment tracking — `bet-studio` hands those to their own places.

## Quick Start

Idea → **1** Sketch capture → **2** Taxonomy + `create_bet` → **3**
Office-hours diagnostic → **4** Causal-chain interrogation → **5** Stress test
→ **6** Rubric → **7** The gate offer → a bet at Idea stage (or Research, if
earned) with a full canvas, an honestly-tagged assumption chain, and a
low-confidence score.

## Operating rules

- **Heartbeat every step.** Say what you're about to do, do it, then report
  what happened before moving on — "drafting all 9 canvas boxes now," "wrote
  `canvas.problem` tagged `assumption`," "taxonomy: no existing segment
  matches, proposing a new one." Never batch silently through steps 1–7.
- **AI-drafted content is never `data`.** Every section you draft — not the
  human — is written via `update_section` with `evidence_tag: "assumption"`
  (a reasoned guess) or `"opinion"` (a pure hunch). Only the human's own
  first-hand knowledge earns `data`, and only they can supply it. The one
  exception: internal-origin bets, where `data`/`estimate` on
  problem/solution content must cite the internal usage it's grounded in
  (Step 1) — still never for anything about the *external* market.
- **The human corrects; you don't author from nothing they said.** Draft from
  their one-liner/conversation/pasted material — extrapolate, don't invent
  facts that weren't implied.
- **The advance offer is explicit and never automatic.** `advance_stage`
  requires the human's own "yes" to the gate question in step 7. No amount of
  a high rubric score substitutes for asking.

## Red flags — STOP

- Tagging a drafted section `data` because it "sounds solid." → It's a guess
  until the human says otherwise. `assumption` or `opinion`, always.
- Accepting the first answer to a diagnostic question and moving on. →
  `references/diagnostic-questions.md` exists because the first answer is
  the polished one. Push once, then push again.
- Writing assumptions to `strategy_assumptions` without covering all three
  risk types. → `references/chain-interrogation.md`'s coverage check exists
  for a reason; flag any of customer/market/technical with zero assumptions.
- Calling `advance_stage` because the rubric score looked good. → The score
  is not the gate. The human's explicit yes to "worth a research slot?" is.
- Silently skipping the stress test's alternative-canvas offer or writing it
  to the engine without the human adopting it. → It's conversation-only
  scaffolding unless they say to keep it.
- Creating a new market/segment/buyer via `upsert_taxonomy` without saying so
  first. → Shared-system tier. Confirm, then write.

## Step 1 — Sketch capture

**Purpose:** get the whole canvas + thesis on the page in minutes, not hours.

**Origin question, first.** Ask: *"Where does this bet come from — (a) a
market hypothesis (we think others will pay), or (b) an internal need (we
built/are building it for ourselves)?"*

- **Market-origin** — proceed exactly as the rest of this workflow is
  written.
- **Internal-origin (dogfood)** — problem/solution boxes may be tagged
  `data` or `estimate` *when grounded in our real internal usage* (name the
  internal system in the section content); log that usage as evidence —
  `log_evidence(bet_id, kind: "external"` or `"experiment_result", title:
  "<internal system> usage", evidence_tag: "data", via: "bet-idea")`, no
  `signal_strength` (internal use is not market demand). Step 4's chain then
  centers on the commercialization leap — "an institution outside NSLS has
  this problem" / "they'll pay rather than build or ignore it" get
  `priority` 1–2, `risk_type: customer`/`market` — and `thesis.right_to_win`
  should name NSLS as the first, live customer. **Guard: internal
  enthusiasm is `interest`, never demand — external evidence still climbs
  the commitment ladder.**

From whatever the person hands you — a one-liner, a rambling conversation, a
pasted doc — draft all **9 canvas boxes** (`canvas.problem`, `.segments`,
`.uvp`, `.solution`, `.channels`, `.revenue`, `.costs`, `.metrics`,
`.unfair_advantage`) and all **6 thesis fields** (`thesis.customer`,
`.problem`, `.offering`, `.why_now`, `.right_to_win`, `.ambition_2028`).
Nothing is written to the engine until step 2's `create_bet` returns a
`bet_id` — all 9+6 drafts live in conversation until then, and then become
the first `update_section(bet_id, field_key, content_md, evidence_tag)`
calls. Every box is `assumption` or `opinion` — never `data`, no matter how
confident the draft sounds.

As you go, **note the order** in which the human actively engages with (adds
to, argues with, corrects) the first three boxes. Don't overthink this — it's
a light read of what they care about first — but keep it; the causal-chain
step below reuses it as the natural order to walk the chain of beliefs.

## Step 2 — Taxonomy

**Purpose:** place the bet in the seeded taxonomy and create it.

Call `list_taxonomy` and help pick the market, segment, and buyer — seeded
taxonomy already has markets (college, high-school), segments
(community-college, 4-year-public, 4-year-private, public-high-school), and
buyers (VP/Director of Career Services (b2b), Undergraduate student (b2c),
Chapter advisor (b2b)). B2B vs. B2C follows directly from which buyer is
picked — don't ask separately.

If none of the seeded options genuinely fit, `upsert_taxonomy(kind, fields)`
creates a new one — **shared-system tier: confirm the fields first.** A new
segment's filter must be a whitelisted-column filter; validate it
immediately by running `size_segment(filter)` and showing the computed size
before treating the segment as real. Don't take an unvalidated segment
forward.

`create_bet(name, one_liner, audience, market_id, segment_id, buyer_id,
motion)` happens here, once the taxonomy is settled — carry over the drafts
from step 1 as the first `update_section` calls against the new `bet_id`.

## Step 3 — Office-hours diagnostic

**Purpose:** pressure-test the weakest boxes before they get load-bearing
assumptions built on top of them.

Read `references/diagnostic-questions.md` and run its forcing questions
against whichever canvas boxes are thinnest — usually segments, problem, or
UVP. Name the actual human the bet serves (not "colleges," a person with a
title). Get the status-quo workaround and what it costs today. Find the
smallest thing someone would pay for **this week**. Push past the first
polished answer — that's the whole point of the reference's anti-sycophancy
rule. Update the relevant sections with the sharpened content once the human
lands on something truer than the first draft.

## Step 4 — Causal-chain interrogation

**Purpose:** name every load-bearing belief and rank which one breaks the
model first if it's wrong.

Read `references/chain-interrogation.md` and walk the chain of beliefs in the
fill order recorded in step 1. For each load-bearing assumption, call
`upsert_assumption(bet_id, statement, source_field_key, belief_type,
risk_type, chain_position, priority)`:
- `belief_type`: `leap_of_faith` | `anecdote` | `fact`
- `risk_type`: `customer` | `market` | `technical`
- `priority`: 1 = riskiest. Ask the domino question — *"if this is wrong,
  what else collapses?"* — to propose the ranking; **the owner confirms it**,
  never you alone.

Check coverage before moving on: if any of customer/market/technical has zero
assumptions recorded, say so and go find one — an uncovered risk type is a
blind spot, not a clean bill of health.

## Step 5 — Stress test

**Purpose:** rate the bet across its 7 dimensions and produce a sequenced
fix-first list — not a scoreboard.

Read `references/stress-test-rubric.md`. Score **Clarity, Desirability,
Viability, Feasibility, Defensibility, Mission, Timing** red/yellow/green,
each with a one-line why. Then sequence, don't just list: reds first, and
among reds the one whose failure would invalidate the most of the rest of the
model — existential risk before nice-to-have risk. This is a prioritized
what-to-fix-first list, not a percentage or an average.

Optionally, draft **one** alternative canvas (a different segment, or a
different value proposition) as a comparison point — present it in
conversation only. Do not write it to the engine unless the human explicitly
adopts it as the new direction.

## Step 6 — Rubric

**Purpose:** produce the bet's first, honestly low-confidence, stack-rank
input.

Call `score_rubric(bet_id, scores)` for all 5 criteria — `market_size`,
`right_to_win`, `time_to_revenue`, `build_to_value_risk`,
`evidence_strength` (all 1–5, higher is always better) — every one at
`confidence: "low"`, each with a short note explaining the score. Show the
resulting rank position: this is deliberately the weakest data point the bet
will ever have, and it should look like it.

## Step 7 — The gate offer

**Purpose:** ask, explicitly, whether the idea has earned a scarce research
slot — and never move it without a real yes.

Ask in these or close to these words: **"Worth one of our research slots?"**

- **Yes** → `advance_stage(bet_id, to_stage: "research", rationale,
  attest: { worth_researching: true })`. Show the returned
  `{ moved, gate: { checks } }` regardless of outcome.
- **No** → leave the bet at Idea. If the human wants it explicitly shelved
  rather than just left idle, confirm the rationale and call
  `set_status(bet_id, status: "parked", rationale)`.

**Never call `advance_stage` without this explicit yes** — the attestation
*is* the point of the gate, not a formality around it.

## The pipeline (where this sits)

```
idea ──bet-idea──▶ Idea-stage bet: full canvas + thesis (assumption/opinion
                    tagged), ranked assumption chain, stress-test sequence,
                    low-confidence rubric score
                  ──▶ human says yes ──▶ Research stage (attest.worth_researching)
                  ──▶ human says no  ──▶ stays Idea, or parked with rationale
       owner picks up research ──▶ bet-research (Phase 4, interim: log_evidence
                                    by hand, guided by the Customer Forces
                                    material referenced here)
```

- Upstream of: `bet-research` (not yet built — interim path noted above).
- Called by: `bet-studio`'s "add an idea" hand-off (carries over any concept
  already stated).
- Writes to: the `strategy-studio` MCP server (Strategy Studio engine behind
  `market.nsls.org`).

## Reference index

- `references/diagnostic-questions.md` — the office-hours forcing questions
  and the anti-sycophancy rule that keeps this step honest.
- `references/chain-interrogation.md` — Maurya's belief-chain procedure,
  operationalized against `upsert_assumption`.
- `references/stress-test-rubric.md` — our 7-dimension rubric, anchored to
  the engine's evidence tags and experiment kinds.
- `references/leanspark-stress-test-notes.md`,
  `references/customer-interview-playbook-notes.md` — the Phase 1 source
  notes these three references are built from.

## No token / server missing

If `strategy-studio` MCP calls fail or the tools aren't visible, don't guess
at what would have been written and don't fail silently — print the exact
values each call would have carried (field keys, evidence tags, assumption
statements, scores) so the human can enter them by hand, and point at
`/connect` or the README's Strategy Studio setup section
(`STRATEGY_MCP_TOKEN`, minted by Kevin, SLT authors only).

## Rationalization table

| Excuse | Reality |
|---|---|
| "This draft is basically certain, I'll tag it `data`." | You drafted it, the human didn't confirm it yet. `assumption` or `opinion` until they do. |
| "They already answered the diagnostic question, moving on." | The first answer is the polished one. Push once, then push again — that's the reference's whole design. |
| "I'll rank the assumption priorities myself, it's obvious which is riskiest." | Domino logic proposes the order. The owner confirms it — it's their bet. |
| "The rubric scored well, let's advance it." | The score isn't the gate. Ask the explicit gate question in step 7 regardless of score. |
| "The alternative canvas is good, I'll just write it in too." | Conversation-only unless the human adopts it. Writing it unasked pollutes the real bet's history. |
| "It's just a new segment, I'll create it and move on." | Shared-system tier — every other bet sees this taxonomy. Confirm first. |
| "No token, I'll skip the write and keep going quietly." | Print what would have been written. Silent skips lose the human's own idea. |
