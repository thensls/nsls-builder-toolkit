# NSLS-Specific Audit Context

Calibration notes for audits on NSLS pages (members.nsls.org, FOL flow, A&E pages, induction pages, marketing pages). Do not apply generic e-commerce or SaaS heuristics blindly — NSLS audience patterns differ.

## The Prestige-Polish Paradox

**Core insight:** NSLS members respond to *institutional credibility* (university affiliations, academic framing, alumni outcomes, leadership development language) more than to *e-commerce urgency* (countdown timers, discount badges, "only X left" scarcity).

**Implications for audits:**
- A "best-practice" violation that *removes* an e-commerce pattern is often correct for this audience. Don't flag the absence of urgency tactics as a P1.
- Polish that signals institutional rigor (clean typography, conservative color, clear academic framing) is high-value here, even when generic UX heuristics would call it "low energy."
- Calls to action framed around growth/leadership/credentials outperform transactional language ("Get FOL" < "Begin your Foundations of Leadership").

## Common patterns in past A/B tests

- **Trust signals beat scarcity.** University logos, alumni testimonials, and academic accreditation cues outperform timer-based or "limited spots" framing.
- **Specificity beats generic encouragement.** Concrete language about credentials and credit hours beats motivational copy.
- **Reducing fields wins.** Postel's Law violations (forcing strict input format) and Parkinson's Law misses (forms that take longer than necessary) consistently underperform.
- **The TNC earlier-in-funnel pattern works.** Showing terms early reduces drop-off vs. surprising users at payment.

## Recurring findings to look for first

When auditing NSLS pages, always check these before broader review:

1. **Pricing clarity.** Is the relevant product price visible and unambiguous? (See product price reference in user memory.)
2. **Step indication.** In multi-step flows (FOL, A&E upsell, induction), is the user's position clear? (Goal-Gradient)
3. **Institutional vs. transactional framing.** Does the copy lean academic/leadership or e-commerce/transactional?
4. **Mobile reflow.** A&E and enrollment pages have historically struggled at 320px width.
5. **Form field count.** Compare to past winning variants. Reductions usually win.
6. **Error states in payment.** P0 if missing — payment errors without clear recovery cause hard drop-off.
7. **A&E attribution gap (analytics, not UX).** ~29% of A&E revenue is unattributed by channel — flag if audit includes any A&E page that affects this.

## Architecture notes

### Enrollment is gated by unique nomination codes — NOT magic links

NSLS members receive a **unique nomination code** via email (Customer.io enrollment campaigns), SMS, or chapter advisor. Codes look like `19122-244-13439` (3-part numeric).

**Correct flow:** nom code → `app.nsls.org/enroll/start/<nomination-code>` → server validates code → HttpOnly enrollment-session cookie set (chapter id, advisor id, code id, expiry) → single redirect to `/enroll/welcome` → no client-side `router.push` race.

**Don't refer to this as "magic link" or "chapter URL"** — those are different patterns. The nom-code URL pattern is `/enroll/start/<code>`. PostHog session data has shown real users in redirect loops between this URL and `/welcome` due to client-side hydration races; this is a known P0-class architectural concern.

### Production enrollment lives at `app.nsls.org/enroll/*`

The `members.nsls.org/enroll/*` URLs are legacy and receive minimal traffic (last 30 days: ~3K pageviews vs ~200K on `app.nsls.org`). Audit only the `app.nsls.org` flow unless the user explicitly asks about legacy.

## Before recommending — check what's already been tested

A heuristic recommendation may already have been tested by the squad and lost. Before treating any P0 / P1 as net-new:

1. **Confluence:** search "enrollment" / "FOL" / "welcome page" / "payment" for outcome pages from the last 18 months.
2. **Slack:** search `#enrollment-squad` and similar channels for "tested", "winner", "lost", "FOL completion."
3. **Airtable test priorities tracker:** look for prior hypotheses on the same lever.
4. **Hex dashboards:** Audience Insights, post-induction, experiment cost/benefit (when available).

Test outcomes per Julia's saved memory: pull from PostHog + Slack first, NOT Airtable (which is write-only for test outcomes).

If a recommendation has already been tested and lost — flag that explicitly in the audit. If it's been tested and won, the recommendation is moot (already implemented or about to be).

## Stakeholder framing

- **For SLT reports:** Lead with predicted SUS, top 3 P0/P1 findings, and revenue/conversion implications. Use LOP-aligned framing if known.
- **For engineering reports:** Lead with WCAG findings (compliance is concrete), include code-level recommendations.
- **For design reports:** Lead with Laws of UX findings, include specific Figma node references where possible.
