# Reading the live signal

Two sources, in order: the Studio's precomputed actuals (fast, already per-step),
then `/posthog` for a fresh or deeper cut.

## Studio `PostHogActuals` (base `appzDWu6GowvnACtv`)

One row per live version of a track. The fields that matter for optimization:

| Field | Meaning |
|---|---|
| `track` | the track slug |
| `live_track_version` | content hash of the shipped build (pairs with the authoring `content_hash`) |
| `step_to_step_continuation` | **primary metric** — average share of members continuing from one step to the next. The weak step is the biggest single drop. |
| `dropoff_by_step` | per-step counts, e.g. `start1854→s1:1354→s2:1221→s3:1189→s4:1186` — read the steepest fall between adjacent steps |
| `step1_dropoff` | share who leave at the very first step (a special, common weak point) |
| `completion_rate` | start→finish share (secondary — confounded by length) |
| `n_users` | sample size — **check this first**; a drop on small N may be noise |
| `median_completion_seconds` | typical time to finish (pacing signal) |
| `period` | the window, e.g. `90d→2026-06-11` |

Read it (a PAT with read on the base; else `/connect` or `/airtable`):
```bash
curl -s "https://api.airtable.com/v0/appzDWu6GowvnACtv/PostHogActuals?filterByFormula=%7Btrack%7D%3D%22<slug>%22" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY"
```
(`filterByFormula` uses field NAMES, e.g. `{track}` — not field IDs.)

**Finding the weak step:** parse `dropoff_by_step` into adjacent pairs and compute
each step's continuation (`countₙ₊₁ / countₙ`); the lowest is the weak step. Cross-
check against `step_to_step_continuation` (the average) — a step well below the
average is the target.

## `/posthog` — deeper or fresher

Use the `/posthog` skill when you need a cut the actuals don't have: a funnel by
step for a date range, drop-off segmented by cohort/chapter, or events since the
last actuals refresh. Ground every number you report in one of these sources —
never estimate a drop-off.

## Pairing signal to content

`dropoff_by_step`'s step positions map to the track's substeps in order (the same
flattened order the demo/player uses). Once you have the weak step index, open the
track's `track.json` at that substep — that's the content the focus-group panel
then diagnoses.
