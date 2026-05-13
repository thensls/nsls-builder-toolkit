# Full UX Audit Report Template

Use this structure when generating audit output. Save as `ux-audit-{descriptor}-{YYYY-MM-DD}.md`.

---

```markdown
# UX Audit: [Page/Frame Name]

**Date:** [YYYY-MM-DD]
**Auditor:** Claude (heuristic review)
**Input type:** [Live URL / Figma frame / Screenshot / HTML]
**Source:** [URL or file reference]
**Layers:** [SUS / Laws of UX / WCAG 2.1 A+AA / all]
**Audience:** [Engineering / Design / SLT / mixed]

## Limits of this audit

This is a heuristic expert review, not user testing or automated accessibility scanning. Specifically:
- The Predicted SUS below is an estimate based on the design, not a measured score from real users.
- WCAG findings are based on [static HTML / static design]. The following could not be evaluated from this input and are flagged in the body: [list, e.g., focus visibility, keyboard nav, screen reader behavior, error states].
- Recommend running axe-core/Lighthouse alongside this report and validating with assistive tech testing before any conformance claim.

---

## Executive summary

**Predicted SUS: [score] ([grade] — [interpretation])**
*Heuristic estimate, not user-validated.*

**Top 3 issues to fix first:**
1. [P0/P1 finding title] — [one-line impact]
2. [P0/P1 finding title] — [one-line impact]
3. [P0/P1 finding title] — [one-line impact]

**Total findings:** [N] across [N] P0, [N] P1, [N] P2, [N] P3

---

## Predicted SUS breakdown

| # | SUS Item | Predicted (1–5) | Contribution (0–4) | Reasoning |
|---|----------|-----------------|---------------------|-----------|
| 1 | Frequent use | x | x | ... |
| 2 | Unnecessarily complex | x | x | ... |
| ... | | | | |

**Total: [sum]/40 → [sum × 2.5] = Predicted SUS [N]**

**Confidence:** [High / Medium / Low] — [reasoning, especially flagging items 1 and 9 as low-confidence from static review]

---

## Findings by severity

### P0 — Critical

#### P0.1 [SUS-7 / Hick / 1.4.3] [Title]
- **Where:** [specific element/location]
- **Issue:** [what's wrong, plain language]
- **Impact:** [who, how]
- **Recommendation:** [concrete fix]
- **Auditable from this input:** [yes / partial / no — explanation]

[repeat for all P0]

### P1 — Major

[same format]

### P2 — Minor

[same format, can be more terse]

### P3 — Polish

[same format, terse]

---

## Findings by category

### SUS findings
[List of findings with SUS item references]

### Laws of UX findings
[Grouped by law]

### WCAG 2.1 A+AA findings
[Grouped by POUR principle, citing criterion number]

---

## Not auditable from this input

These required prototype testing, live keyboard navigation, or assistive tech testing and could not be evaluated from [input type]:
- [criterion / concern]
- [criterion / concern]

**Recommended next step:** [prototype test / live URL test with axe + keyboard / NVDA pass]

---

## Recommended next steps

1. [Highest-leverage action]
2. [Next]
3. [Next]

If considering an A/B test on findings: [hypothesis suggestion based on highest-impact P1 issue]

If considering a real SUS: see SUS instrument in skill templates. Recommend n=12-14 for reliable estimate per Sauro & Lewis.
```
