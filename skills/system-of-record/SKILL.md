---
name: system-of-record
description: >-
  The unified data model made conversational. 9 domains, 95 tables,
  Person.id as universal anchor. Knows both the target schema AND the
  current fragmented reality across all connected systems. Answers
  "where does X live?" and "what's the gap?" Guides /data-intel
  queries and /data-model-discovery exploration. Use when anyone asks
  about data architecture, where a field belongs, how systems relate,
  what the canonical model says, identity resolution, schema gaps, or
  the long-term direction of NSLS data infrastructure.
  Trigger phrases: system of record, SoR, where does this data live,
  what's the schema, unified model, Person.id, canonical, data
  architecture, how do these systems connect, what's the gap, domain
  model, which domain, identity anchor.
---

# /system-of-record — The Map

## Purpose

Society is the concept at the center — the member's experience. Every other system orbits it, each holding a fragment of the truth: HubSpot has 6.9M contacts with enrollment dates and IPEDS numbers. PostHog has behavioral events and AI coach transcripts. The Society DB has track completion and assessment results. Customer.io has campaign engagement. FOL handles 113K monthly users through enrollment. None of them agree on what a "person" is or how to identify one.

The System of Record is the canonical schema that defines what the data SHOULD look like when all systems agree. This skill makes that schema conversational — so when anyone asks "where does graduation data live?" or "how do I join a member's HubSpot enrollment with their Society journey?", the answer comes from the unified model, not from guessing which system to check first.

This skill does not query live data. It is the map that every other skill navigates by.

## The Nine Domains

| Domain | Tables | Key Concept | What It Unifies |
|--------|--------|-------------|-----------------|
| **People & Auth** | 13 | `Person.id` — the universal identity anchor | HubSpot contacts + Society Users + PostHog persons + Customer.io profiles. One person, one ID, multiple emails over a lifetime. |
| **Groups** | 17 | Chapters, teams, masterminds in a strict tree hierarchy (`GroupClosure`) | HubSpot companies (flat) + Society tracks (no group concept). Adds hierarchy, roles, permissions, certifications. |
| **Events** | 9 | Induction ceremonies, leadership events, speaker sessions, attendance | PostHog product events (behavioral) + Feather event records (not yet connected). The SoR distinguishes product analytics from real-world events. |
| **Achievements** | 11 | Certifications with a criteria engine (`all`, `any`, `n_of_m` composite logic) | HubSpot induction milestones (dates only) + Society CompletedTrack (binary). The SoR adds granular criteria evaluation. |
| **Member Context** | 14 | Journals, reflections, goals, coaching transcripts, pgvector embeddings | PostHog ai_generation events (chat buried in event properties) + Society Responses (answers only). The SoR makes coaching a first-class domain with embeddings for semantic matching. |
| **Notifications** | 5 | Notification rules engine, customer.io integration, delivery tracking | Customer.io campaigns + n8n automations + Slack alerts. The SoR unifies notification logic across channels. |
| **Payments** | 12 | Authorize.net (membership) + Stripe (subscriptions/ticketing), guardian payments | HubSpot deal amounts + Stripe IDs. The SoR models the full payment lifecycle including guardian-pays-for-student. |
| **Matching** | 9 | Mastermind group formation, composite scoring (structured 0.6 / semantic 0.4) | **NOTHING** — this domain has zero data in any connected system. It's entirely future capability. |
| **Invitation Campaigns** | ~10 | The full invitation pipeline: import → dedup → suppress → validate → promote → deliver | HubSpot deals (sales side) + Activepieces (orchestration). The SoR makes the pipeline explicit with staging tables and engagement tracking. |

## The Identity Problem (and Solution)

### Current State: Five Systems, Five IDs

| System | Identity Key | Type | Coverage |
|--------|-------------|------|----------|
| Society | `User.id` | cuid | Society users only |
| HubSpot | `hs_object_id` | integer | 6.9M contacts |
| PostHog | `$distinct_id` | string (usually email) | All tracked visitors |
| Feather | `nsls_uid` | integer | Legacy members |
| Customer.io | `cio_id` | string | Messaged members |

**Current join key: email.** It works but breaks when people change emails, have multiple emails, or when systems store emails differently.

### Target State: Person.id

The SoR defines `Person.id` (UUID) as the universal anchor. Every system resolves to it:

```
Person.id (UUID)
├── PersonEmail (multiple emails per person, with status history)
├── MemberProfile.auth_user_id → Society User.id
├── HubSpot hs_object_id (via future sync)
├── PostHog $distinct_id (via $identify with person_id)
├── Customer.io person_id (already designed for UUID)
└── Feather nsls_uid (via InviteeProfile.third_party_data)
```

**When to reference this:** Any time `/data-intel` is joining data across systems via email, note that this is a temporary bridge. The canonical path is `Person.id` resolution.

## Current Reality: Where Each Domain's Data Actually Lives

### People & Auth

| SoR Concept | Current Location | Gap |
|-------------|-----------------|-----|
| Person identity | HubSpot (richest), Society (journey), PostHog (behavioral) | Three different IDs, no unified anchor |
| Email history | HubSpot `email` field (single), Society `User.email` (single) | SoR supports multiple emails per person with status tracking. Nobody does this today. |
| Physical address | HubSpot `mailing_address_*` properties | Not in Society or PostHog |
| Status lifecycle | HubSpot `lifecyclestage` + `hs_v2_date_entered_*` timestamps | HubSpot tracks transitions. Society doesn't. SoR adds immutable audit log. |
| Academic profile | HubSpot `major`, `gpa`, `school_year` (from Feather) | Society doesn't have these. SoR puts them on InviteeProfile. |
| Import pipeline | HubSpot (implicit — contacts appear) + Activepieces | SoR makes it explicit: ImportBatch → ImportRow → dedup → freshness → validate → promote to Person |

