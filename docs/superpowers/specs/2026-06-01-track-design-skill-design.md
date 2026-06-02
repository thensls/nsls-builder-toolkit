# Track Design Skill — Design Spec

**Date:** 2026-06-01
**Author:** Kevin Prentiss (w/ Claude)
**Status:** Approved design → ready for implementation plan
**Home:** `nsls-builder-toolkit` plugin (`~/nsls-skills/nsls-builder-toolkit/skills/track-design/`)

---

## Purpose

Let anyone in the NSLS builders program take a raw idea — *"I want users to learn
how to use AI effectively"* — and walk all the way to a **great Society track**:
a polished design doc a human can review, and an **importable JSON object** that
loads directly into the Society app (ignite-next).

The skill encodes the institutional knowledge that currently lives in three docs
(the track-ontology "grammar," the Clarity Track, and the Self-Leadership Track)
so a builder without product or instructional-design experience can still produce
a track that members love — not just a structurally valid one.

## Success criteria

1. A builder starting from one sentence ends with **two artifacts**: a Student
   Experience Documentation Google Doc and a schema-valid ignite-next track JSON.
2. The JSON imports cleanly via `pnpm db:seed` with no manual repair.
3. The track reflects the ontology's quality bars (clear value promise, single-theme
   steps, 4-part step arcs, personalization tokens that never precede their data,
   AI-generates / student-judges framing) — verified, not assumed.
4. The flow surfaces member-experience risks (drop-off, tone mismatch, fatigue,
   missing off-ramps) *before* the track is authored, via a member focus group and
   a UX validation pass.

## Non-goals

