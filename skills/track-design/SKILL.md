---
name: track-design
description: >-
  Use when a builder wants to turn a raw idea into a complete, importable
  Society app (ignite-next) learning track. Triggers: "design a track",
  "build a track", "new Society track", "author a track", "turn this idea
  into a track", "I want users to learn X on the Society app", "track JSON",
  "ignite-next track". For the Society (ignite-next) app ONLY — not for NSLS
  marketing pages, slides, Slack bots, or automations.
---

# Track Design

Design a complete, production-ready Society (ignite-next) app track — from a raw idea to two shippable artifacts:

1. **Student Experience Documentation** — a Google Doc formatted like the examples in `references/examples/`, giving the product and engineering teams a human-readable walk-through of every step.
2. **Importable ignite-next track JSON** — a directly loadable array that drops into `ignite-next/src/data/tracks-export.json` and seeds via `pnpm db:seed`.

**For the Society app only.** Do not use this skill for NSLS marketing pages, automations, Slack bots, or any non-ignite-next context.

---

## Quick Start

A track goes idea → 2 shippable artifacts through these phases:

**0 Frame** (lock value promise) → **1 Research** → **2 Brainstorm shape** → **3 Member focus group** → **4 UX validation** → **5 Author + emit** (Google Doc + importable JSON) → **6 Validate + handoff**

Each phase names the reference to open and the skill to invoke (see the Reference Index). Phases run in order; the running scratchpad is your resume point if a builder stops mid-pipeline.

---

## Operating Rules

- **Run phases in order.** A builder may skip a phase only on explicit request. When a phase is skipped, record it by name in the Phase 6 handoff note — never skip silently. (Heartbeat rule: "Skipped Phase 3 — builder confirmed existing research is sufficient.")
- **Read the reference before designing.** Each phase cites which `references/` file to open. Do it at that phase, not before. Never design from memory.
- **Keep a running scratchpad.** Maintain an evolving frame → outline → authored content block in the conversation. The builder may stop mid-pipeline; the scratchpad is the resume point.

---

## Red Flags — STOP

- "The value promise is close enough, I'll refine it while designing." → No. The Phase 0 gate is not met. Stay in Phase 0.
- "The builder is in a hurry, I'll skip the focus group / UX audit silently." → No. Skipping is allowed only on explicit request, and MUST be recorded by name in the Phase 6 handoff note.
- "I remember the schema / ontology, I don't need to open the reference." → No. Never design from memory. Open the cited reference at its phase.

Violating the letter of these rules violates their spirit.

---

## Phase 0 — Frame the Idea

**Purpose:** Lock the value promise and the structural classification before any design work begins.

**Read:** Open `references/track-ontology.md`. Study the Track/Step/Substep grammar, the SAY/COLLECT/CHAT/GENERATE action types, the profile token system, and the 6-step "Designing a New Track" framework.

**Work:**
1. Elicit or draft the value promise: *"When a student finishes this track, they will have ___ they didn't have before."* Make it concrete — a deliverable, a clarity, a capability, not a feeling.
2. Classify: artifact-track (produces a tangible output) or practice-track (builds a habit or self-knowledge). Reference the two examples in `references/examples/` for the difference.
3. Identify prerequisites. List any tracks that should run first. From that list, enumerate which profile tokens the track may assume already exist. This set becomes the `--assume` arguments for the Phase 6 validator. If Clarity is a prerequisite, note `--assume-clarity`.
4. Decide which registers this track targets: Student / Early Pro / Established / Transitional / Returning (or a subset).

**HARD GATE: Do not proceed to Phase 1 without a crisp, agreed value promise.** If the builder can't articulate it, keep working here.

**Output:** A one-page frame — value promise, track type, prerequisites + assumed tokens, target registers.

---

## Phase 1 — Research

**Purpose:** Ground the content design in domain best practices and borrow proven patterns from existing tracks.

**REQUIRED:** **Invoke:** Run the `web-research` skill for domain best-practices on the track's subject matter. Ask it to surface the top 5–8 concepts a practitioner would expect to encounter, and any known traps or misconceptions beginners face.

