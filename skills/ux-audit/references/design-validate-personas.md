# Design Validation — Member-Fit Persona Panel (v1)

Eight personas. Each represents a real audience × surface position the validator can convene as a "panel" when scoring a proposed change. Reactions are NOT made up — they are anchored to real HubSpot ticket-category patterns (see `design-validate-hubspot-retrieval.md` for the query mechanics).

> **Society user persona — deferred to v2.** Society is a separate product with its own brand, surfaces, and audience. v1 of the design validator covers the NSLS honor-society product only. When a Society-surface change is submitted, the validator should note: "Society persona not yet defined — net-new bet."

## How to use this file

1. Use the surface matrix (`design-validate-surfaces.md`) to identify which personas live on the proposed change's surface.
2. For each relevant persona, run the HubSpot retrieval query template below.
3. If retrieval returns **≥3 quotes**, generate the persona's predicted reaction grounded in those quotes.
4. If retrieval returns **<3 quotes**, downweight that persona in the rubric AND label the finding: "Limited member-voice signal — [N] quotes found."
5. Never fabricate quotes. If the data isn't there, say so.

---

### Persona 1 — Cold prospect ("Maya, scrolling NSLS.org")

**Audience:** Cold prospect
**Primary surfaces:** Marketing site, email lifecycle (cold outreach)
**One-line summary:** Has heard the name "NSLS" — from a classmate, an email, a search result — and is deciding whether it's legit before sharing any info.
**Voice characteristics:** Skeptical, comparison-shopping, short questions. Pet phrases: "Is this real?", "How much does this cost?", "Is this a scam?". Often types in lowercase, frequently asks "what is this" rather than describing a problem.
**Mental model:** "Another honor society email. Probably pay-to-play. Prove me wrong."
**Frustrations:**
- Can't tell legit from scam at a glance
- Pricing not obvious enough to evaluate
- Nomination feels arbitrary ("why me?")

**Motivations:**
- Resume-worthy credential, IF the credential is real
- Belonging / recognition
- Low-risk evaluation (browse before committing)

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Are you legit/Scam',
  'General Member Inquiry - How much is the NSLS',
  'General Member Inquiry - Nomination Questions'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage IN ('subscriber', NULL)
Limit: 30
```

**Cross-cutting attributes that may matter:** age band (younger = more brand-aware skepticism), state (regional brand awareness varies), source (organic search vs. nominator referral changes trust baseline).
**Behavioral signal placeholder:** PostHog session recordings on /nsls.org marketing pages — bounce rate, scroll depth, "pricing" page visits before /enroll/start. **v2.**
**What they typically LIKE:** Clear "what is this", explicit pricing, named accreditation bodies, presence of school/chapter list (proof other people they know are in it).
**What they typically HATE:** Vague benefits language, urgency tactics ("nominate today!"), missing pricing, ecommerce-style trust patterns that signal "this is a transaction not a credential" — see CDP-261-V2 in `design-validate-encoded-principles.md`.
**What CONFUSES them:** The relationship between "nomination" and "membership". Why did they get an email? How would NSLS know who they are?

---

### Persona 2 — Invitee ("Jordan, just got the nom code email")

**Audience:** Invitee
**Primary surfaces:** Invitee landing (`/enroll/start/<code>`), email lifecycle (invite + reminder cadence)
**One-line summary:** Received a nomination code. Has clicked through to the landing page but hasn't started Step 1 yet. Deciding whether to proceed.
**Voice characteristics:** Cautious, slightly flattered, asks structural questions. "Why was I nominated?" "Is this from my school?" "Is this a real invite or did everyone get one?". Slightly longer messages than cold prospects — they have a code in hand, which gives them a thread to pull.
**Mental model:** "Someone said I qualify. Do I actually qualify, or is this mass-send?"
**Frustrations:**
- Doesn't recognize the nominator
- Doesn't know if the invite is exclusive or universal
- Email looks like marketing — could be a scam

**Motivations:**
- Being recognized for actual achievement
- Validating the invite is legitimately tied to their school
- Understanding what they're being invited TO before committing

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Am I a member',
  'General Member Inquiry - Duplicate Invite',
  'General Member Inquiry - Nomination Questions'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage = 'lead'
Limit: 30
```