### Groups

| SoR Concept | Current Location | Gap |
|-------------|-----------------|-----|
| Chapters | HubSpot companies (type=College/University) | Flat records. No hierarchy. SoR adds GroupClosure tree. |
| Chapter health | HubSpot `chapter___member_count`, `leadership_hours`, `years_active` | Exists but not structured. SoR adds membership rules and evaluation. |
| Mastermind groups | **NOWHERE** | Entirely future. SoR's Matching domain handles formation. |
| Roles & permissions | HubSpot `nsls_role` (semicolon-separated string) | No permission model. SoR adds GroupRole with `is_admin` + permissions jsonb. |
| School identifier | HubSpot `unitid` (IPEDS) on companies | SoR uses `Group.school_identifier`. Same data, canonical location. |

### Achievements

| SoR Concept | Current Location | Gap |
|-------------|-----------------|-----|
| Track completion | Society `CompletedTrack` | Binary complete/incomplete. SoR adds criteria engine. |
| Induction milestones | HubSpot `nsls_core_steps_completed`, `nsls_core_snt3_completed` | Dates only. SoR adds the criteria that define WHAT completion means. |
| Criteria engine | **NOWHERE** | The `all/any/n_of_m` composite logic doesn't exist in any system. |
| Personality assessment | Society `AssessmentResult` | Exists. SoR would reference this as an achievement criterion. |

### Member Context

| SoR Concept | Current Location | Gap |
|-------------|-----------------|-----|
| Chat transcripts | PostHog `ai_generation` events (`prompt_messages` field) | Buried in event properties. Not queryable as conversations. SoR makes them first-class with `CoachingSession` + `CoachingSessionMessage`. |
| Responses | Society `Response` table | Exists. SoR's `JournalEntry` is similar but adds reflection prompts and embeddings. |
| Goals | **NOWHERE** | SoR adds `Goal` with SMART/OKR frameworks and status tracking. |
| Embeddings | **NOWHERE** | SoR uses pgvector for semantic search across all member content. |

### Payments

| SoR Concept | Current Location | Gap |
|-------------|-----------------|-----|
| Stripe data | HubSpot `df_stripe_customer_id` / `df_stripe_account_id` | IDs only. SoR models full transaction lifecycle. |
| Deal pipeline | HubSpot deals (340K across 27 pipelines) | Sales-side. SoR models member-side payments. |
| Guardian payments | **NOWHERE** | SoR adds `PaymentObligation.payer_person_id` for parent-pays-for-student. |

### Matching

**Entirely future.** No data in any connected system. The SoR defines mastermind group formation with composite scoring (structured attributes 0.6 + semantic similarity via pgvector 0.4). This is the domain that will differentiate NSLS from every other honor society.

## How Other Skills Should Use This

### /data-intel
When assembling cross-platform queries, check this skill first to understand:
- What the canonical field name is (SoR's `Person.first_name` vs HubSpot's `firstname` vs PostHog's `person.properties.name`)
- Whether the data you're joining is actually the same thing (HubSpot `school` vs `nsls_chapter_name` vs SoR's `Group.school_name`)
- What you're missing — if the SoR says a domain has 11 tables and you're querying 2 fields, there's more to find

### /data-model-discovery
When exploring a new data source, use this skill to:
- Map discovered properties to SoR domains ("this system has payment records → that's the Payments domain")
- Identify which SoR gaps the new source fills
- Know what join keys to look for (`Person.id` when available, email as fallback)

### /investigation
When finding ground truth, reference the SoR to understand:
- What the canonical state SHOULD be (not just what it IS in one system)
- Whether a discrepancy between systems is a bug or a known gap
- Where to check for the authoritative record

### /hubspot, /posthog, and other platform skills
Each platform skill covers one fragment. This skill covers the whole picture. When a platform skill can't answer a question, this skill knows which OTHER platform has the answer.

## Advisory Concerns (From the SoR Repo)

34 concerns raised during architecture review. 9 resolved, 25 open.

**Resolved blockers:** FERPA compliance, criteria engine architecture, right to erasure, RLS policy design, academic term modeling.

**Open P2 (before launch):** Guardian enrollment abuse, SIM-swap attack vectors, JHL security, audit log strategy, funnel reporting, email domain validation, webhook reconciliation, waitlist race conditions, university SSO, connection pooling.

**Open P3:** Freshness scoring algorithm, multi-channel import, A/B testing framework, email validation service, list hygiene automation, transfer students, chapter health scoring, event speakers/sessions, refund policy, post-event surveys, portfolio/LinkedIn integration, scale targets, build sequence, PersonEmail.inactive definition.

These concerns are active constraints on when and how the SoR can go live. Reference them when anyone proposes a feature that depends on SoR capabilities.

## The Long-Term Arc

```
TODAY:          Email-joined fragments across 7+ systems
                /data-intel stitches them together at query time

PHASE 1:        SoR schema exists as documentation (this skill)
                /data-intel references it for canonical field names
                /data-model-discovery maps new sources against it

PHASE 2:        SoR gets an API layer
                /system-of-record becomes a Layer 2 platform skill
                /data-intel queries SoR directly for unified data
                Platform skills become supplementary for data SoR doesn't yet have

PHASE 3:        All person data resolves via Person.id
                Achievement tracking comes from the SoR criteria engine
                Group hierarchy comes from GroupClosure
                Email-based joins become fallbacks, not primary paths
                HubSpot, PostHog, Society feed INTO the SoR
                /data-intel queries ONE source for the unified picture
```

We are at the boundary between today and Phase 1. The schema exists. The skill makes it conversational. The fragmented reality is mapped. The path forward is clear.
