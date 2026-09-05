# Chart selection

Choose the chart from the **data shape and the question**, never from what
looks interesting. Drawing mechanics (palette, marks, axes, tooltips) are in
the `dataviz` skill; this reference decides *which* chart.

## Step 1 — name the question

| Question word | Data shape | Chart family |
|---|---|---|
| "How has X changed?" | one or few series over time | line, sparkline |
| "Which is biggest / how do these compare?" | categories with one value each | sorted horizontal bar |
| "What share is each?" | parts summing to a whole | stacked bar (100%), or pie if ≤ 4 slices |
| "How far to the goal?" | one value + target | bullet bar, or value + target text |
| "How is X distributed?" | many observations of one variable | histogram, box plot, strip |
| "Is X related to Y?" | pairs of values | scatter; bubble only when a third variable matters |
| "Where exactly?" | precise values, lookup | table |
| "Which of many things need attention?" | many items, each with a status | status grid / table with flags, not a chart |

## Step 2 — check the perception hierarchy

Readers decode some encodings far more accurately than others (Cleveland &
McGill, 1984; replicated by Heer & Bostock, 2010). From most to least accurate:

1. Position on a common scale — dot plot, scatter, line
2. Position on non-aligned scales — small multiples
3. Length — bar
4. Angle / slope — pie, line slope
5. Area — bubble, treemap
6. Volume, density, color saturation — heatmap shading, 3D
7. Color hue — categorical fill

Anything a decision depends on should be encoded at level 1–3. Levels 4–7 are
for redundancy or for "roughly how much", never for the number the reader acts
on.

## Step 3 — apply the specific rules

### Line
- ≤ 4 series. Five or more → small multiples (one mini line chart per series, same scale).
- Label series at the line's end; no legend.
- Y axis starts at zero for counts and money unless the chart is explicitly about small variation, and then say so in the title.
- ≥ 8 points; under that, use a bar or a table.

### Sparkline
- Inside a metric card only. 8–13 points. No axes, no gridlines, no labels except optionally the last value.
- One color. Never compare two sparklines' magnitudes; they have independent scales.

### Bar
- **Horizontal** when category labels are words (chapter names, channels); vertical when categories are time buckets (≤ 12).
- **Sort** by value unless the categories have a natural order (funnel stages, months).
- Bars start at zero, always. A truncated axis on a bar chart is a lie about ratio.
- One color, with the accent on the one bar the title is about.

### Stacked bar / 100% stacked
- Part-to-whole across ≤ 6 categories. Put the most important segment at the baseline so it is readable by length.
- More than 6 segments → group the tail into "Other" or use a table.

### Pie / donut
- Allowed only when: the point is *proportion of a whole*, ≤ 4 slices, one slice is clearly dominant, and no precise comparison is needed.
- Sort slices largest-first from 12 o'clock. Label directly with percentages.
- If the question is "which is biggest?", a sorted bar answers it faster. Default to the bar.

### Bullet bar (Few) — the gauge replacement
```
Revenue YTD   ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░│  $3.9M of $5.2M   (goal marker at 100%, pace marker at 67%)
```
Encodes value, target, and optionally pace/qualitative bands by *length* in a
fraction of a gauge's pixels. Use for any "progress to target" tile.

### Table
- Right-align numbers, left-align text, one decimal policy per column.
- Sort by the column the reader cares about; show the sort.
- ≤ 10 rows visible; more goes behind "show all" or a filter.
- Zebra striping or 1 px row rules, not both. Headers stay visible on scroll.

### Scatter / bubble
- Bubble size only for a third variable that matters; area is level 5 on the hierarchy, so state the sizes in the tooltip.
- Label outliers directly.

## Never on an NSLS dashboard

| Chart | Why | Use instead |
|---|---|---|
| Gauge / speedometer | Angle encoding, huge pixel cost, one number | Bullet bar; value + target |
| 3D anything | Perspective distorts every comparison | Flat version |
| Dual-axis line | Readers cannot tell which axis a line belongs to; scale choice manufactures correlation | Two stacked charts, shared x-axis |
| Radar / spider | Area is meaningless, axis order arbitrary | Sorted bar or table |
| Donut with > 4 slices | Angle + small arcs; unreadable | Sorted bar |
| Stacked area with > 3 series | Middle series are unreadable by position | Small multiples |
| Word cloud | Size ≈ frequency is level 5, layout is random | Sorted bar of top terms |
| Bar chart with truncated y axis | Lies about ratios | Start at zero, or use a dot plot |
| Chart with a legend of > 5 items | Lookup task instead of reading | Direct labels; fewer series |

## Meaningless variety

Five chart types on one page is not richness; it is five decoding tasks.
Rule: **same data shape → same chart type**, everywhere on the page and across
the product's pages. A page with one line chart, one sorted bar, and one table
almost always beats a page with a line, a pie, a gauge, a radar, and a treemap.

## Titles and labels

- Title states the **finding or the question**: `Email drives 44% of enrollments` or `Where do enrollments come from?` — not `Enrollments by channel`.
- Subtitle carries the time frame and unit: `Last 12 weeks · count of paid enrollments`.
- Axis labels in plain English with units; no field names.
- Direct labeling beats legends. Legends beat nothing.
- Tooltips carry the exact value, the date, and the definition. They are not where the primary information lives.
