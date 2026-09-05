---
name: dashboard-design
description: >-
  Use when anyone at NSLS is about to design, lay out, build, or critique a
  dashboard, KPI page, scorecard page, metrics wall, status board, or
  reporting page — before the first HTML, Airtable interface, Looker/Hex/
  PostHog dashboard, or slide of tiles gets built — or when an existing one
  feels cluttered, confusing, slow to read, or "nobody looks at it".
  Triggers: "design a dashboard", "dashboard layout", "which chart should I
  use", "too many metrics", "what goes on the dashboard", "KPI cards",
  "make this dashboard clearer", "simplify this dashboard", "dashboard
  review", "match the Society dashboard look", "what fonts / colors / weights
  for the dashboard", "/dashboard-design". Also fires from /squad-dashboard before
  sections are chosen and from /ux-audit when the target is a dashboard.
---

# Dashboard Design

## Safety

1. **Read-only / design** — reading briefs, screenshots, existing pages, data
   definitions; producing the brief, layout, and review. No friction.
2. **Writes** — creating or editing HTML/config/spec files in the builder's
   repo. Say what will be written and where before writing.
3. **External systems** — this skill never publishes, deploys, or writes to
   Airtable/PostHog/Sheets. Hand off to `/squad-dashboard`, `/netlify-deploy`,
   or `/add-domain`. Never fabricate, interpolate, or "fill in" a metric value
   to make a layout look complete.

## Purpose

Most NSLS dashboards fail the same way: every tracked number is promoted to the
top row, charts are picked by habit, color means nothing in particular, and the
reader cannot tell in five seconds whether things are fine. This skill turns a
pile of metrics into a page that answers one question for one audience, and
gives a non-designer the rules a professional dashboard designer applies by
reflex — purpose first, hierarchy by decision, one chart per data shape, color
with meaning, and honest states when the data is missing or stale.

**SUB-SKILL for chart mechanics** (marks, palettes, axes, tooltips): `dataviz`,
when it is available. This skill decides *what goes where and why*; `dataviz`
decides how a chart is drawn. If `dataviz` is not loadable,
`references/chart-selection.md` plus the Society template are enough to draw
correctly.

## Quick Start

Produce these five things, in order. Do not start on step 3 until steps 1–2
are written down.

| Step | Output | Gate |
|---|---|---|
| 1. **Brief** | Dashboard type, audience, the 1–3 decisions it serves, cadence | One type, one primary audience |
| 2. **Metric triage** | Every metric sorted into Headline / Explain / Detail / Cut, each with its comparison | ≤ 6 headline metrics, every one has a comparison |
| 3. **Layout** | Three-band wireframe (headline → explain → detail) or a named pattern | Headline band fits one viewport |
| 4. **Encoding** | Per tile: metric card or chart type, color role, label, help text | No chart chosen without naming the data shape |
| 5. **Review** | Five-second test + 13-mistakes checklist + states + reflow | All P0 rows clear |

Template for steps 1–2: `references/dashboard-brief.md`. Visual system for
step 4: `references/society-visual-template.md` (fonts, colors, weights,
component recipes) with `templates/society-dashboard.css` as the starting
stylesheet. Do the review with `references/review-checklist.md`.

## 1. Define the purpose

Name the type before anything else. A dashboard serves one of these; mixing
them is the root cause of most clutter.

| Type | Question it answers | Cadence | Shape |
|---|---|---|---|
| **Operational** | What's happening now? What needs attention? | Minutes–daily | Dense status, thresholds, alerts, single screen |
| **Strategic** | Are we on track toward the goal? | Weekly–quarterly | Few metrics vs targets, trend, narrative |
| **Analytical** | What is driving this change? | Ad hoc | Filters, breakdowns, drill-down, exploration |

Desbarats' sharper cut inside "operational": **problem-scanning** (flag what is
outside normal so a human acts) is not **performance-monitoring** (show how we
are doing against a goal). A page that tries to do both does neither. If the
squad needs both, that is two views, not one page.

Write down, in the brief:
- **Audience** — one primary reader (SLT, squad, Gary, a chapter advisor). Others are secondary and get a tab, not a row.
- **Decisions** — the 1–3 decisions this reader makes with the page. A metric that informs no decision is not a headline.
- **Cadence** — how often the reader looks and how fresh the data must be. This sets whether "as of last Friday" is fine or a defect.

## 2. Triage the metrics (the five-second rule)

The reader must grasp the primary status in five seconds. That is impossible
with 15 equal tiles. Sort every metric:

| Bucket | Meaning | Where it lives |
|---|---|---|
| **Headline** | Status the reader needs before anything else | Top band. ≤ 6 (4 is the sweet spot) |
| **Explain** | Trends and breakdowns that explain *why* the headline moved | Middle band. 2–4 charts |
| **Detail** | Exact values, rows, lists for the reader who digs | Bottom band, a tab, or a linked page |
| **Cut** | Nobody decides anything with it here | Off the page. Say so in the spec, and name where it belongs |