**Cross-cutting attributes that may matter:** chapter (chapter-level brand awareness; some campuses have visible NSLS chapters, others don't), source (which advisor / system sent the invite).
**Behavioral signal placeholder:** PostHog `/enroll/start/<code>` → `/enroll/step1` conversion, time on landing, scroll depth. **v2.**
**What they typically LIKE:** Visible institutional markers (their school name, their chapter advisor's name, accreditation), clear "what happens next" preview, presence of a contact-us / question path.
**What they typically HATE:** Removing institutional markers (CDP-261-V1 contact-header removal dropped −2.50%), generic startup-y trust patterns, surprise pricing only revealed after Step 1.
**What CONFUSES them:** Whether "nomination" auto-enrolled them or whether they still have to act. The cost structure (one-time vs ongoing). Whether their school knows.

---

### Persona 3 — Active enrollee on mobile ("Sam, on the bus, filling out Step 2")

**Audience:** Active enrollee
**Primary surfaces:** Enrollment funnel (`/enroll/*`), email lifecycle (in-funnel reminders)
**One-line summary:** Past /step1, deep in the funnel, on a phone, often in a low-attention context (commuting, between classes, late at night).
**Voice characteristics:** Short, mid-task tickets. "Card declined?", "It won't go to the next page", "I can't see the button". Often sent from mobile email clients; punctuation drops. Pet phrases: "doesn't work", "stuck", "tried again".
**Mental model:** "I've decided to do this. Just let me finish."
**Frustrations:**
- Payment confirmation feels uncertain (did it go through?)
- Member ID vs login email confusion at the credentials step
- Buttons too small, CTAs scroll out of view (validated as fixable — CDP-301, CDP-339)
- Sessions timing out mid-flow

**Motivations:**
- Quick task closure
- Confidence the payment landed
- Reliable saving of progress

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Payment Issues',
  'Potential Member Inquiry - Payment Issue/Enrollment over the Phone',
  'General Member Inquiry - MemberID inquiry',
  'General Member Inquiry - Login Issues',
  'General Member Inquiry - Technology Issue'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage IN ('opportunity', 'MQL')
Limit: 30
```

**Cross-cutting attributes that may matter:** device (mobile-specific — strongest signal), age band (younger ↔ more mobile-native but also more impatient), source (which campaign brought them in changes urgency baseline).
**Behavioral signal placeholder:** PostHog funnel completion by device, drop-off step, time-to-payment-confirm. **v2.**
**What they typically LIKE:** Persistent CTAs that stay visible while scrolling (CDP-301, CDP-339), clear "we got your payment" feedback, large touch targets, password-manager-compatible fields.
**What they typically HATE:** Express-checkout / ecommerce-style payment patterns that hide what's being charged (CDP-324 −5.76%), broken payment confirmation, buttons below the fold on mobile.
**What CONFUSES them:** The Member ID vs login email distinction (they think their email IS their ID). Whether their card was charged when the page reloads. What "Part 1" / "Part 2" labels mean if they're abbreviated or removed (CDP-352 −27% A&E when removed).

---

### Persona 4 — Active enrollee on desktop ("Priya, at her laptop, filling out enrollment")

**Audience:** Active enrollee
**Primary surfaces:** Enrollment funnel (`/enroll/*`), email lifecycle
**One-line summary:** Same intent as Sam but on a larger screen, generally in a higher-attention context (desk, library, dorm room). Lower friction baseline; mobile-specific issues don't apply but cognitive-load issues still do.
**Voice characteristics:** Slightly longer tickets, more structured. Will paste error messages. Will reference specific page elements ("the dropdown on Step 3"). Pet phrases: "I tried", "when I click", "the screen says".
**Mental model:** "I'm here to complete a task. Tell me clearly what to do."
**Frustrations:**
- Forms with unclear required-field signaling
- Validation errors that don't say what to fix
- Decision overload at payment (multiple plans, multiple add-ons)

**Motivations:**
- Successful completion in one sitting
- Clear progress / "what step am I on"
- Trustworthy payment step

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Payment Issues',
  'General Member Inquiry - MemberID inquiry',
  'General Member Inquiry - Login Issues',
  'General Member Inquiry - Technology Issue'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage IN ('opportunity', 'MQL')
Limit: 30
```
(Same filter as mobile; the device distinction comes from cross-referencing PostHog when available.)

**Cross-cutting attributes that may matter:** device (desktop specifically), age band (older ↔ may prefer desktop, may need larger type even on desktop), chapter (chapter-led cohorts may enroll in batches from a computer lab).
**Behavioral signal placeholder:** PostHog desktop funnel completion, drop-off step. **v2.**
**What they typically LIKE:** Clear step indicators, visible "what's next" preview, decision-environment simplification at payment (CDP-351, CDP-338), institutional framing of refund guarantees (CDP-214).
**What they typically HATE:** Decision complexity at /start (CDP-293 testimonial on /start −6.57%), surfacing T&Cs early in flow (CDP-335 T&Cs at Step 1 −2.61%), generic green trust-box patterns (CDP-261-V2 −5.17%).
**What CONFUSES them:** Multiple membership tiers shown simultaneously without comparison structure. Hidden costs revealed late. Inconsistent terminology between steps (3.2.4 WCAG).

---

### Persona 5 — Stuck / abandoned enrollee ("Alex, abandoned at the payment step three days ago")

**Audience:** Active enrollee (stalled subset)
**Primary surfaces:** Enrollment funnel (`/enroll/*`), email lifecycle (recovery cadence), occasionally member dashboard if they later complete
**One-line summary:** Started enrollment, hit a wall (often at payment or after), didn't finish. May write a ticket asking for help, asking for a refund of a partial charge, or asking whether they're still "in".
**Voice characteristics:** Frustrated, longer than mobile enrollee tickets, often references something specific that went wrong. Will use the word "tried" repeatedly. Pet phrases: "charged twice", "can't get back in", "still showing as not a member", "want a refund".
**Mental model:** "Something broke and now I don't know if I'm in or out or owed money."
**Frustrations:**
- Doesn't know status (member or not)
- Charged but no confirmation
- Profile half-set-up, can't access dashboard
- Refund process opaque

**Motivations:**
- Resolution (one way or the other)
- Refund if applicable
- Or completion if recoverable

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Refund - FOL - Saved',
  'General Member Inquiry - Refund - FOL - Issued',
  'General Member Inquiry - Payment Issues',
  'General Member Inquiry - Profile-Setup'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage IN ('opportunity', NULL)
Limit: 30
```

**Cross-cutting attributes that may matter:** device (mobile-stall vs desktop-stall hint at different root causes), source (refund regret correlates with certain UTM campaigns), chapter.
**Behavioral signal placeholder:** PostHog drop-off step, time-since-drop-off, return-visit pattern. **v2.**
**What they typically LIKE:** Proactive "we noticed you didn't finish" emails with a deep link back to where they were, clear refund path, visible support contact.
**What they typically HATE:** Re-doing already-completed steps on return, support paths that loop back to FAQ, partial charges with no explanation.
**What CONFUSES them:** Whether the original charge was completed or pending. Whether returning will create a duplicate enrollment. Where to find their nom code if they've lost the email.

---

### Persona 6 — Newly inducted member ("Devon, just paid, on the dashboard for the first time")

**Audience:** Newly inducted
**Primary surfaces:** Member dashboard, email lifecycle (welcome / induction-kit cadence)
**One-line summary:** Completed enrollment within the last ~30 days. Lifecycle stage = `customer`, `date_entered_customer` recent. On the dashboard for the first or second time, orienting themselves.
**Voice characteristics:** Earnest, sometimes uncertain. Will use language like "I just signed up" and "what do I do next". Tickets often more polite/formal than enrollment-stage ones — they're now invested. Pet phrases: "now what", "where do I find", "when does my [induction kit / certificate] arrive".
**Mental model:** "I paid. I'm in. What's the experience supposed to look like?"
**Frustrations:**
- Induction kit shipping status opaque
- Profile-setup steps not obviously labeled as required
- Login issues right after enrollment (different password / different system)
- Not sure what their actual benefits ARE

**Motivations:**
- Realizing the credential (physical kit, certificate)
- Understanding what to do to "use" the membership
- Connecting with their chapter / advisor

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Induction-Kit-Tracking',
  'General Member Inquiry - Profile-Setup-Help',
  'General Member Inquiry - Login Issues',
  'General Member Inquiry - Now what do I do'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage = 'customer'
Join contact: date_entered_customer > now - 30 days
Limit: 30
```

**Cross-cutting attributes that may matter:** chapter (chapter health predicts post-induction engagement quality), state (induction kit shipping experience varies by region), age band.
**Behavioral signal placeholder:** PostHog dashboard first-week sessions, feature-usage breadth. **v2.**
**What they typically LIKE:** Clear "what's next" sequencing, induction-kit tracking, chapter-leader introduction, named accreditation reinforcement (EE-8 trending positive).
**What they typically HATE:** Empty-state dashboards without guidance, requiring login again immediately after payment, generic "welcome" emails with no next step.
**What CONFUSES them:** The difference between "induction" and "enrollment" (some still ask whether they're a member). The difference between online resources and the physical kit. How to find their chapter.

---

### Persona 7 — Disengaged inducted member ("Casey, paid 8 months ago, hasn't logged in since")

**Audience:** Disengaged inducted
**Primary surfaces:** Member dashboard (re-entry attempts), email lifecycle (re-engagement / lapsed cadence)
**One-line summary:** Inducted member (`lifecyclestage = customer`) whose last activity was >90 days ago. Either forgot, doesn't see ongoing value, or had a bad experience and didn't return.
**Voice characteristics:** Two flavors — (a) "I forgot about this, am I still a member?" and (b) "I want a refund, I never used it". Both shorter and less invested than newly-inducted voice. Pet phrases: "still active", "did I pay for this", "refund", "I never used".
**Mental model:** "I think I joined this thing at some point. Is it still a thing for me?"
**Frustrations:**
- Forgot login credentials
- Doesn't remember why they joined / what the benefits are
- Resents recurring or post-induction charges they don't recall agreeing to

**Motivations:**
- Either re-engage (low effort) or exit cleanly (refund / cancel)
- Confirm membership status without much effort
- Not be sold to again

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category IN (
  'General Member Inquiry - Refund - FOL - Issued',
  'General Member Inquiry - Login Issues',
  'General Member Inquiry - Am I a member'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage = 'customer'
Join contact: notes_last_updated < now - 90 days
Limit: 30
```

**Cross-cutting attributes that may matter:** age band, chapter (chapters with high disengagement reflect chapter-level program-health gaps).
**Behavioral signal placeholder:** PostHog login recency, dashboard return rate. **v2.**
**What they typically LIKE:** Frictionless "are you still a member" lookup, simple cancel/refund path, low-touch re-engagement (one-link return).
**What they typically HATE:** High-pressure re-engagement, hidden cancel paths, requiring profile re-setup.
**What CONFUSES them:** Whether they're paying recurring fees. Whether their original payment was one-time. How to log in if their old email is gone.

---

### Persona 8 — Advisor / chapter leader ("Dr. Rivera, runs the chapter at State U")

**Audience:** Advisor / chapter leader
**Primary surfaces:** Advisor tools, email lifecycle (advisor cadence), occasionally marketing site
**One-line summary:** Faculty or staff member running an NSLS chapter on a campus. Identifiable by `advisor_chapter_object_id` on the contact record. Different operating context than members — they're administering the program, not consuming it.
**Voice characteristics:** Professional, structured, often signed with a title. Longer messages. Asks about rosters, dates, deliverables, batch operations. Pet phrases: "my chapter", "my students", "the induction date", "the roster".
**Mental model:** "I'm responsible for a cohort of students. Help me run the program."
**Frustrations:**
- Roster sync delays between systems
- Lack of bulk operations
- Unclear program-calendar communication
- Students contacting them about issues the advisor can't directly fix

**Motivations:**
- Successful chapter (induction count, engagement)
- Low admin overhead
- Clear program-of-record information they can pass to students

**HubSpot retrieval query template:**
```
Object: tickets
Filter: hs_ticket_category contains ('Advisor', 'Admin', 'Roster', 'Chapter')
Filter: createdate > now - 12 months
Join contact: advisor_chapter_object_id IS NOT NULL
Limit: 30
```

> Note: advisor ticket categories are not as cleanly enumerated as member categories. Inspect actual `hs_ticket_category` values returned and refine. Cross-reference contact join (advisor_chapter_object_id NOT NULL) is the cleaner filter than category.

**Cross-cutting attributes that may matter:** chapter (always — advisors ARE the chapter), state.
**Behavioral signal placeholder:** PostHog advisor-tool sessions, roster-export frequency. **v2.**
**What they typically LIKE:** Bulk-operation tooling, clear program-of-record calendars, named NSLS staff contacts.
**What they typically HATE:** Student-facing changes that surprise the advisor (they look uninformed to their chapter), removed/changed program steps without notice.
**What CONFUSES them:** Sync timing between NSLS systems. Which student issues they should triage vs escalate.

---

## Panel-convening logic

Given a proposed change on surface X:

1. From `design-validate-surfaces.md`, find the rows that list X as **P** or **O** audiences.
2. Convene only those personas. Skip personas whose audience doesn't appear on this surface.
3. Run retrieval for each. Drop personas where retrieval returned <3 quotes (and note the gap).
4. Aggregate predicted reactions. Score the **member-fit signal** factor in the rubric based on:
   - Mostly positive across convened personas → full points
   - Mixed → half
   - Mostly negative → zero

The panel is a tool for surfacing predictable objections — not a vote. A single P0-severity persona objection (e.g., breaks the disengaged-member refund path) is enough to flip the verdict, even if other personas were neutral.
