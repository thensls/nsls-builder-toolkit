# LEANSpark stress-test — reference notes for the bet-idea validation step

> Copied from thensls/market-exploration docs/plans, 2026-07-18.

**Saved by Kevin's request (2026-07-17) as follow-up context for Phase 2:**
the `bet-idea` skill's canvas stress-test step (design doc: "canvas
stress-test with a prioritized what-to-fix-first list (LEANSpark pattern)").

Sources:
- https://leanspark.ai/use-cases
- https://leanspark.ai/guides/tutorial-stress-test
- https://leanspark.ai/guides/tutorial-read-results

## The model to borrow

**7 stress-test dimensions** (LEANSpark scores a Lean Canvas across):
1. Clarity
2. Desirability
3. Viability
4. Feasibility
5. Defensibility
6. Mission
7. Timing

(The public guides name the dimensions but do not publish per-dimension
rubrics — when building bet-idea's stress test we define our own rubric per
dimension, anchored to our evidence tags and demand-signal ladder.)

**Three-tier color rating per dimension** (their definitions, verbatim):
- **Red** — "existential risks — things that could kill your business if
  left unaddressed"
- **Yellow** — "known unknowns — you have a hypothesis but no evidence yet"
- **Green** — "validated or low-risk — move on to higher-priority items"

Each score carries a brief explanation of WHY it scored that way — never a
bare color.

**Prioritization framework ("sequence matters more than scores"):**
1. Look at red dimensions first; among those, find the most critical.
2. Existential risks take precedence: "If your Customer Segment is wrong,
   nothing else matters. If your Problem isn't real, your Solution is
   irrelevant."
3. Domino-effect logic: find the assumption that, if wrong, invalidates the
   rest of the model.
4. Each rating points to a SPECIFIC experiment or validation activity as
   the next step — not generic advice.

**The misconception to design against** (quote): "The goal isn't to turn
red into green on a screen. It's to reduce uncertainty through real-world
evidence."

## Mapping onto Strategy Studio (for the Phase 2 plan)

- The 7 dimensions become the stress-test lens inside `bet-idea` step (d);
  red/yellow/green maps naturally onto our evidence tags
  (opinion/assumption ≈ yellow-red, estimate ≈ yellow, data ≈ green) and
  the causal-chain belief types (leap_of_faith / anecdote / fact).
- "Domino-effect logic" IS our `strategy_assumptions.priority` ordering —
  the stress test should propose the priority ranking, the owner confirms.
- "Points toward a specific experiment" maps to our experiment kinds
  (roadshow | pre_sale | concierge | landing_page | pilot | build) —
  channel-aware per the design (warm B2B → rep-led/roadshow instruments).
- Per-dimension explanations feed `update_section` summaries so the
  stress-test verdict is revision-logged like everything else.
- Do NOT gate on "all green" — gates stay evidence-based (the design's
  demand-signal ladder); the stress test is a prioritizer, not a gate.
