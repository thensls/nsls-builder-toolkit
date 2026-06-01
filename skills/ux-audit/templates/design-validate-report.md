# Design Validation Report Template

Use this structure when generating Design Validation Layer output from `/ux-audit` Step 6. Save as `design-validate-{descriptor}-{YYYY-MM-DD}.md`.

Every section that can't be filled from available inputs gets an explicit "not auditable from this input" or "v2 deferred" note rather than fabricated content. Honest framing throughout: this is heuristic + retrieval-grounded validation, not A/B testing.

---

```markdown
# Design Validation — {{descriptor}}

**Date:** {{YYYY-MM-DD}}
**Validator:** Julia Botz · NSLS UX
**Surface:** {{surface from the matrix — e.g., "enrollment funnel"}}
**Audience(s):** {{audiences this change targets}}
**Brand:** {{NSLS or Society}}
**Inputs:** {{mockup file / Figma URL / hypothesis text / Jira ticket}}

## Limits of this validation

This is a heuristic + retrieval-grounded validation, not an A/B test or user study. Specifically:
- The verdict and confidence score are estimates from layer findings — they do not predict measured lift.
- Member-fit signals are retrieved from HubSpot support tickets, which skew toward members who experienced friction; quiet majorities are under-represented.
- Past-test cross-reference is only as complete as the canonical Confluence doc and PostHog experiment list at time of run.
- Anything that requires live user testing, prototype interaction, or assistive-tech validation is flagged in Section 7 (What couldn't be verified).

---

## TL;DR

**Verdict:** {{STRONG POSITIVE / POSITIVE / NEUTRAL / MIXED / NEGATIVE / STRONG NEGATIVE}}
**Multi-factor score:** {{N}}/100
**Range estimate:** {{X% to Y% based on N prior comparable tests on this surface, OR "No prior; net-new bet."}}

**One-paragraph read** (3 sentences max): {{summary of what the change does, the strongest signal for or against, and the recommended next step.}}

**Top 3 things to address before launch:**
1. {{}}
2. {{}}
3. {{}}

---

## 1 · Surface map

What this change touches, top-to-bottom:

| Layer | Element(s) | Notes |
|-------|------------|-------|
| UI components | {{}} | {{}} |
| Behaviors / interactions | {{}} | {{}} |
| Events / instrumentation | {{}} | {{}} |
| Downstream systems | {{}} | {{}} |
| Member touchpoints | {{}} | {{}} |
| Cross-system dependencies | {{}} | {{}} |

**Blast radius:** {{contained-to-single-step / cross-step / cross-flow / cross-product}}

**Auditable from this input:** {{yes / partial / no — explanation}}

---

## 2 · Past-test cross-reference

**Source consulted:** {{Confluence 3602579458 Experiment Learnings — Enrollment Funnel + PostHog experiment-get-all for in-flight, OR "no canonical doc for this surface — net-new bet"}}

### Alignment with validated principles

{{For each principle the change aligns with: "✅ Aligns with [principle name] — [reason] (source: CDP-XXX)". If none, state "No matching validated principles in the canonical doc."}}

### Conflicts with rejected patterns

{{For each rejected pattern the change risks repeating: "⚠️ Risk of repeating [rejected pattern name] — [reason] (source: CDP-XXX)". If none, state "No conflicts with rejected patterns identified."}}

### Direct prior tests (from outcome table)

| Date | Surface | What was tested | Outcome | Relevance |
|------|---------|-----------------|---------|-----------|
| {{}} | {{}} | {{}} | {{WIN / LOSS / INCONCLUSIVE / RUNNING}} | {{how close to current proposal}} |

### In-flight collisions

{{From PostHog `experiment-get-all`, list any currently RUNNING experiments touching the same surface that might collide with this proposed change. Include experiment ID + link. If none, state "No in-flight collisions identified."}}

### Operating rules check

- Tests one variable at a time? {{yes / no — explain if no}}
- Tracks refunds + support contacts alongside conversion? {{yes / no / n/a}}
- Payment-step changes minimize decisions? {{yes / no / n/a}}
- Institutional markers preserved (or explicitly tested)? {{yes / no — flag any removed markers}}

---

## 3 · Member-fit panel

Personas selected from `~/.claude/skills/ux-audit/references/design-validate-personas.md` (8-archetype library). Render the panel below for each persona (3–6 total).

### Persona: {{Persona name}}

**Audience:** {{from audience axis}}
**Voice characteristics:** {{from persona file}}

**Retrieved quotes** ({{N}} from HubSpot tickets, last {{X}} months, filtered by {{filter list}}):

> "{{quote 1}}" — ticket {{ticket ID}}, {{date}}
> "{{quote 2}}" — ticket {{ticket ID}}, {{date}}
> "{{quote 3}}" — ticket {{ticket ID}}, {{date}}

**Reaction signals:**
- 👍 LIKES: {{1–2 bullets, anchored to retrieved evidence}}
- 👎 HATES: {{1–2 bullets, anchored to retrieved evidence}}
- 😕 CONFUSES: {{1–2 bullets, anchored to retrieved evidence}}

**Net signal:** {{POSITIVE / NEUTRAL / MIXED / NEGATIVE}}
**Signal strength:** {{HIGH if ≥10 quotes retrieved · MEDIUM if 5–9 · LOW if 3–4 · UNRELIABLE if <3 — do not weight this persona in panel synthesis when UNRELIABLE}}

{{Repeat the persona block for each panelist.}}

### Panel synthesis

- Personas with positive net signal: {{}}
- Personas with negative net signal: {{}}
- Personas excluded from synthesis (UNRELIABLE signal strength): {{}}
- **Confidence-weighted member-fit signal:** {{POSITIVE / NEUTRAL / MIXED / NEGATIVE}}

---

## 4 · DESIGN.md alignment

{{If a DESIGN.md exists at the target surface, render the table below. Otherwise: "No DESIGN.md found for this surface. Flag: a Department+ scope surface should have one. Recommend running /product-design Generate Mode after this validation."}}

| Principle # | Principle | Verdict | Notes |
|-------------|-----------|---------|-------|
| {{}} | {{}} | {{ALIGNS / CONFLICTS / N/A}} | {{}} |

**Overall DESIGN.md verdict:** {{aligns / one conflict / multiple conflicts / no DESIGN.md}}

---

## 5 · Brand + accessibility check

{{Cross-reference findings from Steps 1–4 of `/ux-audit` if already run on this surface. Otherwise run a lightweight pass against the brand reference (`brand-nsls.md` or `brand-society.md`) and WCAG 2.1 A+AA (`wcag-21-AA.md`).}}

**Brand:** {{NSLS or Society}}
**Prior audit referenced:** {{path to existing audit report, or "none — lightweight pass only"}}

| Severity | Finding | Where | Recommendation |
|----------|---------|-------|----------------|
| {{P0 / P1 / P2 / P3}} | {{}} | {{}} | {{}} |

**A11y blockers:** {{count of P0/P1 WCAG findings; list briefly}}
**Brand blockers:** {{count of P0/P1 brand findings; list briefly}}

---

## 6 · Confidence prediction (three views)

### View A — Directional verdict

**{{STRONG POSITIVE / POSITIVE / NEUTRAL / MIXED / NEGATIVE / STRONG NEGATIVE}}**

Evidence chain:
- Past-test alignment: {{}}
- Member-fit signal: {{}}
- Brand / a11y: {{}}
- DESIGN.md: {{}}
- In-flight collisions: {{}}

### View B — Multi-factor score

| Factor | Weight | Earned | Notes |
|--------|--------|--------|-------|
| Past-test alignment | 35 | {{}} | {{}} |
| Member-fit signal | 25 | {{}} | {{}} |
| Brand alignment | 10 | {{}} | {{}} |
| A11y | 10 | {{}} | {{}} |
| DESIGN.md alignment | 10 | {{}} | {{}} |
| In-flight collision | 10 | {{}} | {{}} |
| **Total** | **100** | **{{N}}** | |

> **Reproducible rubric, not a statistical prediction.** This score is a transparent weighted sum of the layer findings — it does not predict A/B test lift. Two validators running the same inputs through this rubric should land at the same score; that is its only claim.

### View C — Range estimate

{{If ≥3 comparable past tests exist on this surface: "Based on {{N}} prior comparable tests on {{surface}}, lift on {{primary metric}} ranged from {{X%}} to {{Y%}}. The current proposal aligns most closely with {{which past test}} ({{why}})."}}

{{Otherwise: "No prior comparable tests on this surface. Net-new bet — directional verdict (View A) and member-fit signal (Section 3) are the strongest available evidence."}}

---

## 7 · What couldn't be verified

Limits, gaps, and v2 deferrals — flagged honestly rather than fabricated.

- {{e.g., "Online vs in-person chapter split — HubSpot data lacks the modality field. Would need Airtable join. v2 gap."}}
- {{e.g., "PostHog audience-volume data — MCP currently blocked. Persona behavioral context falls back to ticket-category patterns until /connect resolves."}}
- {{e.g., "No member-research interviews surfaced for this surface. Pure ticket-based voice retrieval — quiet-majority members not represented."}}
- {{e.g., "Live prototype interaction not available — keyboard nav, focus order, and error states not verified."}}
- {{Anything else the validation couldn't address.}}

---

## Recommended next step

{{ONE concrete next step. Examples:
- "Open as a ticket for the next sprint."
- "Park until [in-flight test] reads out — re-run validation after."
- "Run /product-design Mode 3 focus group to deepen member-fit signal before filing."
- "Rework to address P0 brand finding, then re-validate."
- "Ship as-is — strong positive across all layers, no blockers."}}

---

*Generated by `/ux-audit` Step 6 — Design Validation Layer. Honest framing: this is heuristic + retrieval-grounded validation, not A/B testing. Decision-quality input, not decision substitute.*
```
