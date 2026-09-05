# Dashboard brief + metric triage template

Fill this in before any layout or code. Copy it into the repo as `DASHBOARD.md`
(or the top of the design spec) so the next builder knows why the page looks
the way it does.

```markdown
# <Dashboard name>

## Type
Operational | Strategic | Analytical   (pick ONE)
If operational: problem-scanning | performance-monitoring   (pick ONE)

## Primary reader
<one role: "SLT on Monday", "Enrollment squad daily", "Gary weekly">
Secondary readers (get a tab, not a row): <...>

## Decisions this page serves
1. <decision>  — needs: <metric(s)>
2. <decision>  — needs: <metric(s)>
3. <decision>  — needs: <metric(s)>

## Cadence and freshness
Reader looks: <daily / weekly / monthly>
Data must be no older than: <hours / days>
Sources refresh: <per source>

## Brand
NSLS | Society   (palette + type come from that brand's reference)

## Metric triage
| Metric | Bucket (Headline / Explain / Detail / Cut) | Comparison shown | Why this bucket |
|---|---|---|---|
| | | | |

Headline count: <n>  (must be ≤ 6)
Cut list and reason: <...>

## States
Fresh: as-of shown at <page header / per tile>
Stale: last confirmed value + "stale since" badge
Missing: "No data · <reason>"
Loading: skeleton at final size
```

## How to fill the triage table

**Comparison shown** must be one of: `vs target`, `vs prior <period>`, `vs
normal range`, or `n/a (detail only)`. A headline row cannot be `n/a`.

**Why this bucket** must name the decision from the list above, or say `no
decision → Cut`. Writing this sentence is what stops every metric from
becoming a headline.

### Worked example (Society Group Health, admin weekly view)

Type: operational · problem-scanning. Reader: the pilot admin on Monday.
Decisions: (1) which members need a nudge this week, (2) which cohort needs
an advisor intervention, (3) whether the pilot as a whole is healthy enough to
report up.

| Metric | Bucket | Comparison | Why |
|---|---|---|---|
| Attendance rate, weekly, per cohort | Headline (one card per cohort, 4) | vs prior week (pt change) + 8-week sparkline; flag if < 50 % | Decision 2: which cohort needs help |
| Members needing attention (attendance < 50 % or 3+ no-shows) | Headline → the `Today` tab count | threshold | Decision 1: who to nudge |
| Attendance trend, 8 weeks, all cohorts | Explain | 4-series line, finding as title | Explains the cohort cards |
| Pattern detected (schedule shift ↔ drop) | Explain | narrative bar | Decision 2, the "why" |
| Member table (attendance bar, no-shows, last seen) | Detail | sorted by attendance, filterable | Decision 1, the working list |
| Members per cohort, no-shows per cohort | Detail (card footer) | count | Context for the card |
| Advisor per cohort | Detail (card footer) | — | Who to call |
| Total members / cohorts | Header subtitle | — | Orientation, not a decision |
| Message volume, coach sessions | Cut | — | Engagement metrics belong on the Coach page, not health scanning |
| Event RSVPs | Cut | — | Events not live in the pilot ("coming soon") |
| Achievement completions | Cut | — | Same |

Headline count: 4 cohort cards + one action count. Cut: 3, each with a home
named so the squad can contest it. Thresholds (50 % attendance, 3 no-shows)
are alert thresholds, not targets — the spec says so.

### Worked example (strategic, goal-pace cards)

Type: strategic. Reader: SLT, weekly. Decisions: (1) are we on plan for the
year, (2) does the squad need to shift spend between channels.

| Metric | Bucket | Comparison | Why |
|---|---|---|---|
| Enrollments YTD | Headline | **pace** vs annual goal: `(value ÷ goal) ÷ (days elapsed ÷ 365)` → verdict word | Decision 1 |
| Revenue YTD | Headline | pace vs annual goal, same formula | Decision 1 |
| Conversion rate, this week | Headline | grey delta vs last week until 8 weeks of history exist, then vs range | Decision 2, funnel health |
| Enrollments MTD / this week | Explain (context line inside the YTD card, mono) | vs monthly goal | Same metric, shorter frames |
| Weekly enrollments, 12 wks | Explain | line, finding as title | Explains headline 1 |
| Enrollments by channel | Explain | sorted bar, accent on the leader | Decision 2 |
| Everything else the squad tracks | Detail or Cut | — | Named home for each Cut |

Headline card shape for a pace metric (all one card):

```
New enrollments · YTD                      ⓘ
48.9K
▲ 75% of 65K goal · Ahead of pace          (68% of year elapsed)
MTD 6,212 of 9,000 · this wk 1,842
```
