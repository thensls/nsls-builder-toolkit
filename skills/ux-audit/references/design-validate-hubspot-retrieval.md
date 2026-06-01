# Design Validation — HubSpot Retrieval Mechanics for Member Voice

The member-fit panel in `design-validate-personas.md` is grounded in **real member-written tickets** from HubSpot, not invented quotes. This file documents what retrieval works, what doesn't, and the exact query patterns per persona.

## Retrieval feasibility (confirmed)

| Capability | Status | Notes |
|---|---|---|
| `subject` searchable | ✅ Yes | Member-written ticket subject |
| `content` searchable | ✅ Yes | Member-written ticket body / free text |
| Filter by `hs_ticket_category` | ✅ Yes | ~180 enum values, hierarchical naming convention |
| Filter by `source_type` | ✅ Yes | EMAIL, PHONE, CHAT, FORM, Ignite, Social Media |
| Filter by `createdate` | ✅ Yes | Use for recency windows |
| Filter by `hs_pipeline` | ✅ Yes | Use to scope to support pipeline vs other |
| Join contact `nsls_chapter_name` | ✅ Yes | 98% fill |
| Join contact `lifecyclestage` | ✅ Yes | 19% fill |
| Join contact `state` | ✅ Yes | 17% fill |
| Join contact `internal___calculated_age__rounded_` | ✅ Yes | 16% fill |
| Filter by online/in-person modality | ❌ No | `preferred_modality` is empty in HubSpot — **v2 needs Airtable join** |
| Filter by device | ❌ Not from HubSpot | Device lives in PostHog (currently blocked) |
| Filter by source/UTM | ❌ Not from HubSpot | Lives in PostHog (currently blocked) |

## Noise exclusions (apply to every query)

Always exclude:

- `hs_ticket_category` containing `'Non Support/Junk'` — generic noise, not member voice
- `source_type = 'Ignite'` — partner system, not member-written
- `source_type = 'Social Media'` — social listening pipe, not direct member voice

These are not member-written tickets in the sense the validator cares about. Including them dilutes the quote pool.

## Query patterns per persona

Every persona has its own retrieval query. All queries follow the same shape; only the filter values change. Always retrieve `subject`, `content`, `createdate`, `hs_ticket_category`, `source_type` as the property set.

### Persona 1 — Cold prospect

Ticket-data retrieval is **partially applicable**. Cold prospects DO write tickets — but only when they're trying to evaluate legitimacy or cost before clicking anything. Use:

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
Filter: hs_ticket_category IN (
  'General Member Inquiry - Are you legit/Scam',
  'General Member Inquiry - How much is the NSLS',
  'General Member Inquiry - Nomination Questions'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage IN ('subscriber', NULL)
Limit: 30
```

**Alternative voice sources (if ticket pool is thin):** Marketing-site form submissions in HubSpot (`forms` object), chatbot transcripts if instrumented on `nsls.org`, replies to cold-email campaigns in Customer.io.

---

### Persona 2 — Invitee

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
Filter: hs_ticket_category IN (
  'General Member Inquiry - Am I a member',
  'General Member Inquiry - Duplicate Invite',
  'General Member Inquiry - Nomination Questions'
)
Filter: createdate > now - 12 months
Join contact: lifecyclestage = 'lead'
Limit: 30
```

**Alternative voice sources:** Replies to the invite email cadence in Customer.io. /enroll/start chatbot transcripts.

---

### Persona 3 — Active enrollee on mobile

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
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

**Device filter:** HubSpot does not carry device. Post-process by either (a) keyword scanning `content` for mobile indicators ("on my phone", "iPhone", "Android") or (b) waiting for PostHog unblock — **v2.**

---

### Persona 4 — Active enrollee on desktop

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
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

**Device filter:** Same caveat as Persona 3 — keyword scan or wait for PostHog. Desktop-specific friction is the harder slice; if device can't be inferred, treat the result set as a superset and label findings accordingly.

---

### Persona 5 — Stuck / abandoned enrollee

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
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

This is the highest-signal pool for payment-step proposals. Stuck enrollees write the most explicit tickets ("I was charged twice", "card declined but I see a charge").

---

### Persona 6 — Newly inducted member

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
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

The `date_entered_customer > now - 30 days` join is what isolates newly-inducted voice from disengaged voice. Without it, the same lifecycle stage covers years of inducted members.

---

### Persona 7 — Disengaged inducted member

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
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

The post-induction-regret signal lives in `Refund - FOL - Issued` AND `Am I a member` (forgot they joined).

---

### Persona 8 — Advisor / chapter leader

```
Tool: mcp__claude_ai_HubSpot__search_crm_objects
Object: tickets
Properties: subject, content, createdate, hs_ticket_category, source_type
Filter: hs_ticket_category CONTAINS ('Advisor') OR CONTAINS ('Admin') OR CONTAINS ('Roster') OR CONTAINS ('Chapter')
Filter: createdate > now - 12 months
Join contact: advisor_chapter_object_id IS NOT NULL
Limit: 30
```

Advisor categories are not as cleanly enumerated as member categories — the contact-join filter (`advisor_chapter_object_id NOT NULL`) is the cleaner cut. Inspect the actual `hs_ticket_category` values returned and refine on a second pass.

**Alternative voice sources:** Advisor-only email replies in Customer.io. Direct conversations with NSLS Coach team (logged in HubSpot notes).

---

## Cross-cutting filter mechanics

When the proposed change is segment-scoped (e.g., "this affects mobile users in mid-Atlantic states aged 18–22"), layer cross-cutting filters on top of the persona query:

```
+ Join contact: state IN ('NY', 'NJ', 'PA', 'DE', 'MD')      [17% fill — caveat]
+ Join contact: internal___calculated_age__rounded_ BETWEEN 18 AND 22   [16% fill — caveat]
```

**Caveat to print in the report when fill rate is low:**

> Geographic filter applies to only the 17% of contacts with `state` populated. Findings may not generalize to the full population. Age filter applies to 16% with `internal___calculated_age__rounded_` populated. Treat segment slices as directional, not representative.

---

## Retrieval honesty rules

These are not optional. Every Design Validation report must follow them.

1. **<3 quotes per persona → downweight in rubric.** If a query returns fewer than 3 relevant member quotes for a persona, that persona's member-fit signal contribution to the score must be halved (max 12.5/25 instead of 25, or zero if it's still ambiguous).

2. **State the gap explicitly in the report.** Print: "Limited member-voice signal for [persona] — [N] quotes found. Reaction inferred from broader ticket patterns, not direct evidence."

3. **Do not extrapolate from sparse data.** If retrieval returned 1 quote, do not generalize from it. Print the quote, label it as anecdotal, and downweight.

4. **Never fabricate quotes.** If the data isn't there, the report says "no quotes available" and the persona is excluded from the panel for that proposal.

5. **Date the retrieval.** Every member-fit panel section should print: "Retrieval window: [createdate range]. Pulled [date]." Member voice ages — what was true 18 months ago may not be true now.

6. **Show the n.** Every persona section: "Based on [N] tickets in retrieval window."

7. **Quote in context, not in isolation.** When pulling a quote, also state the ticket category and (if available) the lifecycle stage of the writer. A single quote without context is theater.
