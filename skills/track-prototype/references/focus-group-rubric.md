# Focus-Group Rubric — 4 dimensions, binary anchored sub-checks

The rubric the Phase-2 panel scores a rendered track against. **Judged from the run-through** (the screenshot gallery + click-through in `report.json`), **not from `track.json`.** Live `generate`/`chat` output is part of what's judged (see `focus-group-panel.md`).

## How scoring works

- **4 dimensions, 4 binary sub-checks each = 16 checks.** Each sub-check is **MET / UNMET**, never a 1–10 score — crisp anchors are more repeatable across re-runs and across tracks than a wide scale (which clusters toward the middle).
- Each sub-check is judged by the **median of 3 independent samples**. Clear majority MET → MET; clear majority UNMET → UNMET; **no clear majority → CONTESTED**.
- **The "score" is checks-met / 16** (e.g. 11/16). There is **no weighted composite** — progress is checks turning green across versions (v1 9/16 → v2 14/16).
- **Ship-bar:** **any UNMET sub-check generates a ranked recommendation.** A **CONTESTED** sub-check generates a **human-review flag**, not an auto-recommendation. There is no average for a weak spot to hide behind.

## Not a prediction — a ranking + gate

These scores are a **relative ranking and a ship-bar gate, NOT a calibrated prediction** of real adoption. Synthetic personas systematically *overstate* adoption; the rubric's predictive validity is unproven until calibration data accrues (see Plan 3 Task 11). Celebrate green checks and act on recommendations; do not over-read the number.

**Calibrate against per-step continuation, not raw completion.** The n=3 seed found the rubric *anti*-correlates with raw completion (it's dominated by track length/position/commitment — a short mandatory form tops completion while scoring lowest here) but ranks **+1** against length-normalized per-step continuation. That's exactly what the "predicts" column below intends — continuation and next-track uptake, not raw end-to-end completion. `calibrate.mjs` reports continuation as the primary coefficient.

## The 4 dimensions

Each sub-check lists what **MET** looks like (UNMET = anything short of it). The "predicts" column maps the dimension to the PostHog metric it's *hypothesized* to predict, for future calibration.

### D1 — Value / payoff · predicts: track start rate + completion/next-track uptake
- **D1.a** Within the first 1–2 screens, the deliverable is named **concretely** (a real output/clarity, not "explore yourself").
- **D1.b** The "why this matters to *me*" is **stated**, not merely implied.
- **D1.c** At completion, a **tangible artifact/clarity** exists the student could point to.
- **D1.d** The ending **previews/motivates the next step** (next track or real-world application).

### D2 — Pacing & momentum · predicts: mid-track drop-off + step-to-step continuation
- **D2.a** No single step exceeds **~8 collects** without a synthesis/break.
- **D2.b** **No wall-of-text** screen; orientation copy stays scannable.
- **D2.c** Each step **names the specific accomplishment** (not a generic "Done!").
- **D2.d** The sequence creates **forward pull** — each step sets up the next.

### D3 — Copy & tone · predicts: completion + sentiment
- **D3.a** Voice is **peer/coach-level and warm** — not corporate or condescending.
- **D3.b** **No unexplained jargon.**
- **D3.c** Personalization **tokens read naturally** (no awkward "Hi {name}," or empty token).
- **D3.d** **On-brand for Society** (matches the voice of the reference example tracks).

### D4 — Friction & fit · predicts: step-1 drop-off + at-risk-segment drop-off
- **D4.a** First interaction is a **low-friction win** (not a cold heavy free-text / long form).
- **D4.b** Later screens **visibly build on earlier answers** (personalization is real, not surface).
- **D4.c** Nothing **invasive or privilege-assuming** is asked early; safe for a first-gen / skeptical member.
- **D4.d** An **anxious or skeptical edge persona would stay in**, not bail.

> The 8 concepts from the earlier draft (value clarity, first-step ease, load, momentum, personalization, copy, peak-end, trust) are all folded into these 16 sub-checks — nothing was dropped, it's just scored as crisp checks instead of fuzzy 1–10s.

## Scorecard output shape

`scorecard.mjs` produces, per run: `{ dimensions: { value:{met,checks}, pacing, copy, fit }, total, composite: "n/16", shipBar: [{dim,key}], contested: [{dim,key}] }`. The dimension keys are `value | pacing | copy | fit`; sub-check keys are `a | b | c | d`.
