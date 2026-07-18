---
name: bet-studio
description: >-
  Use when someone wants to work in the NSLS Strategy Studio — the business-bet
  portfolio pipeline behind market.nsls.org. The front door that shows what's
  already in flight and hands off to the right tool for wherever a bet sits in
  its lifecycle: capturing a new idea, researching one, planning its economics,
  reviewing the portfolio, or tracking a live bet's experiments. Triggers: "bet
  studio", "strategy studio", "business bet", "work on a bet", "new business
  idea", "show the portfolio", "stack rank the bets", "what bets are we
  running".
---

# bet-studio

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** — `list_bets`, `get_stack_rank`, `get_bet`, `list_taxonomy`.
   Everything this skill does. Free, no confirmation needed.
2. **Configuration / new-content** — none. This skill is a **router**; it never
   drafts canvas content, sections, or scores itself. Any authoring happens in
   the sub-skill it hands off to, under that skill's own tier for it.
3. **Write to shared systems** — this skill never calls a write tool. If the
   interim guidance below ever puts `advance_stage` or `set_status` in front of
   a builder (e.g. flagging a bet to kill in the review interim), that call is
   **always confirmed with the human first** — named the bet, named the tool,
   said out loud what it does — never assumed on their behalf.

## Purpose

A builder shouldn't have to know which of six lifecycle skills to run, or dig
through the engine to see what's already there. They say what they want to do,
see the live portfolio, pick a bet, and get handed the right tool with that
bet's context already loaded. This skill is a **router**: it asks the
lifecycle question, reads the live portfolio, and hands off — the real work
(drafting, interrogating, scoring, reviewing) stays in the sub-skills.
(`market.nsls.org` is the same data as a dashboard *view*; this skill is the
*doer*.)

## The lifecycle map

| Builder wants to… | Hand off to | Moves the bet |
|---|---|---|
| **Add an idea** | `bet-idea` (carry over any concept already stated) | → Idea |
| **Research a bet** | `bet-research` (works the assumption chain riskiest-first: self-serve market research, warm-channel interviews via Customer Forces, sizing both directions, roadshow sprints — drives the research→planned gate; hand off with `get_bet` context) | Research → Planned |
| **Plan economics / proof plan** | `bet-plan` (2026–2028 model with downside/base/upside, execution & risk, sell-first channel-aware experiment with three thresholds, adversarial review loop — drives the planned→live gate; hand off with `get_bet` context) | Planned → Live |
| **Portfolio review** | *Phase 5 `bet-review` — not built.* Interim: render the stack rank + portfolio overview yourself — `get_stack_rank` plus `list_bets` (see `references/portfolio-views.md`) — then drill into `get_bet` only for the 1–3 bets the human picks, to check that bet's status update and flag invalidated assumptions. Per-bet health across the whole board arrives with the Phase 3 UI / a future bulk endpoint — the engine has no bulk status tool today, so don't loop `get_bet` over the full portfolio. | n/a (cross-cutting) |
| **Run experiments** | *Phase 5 `bet-run` — not built.* Interim: say plainly it's coming. | Live → Running → Scaling |

## Flow

1. **Ask the lifecycle question:** *"What would you like to do — add an idea,
   research a bet, plan its economics, review the portfolio, or track a live
   bet's experiments?"*
2. **Show the live portfolio** (skip only when adding a brand-new idea with
   nothing to compare against). Call `get_stack_rank` for active bets and
   `list_bets` for the graveyard, grouped by stage cohort with each bet's
   confidence surfaced beside its rank — never let a low-confidence idea-stage
   sketch read as comparable to an evidence-backed research-stage bet. Parked
   and killed bets render last, under a collapsed "Graveyard." Exact recipes
   and rendering rules: `references/portfolio-views.md`. Ask which bet they
   want, or confirm the intent is genuinely a new one.
3. **Sanity-check stage vs. intent.** The bet's `stage` (from the listing) is
   the signal — an idea-stage bet has no economics to plan yet. "Research a
   bet" on an IDEA-stage bet needs the stage gate first: evidence logged
   while the bet sits at Idea is preliminary and does not advance anything.
   Route to `bet-idea` — it resumes existing Idea-stage bets without
   re-creating — if the canvas itself isn't done; if the canvas is done
   and the owner judges it worth a research slot, draft the
   `advance_stage(bet_id, to_stage: "research", attest: { worth_researching:
   true })` call for the OWNER to fire (bet-studio stays read-only — it
   drafts the call, the owner fires it), then show the returned gate
   checklist. A bet at Research goes to `bet-research`; at Planned, to
   `bet-plan` — each loads `get_bet` context on hand-off. A bet already
   `planned`+ has nothing left for `bet-idea` to do. A request that duplicates an existing bet (same name/
   one-liner in the listing) surfaces the existing one before anything new
   gets created. When intent and stage don't line up, say so and route to what
   actually fits.
4. **Hand off** with the chosen bet's full context loaded — call `get_bet` and
   carry its `bet_id`, `name`, `stage`, canvas/thesis sections, assumption
   chain, and latest scores into the sub-skill. Tell the builder which skill
   is running and why.

## Heartbeat rule

Report every read before acting on it — "portfolio: 6 active (2 idea, 3
research, 1 planned), 2 in the graveyard" — and report every hand-off ("routing
to `bet-idea` with your one-liner carried over"). Never silently skip the
portfolio view, and never silently substitute a different bet than the one
named.

## No token / server missing

If `strategy-studio` MCP calls fail or the tools aren't visible, don't fail
silently and don't guess at portfolio state. Say so, then point at the
README's **Strategy Studio** setup section (`STRATEGY_MCP_TOKEN`, minted by
Kevin, SLT authors only) and suggest running `/connect`.

## What this skill does NOT do

- It does not draft, interrogate, score, or review — it routes. Each sub-skill
  owns its work.
- It does not write to the engine — reads only, always.
- It is not the dashboard — for the visual portfolio, that's `market.nsls.org`.

## Reference index
- `references/portfolio-views.md` — tool-call recipes and rendering rules for
  the stack rank, stage grouping, and graveyard.
- Hand-off targets: `bet-idea`, `bet-research`, `bet-plan` (built);
  `bet-review`, `bet-run` (Phase 5, not yet built).