- Not a track *editor* for live tracks (that's the admin UI). It produces a new
  track artifact for import.
- Not a replacement for real user testing — the focus group is simulated personas.
- Does not itself run `pnpm db:seed` or touch a production DB. It emits the JSON and
  a handoff note; loading is an explicit engineering step.

---

## Decisions (locked during brainstorming)

| Decision | Choice |
|---|---|
| JSON target | **Directly importable ignite-next JSON** (matches `src/data/tracks-export.json` + `prisma/seed.ts` upsert-by-`id` contract) |
| Focus-group panel | **New Society member/student personas**, **bundled inside** the skill (`references/member-personas.md`) |
| Home / audience | **Org `nsls-builder-toolkit` plugin** (PR-gated, auto-updates for everyone) |
| Pipeline shape | **Full guided pipeline, gated but skippable** (experienced builders can skip a phase explicitly) |
| Validator | **Ship a JSON validator script** (required fields, types, unique ids/slugs, token-ordering rule) |

---

## Architecture: a 7-phase pipeline

The spine is the track-ontology doc's own 6-step "Designing a New Track" framework,
wrapped with **research** up front and **validation + dual output** at the end.
Each phase is a gate with an explicit, skippable checkpoint.

### Phase 0 · Frame the idea
- Capture the raw idea verbatim.
- Pin the **value promise**: *"When a student finishes this track, they will have
  ______ that they didn't have before."* **Hard gate** — a vague value promise
  produces a vague track; do not proceed without a crisp one.
- Classify: **artifact-track** (produces a thing, like Clarity → career statement)
  vs **practice-track** (activates a running loop, like Self-Leadership).
- Prerequisites: does it need Clarity profile data? Which existing profile tokens
  can it assume already exist?
- Audience registers (reuse the Self-Leadership register model: Student / Early Pro
  / Established / Transitional / Returning) — decide whether the track is
  register-aware.
- **Output:** a one-page frame (value promise, type, prereqs, registers).

### Phase 1 · Research
- Domain best-practices for the topic via `web-research` (e.g. "how adults learn to
  use AI effectively" → real pedagogy, mental models, common failure modes).
- Relevant NSLS knowledge if any.
- Pattern study of the two reference tracks: which proven patterns apply here —
  generation-then-select, private self-assessment, register system, the gap-is-gold
  framing, celebration arcs, derived (not asked) signals.
- **Output:** a research brief that names the patterns this track will borrow.

### Phase 2 · Brainstorm the track shape
Walk the ontology framework:
- What must the AI coach know to deliver the value promise? → the data to collect.
- Cluster that data into **Steps** (one clear theme each — "what was that step about?"
  answerable in one sentence).
- **Sequence** intentionally: simpler/factual before complex/reflective; collect a
  field before any substep references its token.
- Design each step's **4-part arc**: Orient (SAY) → Collect/Explore (COLLECT) →
  Synthesize (GENERATE/CHAT) → Celebrate (SAY/celebration).
- **Output:** a track outline — ordered steps, each with a substep skeleton, the
  profile fields/tokens it produces, and where it reuses a proven pattern.

### Phase 3 · Member focus group + iterate
- Run a panel of **Society member/student personas** (the 5 registers, plus 1–2
  edge personas: the content-drifter, the over-eager completionist) against the
  Phase 2 outline.
- Personas react with authentic friction: drop-off risk, tone/register mismatch,
  "this step is doing too much," cognitive fatigue, missing off-ramps (cf. the Pull
  check), where AI-generated content would feel generic vs. recognized.
- **Iterate the outline** until the panel surfaces nothing load-bearing.
- **Output:** revised outline + a short "what members told us / what we changed" log.

### Phase 4 · UX / design validation
- Invoke `ux-audit`'s Design Validation Layer on the flow:
  - Predicted SUS estimate.
  - Laws of UX, especially cognitive load / fatigue (the ontology's "more than 10
    questions without a break" rule), recognition-over-recall, peak-end (celebration).
  - Society brand alignment on copy + celebration screens.
  - Member-fit.
- **Output:** validation readout + any required outline fixes.

### Phase 5 · Author + emit
Expand every substep to full content, then produce **two artifacts from one model**:
- Prompts with personalization **tokens**; CHAT **system prompts** (the single most
  important content for any chat substep); GENERATE configs (`aiPromptConfig`,
  `multiselectPrompt`, `multiselectSchema`); celebration screens; option sets.
- **Artifact A — Google Doc** in the "Student Experience Documentation" format
  (Track at a Glance table, per-step walkthrough, "Why this matters" callouts,
  design-notes appendix) via `gdoc-build`. For human/stakeholder review.
- **Artifact B — importable ignite-next JSON**: a JSON array of
  `track → steps[] → substeps[]` with stable `id`s and only author-provided fields.

### Phase 6 · Validate + handoff
- Run the **JSON validator** (Phase-5 output → schema check): required fields
  present (`id`/`title`/`prompt`/`type`); valid `type`/`fieldType` vocab; unique
  ids and per-parent slugs; no auto-managed fields leaked (`order`, `version`,
  `isDraft`, `trackId`/`stepId`, timestamps); and the **token-ordering rule** — every
  `{token}` references a field collected in an earlier substep, never a later one.
- **Output:** validation report + handoff note: write into
  `ignite-next/src/data/tracks-export.json`, run `pnpm db:seed`, what's auto-generated.

---

## Components & boundaries

```
skills/track-design/
├── SKILL.md                      # 7-phase pipeline, gates, skip rules, sub-skill orchestration
├── references/
│   ├── track-ontology.md         # the grammar + the 6-step framework (distilled from track-ontology.docx)
│   ├── track-json-schema.md      # exact ignite-next importable schema (Prisma models, field-by-field
│   │                             #   author-vs-auto, value vocab, options shapes, seed/upsert mechanics)
│   ├── member-personas.md        # the focus-group panel (5 registers + edge personas)
│   └── examples/
│       ├── clarity-track.md       # gold-standard artifact-track
│       └── self-leadership-track.md  # gold-standard practice-track
└── scripts/
    └── validate-track-json.mjs   # node validator: schema + token-ordering rule; exits non-zero on failure
```

- **SKILL.md** orchestrates; it does not embed the schema or ontology inline (those
  live in `references/` so they're versioned and skimmable).
- **`web-research`, `ux-audit`, `gdoc-build`** are invoked, not reimplemented.
- **Member focus group** runs inline from `member-personas.md` (no separate skill).
- **Validator** is a standalone script so it's runnable and testable independent of
  the model's reasoning.

## Data flow

```
raw idea
  → Phase 0 frame (value promise, type, prereqs, registers)
  → Phase 1 research brief (+ borrowed patterns)
  → Phase 2 track outline (steps, substep skeleton, tokens produced)
  → Phase 3 focus-group-revised outline
  → Phase 4 UX-validated outline
  → Phase 5 authored content → { Google Doc, track JSON }
  → Phase 6 validated JSON + handoff note
```

State between phases is held in a working doc (the skill's scratchpad); the builder
can stop and resume.

## Error handling & edge cases

- **No crisp value promise (Phase 0):** hard stop with guidance, don't proceed.
- **Token references uncollected data:** validator fails with the specific token +
  the substep that should have collected it.
- **Skipped phase:** allowed only on explicit builder request; the skill logs the
  skip in the handoff note so reviewers know what wasn't validated (per the
  "skill steps must heartbeat, never skip silently" rule).
- **Builder lacks the ignite-next repo:** skill still produces both artifacts; the
  handoff note explains the load step is done by someone with repo access.
- **GENERATE/CHAT content quality:** Phase 5 enforces the ontology principles
  (AI generates / student judges; inject profile data explicitly into system prompts).

## Testing

- Validator unit-tested against: a known-good track (round-trip a slice of
  `tracks-export.json`), a track with a leaked `order` field, a duplicate slug, and
  a forward-token reference — each must fail with a clear message.
- End-to-end smoke: run the pipeline on the example idea ("learn to use AI
  effectively") and confirm the emitted JSON passes the validator and the doc renders.

## Open questions / deferred

- Whether to later extract the member focus group into a standalone reusable
  `member-focus-group` skill (decided: bundle for now; revisit if other Society
  features need it).
- Optional future: a direct `tracks.create` tRPC path for one-record authoring
  (out of scope; bulk JSON + seed is the supported import path today).
