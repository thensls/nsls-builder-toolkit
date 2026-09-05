# Sources and frameworks

What this skill draws on, so a builder can go deeper or challenge a rule.

## Books and papers

| Source | What we took from it |
|---|---|
| **Stephen Few**, *Information Dashboard Design* (O'Reilly, 2006; 2nd ed. Analytics Press, 2013) and the Perceptual Edge whitepaper *Common Pitfalls in Dashboard Design* | The single-screen rule; the thirteen common mistakes (section J of the review checklist); bullet graphs as the gauge replacement; sparklines as in-card trend; "meaningless variety" as a named defect |
| **Nick Desbarats**, *Practical Dashboards* (Practical Reporting, 2020) | "Dashboard" hides about a dozen distinct display types; problem-scanning vs performance-monitoring must not share a page; targets ≠ alert thresholds; percent-change-from-prior-period alone is misleading; flag metrics against a normal range |
| **William Cleveland & Robert McGill**, "Graphical Perception" (*JASA*, 1984); replicated by **Heer & Bostock**, "Crowdsourcing Graphical Perception" (CHI 2010) | The perception hierarchy: position > length > angle/slope > area > volume/saturation > hue. Why bars and lines beat pies, gauges, and heatmaps for numbers people act on |
| **Edward Tufte**, *The Visual Display of Quantitative Information* (1983) | Data-ink ratio, chartjunk, small multiples, graphical integrity (bars start at zero; no lie factor) |
| **Cole Nussbaumer Knaflic**, *Storytelling with Data* (Wiley, 2015) | Declutter first; preattentive attributes (size, color, position) used sparingly and consistently; titles that state the takeaway |
| **Ben Shneiderman**, "The Eyes Have It" (1996) | Visual information-seeking mantra: overview first, zoom and filter, details on demand → progressive disclosure |
| **Jakob Nielsen / NN/g**, F-pattern and Z-pattern reading research; *Clutter-Free: One of the 3 Cs for Better Charts* | Where the eye lands first; top-left is prime; > 7 competing elements above the fold drives abandonment; declutter charts |
| **Gestalt principles** (proximity, similarity, enclosure, alignment) | Grid and grouping rules; why alignment reads as "clean" |
| **WCAG 2.1** 1.4.3 (text contrast 4.5:1), 1.4.11 (non-text contrast 3:1), 1.4.1 (use of color), 2.4.2 (page titled) | Measured contrast; status never by color alone; per-page titles |

## Practitioner references consulted (2026)

- datawirefra.me, *12 Dashboard Layout Patterns That Actually Work* — the pattern table in `layout-patterns.md`, including the 4–6 KPI limit at 1280 px and the 2×4 grid for 7–8 metrics
- Anastasiya Kuznetsova, *Anatomy of the KPI Card* — label → value → delta → time frame order
- ClearPoint Strategy, *KPI Dashboard Best Practices*; Aufait UX, *Dashboard Design Principles*; 5of10, *Dashboard Design Best Practices* — convergent guidance on 4–6 headline metrics, Z-pattern layout, consistent status colors, progressive disclosure

## Society visual template

`society-visual-template.md` and `templates/society-dashboard.css` are derived
from two Society Admin pilot screens (Group Health · Members, and Cohort
comparison, 2026): Inter in three weights, monospace for data, cream ground
with `--line #DED8CC` hairlines and `--grey #6B6460` secondary text,
terracotta / amber / leaf-green status, black as the CTA color. Hex values
marked ≈ were sampled from the screenshots; confirmed tokens come from the
shared Society design language used on gary.nsls.org and ignite-next.

## NSLS-specific lessons folded in

- Reveal with `visibility`, not `display`; global `nowrap` in flex children; pale brand line fails 1.4.11 at 1.33:1; per-page `<title>` because execs print — from the gary.nsls.org build (Aug 2026)
- "Silent failure is the recurring bug": a missing value rendered as `0` or a blank, a stale number shown as live, a carry-forward with no label — every one has produced a wrong decision somewhere in the org. Hence the four required states and the no-fabrication rule
- `/squad-dashboard`'s pull-and-confirm gate: fail loud and keep the last confirmed value; never interpolate
- Brand palettes and type: `/ux-audit` `references/brand-nsls.md`, `references/brand-society.md`

## Original seed

The skill began from a seven-principle summary of a SaaS dashboard design
talk: define the purpose (operational / strategic / analytical, never mixed);
the five-second rule with top / middle / bottom hierarchy; progressive
disclosure; intentional visualization (bar = comparison, line = trend,
pie = proportion only, bubble = multivariate, sparkline = lightweight trend);
systematic color; contextual help; and the three opening questions — what
decisions, what first, what can be hidden.
