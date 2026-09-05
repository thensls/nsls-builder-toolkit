# Dashboard review checklist

Run this on every dashboard before it is shared, and on any existing dashboard
someone calls confusing. Score each row **Pass / Fail / N/A**. Every P0 row
must pass before the page ships. Report failures as `P0 · <row> · <what you
saw> · <fix>`.

## A. Purpose (P0)

| # | Check |
|---|---|
| A1 | The page names one type: operational, strategic, or analytical — and only one describes it |
| A2 | One primary reader is named; secondary readers are served by a tab or link, not a row |
| A3 | Every headline metric maps to a stated decision |
| A4 | The spec has a Cut list with reasons |

## B. Five-second test (P0)

| # | Check |
|---|---|
| B1 | Someone who did not build it, shown the page for 5 s, can say whether things are on track |
| B2 | …and can say which single tile needs attention (or that none does) |
| B3 | The eye lands on the headline band first; nothing above or beside it competes (no hero image, no oversized filter bar, no logo wall) |

Protocol: give a fresh subagent (or a colleague) a screenshot for five seconds
of reading, then ask B1 and B2 without the image. Record their verbatim answer.

## C. Metric triage (P0)

| # | Check |
|---|---|
| C1 | ≤ 6 tiles in the headline band |
| C2 | Every headline value has a comparison: target, prior period, or normal range |
| C3 | Targets and alert thresholds are not confused (a "goal" label is a goal, not a trigger) |
| C4 | No metric appears as three tiles for three time frames; one card, cadence-matched hero |
| C5 | No bare percent-change is colored good/bad without a target or range behind it |
| C6 | The metric measures the thing decided on (not a proxy that is easier to count) |

## D. Layout and hierarchy (P1)

| # | Check |
|---|---|
| D1 | Headline + explain bands fit one 1280×800 viewport for operational/strategic pages — **proven by a screenshot at that size**, not a computed budget |
| D1b | Header ≤ 120 px; cards within a band are equal height |
| D2 | Order is importance → logic (funnel, time), never alphabetical or by source |
| D3 | 12-column grid; one gutter, one radius, one padding; edges align |
| D4 | Whitespace: nothing touches; no tile was shrunk to make room |
| D5 | Default view is calm; drill-down is one level |
| D6 | Splits are by audience/question, not by data source; nothing must be compared across tabs |

## E. Encoding (P1)

| # | Check |
|---|---|
| E1 | Each chart's data shape was named before the chart was chosen (spec says so) |
| E2 | No gauge, 3D, dual-axis, radar, word cloud, truncated-axis bar, donut with > 4 slices |
| E3 | Same data shape → same chart type across the page |
| E4 | Bars sorted (unless natural order) and start at zero; ≤ 4 line series or small multiples |
| E5 | Series labeled directly; legends ≤ 5 items where unavoidable |
| E6 | Chart titles state the finding or question; subtitles carry time frame and unit |
| E7 | Metric cards follow label → value → comparison → time frame; value is the largest text |
| E8 | Number formatting is consistent per band; headline precision ≤ 3 significant figures |

## F. Color (P1)

| # | Check |
|---|---|
| F1 | One status triad, same hues on every page of the product |
| F2 | One accent for emphasis; everything else grey; brand color only on header/title/links |
| F3 | Status never conveyed by color alone (symbol or word present) |
| F4 | Passes a colorblind simulation (deuteranopia at minimum) |
| F5 | Text contrast ≥ 4.5:1; borders/status marks ≥ 3:1 — **measured**, not judged |
| F6 | Categorical hues ≤ 5 |
| F7 | Brand confirmed (NSLS vs Society) and palette matches its reference |
| F8 | Society pages: cream ground, hairline `--line` edges, black CTA, status only in terracotta / amber / green; unfilled tracks grey |
| F9 | Society pages: Inter in 700 / 600 / 400 only; every data value (emails, dates, durations, ticks, legend values) in monospace |

## G. Help and labels (P2)

| # | Check |
|---|---|
| G1 | Every derived metric has an info affordance: what it counts, formula, source, refresh |
| G2 | Labels are plain English; no field names, no unexpanded acronyms |
| G3 | Definitions reuse the same text wherever the metric appears |
| G4 | No design rationale in reader-facing copy ("shown uncolored because…", "axis starts at zero"); that text lives in the spec |
| G5 | Headline metrics with a goal show pace (value ÷ goal vs elapsed ÷ period) with a verdict word, not a bare percent of goal |

## H. States (P0)

| # | Check |
|---|---|
| H1 | `as of <date/time>` is visible without scrolling |
| H2 | Stale data shows last confirmed value **and** a stale badge |
| H3 | Missing data shows `No data · <reason>`, never `0`, `—`, or a blank that looks like a value |
| H4 | Loading uses a skeleton at final size; layout does not jump |
| H5 | No value is fabricated, interpolated, or carried forward unlabeled |
| H6 | Small-sample numbers carry `n` |

## I. Responsive and accessibility (P1)

| # | Check |
|---|---|
| I1 | Every page tested at 320 / 375 / 768 / 1024 / 1280; no horizontal page scroll |
| I2 | Hover reveals use `visibility`, not `display`; no reflow on hover |
| I3 | Long text in flex children has `min-width: 0` and wraps |
| I4 | Each page has its own `<title>` |
| I5 | Keyboard reachable filters and tabs; focus visible |
| I6 | Charts have a text alternative (table toggle or `aria-label` with the finding) |

## J. Few's thirteen mistakes — final sweep (P1)

Mark any that still apply:

1. Exceeds a single screen (for operational/strategic)
2. Inadequate context — numbers without comparison
3. Excessive detail or precision
4. Deficient measure — the number is not the thing that matters
5. Inappropriate display media — wrong chart for the shape
6. Meaningless variety — chart types for their own sake
7. Poorly designed media — dual axes, truncated bars, unsorted categories, legends
8. Inaccurate encoding — areas or angles for numbers people act on
9. Poor arrangement — importance not reflected in position
10. Ineffective highlighting — nothing stands out, or everything does
11. Useless decoration — gradients, icons, borders that carry no data
12. Misused color — decorative color, status by hue alone, off-brand palette
13. Unattractive display — inconsistent spacing, type, alignment that make people not come back

## Reporting

```
Dashboard review · <name> · <date>
Type: <operational|strategic|analytical>  Reader: <role>  Brand: <NSLS|Society>

P0 failures (block):
- C1 · 9 tiles in the headline band · demote refund rate, AOV, NPS, tickets, visitors to Detail/Cut
- H3 · Revenue card renders "$0" when the Sheet range returns no rows · show "No data · no rows in range" (reserve "source unreachable" for a failed fetch)

P1 failures:
- E2 · Gauge for YTD progress · bullet bar
- F5 · Border #ded8cc on white = 1.33:1 · use #6b6460 (5.42:1)

Passed: A1–A4, B1–B3, …
Five-second answers (verbatim): "<…>"
```
