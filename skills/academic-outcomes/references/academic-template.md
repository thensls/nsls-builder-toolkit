# The academic-outcomes template (partner-neutral)

Extracted from the WGU BSMGT crosswalk (`~/build_society_wgu.py`, 2026-06-23) with
the partner-specific crosswalk removed. This is the anatomy of the doc and how to
write each part so a college or accreditation body reads it as authoritative.

## Why this format lands with academia
Accreditors and universities verify claims. The competency → evidence structure
is exactly what they look for: a measurable capability paired with the concrete
artifact that proves it. The document's authority comes from being **true and
checkable**, not from adjectives. Inflate one row and the whole document loses
standing.

## Document anatomy

**Title + subtitle** — Society-branded (e.g. "Society by NSLS · Academic Learner
Outcomes" / "Learning Outcomes · <month year>").

**About this package** — one paragraph. Introduce Society anchored to NSLS (the
name partners recognize): "The National Society of Leadership and Success (NSLS)
has built Society, a new learning and community platform…" State that what
follows describes the learning experiences and what each develops. Where a
capability is still in development, it is described as designed and its status
noted.

**How learning works on Society** — the cross-cutting tenets, as bullets. These
are stable; reuse them:
- **Cohort, not solo.** Members work alongside a group pursuing their own goals, and help one another along the way.
- **Learner-led, AI-assisted.** The AI offers questions and summaries; the member brings the critical thinking that refines, critiques, and lands the final output. The judgment is always the member's.
- **Real artifacts, not exercises.** Each step produces something the member keeps and uses.
- **Coach-aware.** Everything produced enters the AI coach's context, so later guidance is specific to this member.
- **Revisable.** Any step can be repeated, so outputs keep reflecting who the member actually is as they grow or change.
- **Gap-closing.** The work is aimed at the distance between where the member is and where they want to go.

**At a glance** (bundle only) — a table: each track/capability → the internal
capability it develops → status. (The `partner-crosswalk` skill adds partner
columns here; the standalone doc does not.)

**Sections** — `Learning Experiences` (tracks) then `Platform Capabilities`.

## Per-track anatomy (each item)

1. **Meta line** (italic) — `type · status · estimated effort · Develops <internal
   capability>`. Type = Track / leveled Track / Platform capability. Status = Live
   / Designed. Keep maps-to internal — no partner framework here.
2. **Description** — one or two sentences on what the experience is.
3. **Competencies table** — the heart of the doc (see below).
4. **How it works** — the mechanics: the generate-then-review pattern, the loop,
   the readiness gate, etc. Concrete, present-tense for live parts.
5. **Excluded by design** (optional) — what this track deliberately does not
   cover, and where that work lives instead. Signals intentional scope.
6. **Outputs** — the artifacts the member keeps, held in their profile.
7. **Status** (italic) — live vs. designed, with an honest note for unbuilt parts.

## Writing competencies (the part authors get wrong)

Each row: **Competency (verb-led, measurable) → Evidence the member produces (a
real in-track artifact, named to its step).**

Good — verb-led, measurable, evidence tied to a real step:

| Competency | Evidence the member produces |
|---|---|
| The member can determine a salary target from real cost inputs. | A monthly and annual income target computed from six cost-of-living inputs (collect: cost-inputs → salary-target). |
| The member can compose a career statement that synthesizes their profile. | A finalized career statement the member edits from an AI draft (generate: career-statement). |

Bad — and why:

| Bad competency | Why it fails | Fix |
|---|---|---|
| "Quantitative financial literacy applied to career planning" | Noun phrase, not a measurable capability; can't be assessed. | "The member can determine a salary target from real cost inputs." |
| "Understands career options" | "Understands" isn't observable. | "The member can select a profile-matched role from generated options." |
| "Integration of reflection into an actionable plan" (evidence: "the full artifact set, taken together") | Stretch competency with no single artifact — invented synthesis. | Tie to one real step, or cut it. |
| "Builds an employer-outreach plan" (for a designed-not-built step) | Claims evidence from a step that doesn't run. | Move to a "Planned enhancements" footnote, future-tense; never in the table. |

## Handling designed-not-built parts
A competency belongs in the table only if a member can produce its evidence
**today**. Designed-but-unbuilt capability goes in the `status` note or a
"Planned enhancements" line, clearly future-tense — never in Competencies or
Outputs. (This is the 2026-06-23 rule: design-tense + status footnotes.)

## Tone
No denigration of any external framework (matters once a `partner-crosswalk` is
layered on). Authoritative through accuracy, not adjectives. Present-tense for
live, design-tense for planned.
