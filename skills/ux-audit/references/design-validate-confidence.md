# Design Validation — Three-View Confidence Prediction

Every Design Validation report concludes with three views of confidence. They are **not** redundant — each answers a different question and each is rendered honestly with stated limits.

| View | Question it answers | Output form |
|---|---|---|
| A. Directional verdict | "Should we test this?" | One of six labels |
| B. Multi-factor score | "How well does it satisfy our rubric?" | 0–100, with factor breakdown |
| C. Range estimate | "What's the plausible lift range, given priors?" | Range based on ≥3 comparable past tests, or "No prior; net-new bet" |

Never collapse the three into a single number. The point of three views is to surface where they disagree.

---

## A. Directional verdict

Six values. Pick the one that best summarizes the predicted reaction, NOT the score in (B).

| Verdict | Meaning |
|---|---|
| **STRONG POSITIVE** | Aligns with multiple validated principles, no rejected patterns, member-fit panel is overwhelmingly positive, no brand/a11y violations. Worth shipping to test with high prior. |
| **POSITIVE** | Aligns with at least one validated principle, no rejected patterns, member-fit panel is mostly positive. Worth testing. |
| **NEUTRAL** | No clear alignment or rejection. Net-new bet — limited basis to predict. Ship to learn, not to win. |
| **MIXED** | Some panels react positively, some negatively. Or aligns with one principle but partially repeats another rejected one. Worth testing but expect uneven results across segments. |
| **NEGATIVE** | Partially repeats a rejected pattern, OR member-fit panel is mostly negative, OR has a P1 brand/a11y violation. Recommend reframing before testing. |
| **STRONG NEGATIVE** | Directly repeats a rejected pattern from prior tests, OR has a P0 brand/a11y violation, OR a single persona predicts a P0-severity break (e.g., kills the refund path). Don't test as-is. |

### How verdict relates to score

Verdict should generally track the score, but the score is a rubric and the verdict is a judgment call. They can diverge when:

- A single high-severity item (e.g., P0 a11y violation) drops the verdict to STRONG NEGATIVE even though the score is still 70+.
- A net-new bet on a no-canonical surface scores 50 (mostly neutrals) but the verdict is NEUTRAL, not MIXED — the absence of evidence is honest, not negative.

Always state the divergence: "Verdict NEGATIVE despite score 68/100 — the C-view flagged a P0 a11y break that overrides rubric weighting."

---

## B. Multi-factor score (0–100)

A reproducible rubric. Same input → same score. **It is not a statistical prediction.** It is an alignment audit expressed as a number.

### Rubric

| Factor | Weight | Full score when… | Half when… | Zero when… |
|---|---|---|---|---|
| **Past-test alignment** | 35 | Aligns with at least one validated principle on this surface, repeats no rejected pattern | Aligns with one validated AND partially repeats one rejected, OR aligns weakly | Repeats a rejected pattern with no offsetting alignment |
| **Member-fit signal** | 25 | Convened persona panel is mostly positive | Mixed across personas | Mostly negative |
| **Brand alignment** | 10 | No brand violations | One P1 violation | One P0 violation |
| **A11y (WCAG 2.1 AA on auditable items)** | 10 | Conformant on every checkable item | One P1 violation | One P0 violation OR multiple P1s |
| **DESIGN.md alignment** | 10 | Aligns with all stated principles | Conflicts with one principle | Conflicts with two or more principles |
| **In-flight collision** | 10 | No collision with another live or scoped test on this surface | Partial overlap (different metric, same surface) | Direct collision (same surface, same metric, same window) |

### Neutral fallbacks (when evidence doesn't exist)

| Factor | If no canonical past-test doc for the surface | If no DESIGN.md exists |
|---|---|---|
| Past-test alignment | 17.5 (neutral half) | — |
| DESIGN.md alignment | — | 5 (neutral half) |

State the fallback explicitly in the report: "Past-test alignment scored 17.5/35 — neutral fallback because no canonical learnings doc exists for [surface]."

### Rendering rules

- Always show the factor breakdown, not just the total. The total is meaningless without seeing which factors drove it.
- Always state: "Reproducible rubric, not a statistical prediction."
- Round to whole points. Don't pretend to two decimals of precision.
- If member-fit signal was downweighted due to sparse retrieval (<3 quotes per persona), say so under the score.

### Example rendering

```
Multi-factor score: 67/100
  Past-test alignment:  28/35  (aligns w/ CDP-351 decision-environment simplification)
  Member-fit signal:    12/25  (mixed — Sam positive, Casey negative)
  Brand alignment:      10/10
  A11y:                 10/10
  DESIGN.md alignment:   5/10  (neutral fallback — no DESIGN.md in repo)
  In-flight collision:   2/10  (partial — overlaps with CDP-XXX same-surface test)

Reproducible rubric, not a statistical prediction.
```

---

## C. Range estimate

Only render when **≥3 comparable past tests** on the same surface provide a prior on the same metric family. Otherwise return:

> No prior; net-new bet.

### What "comparable" means

All three must be true:

1. **Same surface** — the surface-axis cell matches (see `design-validate-surfaces.md`). Enrollment funnel tests do not count as prior for member-dashboard changes.
2. **Same general intent** — friction reduction at payment, social proof at /start, mobile simplification, etc. Three random enrollment tests with no shared intent are NOT a prior.
3. **Same metric family** — primary metric must be in the same family. "Nom-code-to-plaque" tests prior for nom-code-to-plaque proposals. Don't mix A&E lift priors with FOL lift priors.

### Render format

State `n`, the metric, the surface, and the range:

> Based on 4 prior comparable tests on `/enroll/*` (intent: friction reduction at payment step), lift on nom-code-to-plaque ranged from **−5.2% to +9.2%**. Median −0.4%. Two of four shipped.

Always include:
- `n` (number of comparable priors)
- Surface
- Intent label
- Metric family
- Min, max, and (optionally) median
- Ship rate among those priors, if known

Never:
- Project a single number ("we expect +3.5% lift") — the rubric does not support a point estimate
- Mix metric families (FOL conversion priors used for A&E proposals)
- Use enrollment-funnel priors for non-enrollment surfaces

### When to upgrade or downgrade range honesty

- If all 3+ priors moved in the same direction → say so: "All 4 priors moved positively; range +1.2% to +9.2%."
- If priors are bimodal (clustered at win OR loss, nothing in middle) → say so: "Bimodal priors — two losses around −5%, two wins around +8%. Either ships big or doesn't."
- If priors are old (>12 months) → flag staleness: "Range based on tests from [date range]. Funnel has shipped X changes since."

---

## Putting the three views together

The report should print A, B, C in that order, then a one-line synthesis:

```
VERDICT (A):  POSITIVE
SCORE (B):    67/100
RANGE (C):    Based on 4 priors on /enroll/*, lift ranged −5.2% to +9.2%; median −0.4%.

Synthesis: Test it. Rubric is solid (B), priors support the direction (A), but range
is wide (C) — don't over-promise on the magnitude.
```

The synthesis is one sentence. If the three views disagree, name the disagreement instead of papering over it:

```
Synthesis: Score (67) and verdict (POSITIVE) look encouraging, but the range view
shows priors went bimodal — half won big, half lost. Treat this as a swing-for-fences
test, not a safe win.
```
