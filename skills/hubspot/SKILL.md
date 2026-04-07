---
name: hubspot
description: >-
  Query NSLS HubSpot CRM — 6.9M contacts, 340K deals, 357K tickets, 11K companies.
  Search members by chapter/school/status, look up enrollment history, check
  induction milestones, explore chapter health, investigate support tickets.
  NSLS syncs from Feather (legacy platform) with rich custom properties.
  Read-only access. Trigger phrases: hubspot, CRM, member lookup, chapter,
  enrollment, induction, IPEDS, school data, deal pipeline, ticket, support
  history, member status, who enrolled, chapter health.
---

# HubSpot CRM

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (searches, lookups, property discovery) — runs without friction. No approval needed. This is the skill's default and only current mode.
2. **Configuration** — N/A. Current access is read-only.
3. **Write** (create/update contacts, deals, companies) — requires reauthorization with write permissions. If the user requests a write operation, inform them that the current connection is read-only and they'd need to reconnect via `/mcp` with write permissions enabled.

If HubSpot tools aren't available, run `/connect` first. For cross-system intelligence that combines HubSpot with PostHog, Airtable, Slack, and more, use `/data-intel`.

## Purpose

This skill makes NSLS's 6.9M-contact CRM accessible through conversation — not just running searches, but knowing which properties to query, what the NSLS-specific fields mean, and how to navigate a CRM that was built over years with Feather sync, Salesforce migration artifacts, and 50+ per-state school dropdowns. If you need to look up a member, understand a chapter, trace an enrollment, or investigate a support ticket — this is where you start.

## NSLS HubSpot Landscape

**Account:** 5345251 | **UI:** app.hubspot.com | **Auth:** Red (rakasha@nsls.org), owner ID 78840157

| Object | Count | What It Represents |
|--------|-------|-------------------|
| `contacts` | **6.9M** | NSLS members, prospects, advisors, parents, referees |
| `companies` | **11.1K** (3.6K schools) | Schools/chapters + corporate partners |
| `deals` | **340K** | Chapter sales pipeline — "{School} - {Type} - {Semester}" |
| `tickets` | **357K** | Customer support — fee assistance, induction kits, enrollment questions |

**How NSLS uses HubSpot:**
- **Member CRM** — every NSLS member synced from Feather (legacy Drupal platform) with enrollment dates, induction milestones, academic data
- **Chapter management** — schools as companies, chapter health metrics, advisor contacts
- **Enrollment pipeline** — deals track chapter sales (PD, NCO, renewals) across 27 pipelines
- **Customer support** — 357K tickets covering fee questions, "is this a scam?" parent calls, graduation regalia, scholarship inquiries

## MCP Tools

All tools are prefixed with `mcp__claude_ai_HubSpot__`.

| Tool | What It Does |
|------|-------------|
| `get_user_details` | Current authenticated user info + available object types + tool availability |
| `get_properties` | Property definitions for an object type (data types, enum values) |
| `get_crm_objects` | Retrieve specific objects by ID with chosen properties |
| `search_crm_objects` | Search with filters, pagination, sorting. **REQUIRES `chatInsights` parameter.** |
| `search_properties` | Keyword search for property definitions (max 5 keywords per call) |
| `search_owners` | Search HubSpot owners by name/email or batch lookup by ID |

### CRITICAL: chatInsights Is Required

Every call to `search_crm_objects` MUST include the `chatInsights` parameter:

```json
{
  "objectType": "contacts",
  "filterGroups": [...],
  "properties": ["email", "nsls_member_status"],
  "chatInsights": {
    "userIntent": "Find members at Colorado State with completed core steps",
    "satisfaction": "NEUTRAL"
  }
}
```

`satisfaction` accepts: `"NEUTRAL"`, `"SATISFIED"`, `"DISSATISFIED"` — not numbers.

## NSLS Custom Properties on Contacts

### Identity & Membership
- `nsls_uid` / `nsls_uid_link` — Feather/Drupal user ID (e.g., "6258293", URL: members.nsls.org/user/{uid})
- `nsls_uuid` — UUID from Feather
- `nsls_member_status` — member status
- `nsls_role` — member/advisor/eboard (multi-select, semicolon-separated: `"advisor;eboard;member"`)
- `nsls_membership` — created from invitation or sync
- `member_account_status` — active: `"true"` / `"false"` (string, not boolean)
- `lifecyclestage` — HubSpot lifecycle (subscriber → lead → customer)
- `enrollment_start_date` — NSLS enrollment date

