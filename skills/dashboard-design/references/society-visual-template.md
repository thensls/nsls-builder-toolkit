# Society dashboard visual template

The house style for any Society-branded dashboard or admin surface. Derived
from the Society Admin pilot screens (Group Health · Members table, and
Cohort comparison, 2026). Match these fonts, colors, and weights before
inventing anything. Starter CSS with every token below:
`templates/society-dashboard.css`.

Hex values marked **≈** were sampled from screenshots and should be replaced
with the exact tokens from the Society UI repo when you have it. Values
without the mark are confirmed tokens from the shared Society design language
(gary-portal / ignite-next lineage).

## Feel in one line

Warm cream ground, near-black ink, one hairline everywhere, big confident
numbers, monospace for anything that is data, color only where it means
something.

## Type

| Role | Font | Size | Weight | Tracking / case |
|---|---|---|---|---|
| Page title (H1) | Inter | 40–44 px | 700 | −0.02 em, sentence case (`Group Health`, `Cohort comparison`) |
| Eyebrow above title | Inter | 12–13 px | 600 | +0.12 em, ALL CAPS, muted (`ADMIN · PILOT`) |
| Page subtitle | Inter | 17 px | 400 | muted (`112 members across 14 cohorts`) |
| Chart / card title (the finding) | Inter | 26–28 px | 700 | −0.01 em (`Cohort A is pulling ahead. Cohort C is eroding.`) |
| Card eyebrow | Inter | 12 px | 600 | +0.12 em, ALL CAPS, muted (`ATTENDANCE RATE · WEEKLY`) |
| Hero value on a metric card | Inter | 36–40 px | 700 | −0.02 em; delta rides inline at same size (`86%↑ 9pt`) |
| Card label / entity name | Inter | 17–18 px | 600 | (`Cohort A`, `Devon Carr`) |
| Nav item | Inter | 17 px | 600 | sentence case |
| Body / table cell text | Inter | 15–16 px | 400 | |
| Table header | Inter | 12–13 px | 600 | +0.10 em, ALL CAPS, muted; sorted column in ink with arrow |
| Section label in nav | Inter | 11–12 px | 600 | +0.14 em, ALL CAPS, muted, with hairline rule |
| **Data / meta** — emails, dates, durations, counts, axis ticks, legend values, "3 groups", "as of" | **Monospace** (JetBrains Mono / IBM Plex Mono class) | 13–15 px | 400 | muted for meta, ink for values |
| Badge / pill text | Inter | 11–12 px | 600–700 | +0.02 em; ALL CAPS for state pills (`NEEDS HELP`, `ADMIN`) |

Rules that make it read as Society:
- **Numbers that are data go monospace.** Tenure, last-seen, axis labels, legend percentages, member counts. Prose stays in Inter. This one move does most of the "dashboard, not brochure" work.
- **Titles state the finding**, not the metric name. Weight 700, ink color, no color in the title itself.
- Two weights carry the page: 700 for titles and hero numbers, 600 for labels and nav, 400 for everything else. No 500, no 800.
- Tight tracking on anything ≥ 26 px; loose tracking only on ALL-CAPS eyebrows.
- The `Society` wordmark uses the brand logotype (HW Cigars, title case) — the only place a non-Inter face appears.

## Color

### Ground and ink

| Token | Value | Use |
|---|---|---|
| `--bg` | ≈ `#F7F5F0` | Page and sidebar ground (warm cream, never pure white) |
| `--surface` | ≈ `#FDFCFA` | Card fill on the cream ground |
| `--surface-2` | ≈ `#EFEBE3` | Filled panels (chart card), table header row, filter chips, active nav, date picker |
| `--line` | `#DED8CC` | Hairlines: card edges, table row rules, nav section rules. **Not** for control borders (fails 3:1) |
| `--ink` | ≈ `#1A1714` | Titles, hero values, primary text, black buttons and bars |
| `--grey` | `#6B6460` | Secondary text, eyebrows, meta, table headers, icon strokes; passes 5.4:1 on white |
| `--grey-3` | ≈ `#A9A29A` | Disabled nav, "coming soon", inactive rows |

### Status (the only place red/amber/green appear)

| Token | Value | Meaning | Where seen |
|---|---|---|---|
| `--bad` | ≈ `#C8553D` (terracotta) | Failing threshold, needs help | `4 no-shows` pill, `NEEDS HELP`, attendance < 40 % bar, Cohort C line, red `4` count, `Today` badge |
| `--bad-bg` | ≈ `#F6E4DF` | Tint for a flagged card or chip | Cohort C card, `Attendance · < 50%` chip |
| `--watch` | ≈ `#D98E3A` (amber) | Approaching threshold | `3 no-shows` pill, 40–50 % bars, `No-shows · 3+` chip |
| `--watch-bg` | ≈ `#F8ECDD` | Tint for a watch chip | |
| `--good` | ≈ `#8BC65A` (leaf green) | On track / improving | Cohort A line and sparkline only — never on a neutral element |
| `--neutral-track` | ≈ `#E6E1D8` | Unfilled part of any progress bar | Grey, never red |