**Study:** Re-read `references/examples/clarity-track.md` and `references/examples/self-leadership-track.md`. Note which patterns are borrowable:
- Generation-then-select (surface options; member picks)
- Private self-assessment (COLLECT before any sharing)
- Register-aware prompting (token-conditional copy)
- Celebration arcs (what good looks like on the celebration screen)
- Derived-not-asked signals (infer tokens from answers; don't ask a field you can compute)

**Output:** A research brief — the 5–8 domain concepts the track must address, and a named list of patterns from the examples this track will borrow.

---

## Phase 2 — Brainstorm the Shape

**Purpose:** Turn the research brief into a step/substep outline with defined field/token outputs.

**Apply the ontology's 6-step framework** (from `references/track-ontology.md`):
1. What must the coach know to serve this member well? → list the profile fields this track collects.
2. Cluster those fields into single-theme steps. Each step should have one coherent purpose.
3. Sequence steps: factual before reflective; simpler before complex; always collect a field *before* any step that references its token.
4. Design each step's 4-part arc: **Orient** (SAY — frame what's coming) → **Collect/Explore** (COLLECT, CHAT, or GENERATE — the main action) → **Synthesize** (SAY or CHAT — make meaning) → **Celebrate** (SAY — acknowledge progress, named specifically).
5. Review the sequence for token-ordering: no step may reference a token that hasn't been collected yet.
6. Check register coverage: do any steps need register-conditional copy?

**Plan the value moments.** As you sequence, mark where the track can hand
personalized insight back to the member right after it collects the data for it
(a pull-along moment). These become GENERATE substeps authored via `value-moment`
in Phase 5 — note the trigger field + intent now; author the grounded prompt then.

**Output:** An ordered step/substep outline. For each step: single-sentence purpose, action types used, the profile fields/tokens it produces or consumes, and any planned value moments.

---

## Phase 3 — Member Focus Group + Iterate

**Purpose:** Pressure-test the outline against the member panel before writing a word of content.

**Read:** Open `references/member-personas.md`. Load the 5 registers + 2 edge personas and the facilitation protocol.

**Run the protocol** against the Phase 2 outline:
- For each persona: does the step sequence feel right? Is any step confusing, insulting, or skippable? Is anything missing that this member would expect?
- Pay special attention to the edge personas (anxious first-gen student, highly skeptical returning member).
- Iterate the outline until the panel surfaces nothing load-bearing — minor wording concerns are fine to log and defer.

**Output:** Revised step/substep outline + a short "what members said / what we changed" log (3–8 bullets). This log goes into the Phase 6 handoff note.

---

## Phase 4 — UX / Design Validation

**Purpose:** Catch cognitive load, brand, and experience problems before authoring full content.

**REQUIRED:** **Invoke:** Run the `ux-audit` skill's Design Validation Layer on the current outline. Pass the full step/substep sequence and the target registers.

**The validation covers:**
- Predicted SUS score — flag if steps feel like tasks rather than conversations
- Laws of UX: cognitive load and fatigue (is any step doing too much?), recognition-over-recall (are options surfaced or must the member invent answers?), peak-end rule (is the final experience worth remembering?), celebration quality
- Society brand alignment: copy tone, celebration screen language, visual metaphors if any
- Member-fit: does the experience respect where a first-gen student or skeptical returning member is at?

**Apply required fixes** to the outline before proceeding. Note what changed.

**Output:** Validation readout (predicted SUS, flagged issues) + a list of fixes applied.

---

## Phase 5 — Author + Emit

**Purpose:** Expand the outline to full content and emit both shippable artifacts.

**Read:** Open `references/track-json-schema.md`. Study the exact JSON shape, required vs. optional fields, the `id` stability rule, what must NOT be included (order/version/isDraft/trackId/stepId/timestamps), and how the file loads (`ignite-next/src/data/tracks-export.json` → `pnpm db:seed` upsert-by-id).

**Expand every substep to full content:**
- **SAY substeps:** Full copy with any register-conditional branches. Named, specific celebration language — never generic ("You just mapped your leadership values for the first time — that matters.").
- **COLLECT substeps:** Prompt text, field key, input type, placeholder text, validation rules (required? max length?). Use derived-not-asked where possible.
- **CHAT substeps:** Full system prompt — this is the most important content for any chat substep. Inject profile data explicitly using token syntax. The system prompt should tell the AI what the member has shared so far, what role to play, and what outcome to drive toward.
- **GENERATE substeps:** Full generation config — model, system prompt, output field, trigger condition. **For personalized insight nuggets (value moments), use the `value-moment` skill** — hand it the fields collected up to that point + the value promise; it returns ranked, grounded generate substeps (with example outputs) to author in. Don't hand-write value-moment prompts (you'd skip its faithfulness rule). Write the template to read the supplied profile block, not `{slug}` tokens (the generate path passes a profile object; see `value-moment`).
- **Option sets:** Every option label, value, and any downstream token it sets.

**Emit both artifacts from the same authoring pass:**

**(a) Student Experience Documentation Google Doc**

**REQUIRED:** Use the `gdoc-build` skill. Format it like the examples in `references/examples/`:
- **Track-at-a-Glance table** — name, type (artifact/practice), registers, prerequisites, step count, estimated time
- **Per-step walkthrough** — step name, purpose sentence, substep breakdown with full content
- **"Why this matters" callouts** — one per step, written for a skeptical member