### Academic
- `school` — school name (also used for Facebook Ads integration)
- `nsls_chapter_name` — chapter name (e.g., "Colorado State University Global")
- `chapter_object_id` — HubSpot custom Chapter object ID (NOT a company ID)
- `year_in_school` / `school_year` — year in school
- `major` — (Feather: field_account_major)
- `gpa` — (Feather: field_account_gpa)
- Per-state school dropdowns — 50+ properties like `ohio_oh_schools`, mostly empty

### Induction Milestones
- `nsls_core_steps_completed` — date all core induction steps completed
- `nsls_core_snt3_completed` — SNT 3 completion date
- `nsls_executive_better_world_project` — BWP completion date
- `induction_kit_fee` — IKF status
- `national_induction_ceremony_webinar_date` — ceremony date
- `enrolled_in_moodle` — LMS enrollment

### Enrollment Funnel
- `enrollment_abandonment_reason` — why they didn't complete enrollment
- `enrollment_abandonment_additional_info` — additional context

### Engagement
- `nps_nsls_experience` — NPS score on NSLS experience
- `no_longer_at_school` — left school flag
- `referee_school` — referral school name

### Financial
- `df_stripe_customer_id` / `df_stripe_account_id` — Stripe integration

## NSLS Custom Properties on Companies (Schools)

### School Identity
- `name`, `domain`, `type` ("College/University" for schools)
- `unitid` / `unitid_number_` — **IPEDS number** (~88% coverage across institutions)
- `peer_schools__self_selected_ipeds_data_` — peer schools from IPEDS
- `school_size`, `school_type__c` (classification), `school_length__c` (2yr/4yr)
- `private_or_public_institution`, `n4_year_private_or_public`
- `school_population__c` — total enrollment

### Chapter Data
- `chapter_id`, `chapter_create_date`, `chapter___creation_year`
- `nsls_chapter_status` — Active/Inactive
- `nsls_chapter_type` — Online/Hybrid/Live-Online/Part of Ntl Office
- `chapter___years_active_2` — years active (calculated)
- `chapter___member_count` — total members in chapter
- `chapter___leadership_hours` — total leadership hours
- `count_of_chapters` — schools can have multiple chapters
- `nsls_core_accepting_members` — currently accepting new members?
- `chapter_state` — state location

### Social & Web
- `nsls_twitter`, `nsls_instagram`, `nsls_facebook`, `nsls_linkedin`
- `university_s_nsls_website`, `nsls_chapter_logo`

## Deal Pipelines (27 total)

### Primary Pipelines

| Pipeline | What It Tracks |
|----------|---------------|
| **Program Development Chapter** | New chapter sales: Meeting Booked → Part 1 → Part 2 → Application → Invitation → Materials → Complete |
| **Non-Chapter Outreach** | School outreach: Meeting → Stakeholder → Decision → Commitment → Invitation → Complete |
| **Invitations** | Invitation cycles: Started → Consultation → Proposal → Accepted → Procurement → DB Upload → Complete |
| **Renewals** | Chapter renewals: Identified → Review → Consultation → Proposal → Agreement → Finalized |
| **Student PD Chapter** | SPD intern-driven chapter launches |

Other pipelines: Alumni Chapter, Add On Online Chapter, Ecommerce, NSLS Partnerships, Broadcast Speakers, Motivational Mondays, various recruitment pipelines, Partnership Opportunity, Foundation Donor, Articulation Agreement, plus 4 migrated from Salesforce.

**Deal naming pattern:** `{School Name} - {PD|NCO|PD Re-Sell} - {Semester} {Year}`

**Pipeline/stage IDs are UUIDs** — use `get_properties` on deals to resolve human-readable labels.

## Person Lookup & Investigation

### Search by email
```
search_crm_objects:
  objectType: "contacts"
  query: "user@example.com"
  properties: ["email", "firstname", "lastname", "nsls_member_status", "nsls_role", "nsls_chapter_name", "enrollment_start_date"]
```