Status rules, as seen on the reference screens:
- A **flagged row or card gets three cues at once**: the pill (`NEEDS HELP`), the tinted background, and the colored number. Never color alone.
- The **unfilled track is grey**. Red belongs only to the filled portion when the value is below threshold.
- One flagged card per band is a signal; if most cards are tinted, the thresholds are wrong.
- Counts inherit the status color of their row (`4` in terracotta, `2` in grey).

### Series (categorical, ≤ 4)

| Token | Value | Note |
|---|---|---|
| `--s1` | ≈ `#8BC65A` green | Doubles as `--good` when the series is the one doing well |
| `--s2` | ≈ `#7B84E8` periwinkle | |
| `--s3` | ≈ `#C8553D` terracotta | Doubles as `--bad` when that series is the problem |
| `--s4` | ≈ `#D98E3A` amber | |

Series color appears in exactly four places for one entity: the legend dot,
the line, the card's leading dot, and the card's sparkline. Nothing else on
the page borrows it.

### Accents

| Token | Value | Use |
|---|---|---|
| `--accent-soft` | ≈ `#E9C7EC` lilac | Notification count badges on nav (`2`, `3`) — informational, not status |
| `--ink` on white | | Primary button (`Export CSV`), bulk-action bar, insight bar, active filter chip. Black is the CTA color; there is no blue button |

## Components (recipes)

**Metric card** — `--surface`, 1 px `--line`, radius 16 px, padding 24 px.
Row 1: colored dot + entity name (600, 17 px) left, meta in mono muted right
(`3 groups`). Row 2: hero value 700 / 36–40 px with inline arrow + delta
(`41%↓ 24pt`). Row 3: sparkline, 8–12 points, series color, 2 px stroke, no
axes, ~60 px tall. Row 4 (hairline above): two mono meta pairs
(`Members 24 · No-shows 8`). Row 5 (hairline above): `Advisor · Red R.` in
grey. Flagged variant: `--bad-bg` fill, `--bad` 1 px border, `NEEDS HELP`
pill after the name.

**Chart panel** — `--surface-2` fill (no border), radius 20 px, padding
32 px. Eyebrow in caps → finding as title (700, 28 px) → legend top-right
with dots and mono values → chart. Gridlines dotted `--line`; ticks mono
`--grey`; y axis 0–100 % for rates; lines 2 px; end-dot on the last point.

**Data table** — card with 1 px `--line`, radius 16 px. Header row
`--surface-2`, caps 600 12 px `--grey`; sorted column in `--ink` with `↓`.
Rows 80 px tall with avatar 44 px; name 600 + email mono `--grey` beneath;
inline mini-bar 120 × 4 px (`--neutral-track` + status fill) followed by
mono value; status pill after the name; inactive rows at 55 % opacity.

**Filter chips** — pill, `--surface-2`, 600 label `·` 400 value `⌄`. Active
chip inverts to `--ink` with white text and `×`. Status chips tint
(`--bad-bg` + `--bad` dot + `--bad` text). "Add filter" is a dashed `--line`
pill. Chips sit on one row; more than fits → sidebar filters.

**Bulk-action bar** — full-width `--ink` bar, radius 12 px, white 600 text,
white icons, selection count left, actions center, `Clear selection` right in
`--grey-3`.

**Insight bar** ("Pattern detected") — `--ink`, radius 16 px, icon in a
darker square, caps eyebrow `--grey-3`, title white 600 18 px, body
`--grey-3` 15 px, white pill button `Open report ›`.

**Tabs** — text 600 17 px, counts in mono `--grey` 13 px after the label,
active tab `--ink` with 2 px underline; a red count badge only when the tab
holds items needing action (`Today 4`).

**Sidebar** — 300 px, same cream, 1 px `--line` divider; logo mark black
rounded square with white `S`; nav items 600 17 px with 20 px icons; active
item `--surface-2` rounded 12 px; count badges lilac; sections labeled in
caps with hairline rules; `Settings` and `Sign Out` pinned bottom.

## Spacing and shape

- Grid gutter 24 px; card radius 16 px; panel radius 20 px; pill radius full; button radius 12 px.
- One shadow policy: none. Depth comes from `--surface` on `--bg` and the hairline.
- Content max-width ~1560 px inside the canvas; header block 120 px (eyebrow + H1 + subtitle) with the primary action right-aligned at the H1's vertical center.
- Empty ground between bands: 32 px. Between cards: 24 px.

## Do not

- Pure white page background; drop shadows; gradients; colored card titles; blue links or buttons; red on an unfilled track; series color on any non-series element; more than four series; Inter for axis ticks or emails; a status color with no pill or word beside it.
