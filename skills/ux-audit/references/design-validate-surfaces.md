# Design Validation — Surface × Audience Matrix

The Design Validation Layer is **scope-aware**: a learning from one product surface does not contaminate another unless the underlying principle is plausibly universal. Before a proposed change can be evaluated, the validator MUST locate it in the product × audience matrix below, then apply the transfer rules to decide which past evidence is admissible.

## The matrix

Rows = product surface. Columns = audience. Cells:

- **P** = primary cell (this audience is the dominant user of this surface)
- **O** = overlap / secondary (this audience uses the surface but isn't its main target)
- **—** = not applicable

| Surface \ Audience           | Cold prospect | Invitee | Active enrollee | Newly inducted | Engaged inducted | Disengaged inducted | Society user | Advisor |
|------------------------------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Enrollment funnel** (`/enroll/*`)     | — | O | **P** | — | — | — | — | — |
| **Invitee landing** (`/enroll/start/<code>`) | — | **P** | O | — | — | — | — | — |
| **Member dashboard**          | — | — | O | **P** | **P** | **P** | — | O |
| **Society app**               | — | — | — | O | O | O | **P** | — |
| **Marketing site** (nsls.org) | **P** | O | — | — | — | — | — | O |
| **Advisor tools**             | — | — | — | — | — | — | — | **P** |
| **Email lifecycle**           | O | **P** | **P** | **P** | **P** | **P** | O | O |

## Transfer rules — which past evidence can I bring in?

| Relationship | Transfer? | How to label in the report |
|---|---|---|
| Same surface, same audience (same cell) | **Yes — directly transferable** | "Validated on this surface for this audience." |
| Same surface, different audience | **Cautiously — caveat required** | "Validated on this surface for [other audience]; behavior may differ for [this audience] because [reason]." |
| Different surface, same audience | **Cautiously — caveat required** | "Validated for this audience on [other surface]; this surface has different cognitive load / decision pressure." |
| Different surface, different audience | **Do NOT transfer** UNLESS the principle is plausibly universal | "No on-surface evidence. Principle is universal (WCAG, Fitts, Hick, touch-target sizing) so transfer is admissible." |

### What counts as "plausibly universal"
Only these qualify without per-surface re-validation:

- **WCAG 2.1 AA** — contrast, focus order, labels, alt text, target size 2.5.5
- **Cognitive-load** principles — Miller's 7±2, chunking
- **Hick's Law** — choice paralysis at decision points
- **Fitts's Law** — target size + distance
- **Touch-target sizing** — 44×44pt minimum on mobile (also WCAG 2.5.5)

Anything else — including "social proof works", "urgency works", "trust badges work" — must be re-validated per surface. Generic ecommerce patterns have already been proven NOT to transfer onto the enrollment funnel (see `design-validate-encoded-principles.md`).

## Canonical past-test source per surface (v1)

| Surface | Canonical doc | Status |
|---|---|---|
| Enrollment funnel | [Experiment Learnings — Enrollment Funnel](https://nsls.atlassian.net/wiki/spaces/NSLS/pages/3602579458) (Confluence 3602579458) | **Encoded** in `design-validate-encoded-principles.md` |
| Invitee landing | Same doc (per Julia: "could apply to invitee group, but def for enrollment tests") | **Partial** — apply enrollment principles with caveat |
| Member dashboard | — | No canonical doc — net-new bet |
| Society app | — | No canonical doc — net-new bet |
| Marketing site | — | No canonical doc — net-new bet |
| Advisor tools | — | No canonical doc — net-new bet |
| Email lifecycle | — | No canonical doc — net-new bet |

When a proposed change lands on a surface with no canonical doc, the past-test alignment factor in the confidence rubric returns the neutral score (17.5/35). Do not fabricate prior evidence.

## Cross-cutting segment attributes

These are **filter parameters**, not personas. Any persona panel can be sliced by them. They are inputs to HubSpot / PostHog queries — not separate seats at the table.

| Attribute | Source | Fill rate | Use |
|---|---|---|---|
| `chapter` | HubSpot `nsls_chapter_name` | 98% | Slice by chapter for chapter-level health checks |
| `lifecycle stage` | HubSpot `lifecyclestage` | 19% (`customer` = inducted) | Distinguish enrollee vs inducted vs disengaged |
| `age band` | HubSpot `internal___calculated_age__rounded_` | 16% | Age-based UX hypotheses (mobile literacy, etc.) |
| `state` | HubSpot `state` | 17% | Geographic / regional cohorts |
| `online vs in-person modality` | NOT in HubSpot — `preferred_modality` empty | — | **v2 deferred** — needs Airtable join |
| `device` | PostHog | — | **v2 deferred** — PostHog MCP currently blocked; unblock via /connect or Hex bridge |
| `source / UTM` | PostHog | — | **v2 deferred** — same blocker |
| `ticket category` | HubSpot `hs_ticket_category` | ~100% on tickets | Filter member-voice retrieval by support theme |

When fill rate is low (≤20%), interpret findings cautiously and state the fill rate in the report. Do not project a 16%-fill attribute onto the full member base.

## When in doubt

Ask: "On which cell of the matrix does this change live, and does my evidence come from that same cell?" If the answer is no on both, the verdict is closer to **net-new bet** than to a confident projection.
