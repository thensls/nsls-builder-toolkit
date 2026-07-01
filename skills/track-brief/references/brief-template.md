# The brief document — one Google Doc, two parts

track-brief produces **one** Society-branded Google Doc (via `gdoc-build`) with
two parts. Part 1 is the human/backlog-facing brief; Part 2 is the build spec
`track-design` reads. One doc, one `brief_doc_url`, one source of truth. Build it
with `gdoc-build` (Society branding) — real headings and tables, not markdown.

---

## Part 1 — Creative Content Brief (the backlog artifact)

Readable by anyone; this is what the Studio card links to. Sections:

1. **Working title** + one-line promise.
2. **Audience** — who it's for, and which member level(s): Honor / Associate /
   Impact.
3. **Benefit to the audience** — why *they* care; the felt payoff (this line also
   becomes the `benefit` field on the backlog card).
4. **Starting place** — where the member is when they begin (knowledge, mindset,
   situation).
5. **Ending place** — where they are after finishing (what's different for them).
6. **What they'll learn** — the substantive content.
7. **Outcomes** — measurable, in the outcome→evidence style below.
8. **Prerequisites + sequencing** — foundational assumed, plus any explicit prior
   tracks.
9. **Why now** — the strategic/portfolio reason this idea earns development.

### The outcomes format (WGU outcome→evidence)

From the WGU BSMGT crosswalk (2026-06-23): each capability is a **measurable
competency** with an explicit **outcome → evidence** alignment. Use it so briefs
are assessable, not vibes — and partner-mappable (WGU, etc.). Each outcome is a
row:

| Competency (verb-led, measurable) | Evidence (the in-track artifact that proves it) | Alignment (capability / power-skill) — optional |
|---|---|---|
| "The member can articulate a target role and the path to it." | A saved career statement + a 3-step plan produced in-track. | WGU Five Power Skills / a Society capability |

Rules:
- **Verb-led and measurable** — "can articulate," "can produce," "can compare,"
  not "understands" or "feels more confident."
- **Evidence is an in-track artifact** — something the member actually makes or
  saves inside the track (a statement, a plan, a ranked list, a message), so it
  can be checked. If an outcome has no in-track artifact, it isn't measurable
  yet — fix the outcome or add the step that produces the evidence.
- This evidence column is what the focus-group rubric's **Value** dimension
  scores against, and what maps to WGU competencies.

---

## Part 2 — Track Template Brief (the build spec)

The bridge from idea to buildable. Part 1 is the *why/what*; this is *how it's
structured*. `track-design` consumes it as its Phase-0 input. Sections:

1. **Goals** — the track's objectives (derived from Part 1's outcomes).
2. **Where the member is** — entry state / assumed context (operationalizes
   "starting place").
3. **What information will be collected** — the inputs the track gathers (the
   fields / answers), in rough order. *This is the raw material the `value-moment`
   sub-skill reads.*
4. **What the member will learn** — the content delivered, mapped step-by-step to
   the collected info. One row per learning beat, e.g.:

   | Collected input | What we teach right after it |
   |---|---|
   | target role (§3) | how to read a real job posting for that role's must-haves |
   | current resume bullets (§3) | rewriting one bullet into accomplishment form |
5. **Value moments** — where personalized insight nuggets fire. **Produced by the
   `value-moment` sub-skill** — this section is literally its output (the ranked,
   grounded candidates with example outputs). Each is tied to data collected by
   that point.
6. **Outcome → evidence map** — which step produces the evidence for each outcome
   in Part 1.
7. **Sequencing + level** — prerequisites, member level(s).
8. **Track type + assumed context** — the metadata `track-design` needs at its
   Phase 0, so the handoff doesn't force a re-interview:
   - **Track type:** `artifact-track` (produces a tangible output the member
     keeps — a plan, a profile, a document) or `practice-track` (builds a habit
     or self-knowledge). This drives `track-design`'s step structure, so decide
     it here.
   - **Assumed profile tokens:** from the prerequisites in §7, list the profile
     fields a completed prerequisite track already produced that this track may
     assume exist (e.g. Clarity → a saved target role). These become
     `track-design`'s `--assume…` validator arguments. If none, say "none —
     starts from scratch."

---

## How the two parts connect

- Part 1 §7 (Outcomes) → Part 2 §1 (Goals) and §6 (Outcome→evidence map).
- Part 1 §4 (Starting place) → Part 2 §2 (Where the member is).
- Part 2 §3 (info collected) is the input to `value-moment`, whose output fills
  Part 2 §5.

Keep them consistent — if you change an outcome in Part 1, update the goal and the
evidence-map row in Part 2.
