# Portfolio views — tool-call recipes and rendering rules

Used by `bet-studio` step 2 (show the live portfolio) and by the interim
portfolio-review guidance. All calls are read-only, no confirmation needed.

## Recipe 1 — active bets, stack-ranked

```
get_stack_rank()   // no args
```

Returns every `status: "active"` bet, ordered by cached `rank_score` (0–100)
descending, with `ownerPerson` resolved (name + photo) on each row. This is
the primary listing — it already carries the ranking; don't re-sort it.

## Recipe 2 — the graveyard (parked / killed)

`get_stack_rank` only returns active bets, so the graveyard needs a separate
call:

```
list_bets({ status: "parked" })
list_bets({ status: "killed" })
```

(Two calls, not one `list_bets({})` — filtering client-side after a single
unfiltered call also works and costs the same round trip either way; either
is fine. `list_bets` takes `stage?` and `status?`, both optional, and returns
the same bet rows ordered by `rank_score` desc.)

## Recipe 3 — taxonomy labels

```
list_taxonomy()   // no args
```

Returns `{ markets, segments, buyers }`. Bet rows carry `market_id` /
`segment_id` / `buyer_id` (uuids), not names — call this once per portfolio
view and build an id→name lookup so bets can render as human-readable chips
("Community College · Career Services") instead of raw ids.

## Recipe 4 — bet detail for hand-off

```
get_bet({ bet_id })
```

Full memo: bet row, all canvas + 5 memo-page sections, assumption chain,
evidence, per-criterion scores, experiments, latest status updates, stage
events, recent revisions. Called once, on the single bet chosen for hand-off
(step 4) — never in a loop over the whole portfolio; that's an N+1 pattern
this skill doesn't need.

## Rendering rules

**Group by stage cohort, in lifecycle order:** idea → research → planned →
live → running → scaling. Within each cohort, preserve the `rank_score`
ordering `get_stack_rank` already returned — don't re-rank across cohorts.

**Confidence beside rank — as a stage proxy, not a per-criterion lookup.**
The literal per-criterion `confidence` (`low`/`medium`/`high`) lives on
`strategy_scores`, which only `get_bet` exposes — calling it for every bet in
a listing is the N+1 pattern recipe 4 warns against. The engine's own gates
make the stage a reliable proxy instead, so use it:

| Stage | Confidence label to show | Why |
|---|---|---|
| Idea | `low` | `bet-idea`'s rubric step always scores at low confidence by design — nothing has been tested yet. |
| Research | `low → medium` (rising) | Assumptions are being resolved; not gated until the next stage. |
| Planned, Live, Running, Scaling | `medium/high` | The `research → planned` gate requires all 5 rubric criteria re-scored at medium+ confidence — bets can't reach this cohort otherwise. |

Render this plainly next to the rank — e.g. `#2 · rank 74 · confidence: low
(idea-stage)` — so a low-confidence idea-stage sketch is never presented as
directly comparable to an evidence-backed research-or-later bet. If a builder
wants the exact per-criterion confidence and notes for one specific bet, drill
in with `get_bet` (recipe 4) rather than inferring further from the listing.

**Graveyard last, collapsed.** Parked and killed bets (recipe 2) render after
every active cohort, under a single "Graveyard" heading, collapsed to
name + stage-at-exit + status by default — expand only if asked. Killed bets
keep their full history in the engine; this view doesn't need to surface it
unless the builder asks.

**Owner faces.** `get_stack_rank`'s `ownerPerson` is the only recipe here that
resolves a face — use it for the active cohorts. The graveyard listing
(`list_bets`) returns the raw `owner` email only; that's fine for a collapsed
view.
