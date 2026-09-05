# Metric card anatomy

The metric card (KPI tile, stat tile) is the unit of the headline band. Get it
right once and reuse it everywhere; inconsistency between cards is what makes a
page feel amateur.

## Order of elements (top to bottom, never rearranged)

```
┌───────────────────────────────┐
│ New enrollments · this week  ⓘ│  1 label + help affordance
│                               │
│ 1,842                         │  2 value (hero — largest text on the card)
│ ▲ +7.7% vs last week          │  3 comparison, with symbol AND color
│ On pace for 9,000 MTD goal    │  4 status sentence (optional, plain English)
│ ▁▂▂▃▃▄▄▅▆▆▇█  12 wk           │  5 sparkline (optional, no axes)
│ as of Fri Sep 4               │  6 time frame / freshness (if not on header)
└───────────────────────────────┘
```

| # | Element | Rules |
|---|---|---|
| 1 | **Label** | Plain English, ≤ 4 words, includes the time frame word (`this week`, `YTD`). Never a field name or acronym the reader has to expand. |
| 2 | **Value** | 2–3× the label size. Right unit, right rounding (below). One value per card. |
| 3 | **Comparison** | One of: vs target, vs prior period, vs normal range. Symbol + color + words (`▲ +7.7% vs last week`). Direction color follows the *good* direction: rising refunds are red. |
| 4 | **Status sentence** | Optional. Says what the comparison means: `On pace`, `Below pace by 1,200`, `Outside normal range`. |
| 5 | **Sparkline** | 8–13 points, no axes, no gridlines, one color (grey; accent for the last point if useful). Trend only; never read exact values from it. |
| 6 | **Freshness** | On the page header if all tiles share a source and time; per card if they differ. |

## Number formatting

| Kind | Format | Not |
|---|---|---|
| Counts | `1,842` · `48.9K` · `1.2M` | `48915` · `48,915.00` |
| Money | `$147K` · `$3.9M` · `$80` | `$3,912,440.17` |
| Rates | `3.8%` · `41%` | `0.038` · `3.8147%` · `41.0000%` |
| Deltas | `▲ +132` or `▲ +7.7%`, one of the two | both, unlabeled |
| Small samples | value plus `n = 11,200` | a rate with no denominator |
| Missing | `No data` + reason | `0` · `—` · `N/A` alone |

Precision rule: show the fewest digits that still support the decision. Two
significant figures for headline values; exact values belong in the detail
table. Consistent precision across cards on the same band (`3.8%` next to
`41%` is fine; `3.8%` next to `41.27%` is not).

## Comparison types and when each is right

| Dashboard type | Primary comparison | Secondary |
|---|---|---|
| Strategic | **vs target**, expressed as pace (`59.8% of goal at 67% of year`) | vs prior period |
| Operational (monitoring) | **vs target / threshold** | vs prior |
| Operational (problem-scanning) | **vs normal range** — is this outside what we usually see? | none; flag or no flag |
| Analytical | whatever the filter set implies | — |

**Target ≠ alert threshold** (Desbarats). The target is where you want to be;
the threshold is when a human must act. A revenue card showing `59.8% of goal`
is a target comparison. A support-tickets card turning amber at 200 is a
threshold. Do not label a threshold "goal".

**Pace is the strategic comparison.** A flat `75% of goal` is meaningless
without knowing how much of the period has elapsed. Compute both and show the
verdict:

```
pace   = (value ÷ goal) ÷ (elapsed ÷ period)      e.g. (48,915 ÷ 65,000) ÷ (248 ÷ 365) = 1.11
status = pace ≥ 1.00 → "Ahead of pace" (good) · 0.90–0.99 → "Slightly behind" (watch) · < 0.90 → "Behind pace" (bad)
card   = 48.9K  ·  ▲ 75% of 65K goal  ·  Ahead of pace (68% of year elapsed)
```

Elapsed uses the calendar days of the period through the as-of date, not
today. State the pace bands in the spec; they are thresholds, and a squad may
set different ones.

**Period that does not reconcile, no verdict.** If the supplied figures do not
add up for the stated period (an MTD that is impossible given the days
elapsed, a YTD that is smaller than the sum of the weeks), do not pick the
interpretation that makes the card look best. Show the value with its stated
frame, no pace verdict, and put the discrepancy in the spec as a question for
the data owner.

**No history, no color.** A headline metric must carry a comparison, but if
there is no target and fewer than 8 prior periods to build a normal range,
show the prior-period delta **in grey with no verdict**: `+0.2 pts vs last
week`. Note in the spec when a range becomes computable. Never invent a range
from two data points, and never color a delta because it moved in the
pleasant direction.

**Percent change alone is noise.** `+7.7% vs last week` means nothing without
knowing normal week-to-week variance. Prefer the range: compute the last 8–12
periods, show whether this one is inside or outside the usual band. If you
cannot compute a range, show the delta but do not color it as good/bad; color
only comparisons against a target or range.

## Status colors on a card

- Three states max: good / watch / bad. Same three hues across the entire product.
- Color applies to the comparison line or a small status chip, **never to the whole card background** (a wall of red cards is unreadable; one red chip among grey cards is a signal).
- Every colored status carries a non-color cue: `▲ ▼`, `●`, or a word.
- Neutral (no target, informational) is grey. Do not invent a fourth color for "unknown" — use the missing-data state.

## Sizes that work

At 1280 px wide with a 12-column grid and 24 px gutters:

| Cards in row | Card width | Fits |
|---|---|---|
| 4 | ~290 px | label, value, comparison, sparkline |
| 5 | ~230 px | label, value, comparison (no sparkline) |
| 6 | ~190 px | label + value only; comparison must be short |
| > 6 | — | use two rows of 4, or demote to Explain |

Value type size: 32–40 px for 4 across; 28 px for 6 across. Label 12–13 px.
Comparison 13–14 px. The hierarchy must survive at 375 px wide when the cards
stack; check that the value is still the largest element.

## The one-metric rule

One card, one value. Weekly, MTD, and YTD of the same metric are **one card**:
the cadence-matched frame is the hero, the other two are a small context line
(`MTD 6,212 · YTD 48,915`). Three cards for one metric wastes two headline
slots and makes the top band lie about what matters.