### Search by chapter
```
search_crm_objects:
  objectType: "contacts"
  filterGroups: [{"filters": [
    {"propertyName": "nsls_chapter_name", "operator": "EQ", "value": "University of Maryland Global Campus"}
  ]}]
```

### Cross-reference with Society
Society's User model has `hubSpotId` (stored via `nsls.ts:100-101` from NSLS API sync). This maps to HubSpot's `hs_object_id`. The field exists but is **never read back** — currently a write-only bridge. Email is the most reliable cross-reference key.

### Advisor lookup
Advisors have multi-role: `nsls_role: "advisor;eboard;member"`. Many are chapter success reps managing multiple chapters with `@nsls.org` emails.

```
search_crm_objects:
  objectType: "contacts"
  filterGroups: [{"filters": [
    {"propertyName": "nsls_role", "operator": "EQ", "value": "advisor"}
  ]}]
```
Returns ~2,712 advisor contacts.

## Diagnostic Loop

When queries return unexpected results:

1. **0 results?** Check property name spelling. Use `search_properties` with keywords to find the right name. Property names use underscores and lowercase (e.g., `nsls_chapter_name` not `nslsChapterName`).
2. **Wrong data?** Check the filter operator. `EQ` is exact match. `CONTAINS_TOKEN` for partial matching. `HAS_PROPERTY` to check existence.
3. **Missing properties?** Many NSLS custom properties are sparse — not all 6.9M contacts have all fields populated. Check if the property exists with `HAS_PROPERTY` before filtering on its value.
4. **Need to discover properties?** Use `search_properties` with up to 5 keywords. Or call it with no keywords to get ALL properties for an object type (warning: very large output).
5. **Slow or timeout?** 6.9M contacts means unfiltered searches will fail. Always add filters. Limit results with `limit` parameter.
6. **Pipeline/stage IDs look like UUIDs?** Call `get_properties` on deals with `propertyNames: ["pipeline", "dealstage"]` to get the label → ID mapping.

## Output Guidelines

- **Read-only access.** Cannot create, update, or delete any records.
- **chatInsights always required** on `search_crm_objects` — every call, no exceptions.
- **PII awareness.** HubSpot contains names, emails, phone numbers, GPA, school information. Don't include PII in outputs shared outside the immediate team.
- **Scale awareness.** 6.9M contacts. Always filter. A query for "all contacts" will time out.
- **Cross-system analysis?** Use `/data-intel` which orchestrates queries across HubSpot + PostHog + other connected systems.
- **For leadership:** Lead with the insight ("12% of members at online chapters complete induction in under 2 weeks"), not the query.
- **For engineering:** Include the exact tool call parameters so they can reproduce.

## Gotchas & Trapdoors

- **`chatInsights` is REQUIRED** on `search_crm_objects`. Omitting it causes the call to fail.
- **`satisfaction` expects strings** — `"NEUTRAL"`, `"SATISFIED"`, `"DISSATISFIED"`. Not numbers.
- **Many custom properties are sparse.** Don't assume all 6.9M contacts have `major`, `gpa`, `enrollment_start_date`, etc. Check with `HAS_PROPERTY` first.
- **`member_account_status` is a string** — `"true"` / `"false"`, not a boolean.
- **Advisor contacts have semicolon-separated roles** — `"advisor;eboard;member"`. Filtering `nsls_role EQ "advisor"` works because HubSpot matches within multi-select values.
- **`chapter_object_id` is NOT a company ID.** It references a custom HubSpot Chapter object. Don't try to look it up as a company.
- **`unitid` (IPEDS) is on companies, NOT contacts.** To get a member's IPEDS data, look up their school in companies.
- **Per-state school dropdowns** (50+ properties like `ohio_oh_schools`) exist but are mostly empty. Use `school` or `nsls_chapter_name` instead.
- **Deal pipeline/stage IDs are UUIDs.** Human-readable labels require a `get_properties` call.
- **Feather sync artifacts.** Many property descriptions reference "Feather Internal Name" — this is the legacy Drupal platform. The data is real, the naming just reflects the migration history.
- **`current_former__c` is unreliable.** Description says "synced from Feather only when chapter is created, therefore this is not reliable."
- **HubSpot has Salesforce migration artifacts.** Some pipelines are prefixed "Salesforce -" and some properties have `__c` suffixes from the Salesforce migration.
