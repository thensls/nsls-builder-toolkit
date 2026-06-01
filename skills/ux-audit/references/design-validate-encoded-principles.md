# Design Validation — Encoded Principles (Enrollment Funnel)

This is the auto-flag ruleset. Every proposed change on the enrollment funnel surface (and tentatively the invitee landing surface) is checked against these principles. Each principle yields a specific output phrasing the validator must use.

Source: [Experiment Learnings — Enrollment Funnel](https://nsls.atlassian.net/wiki/spaces/NSLS/pages/3602579458) (Confluence 3602579458).

> **Scope.** These principles apply to the enrollment funnel surface (and tentatively the invitee landing surface). They do NOT directly transfer to Society, member dashboard, advisor tools, or marketing surfaces — those need their own learnings docs. Only universal principles (WCAG, Fitts, Hick, touch-target sizing) cross surface boundaries without re-validation.

---

## How to use this file

For each principle below:

1. Check whether the proposed change satisfies the **specific check**.
2. If yes (ALIGN with validated, or AVOID rejected), use the prescribed phrasing.
3. If no, use the corresponding warning phrasing.
4. Cite the source experiment(s) by Jira key in the report.

A change can simultaneously align with one principle and repeat another rejected one. Report both. Don't pick the more flattering one and hide the other.

---

## Validated principles — flag ALIGNMENT

### V1. Prestige + friction reduction together

**Specific check:** Does the proposed change reduce friction (fewer steps, fewer fields, faster path) WHILE preserving or enhancing institutional / prestige markers (NSLS branding, accreditation, school/chapter visibility)?

**Source experiments:** [CDP-237](https://nsls.atlassian.net/browse/CDP-237), [CDP-351](https://nsls.atlassian.net/browse/CDP-351), [CDP-214](https://nsls.atlassian.net/browse/CDP-214)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V1 (Prestige + friction reduction together) because it [reduces X friction while preserving Y prestige marker]. Validated by CDP-237, CDP-351, CDP-214.

**Output phrasing when partially aligned (friction reduced but prestige removed):**
> Proposed change PARTIALLY aligns with V1 — it reduces friction but also removes [prestige marker]. Per CDP-261-V1, removing institutional markers carries downside risk. Recommend retaining the marker.

---

### V2. Mobile simplification specifically

**Specific check:** Does the proposed change simplify the mobile experience (collapsing layouts, persistent CTAs, larger touch targets, fewer above-fold decisions) — specifically targeting mobile, not just generally?

**Source experiments:** [CDP-353](https://nsls.atlassian.net/browse/CDP-353), [CDP-339](https://nsls.atlassian.net/browse/CDP-339), [CDP-301](https://nsls.atlassian.net/browse/CDP-301), [EE-9](https://nsls.atlassian.net/browse/EE-9)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V2 (Mobile simplification) because it [collapses/persists/enlarges X on mobile]. Validated by CDP-353, CDP-339, CDP-301, EE-9.

**Output phrasing when desktop-only change:**
> Proposed change does not engage V2 because it targets desktop only. Re-evaluate against V2 if a mobile counterpart is added.

---

### V3. Decision-environment simplification at payment

**Specific check:** Does the proposed change reduce cognitive load specifically at the payment step (fewer choices, clearer pricing, deferred decisions)?

**Source experiments:** [CDP-351](https://nsls.atlassian.net/browse/CDP-351), [CDP-338](https://nsls.atlassian.net/browse/CDP-338)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V3 (Decision-environment simplification at payment) because it [removes / defers / clarifies X at payment]. Validated by CDP-351, CDP-338.

**Companion operating rule:** Payment is a cognitive bottleneck — minimize decisions there. See operating rules below.

---

### V4. Persistent CTAs on mobile

**Specific check:** Does the proposed change keep the primary CTA visible while scrolling on mobile (sticky footer, anchored bar, or above-fold-on-all-viewports placement)?

**Source experiments:** [CDP-301](https://nsls.atlassian.net/browse/CDP-301), [CDP-339](https://nsls.atlassian.net/browse/CDP-339)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V4 (Persistent CTAs on mobile) because it [persists CTA via X mechanism]. Validated by CDP-301, CDP-339.

**Output phrasing when the change moves a CTA below the fold or removes a sticky element:**
> Proposed change CONFLICTS with V4 — it [moves CTA below fold / removes sticky mechanism]. CDP-301 and CDP-339 validated that persistent mobile CTAs improve conversion. Recommend retaining persistence.

---

### V5. Voluntary commitments as trust signals

**Specific check:** Does the proposed change introduce a member-initiated commitment (e.g., voluntary opt-in for SMS, calendar reminder, save-progress) that signals trust through autonomy rather than through generic badges?

**Source experiments:** [CDP-149](https://nsls.atlassian.net/browse/CDP-149) (SMS opt-in)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V5 (Voluntary commitments as trust signals) because it [introduces voluntary X]. Validated by CDP-149.

---

### V6. Risk reversal framed institutionally

**Specific check:** Does the proposed change use institutional language for risk reversal (e.g., "30-day refund guarantee" framed as NSLS policy, not as ecommerce return-window copy)?

**Source experiments:** [CDP-214](https://nsls.atlassian.net/browse/CDP-214) (30-day refund copy)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V6 (Risk reversal framed institutionally) because it [frames X as institutional policy / NSLS guarantee]. Validated by CDP-214.

**Output phrasing when the change uses generic ecommerce framing:**
> Proposed change PARTIALLY aligns with V6 — risk reversal is present but framed in generic ecommerce language. CDP-214 validated the institutional framing specifically. Recommend re-framing as NSLS policy.

---

### V7. Credibility signals from authoritative institutions

**Specific check:** Does the proposed change add or strengthen credibility signals from authoritative bodies (accreditation, university partnerships, named institutional endorsements) — not generic "trusted by" badges?

**Source experiments:** [EE-8](https://nsls.atlassian.net/browse/EE-8) (accreditation badges, trending positive)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V7 (Credibility signals from authoritative institutions) because it [adds / strengthens X institutional marker]. Trending positive per EE-8.

> Note: EE-8 is **trending** positive, not yet fully validated. State this when citing.

---

### V8. Device-specific design + decisions

**Specific check:** Is the proposed change explicitly designed for one device class (mobile OR desktop), with the recognition that mobile and desktop behave as different surfaces?

**Source experiments:** [CDP-338](https://nsls.atlassian.net/browse/CDP-338), [CDP-339](https://nsls.atlassian.net/browse/CDP-339), [CDP-353](https://nsls.atlassian.net/browse/CDP-353), [EE-9](https://nsls.atlassian.net/browse/EE-9)

**Output phrasing when aligned:**
> Proposed change ALIGNS with V8 (Device-specific design + decisions) because it explicitly targets [mobile / desktop] with [device-appropriate X]. Validated by CDP-338, CDP-339, CDP-353, EE-9.

**Output phrasing when the change is one-size-fits-all:**
> Proposed change does not engage V8 — it ships the same treatment to mobile and desktop. CDP-338, CDP-339, CDP-353, EE-9 all validated device-specific treatments. Recommend splitting into device-specific variants.

---

## Rejected patterns — flag REPETITION as warning

### R1. Generic ecommerce-style trust patterns

**Specific check:** Does the proposed change introduce generic ecommerce trust patterns (green checkmark trust boxes, SSL padlock callouts, "trusted by 10,000+ members" badges, generic security ribbons) instead of institutional credibility markers?

**Source experiments:** [CDP-261-V2](https://nsls.atlassian.net/browse/CDP-261) (green trust box, **−5.17%**)

**Output phrasing when repeated:**
> Proposed change REPEATS R1 (Generic ecommerce-style trust patterns) from CDP-261-V2 (green trust box, **−5.17%**) — recommend reframing because generic trust patterns signal "transaction" not "credential", which hurts conversion on a prestige product. Use institutional markers (V7) instead.

---

### R2. Removing institutional markers without testing

**Specific check:** Does the proposed change remove an institutional marker (contact header, NSLS branding, accreditation, "Part 1 / Part 2" labels, chapter info) without an explicit hypothesis and isolated test?

**Source experiments:**
- [CDP-261-V1](https://nsls.atlassian.net/browse/CDP-261) (contact-header removal, **−2.50%**)
- [CDP-352](https://nsls.atlassian.net/browse/CDP-352) ("Part 1" label removal, **−27% A&E**)

**Output phrasing when repeated:**
> Proposed change REPEATS R2 (Removing institutional markers) from CDP-261-V1 (**−2.50%**) and CDP-352 (**−27% A&E**) — recommend retaining the marker. Removing institutional markers untested has caused measurable downstream losses twice. See operating rule O5.

---

### R3. Default to express checkout / ecommerce-style payment patterns

**Specific check:** Does the proposed change default to express checkout (Apple Pay first, one-click pay, Buy Now branding) or other ecommerce-style payment patterns that hide the credential/membership nature of the transaction?

**Source experiments:** [CDP-324](https://nsls.atlassian.net/browse/CDP-324) (**−5.76%**)

**Output phrasing when repeated:**
> Proposed change REPEATS R3 (Default to express checkout) from CDP-324 (**−5.76%**) — recommend reframing because express-checkout flows reduce trust on a credential purchase. Members want to see what they're paying for. Use V3 (decision-environment simplification) without removing the institutional framing.

---

### R4. Removing form elements that serve psychological orientation

**Specific check:** Does the proposed change remove a form element (date picker, optional field, confirmation step) that, while not strictly necessary, gives members psychological orientation or commitment?

**Source experiments:** [CDP-309](https://nsls.atlassian.net/browse/CDP-309) (calendar picker removal, dropped downstream conv)

**Output phrasing when repeated:**
> Proposed change REPEATS R4 (Removing form elements that serve psychological orientation) from CDP-309 (calendar picker removal dropped downstream conversion) — recommend retaining the element. Some "extra" fields function as commitment devices; removing them reduces follow-through.

---

### R5. Adding decision complexity at /start

**Specific check:** Does the proposed change add content to the `/start` page that introduces additional decisions, evaluation, or cognitive load (testimonials, plan comparison, content-heavy hero) before the member commits to the funnel?

**Source experiments:** [CDP-293](https://nsls.atlassian.net/browse/CDP-293) (testimonial on /start, **−6.57%**)

**Output phrasing when repeated:**
> Proposed change REPEATS R5 (Adding decision complexity at /start) from CDP-293 (testimonial on /start, **−6.57%**) — recommend reframing. The /start page should reduce decisions, not add them. Move the content to a later step or a separate page.

---

### R6. Surfacing legal/T&Cs early in flow

**Specific check:** Does the proposed change surface terms-of-service, privacy policy, refund policy, or other legal copy at Step 1 or earlier — instead of at the payment confirmation step?

**Source experiments:** [CDP-335](https://nsls.atlassian.net/browse/CDP-335) (T&Cs at Step 1, **−2.61% nom-code-to-plaque**)

**Output phrasing when repeated:**
> Proposed change REPEATS R6 (Surfacing legal/T&Cs early) from CDP-335 (T&Cs at Step 1, **−2.61% nom-code-to-plaque**) — recommend moving legal copy to the payment confirmation step. Early legal surfacing reads as transactional friction.

---

## Operating rules — always check

These are not pass/fail rules — they are guardrails. Every report should confirm the change satisfies them.

### O1. Test one variable at a time

**Specific check:** Is the proposed change isolated to one variable, or does it bundle multiple changes (copy + layout + color + new component)?

**Output phrasing when not isolated:**
> O1 (Test one variable at a time) violated — proposed change bundles [list bundles]. Recommend splitting into separate tests so the winning factor can be attributed.

---

### O2. Track refunds and support contacts alongside conversion

**Specific check:** Does the test plan include refund rate AND support-contact rate as secondary metrics, not just conversion?

**Output phrasing when missing:**
> O2 (Track refunds and support contacts) not addressed — recommend adding refund rate and ticket-volume tracking as secondary metrics. Conversion lift that creates downstream refunds or support load is a false win.

---

### O3. Payment is a cognitive bottleneck — minimize decisions there

**Specific check:** Does the proposed change add ANY decision at the payment step (new plan choice, new add-on, new optional field)?

**Output phrasing when violated:**
> O3 (Payment is a cognitive bottleneck) violated — proposed change adds [decision X] at payment. CDP-351 and CDP-338 validated that fewer payment decisions improve conversion. Recommend moving the decision earlier or later.

---

### O4. When prerequisite purchase gates a downstream metric, exclude or scope carefully

**Specific check:** Does the proposed change measure a downstream metric (e.g., A&E completion) where access requires a prior purchase (FOL completion)? If so, is the measurement properly scoped to only the audience that completed the prerequisite?

**Output phrasing when not scoped:**
> O4 (Prerequisite-gated metric scoping) at risk — proposed test measures [downstream metric] which is gated by [prerequisite]. Recommend scoping the analysis to the subset that completed the prerequisite, or pre-registering the exclusion logic.

---

### O5. Never remove institutional markers untested

**Specific check:** Does the proposed change remove an institutional marker (NSLS branding, accreditation, chapter / school name, "Part 1" labels, contact header)?

**Output phrasing when violated:**
> O5 (Never remove institutional markers untested) violated — proposed change removes [marker]. CDP-261-V1 (**−2.50%**) and CDP-352 (**−27% A&E**) both showed measurable downstream losses from this pattern. If the removal is intentional, isolate it as its own test with a clean rollback path. Otherwise, retain the marker.

---

## Final scope reminder

These principles apply to the enrollment funnel surface (and tentatively the invitee landing surface). They do NOT directly transfer to Society, member dashboard, advisor tools, or marketing surfaces — those need their own learnings docs.