Cut is about the decision, not the data quality. A metric with a perfectly good
comparison (support tickets, up 12 % vs last week) is still Cut if no reader
of *this* page acts on it; a metric with no comparison at all may still be
Detail if someone looks it up here. The spec names the home for every Cut
metric so the squad can contest it.

**Every headline metric carries a comparison.** A bare number is not a status.
The comparison is one of: target/goal, alert threshold, prior period, or a
normal range. Rules from Desbarats worth adopting verbatim:

- A **target** (where we want to be) is not an **alert threshold** (when a human must act). Show the right one for the type: strategic → target; operational → threshold.
- **Percent change vs last period, alone, is noise.** 1,710 → 1,842 is +7.7%, but is that normal week-to-week wobble or a real move? Prefer "vs goal pace" or "vs 12-week range" and reserve the delta as secondary context.
- Flag the metric, not the page: the reader should be able to find *which* tile needs attention without reading all of them.

Common NSLS pattern: a squad tracks weekly, MTD, and YTD for the same metric.
Pick the one that matches the cadence for the headline; the other two are
context inside the same card or go to Detail. Three tiles for one metric is a
top-row slot wasted twice.

## 3. Lay it out

Readers scan in an F/Z pattern: across the top, then down the left. Put the
answer where the eye lands first.

```
┌──────────────────────────────────────────────────────────┐
│ Title · one-line purpose · as of <date>        [filters] │
├─────────────┬─────────────┬─────────────┬────────────────┤
│ HEADLINE    │ HEADLINE    │ HEADLINE    │ HEADLINE       │  ≤ 6 metric cards
├─────────────┴──────┬──────┴─────────────┴────────────────┤
│ EXPLAIN (trend)    │ EXPLAIN (breakdown)                 │  2–4 charts
├────────────────────┴─────────────────────────────────────┤
│ DETAIL (table / list / experiments)      → tab or link   │
└──────────────────────────────────────────────────────────┘
```

- **Single screen for operational and strategic.** The headline and explain bands fit one viewport at 1280×800 with no scrolling. Detail may scroll or live behind a tab. Vertical budget at 1280×800: header ≤ 120 px (eyebrow, title, one subtitle line, as-of on the same row as the title), headline band ≤ 220 px, explain band ≤ 380 px, gaps 32 px. **Verify with a screenshot at 1280×800, not a computed estimate**; every computed budget so far has been wrong.
- **Cards in a band share one height.** Use grid `align-items: stretch`; put optional content (sparkline, context lines) in the same slot on every card, or leave the slot empty rather than letting cards ragged-bottom.
- **Progressive disclosure.** Overview first, details on demand. If a view is crowded, split by *audience or question* into tabs or pages, not by data source. Never make the reader compare numbers across tabs.
- **Grid, not freeform.** 12-column grid, one gutter size, one card radius, one card padding. Alignment does more for "clean" than any color choice.
- **Whitespace is a feature.** If the page feels cramped, remove a tile before shrinking the font.
- **Left-align labels and text; right-align numbers** in tables so magnitudes compare by eye.
- **Order by importance, then by logic** (funnel order, time order), never alphabetically or by which sheet the number came from.

Twelve named layout patterns (KPI row + grid, inverted pyramid, monitoring
wall, comparison columns, mobile card stack…) with when-to-use guidance are in
`references/layout-patterns.md`. Default for an NSLS squad or SLT page is
**KPI row + chart grid**.

## 4. Encode each tile

### Metric cards

One card, one metric, always in this order: **label → value → comparison →
time frame**. Optional sparkline. Full anatomy, number formatting, and status
rules in `references/metric-card-anatomy.md`. The three rules that matter most:

1. The **value is the largest text on the card**; the label is small and plain English, not a field name (`New enrollments this week`, not `enr_wk`).
2. **Round to what the decision needs.** `$3.9M` not `$3,912,440.17`; `3.8%` not `3.8147%`. Two significant figures is usually right for a headline.
3. **Status is never color alone.** Pair red/green with a symbol or word (`▲ +7.7%`, `Below pace`).

### Charts — pick by data shape

| You want to show | Use | Not |
|---|---|---|
| Change over time | Line (≤ 4 series); sparkline inside a card | Bar-per-week for > 12 points; area stacks |
| Compare categories | Horizontal bar, sorted | Pie; radar; 3D anything |
| Part of a whole | Stacked bar, or a pie **only** if ≤ 4 slices and proportion is the point | Donut ring with 8 slices |
| Progress to a target | Bullet bar, or value + target text | Gauge / speedometer |
| Distribution | Histogram, box plot | Pie |
| Relationship | Scatter; bubble only when a third variable matters | Dual-axis line |
| Exact values / lookup | Table with sorted rows and right-aligned numbers | A chart the reader squints at |

