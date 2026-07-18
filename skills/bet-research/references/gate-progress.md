# Gate progress — the research→planned checklist, rendered client-side

Used by `bet-research` throughout — shown after every evidence write and at
the end of every session (Step R7). This checklist mirrors the engine's
`gates.ts` exactly; the numbers below are transcribed from it and must stay
exact if the engine ever changes.

## The rule (verbatim)

```
NEVER call advance_stage to "check progress". research→planned has no
attestation — if the gate happens to pass, the probe MOVES the bet. Compute
progress from get_bet instead, using the checklist below. advance_stage is
called exactly once: when the owner says advance.
```

Unlike `idea → research` (which requires `attest.worth_researching`),
`research → planned` has no attestation gate. That means there is no safe
way to "peek" at the checklist by calling `advance_stage` — if all seven
checks already pass, the call moves the bet on the spot. Compute the
checklist yourself from `get_bet` (sections, assumptions, evidence, scores)
every time, and reserve `advance_stage` for the one moment the owner actually
says go.

## The checklist (transcribed from `gates.ts` — keep the numbers exact)

1. **`market_complete`** — all 5 `market.*` sections have non-empty
   `content_md`.
2. **`econ_complete`** — all 5 `econ.*` sections have non-empty `content_md`.
3. **`top_assumptions_resolved`** — the engine takes `ranked.slice(0,3)`: the
   up-to-3 riskiest (lowest `priority` value) assumptions present are all
   `validated` or `invalidated`. The denominator is `min(3, assumption
   count)`, not a fixed 3 — a bet with only 1 or 2 assumptions needs exactly
   those resolved, no more. Fails only when zero assumptions exist ("nothing
   has been de-risked"). The client-side bar must never read red when this
   check would already pass.
4. **`conversations`** — evidence rows of kind `interview` or `roadshow`:
   total ≥ 5 AND rows with `data.problem_confirmed === true` ≥ 4 AND distinct
   `entity_id` values ≥ 3 (five meetings with one friendly school can't
   satisfy it).
5. **`demand_signals`** — ≥ 2 rows with `signal_strength` ∈ {exploration,
   commitment, payment} AND non-empty `link`. Interest never counts; unlinked
   grades never count.
6. **`sizing_both_ways`** — `market.obtainable` section `data.top_down` AND
   `data.bottom_up` are both numbers, and both are DOLLAR figures (obtainable
   revenue) — see `references/self-serve-research.md` for how each is
   composed. Raw counts never belong in either field.
7. **`rubric_scored`** — latest score per criterion exists for all 5 AND none
   is still `low` confidence.

## Rendering format

Show this after EVERY evidence write and at the end of every session:

```
research → planned gate
  [✓] market page 5/5        [✗] econ page 3/5 (missing: unit_economics, cases)
  [✗] top assumptions 1/3 resolved (denominator = min(3, assumption count))
  [✗] conversations 2/5 · problem-confirmed 2/4 · institutions 2/3
  [✓] demand signals 2/2 linked exploration+
  [✓] sized both ways (top-down 1.4M / bottom-up 900K)
  [✗] rubric: evidence_strength still low confidence
Next cheapest unlock: …
```

Always close with the single next-cheapest unlock, tied to the riskiest
unresolved assumption — not just the check that happens to be closest to
green. A cheap unlock on a low-stakes check is a worse recommendation than a
harder unlock on the assumption that would collapse the most of the model if
wrong.

## `staleAssumptions`

Every `update_section` response includes `staleAssumptions` — assumptions
anchored to that field via `source_field_key`. Rewriting a section can leave
its assumptions validated against text that no longer exists underneath
them. Re-interrogate any assumption listed there, and say so out loud
(heartbeat) — this is engine-provided; consume it, never skip it silently.