**(b) Importable ignite-next track JSON**

Emit as a JSON array. Rules:
- Stable `id` fields (slug-based, agreed at authoring time, never change)
- Only author-provided fields — no `order`, `version`, `isDraft`, `trackId`, `stepId`, or timestamps
- Matches the schema in `references/track-json-schema.md` exactly

**(c) Preview it working in the demo**

Build the prototype so the authored track — including any value-moment generate
substeps — is **showable and actually runs**: answer the questions and the
generate steps stream real AI output from the proxy.

Run the `build-prototype.mjs` script from the sibling `track-prototype` skill
(resolve its path in your install; shown here as `<track-prototype>`):
```bash
node <track-prototype>/scripts/build-prototype.mjs track.json \
  --prereq <prereq-track.json>,<...> --out demo/ \
  --assets <ignite-next/public> \
  --proxy-url <proxy> --proxy-token <token>
# then serve the static build and open it:
cd demo && python3 -m http.server 8000   # → http://localhost:8000
```
`demo/` is a static site — it must be **served**, not opened as `file://` (the
module scripts + proxy fetch need an http origin). Any static server works.
- **`--assets <ignite-next/public>`** copies the app images/videos the track
  references (`/img/…`, `/video/…`) into the build so they resolve; omit it and
  those URLs 404. Only referenced files are copied.
- **`--prereq`** points at the prerequisite tracks' JSON (from Phase 0). The build
  seeds a synthetic prerequisite profile so cross-track generate/chat steps
  resolve, and each AI screen shows a **📌 prompt-context note** listing the data
  behind the output (entered-this-demo vs. synthetic-prerequisite) — so you can
  confirm the context that produced what you're seeing.
- **Iterate (tight loop):** edit a substep → rebuild → the demo restores your
  position (localStorage) and re-runs that generate step. Tweak the prompt and
  re-preview until the value moment lands.
- Without a proxy, generate steps fall back to their baked sample text.

---

## Phase 6 — Validate + Handoff

**Purpose:** Machine-verify the JSON, fix all errors, and write the complete handoff note.

**Run the validator:**
```bash
node scripts/validate-track-json.mjs <emitted.json> --assume <prereq-token-list>
# If Clarity is a prerequisite:
node scripts/validate-track-json.mjs <emitted.json> --assume-clarity
# Combined example:
node scripts/validate-track-json.mjs my-track.json --assume goal,strengths --assume-clarity
```

(Validator reference: `scripts/validate-track-json.mjs`. CLI: exits non-zero on errors; warnings are advisory.)

**Fix ALL errors.** Warnings should be reviewed — address any that reflect a real design problem (token reference to uncollected field, missing celebration screen, empty system prompt).

**Write the handoff note.** Include:
- How to load: write the JSON into `ignite-next/src/data/tracks-export.json`, run `pnpm db:seed`; the upsert-by-id means re-seeding is safe.
- What's auto-generated on seed (do NOT manually set these fields).
- Member focus-group log (from Phase 3).
- UX validation findings summary (from Phase 4).
- Any phases that were skipped, and why. (If none were skipped, say so explicitly.)

---

## Reference Index

| Phase | Reference file(s) read | Skill(s) invoked |
|-------|----------------------|-----------------|
| Phase 0 | `references/track-ontology.md` | — |
| Phase 1 | `references/examples/clarity-track.md`, `references/examples/self-leadership-track.md` | `web-research` |
| Phase 2 | `references/track-ontology.md` (6-step framework) | — |
| Phase 3 | `references/member-personas.md` | — |
| Phase 4 | — | `ux-audit` |
| Phase 5 | `references/track-json-schema.md`, `references/examples/` | `gdoc-build`, `value-moment`, `track-prototype` (build-prototype for the demo preview) |
| Phase 6 | — | `scripts/validate-track-json.mjs` (CLI) |

---

## Definition of Done

All five Definition-of-Done conditions below must be true before calling this skill complete:

1. **Both artifacts exist:** Student Experience Documentation Google Doc (link in handoff note) and importable ignite-next track JSON file.
2. **Validator exits 0:** `node scripts/validate-track-json.mjs` with correct `--assume` flags returns no errors.
3. **Value promise satisfied:** The Phase 0 value promise is traceable to a concrete deliverable in the track — a student finishing the track actually gets what was promised.
4. **Token-ordering rule satisfied:** No step references a profile token that hasn't been collected in an earlier step.
5. **Handoff note written:** Includes load instructions, auto-generated fields, focus-group log, UX validation summary, and an explicit statement of which phases (if any) were skipped.