Why the table looks like this: readers judge **position and length** far more
accurately than **angle, area, or color intensity** (Cleveland & McGill). Bars
and lines sit at the top of that hierarchy; pies, gauges, and heatmap shading
sit at the bottom. Full chooser, the perception hierarchy, and the never-use
list are in `references/chart-selection.md`. Drawing mechanics: `dataviz`.

**Meaningless variety is a mistake.** Five different chart types on one page to
"keep it interesting" costs the reader a new decoding step per chart. Same
data shape → same chart type, everywhere.

**Title every chart with the finding or the question**, not the metric name:
`Weekly enrollments up 52% since June` beats `Enrollments (weekly)`. Label
series directly on the chart; a legend is a lookup table the reader should not
need.

### Color — four roles, nothing decorative

| Role | Rule |
|---|---|
| **Status** | One fixed triad for the whole product: good / watch / bad. Same hue means the same thing on every page. |
| **Emphasis** | One accent color for "look here". Everything else is grey. |
| **Series** | Categorical hues only when categories must be told apart; ≤ 5. |
| **Brand** | Header, title, links. Never used for status or series. |

- Grey is the default. Color is spent, not sprinkled. The unfilled part of a progress bar is grey, not red; red is reserved for a status that fails its threshold.
- Colorblind-safe: never red vs green as the only cue; test with a simulator.
- Contrast: text 4.5:1, UI borders and status marks 3:1 (WCAG 1.4.11). **Measure it; do not eyeball it** — a pale brand line that looks fine measures about 1.4:1 on white (1.3:1 on cream) on an NSLS surface.
- Palette source: confirm the brand first.
  - **Society** (most staff/admin dashboards): follow `references/society-visual-template.md` — cream ground, near-black ink, hairlines, Inter + monospace for data, terracotta/amber/green status. Start from `templates/society-dashboard.css`.
  - **NSLS** (institutional, chapter- or partner-facing): Academic Blue `#18315A`, one secondary accent per artwork. Tokens in `/ux-audit`'s `references/brand-nsls.md`.

### Fonts and weights (Society)

Inter carries the page in three weights: 700 for the title, the finding, and
the hero number; 600 for labels, nav, and pills; 400 for body. **Anything that
is data — emails, dates, durations, counts, axis ticks, legend values — is
set in monospace.** Tight tracking (−0.02 em) on anything ≥ 26 px; loose
tracking on ALL-CAPS eyebrows only. Full scale and component recipes in the
Society template.

### What goes on the page vs. in the spec

Design rationale lives in the spec, never in reader-facing copy. `Shown
uncolored because no 12-week range exists yet` is a spec note; the card just
shows `+0.2 pts vs last week` in grey. `Axis starts at zero` is a spec note;
the chart just starts at zero. A reader should never see the designer
thinking.

### Contextual help

Every derived or non-obvious metric gets an info affordance that answers, in
one sentence each: **what it counts, the formula, the source, when it
refreshes.** `Conversion = paid enrollments ÷ landing visitors, PostHog,
refreshed nightly.` Define once; reuse the definition text wherever the metric
appears. A glossary panel or tab is fine for pages with > 6 defined terms.

## 5. Show honest states

A dashboard that silently shows a stale or missing number as if it were live is
the most expensive bug this org keeps shipping. Every data-bearing tile has
four states, and the design specifies all four:

| State | Show |
|---|---|
| **Fresh** | Value + `as of <date/time>` on the page header (and per tile if sources differ) |
| **Stale** | Last confirmed value **plus a visible `stale since <date>` badge**. Never the value alone. |
| **Missing** | `No data` with the reason (`source unreachable`, `not yet reported`). Never `0`, never a dash that looks like a value. |
| **Loading** | Skeleton in the card's final size, so the layout does not jump |

Never fabricate, interpolate, or carry a number forward without labeling it.
Keep the last confirmed value and say it is last-confirmed.

## 6. Review before shipping

Run `references/review-checklist.md`. The two tests that catch the most:

**Five-second test.** Show the page to someone who did not build it for five
seconds, hide it, and ask the question the type owes an answer to. Strategic:
"Are we on track?" Operational: "What needs attention?" Analytical: "What
question does this page answer, and where would you start?" If they cannot
answer, the headline band (or, for analytical pages, the title and filter
row) is wrong. Do this with a real person once; do
it with a fresh subagent every iteration.

**Reflow and measure.** Test every page (not just the one that changed) at
320 / 375 / 768 / 1024 / 1280. Reveal elements with `visibility`, not
`display`, so hover states do not reflow the grid, and restore visibility on
`:focus-within` as well as `:hover` so keyboard users can reach the control.
Give each page its own `<title>`; execs print these.

