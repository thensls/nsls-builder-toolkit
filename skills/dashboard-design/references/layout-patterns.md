# Layout patterns

Pick one pattern per page. The pattern follows the brief (type, audience,
decisions), never the other way round. Default for an NSLS squad or SLT page:
**KPI row + chart grid**.

## The grid

- 12 columns, one gutter (24 px desktop, 16 px mobile), one outer margin.
- One card radius, one card padding, one shadow or one 1 px border — not both.
- Max content width 1280–1440 px; center it. Dashboards wider than that force the eye to travel further than a Z-scan can cover.
- Vertical rhythm: bands separated by 2× the gutter; tiles inside a band by 1×.
- Header: title, one-line purpose, `as of`, filters. Never taller than 72 px.

## Patterns

| # | Pattern | Structure | Use for | Avoid when |
|---|---|---|---|---|
| 1 | **KPI row + chart grid** | 4 cards across → 2 charts side by side → full-width table | Strategic weekly/monthly pages, SLT views, squad outcome pages | > 6 headline metrics |
| 2 | **KPI grid 2×4** | Two rows of four cards → charts below | Operational monitoring with 7–8 metrics | Reader must rank the metrics; two rows flatten priority |
| 3 | **Sidebar + canvas** | 15–20% left sidebar for filters/nav → canvas with pattern 1 | Analytical pages with ≥ 3 filters or multi-page reports | One page with 1–2 filters (use a top filter bar) |
| 4 | **Top filter bar** | Title → filter row → pattern 1 | Self-serve pages where filters change often | Filters exceed one row (8+) |
| 5 | **Inverted pyramid** | One hero KPI centered and large → one trend → one breakdown → detail | Board slides, quarterly reviews, single-goal pages | Operational pages needing many metrics at once |
| 6 | **Quadrant** | Four equal panels | Balanced scorecards, four-part frameworks (e.g., a 2×2) | One dimension matters more than the others |
| 7 | **Tabbed** | Tabs per audience or question, each holding pattern 1 | Serving SLT + squad + finance from one URL | Readers must compare numbers across tabs |
| 8 | **Monitoring wall** | Dense 3×4 or 4×5 grid of small status cards | Real-time ops, pipeline health, "what is red right now" | Anything the reader must read closely |
| 9 | **Headline + detail split** | Left half: hero KPI + trend; right half: breakdown by one dimension | Daily standups, one-metric deep dives | More than one primary question |
| 10 | **Comparison columns** | 2–3 parallel columns, same metrics per segment | A/B tests, region or cohort comparison, this-year vs last | Segments are not directly comparable |
| 11 | **Scrolling report** | Single tall column of stacked sections | Monthly narrative reports, investor-style updates | Interactive pages; scrolling fights filtering |
| 12 | **Mobile card stack** | One column: primary KPI → 3 secondary → one chart → top-5 table | Phone-first readers (chapter advisors, field staff) | Desktop-primary pages |

## Choosing

```
Type = analytical, ≥ 3 filters ............ 3 (sidebar) or 4 (top bar)
Type = operational, "what is red" ......... 8 (wall)
Type = strategic, 1 goal .................. 5 (inverted pyramid)
Type = strategic, 3–6 metrics ............. 1 (KPI row + grid)
Multiple audiences, no cross-compare ...... 7 (tabs), each tab = 1
Head-to-head segments ..................... 10 (comparison columns)
Phone-first ............................... 12
```

## Responsive rules

| Width | Cards per row | Charts per row | Notes |
|---|---|---|---|
| ≥ 1280 | 4 (max 6) | 2 | Full pattern |
| 1024 | 4 | 2 | Narrow gutters to 20 px |
| 768 | 2 | 1 | Sidebar collapses to top bar or drawer |
| 375 | 1 | 1 | Value still the largest element; tables show top 5 with "show all" |
| 320 | 1 | 1 | No horizontal scroll anywhere except inside a table's own container |

- Test **every** page at all five widths, not just the one you touched. A shared stylesheet change reflows pages you did not open.
- Reveal-on-hover elements use `visibility`, never `display`; a pencil icon appearing mid-sentence reflows the whole grid. Restore visibility on `:focus-within` as well as `:hover`, or keyboard users cannot reach the control.
- Flex children that hold long text need `min-width: 0` and `white-space: normal`; a global `nowrap` will push the page wider at every breakpoint.
- Wide tables scroll inside their own `overflow-x: auto` container; the page body never scrolls horizontally.
- Each page gets its own `<title>`; readers print dashboards and the title becomes the printout header.

## Progressive disclosure mechanics

- **Default view is the calm view.** Nothing collapsed is required to answer the headline question.
- Split by **audience or question**, not by data source. "Enrollment" and "Revenue" tabs are wrong if the SLT decision needs both; "SLT view" and "Squad view" tabs are right.
- Drill-down goes **one level**: card → its explain chart → its detail table. Deeper than that is an analytical tool, not a dashboard.
- Filters that change the whole page live at the top; filters that change one chart live on that chart.
- Remember the reader's last tab and filter (local storage) so returning costs nothing.
