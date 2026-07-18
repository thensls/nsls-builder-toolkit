# Gate progress — entry check + the planned→live checklist, rendered client-side

Self-contained copy for `bet-plan`: the entry-side summary of the
research→planned gate (so a bet arriving here can be sanity-checked without
reading `bet-research`'s reference material), and the full planned→live
checklist this skill drives toward. Shown after every section write and at
the end of every session (Step P5 is the final render before the advance
offer).

## The NEVER-probe rule (verbatim)

```
NEVER call advance_stage to "check progress". research→planned has no
attestation — if the gate happens to pass, the probe MOVES the bet. Compute
progress from get_bet instead, using the checklist below. advance_stage is
called exactly once: when the owner says advance.
```

The same reasoning governs `bet-plan`'s own gate: **planned→live also
carries no attestation** — `advance_stage(bet_id, to_stage: "live", ...)`
takes a `rationale`, never an `attest` object. That means there is no safe
way to "peek" at the planned→live checklist by calling `advance_stage`
either — if all four checks below already pass, the call moves the bet on
the spot. Compute the checklist from `get_bet` every time, and reserve
`advance_stage` for the one moment the owner actually says take it live.

## Entry check (research→planned, summary)

A bet handed to `bet-plan` should already be at stage `planned` — meaning
`bet-research` drove it through the research→planned gate already. If a bet
arrives at stage `research` instead, it belongs to `bet-research`; the quick
tell is whether the seven research→planned checks are green. If any read
red, route back to `bet-research` with one sentence naming which check
failed — don't attempt to close research-stage gaps from inside `bet-plan`.

The seven checks, one line each (numbers match `bet-research`'s
`references/gate-progress.md` exactly):

1. `market_complete` — all 5 `market.*` sections non-empty.
2. `econ_complete` — all 5 `econ.*` sections non-empty.
3. `top_assumptions_resolved` — the up-to-3 riskiest (lowest `priority`
   value) assumptions present are `validated` or `invalidated`; denominator
   is `min(3, assumption count)` — a bet with only 1 or 2 assumptions needs
   exactly those resolved, not a padded /3.
4. `conversations` — ≥5 interview/roadshow evidence rows, ≥4
   problem-confirmed, ≥3 distinct institutions.
5. `demand_signals` — ≥2 linked rows at `exploration`/`commitment`/`payment`.
6. `sizing_both_ways` — `market.obtainable` has both `data.top_down` and
   `data.bottom_up` as numbers, both DOLLAR figures (obtainable revenue) —
   see `bet-research`'s `references/self-serve-research.md` for how each is
   composed.
7. `rubric_scored` — all 5 criteria scored, none still `low` confidence.

If the checklist reads green but the bet was never advanced (an owner sat on
a ready bet), say so and offer the advance rather than silently starting
`bet-plan`'s own work on a research-stage bet.

## The planned→live checklist (transcribed from `gates.ts` — keep exact)

1. **`exec_complete`** — all 5 `exec.*` sections have non-empty
   `content_md`: `capabilities`, `team`, `dependencies`, `top_risks`,
   `core_impact`.
2. **`proof_complete`** — all 6 `proof.*` sections have non-empty
   `content_md`: `experiment_2026`, `investment`, `milestones`,
   `threshold_continue`, `threshold_accelerate`, `threshold_stop`.
3. **`experiment_defined`** — ≥ 1 experiment exists on the bet.
4. **`sell_first`** — every experiment with `kind: "build"` has a
   non-empty `rationale`.

## Rendering format

Show this after EVERY `exec.*`/`proof.*` write and at the end of every
session:

```
planned → live gate
  [✓] exec page 5/5
  [✗] proof page 4/6 (missing: threshold_accelerate, threshold_stop)
  [✓] experiment defined (1: pre_sale — "Fall roadshow pre-sale")
  [✓] sell-first: 0 build experiments, nothing to check
Next cheapest unlock: …
```

Always close with the single next-cheapest unlock. If the adversarial
review hasn't run yet, say so explicitly alongside the checklist — the
review isn't one of the four engine-checked boxes, but Step P4 makes it a
required step before the advance offer regardless of what the checklist
reads. Check for a completed round by looking for an "Adversarial review
round N" block in `exec.top_risks` — Step P4 writes one after every
completed round, even a clean one with no accepted fixes.
