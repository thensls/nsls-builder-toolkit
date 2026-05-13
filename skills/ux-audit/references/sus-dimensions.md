# SUS Dimensions Reference

The System Usability Scale (Brooke, 1986) — 10 items, 5-point Likert, scored 0–100. Items 1, 3, 5, 7, 9 are positive; 2, 4, 6, 8, 10 are negative.

**Important: this skill produces a Predicted SUS, not a real SUS.** Real SUS requires users completing a task and answering the items themselves. The heuristic estimate predicts how users would likely respond given the design they're shown.

## The 10 items (verbatim, © Digital Equipment Corporation 1986)

1. I think that I would like to use this system frequently. *(positive)*
2. I found the system unnecessarily complex. *(negative)*
3. I thought the system was easy to use. *(positive)*
4. I think that I would need the support of a technical person to be able to use this system. *(negative)*
5. I found the various functions in this system were well integrated. *(positive)*
6. I thought there was too much inconsistency in this system. *(negative)*
7. I would imagine that most people would learn to use this system very quickly. *(positive)*
8. I found the system very cumbersome to use. *(negative)*
9. I felt very confident using the system. *(positive)*
10. I needed to learn a lot of things before I could get going with this system. *(negative)*

## Scoring formula

For each item, score the response 1–5. Then:
- Positive items (1, 3, 5, 7, 9): contribution = score − 1
- Negative items (2, 4, 6, 8, 10): contribution = 5 − score
- Sum all 10 contributions (range: 0–40)
- Multiply by 2.5 → Predicted SUS (range: 0–100)

## Calibration table (Sauro & Lewis, normative data)

| Predicted SUS | Grade | Interpretation |
|---|---|---|
| 84.1+ | A+ | Excellent — top 10% |
| 80.8–84.0 | A | Excellent |
| 78.9–80.7 | A− | Good |
| 77.2–78.8 | B+ | Good |
| 74.1–77.1 | B | Above average |
| 72.6–74.0 | B− | Above average |
| 71.1–72.5 | C+ | Average |
| 65.0–71.0 | C | Average (industry mean ~68) |
| 62.7–64.9 | C− | Below average |
| 51.7–62.6 | D | Poor |
| <51.7 | F | Awful — bottom 15% |

## How to assess each item heuristically

Mark each item with a predicted score (1–5) and reasoning. Be explicit when you can't tell.

| # | What to look for in the artifact | Confidence from static review |
|---|---|---|
| 1. Want to use frequently | Value clarity, friction level, perceived utility for return tasks | **Low** — really requires behavioral data; lean on perceived value |
| 2. Unnecessarily complex | Cognitive load, density, hidden complexity, jargon | High |
| 3. Easy to use | Pattern familiarity (Jakob), affordance clarity, label specificity | High |
| 4. Need technical support | Help availability, error recovery, glossary/tooltips, jargon density | Medium |
| 5. Functions well integrated | Consistency across components, logical grouping, single visual language | High |
| 6. Too much inconsistency | Mixed patterns, varied button styles, terminology drift, layout shifts | High |
| 7. Most people learn quickly | Discoverability, primary path obviousness, signposting | Medium |
| 8. Cumbersome to use | Step count, redundant inputs, friction points, dead ends | High |
| 9. Confidence using | Feedback quality, error states, action reversibility, undo/back paths | **Low** — confidence is post-task; infer from clarity of feedback shown |
| 10. Need to learn a lot first | Onboarding requirement, prerequisite knowledge, terminology load | Medium |

## Output format for the report

```
### Predicted SUS

**Predicted SUS: 64 (D — Below average)**
*Heuristic estimate, not user-validated. Run the actual instrument before any ship decision.*

| # | Item | Predicted (1–5) | Contribution (0–4) | Reasoning |
|---|------|-----------------|---------------------|-----------|
| 1 | Frequent use | 3 | 2 | Value clear but friction in setup may suppress return |
| ... | | | | |

**Total: 26/40 → 26 × 2.5 = 65**

**Confidence:** Medium. Items 1 and 9 are low-confidence from static review.
```