## Hierarchy — where this sits

```
/dashboard-design   → decide what goes on the page and why (this skill)
  dataviz           → draw each chart correctly (marks, palette, axes)
  /squad-dashboard  → wire data sources, build, deploy a squad page
  /ux-audit         → SUS / Laws of UX / WCAG / brand review after it exists
  /product-design   → DESIGN.md intent for the product the dashboard lives in
  /posthog, /hubspot, /airtable, /data-intel → where the numbers come from
  /add-domain       → branded subdomain once it is live
```

Setup and data pulls live in those skills; do not duplicate them here. When
`/squad-dashboard` is about to pick sections, run steps 1–2 of this skill
first and feed the brief in.

## Output guidelines

- **SLT / board readers** want the headline band, one trend, and a sentence of narrative. Everything else is a tab.
- **Squad readers** want the explain band and the experiments list; they already know the headline.
- **Engineers and analysts** want the detail table, filters, and the definitions.
- The design spec itself: state the type, the decisions, the triage table with reasons for every Cut, and the four states. A spec that lists tiles without saying what was left off is incomplete.
- Small samples and low-confidence numbers carry their `n` (`4.1% vs 3.6%, n = 11,200 per arm`).

## Rationalization table

| Excuse | Reality |
|---|---|
| "They asked for everything on one page" | They asked to *see* everything. Headline band + tabs shows everything and still passes the five-second test. Put the cut list in the spec so they can push back. |
| "Weekly, MTD, and YTD are all important" | Same metric, three time frames = one card with the cadence-matched value as hero and the other two as context. |
| "Two time horizons are two different questions, so two cards" | Both questions are "are we on pace?" One card answers both: `48.9K YTD · 75% of goal at 68% of year` with `MTD 6,212 / 9,000` as the context line. Two cards spend a headline slot to repeat the label. |
| "I'll keep the rest in a small secondary strip so nothing is lost" | A strip of 8 small tiles is a second headline band in a smaller font. The reader still scans all of them. Detail goes to a table or tab; Cut goes in the spec. |
| "It went up, so the delta is green" | Up is only good against a target or a normal range. A +0.2 pt move inside normal wobble colored green teaches the reader that green means nothing. Grey until there is a reference. |
| "Readable in under a minute is good enough" | Five seconds is the test. Sixty seconds means the reader read every tile; the layout did no work. |
| "A pie is fine, it's only four slices" | Four slices and the point is proportion → fine. Four slices and the point is *which is biggest* → sorted bar. Name the question first. |
| "The gauge looks premium" | A gauge spends 40× the pixels of a bullet bar to encode one number by angle, the encoding readers judge worst. Bullet bar or value + target. |
| "I'll add color to make it less boring" | Decorative color destroys status color. If the page is boring, the metrics are undifferentiated, not undercolored. |
| "The data is only a few days old, no need for an as-of" | The reader cannot know that. `as of` costs one line and prevents a wrong decision. |
| "Show `0` when the source fails, it's just for now" | Zero is a value. A reader will act on it. Show `No data · source unreachable`. |
| "It looked fine on my screen" | Reflow-test every page at five widths and measure contrast. Two NSLS defects passed visual review and failed measurement. |
| "We'll simplify after launch" | Nobody looks at a dashboard twice after it confused them once. Simplify before the first share. |
| "Different charts keep it interesting" | Each new chart type is a new decoding task. Same shape, same chart. |

## Red flags — STOP and go back to step 1

- More than 6 tiles in the top band, or a second row of "small" tiles under it — unless the brief names an operational pattern that allows more (KPI grid 2×4 for 7–8 metrics; monitoring wall for status scanning) and every tile is a flagged status, not a number to read
- The same metric on more than one headline card (weekly / MTD / YTD)
- A headline number with no target, prior, or range next to it
- A green or red delta with no target or normal range behind it
- Brand (NSLS vs Society) not confirmed before a color was chosen
- A pie, donut, gauge, radar, or 3D chart anywhere
- Two chart types showing the same data shape
- Any hue whose meaning cannot be stated in three words
- No `as of` on the page
- A tile that can render `0` or `—` when its source fails
- The spec has no "Cut" list
- "Operational" and "strategic" both describe the page

## Common mistakes (Few's thirteen, applied)

Exceeding a single screen · inadequate context (no comparison) · excessive
precision · a deficient measure (the number is not the thing that matters) ·
wrong chart for the data · meaningless variety · poorly designed media (dual
axes, truncated bars, unsorted categories) · inaccurate encoding · poor
arrangement (importance ignored) · weak highlighting (nothing stands out, or
everything does) · decoration and clutter · color misuse · an unattractive
display that nobody wants to return to. The checklist reference scores each.

## Sources

Frameworks and citations this skill draws on: `references/sources.md`.
