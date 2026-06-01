# Track Design Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `track-design` skill in the `nsls-builder-toolkit` plugin: a 7-phase guided pipeline that takes a builder from a raw idea to a Society track (a Student Experience Doc + an importable ignite-next JSON object).

**Architecture:** A `SKILL.md` orchestrator that walks 7 gated-but-skippable phases, leaning on existing skills (`web-research`, `ux-audit`, `gdoc-build`) and four bundled `references/` files (ontology, JSON schema, member personas, two example tracks). One real executable: a dependency-free Node validator (`scripts/validate-track-json.mjs`) built test-first with `node:test`, enforcing the ignite-next schema contract and the ontology's token-ordering rule.

**Tech Stack:** Markdown (skill + references), Node.js ESM + `node:test`/`node:assert` (validator, no npm deps). Target import format: `ignite-next/src/data/tracks-export.json` loaded by `prisma/seed.ts` (`pnpm db:seed`, upsert-by-`id`).

**Source material (retrievable, for any executor):**
- Spec: `docs/superpowers/specs/2026-06-01-track-design-skill-design.md` (this repo)
- Track ontology doc (Google Drive, docx): id `1W4Rt4XYRaUXlJB4G3Kr1cQPwS98mbHGU` ("How Tracks Work")
- Self-Leadership Track (Google Doc): id `117wLOEf4efPXbIlzVZHhoj92RP3w_zrJbKRu4Amu4LQ`
- Clarity Track (Google Drive, docx): id `14smqJL4ajIvk8hYSUDxtfeqv9MpYAJsa`
- ignite-next schema source: `/Users/k/code/ignite-next/prisma/schema.prisma`, `scripts/export-tracks.ts`, `prisma/seed.ts`, `src/data/tracks-export.json` (read with `mcp__claude_ai_Google_Drive__read_file_content` for Drive ids; read files directly for the repo)

**Working branch:** `track-design-skill` (already created off `main`; spec already committed).

---

## File Structure

```
skills/track-design/
├── SKILL.md                              # orchestrator: 7 phases, gates, skip rules, sub-skill calls
├── references/
│   ├── track-ontology.md                 # grammar (Track/Step/Substep, types, tokens, profile) + 6-step framework
│   ├── track-json-schema.md              # exact ignite-next importable schema + seed/upsert mechanics
│   ├── member-personas.md                # focus-group panel: 5 registers + 2 edge personas
│   └── examples/
│       ├── clarity-track.md              # gold-standard artifact-track (condensed)
│       └── self-leadership-track.md      # gold-standard practice-track (condensed)
└── scripts/
    ├── validate-track-json.mjs           # validator: exports validateTracks(); CLI wrapper; exits non-zero on error
    └── validate-track-json.test.mjs      # node:test suite
```

Each file has one responsibility: `SKILL.md` orchestrates and never inlines the schema/ontology; references are versioned knowledge; the validator is executable and independently testable.

---

## Task 1: Scaffold the skill directory and SKILL.md frontmatter

**Files:**
- Create: `skills/track-design/SKILL.md`

- [ ] **Step 1: Create the skill directory and SKILL.md with frontmatter + skeleton**

Create `skills/track-design/SKILL.md` with exactly this opening (body filled in Task 7):

```markdown
---
name: track-design
description: >-
  Take a raw idea for a Society app learning experience and design a complete,
  importable track — end to end. Walks a builder through framing the value
  promise, researching, brainstorming the step structure, getting member
  focus-group feedback, validating UX, then emits both a Student Experience
  Documentation Google Doc and a directly-importable ignite-next track JSON.
  Use when someone says: design a track, build a track, new Society track,
  track design, "I want users to learn X" on the Society app, turn this idea
  into a track, author a track, track JSON, ignite-next track. For the Society
  (ignite-next) app only — not for NSLS marketing pages or automations.
---

# Track Design

<!-- body added in Task 7 -->
```

- [ ] **Step 2: Verify the directory and file exist**

Run: `ls skills/track-design/ && head -5 skills/track-design/SKILL.md`
Expected: `SKILL.md` listed; frontmatter shows `name: track-design`.

- [ ] **Step 3: Commit**

```bash
git add skills/track-design/SKILL.md
git commit -m "feat(track-design): scaffold skill + frontmatter"
```

---

## Task 2: Author references/track-json-schema.md

This is the contract the JSON generator and the validator both target. Content is the schema extracted from the ignite-next repo.

**Files:**
- Create: `skills/track-design/references/track-json-schema.md`

- [ ] **Step 1: Re-read the authoritative sources (do not work from memory)**

Read these in full:
- `/Users/k/code/ignite-next/prisma/schema.prisma` (Track, Step, SubStep models)
- `/Users/k/code/ignite-next/scripts/export-tracks.ts` (emitted shape)
- `/Users/k/code/ignite-next/prisma/seed.ts` (how JSON loads: `buildSubstepData`, upsert-by-id, `--fresh`)
- Sample structure of `/Users/k/code/ignite-next/src/data/tracks-export.json` via:
  `node -e "const t=require('/Users/k/code/ignite-next/src/data/tracks-export.json'); console.log(JSON.stringify(t[0]?.steps?.[0]?.substeps?.[0],null,2))"`

- [ ] **Step 2: Write the reference doc**

Create `skills/track-design/references/track-json-schema.md` covering, with exact field names quoted from the Prisma models:
1. **Loading mechanism (the bottom line):** importable file is `src/data/tracks-export.json` (a JSON array); loader is `prisma/seed.ts` via `pnpm db:seed`; upsert by `id`; content not present in the JSON is set `isActive=false`; `--fresh` wipes (refuses against `sslmode=require` unless `ALLOW_FRESH_SEED=true`). No separate import script. The tRPC `*.create` mutations are the admin UI path, NOT the bulk path.
2. **Track object:** required `id` (stable unique string; also copied to `trackGroupId`), `title`, `steps[]`; optional `slug`, `description`, `onEnter`, `onComplete`, `isLocked`. Author MUST NOT emit: `trackGroupId`, `version`, `isDraft`, `order`, `isActive`, `createdAt`, `updatedAt`. Note: track `imageUrl` is exported but not read by seed.
3. **Step object:** required `id`, `title`, `substeps[]`; optional `slug`, `description`, `imageUrl`, `onEnter`, `onComplete`. Auto: `order`, `trackId`, `version`, `isActive`, timestamps.
4. **SubStep object:** required `id`, `title`, `prompt`, `type`; `slug` auto-from-title if absent. Full optional field table with seed defaults (reproduce the field-by-field table: `fieldType`→null, `showTitle`→false, `callout*`, `chatSystemPrompt`→null, `suggestions`→[], `options`→null, `aiPromptConfig`→null, `multiselect*`, `dropdownOptions`→[], `checkboxOptions`→[], `bannerTexts`→[], all `celebration*` with defaults `celebrationShowConfetti`→true / `celebrationConfettiCount`→30 / `celebrationShowPath`→false, all `assessment*`, `autoProgressOnSelect`→false, `onEnter`/`onExit`/`nextSubStepId`/`nextStepId`/`nextTrackId`→null). Auto/never-emit: `order`, `stepId`, `version`, `isActive`, timestamps.
5. **Admin-only fields to AVOID in import JSON** (ignored or create-only-null on seed): `promptMode`, `promptAiPrompt`, `promptGenerated`, `suggestionsMode`, `suggestionsPrompt`, `suggestionsSchema`, `suggestionsMin`, `suggestionsMax`, `multiselectGenerationMin`, `multiselectGenerationMax`, `contextTag`, `celebrationShowProfileButton`.
6. **Value vocab:** `type` ∈ {`say`, `collect`, `generate`, `chat`, `ai-process`}. Common `fieldType`: `text`, `textarea`, `select`, `multi-select`, `image-multiselect`, `dropdown-with-checkboxes`, `currency`, `education`, `work`, `banner`, `banner-multiple`, `celebration`, `assessment-results`, `dream-job-select`, `dream-job-requirements`.
7. **`options` shapes:** array of strings, OR objects: for collect `{ text, answerId?, imageUrl?, imagePrompt?, nextSubStepId? }`; for generate `{ text, description }`. `aiPromptConfig` = `{ model, template, executeOn }`. `multiselectSchema` = stringified JSON schema.
8. **Token mechanics:** tokens are `{slug}` placeholders replaced by a prior substep's stored response. The producing substep is addressed by its **slug** (confirm via `optionsSourceSlug` semantics in seed/router). A token must reference a slug collected in an EARLIER substep, or a profile field from a completed prerequisite track.
9. **One real example each** of `say`, `collect` (simple text + rich image-multiselect), `chat`, `generate` (copy verbatim from the sampled JSON).

- [ ] **Step 3: Verify required sections present**

Run: `grep -ciE "tracks-export.json|pnpm db:seed|trackGroupId|chatSystemPrompt|aiPromptConfig|token" skills/track-design/references/track-json-schema.md`
Expected: a count ≥ 6 (all key anchors present).

- [ ] **Step 4: Commit**

```bash
git add skills/track-design/references/track-json-schema.md
git commit -m "feat(track-design): add ignite-next track JSON schema reference"
```

---

## Task 3: Author references/track-ontology.md

**Files:**
- Create: `skills/track-design/references/track-ontology.md`

- [ ] **Step 1: Read the source**

Read the track-ontology doc via `mcp__claude_ai_Google_Drive__read_file_content` with `fileId: 1W4Rt4XYRaUXlJB4G3Kr1cQPwS98mbHGU`.

- [ ] **Step 2: Write the reference doc**

Create `skills/track-design/references/track-ontology.md` as a distilled, builder-facing version covering:
1. Three levels: Track → Step → Substep (one-line jobs each).
2. Track = a value promise; what a track contains; sequential + dependencies.
3. Step = themed chapter = unit of accomplishment; the 4-part arc (Orient → Collect/Explore → Synthesize → Celebrate); single-theme rule.
4. Substep = one screen; the three modes SAY / COLLECT / CHAT, plus GENERATE (AI-authored SAY) and generate-then-select; field types.
5. Personalization: the `{slug}` token pattern; where tokens can appear; **tokens cannot reference data not yet collected**.
6. The AI's three roles + design principles ("AI generates, student judges"; "orient, don't constrain" for chat; inject profile data explicitly into system prompts).
7. The profile (mirror + briefing file); it grows over time.
8. **The 6-step "Designing a New Track" framework** verbatim in intent: (1) value promise, (2) what the coach needs to know, (3) sequence steps, (4) design each step's arc, (5) write prompts with personalization, (6) write CHAT system prompts.
9. Quick-reference glossary table.

Keep it skimmable; this is the design rubric the SKILL.md phases cite.

- [ ] **Step 3: Verify**

Run: `grep -ciE "value promise|SAY|COLLECT|CHAT|GENERATE|token|6.?step|arc" skills/track-design/references/track-ontology.md`
Expected: count ≥ 6.

- [ ] **Step 4: Commit**

```bash
git add skills/track-design/references/track-ontology.md
git commit -m "feat(track-design): add track ontology + design-framework reference"
```

---

## Task 4: Author the two example tracks

**Files:**
- Create: `skills/track-design/references/examples/clarity-track.md`
- Create: `skills/track-design/references/examples/self-leadership-track.md`

- [ ] **Step 1: Read the sources**

- Clarity: `mcp__claude_ai_Google_Drive__read_file_content` `fileId: 14smqJL4ajIvk8hYSUDxtfeqv9MpYAJsa`
- Self-Leadership: `mcp__claude_ai_Google_Drive__read_file_content` `fileId: 117wLOEf4efPXbIlzVZHhoj92RP3w_zrJbKRu4Amu4LQ`

- [ ] **Step 2: Write clarity-track.md (gold-standard artifact-track)**

Condense to: header (value promise, slug `clarity`, type=artifact, ~12 steps), the "Track at a Glance" step→collects→output table, and 3–4 annotated patterns this track demonstrates (generation-then-select for strengths/inspirations/dream-job; progressive narrowing for values; GENERATE for career statement; celebration arcs). Mark it `<!-- reference example: do not edit as live content -->`.

- [ ] **Step 3: Write self-leadership-track.md (gold-standard practice-track)**

Condense to: header (value promise, slug `self-leadership`, type=practice, 7 steps), the Track-at-a-Glance table, and the load-bearing patterns: the Pull check as filter-not-gate (with content-floater branch), the PRIVATE Progress Systems Rubric, derived-not-asked commitment tier, the Language Register system (5 registers + swap table), "activates not completes." Mark as a reference example.

- [ ] **Step 4: Verify**

Run: `ls skills/track-design/references/examples/ && grep -ciE "value promise|Track at a Glance|pattern" skills/track-design/references/examples/*.md`
Expected: both files listed; each shows matches.

- [ ] **Step 5: Commit**

```bash
git add skills/track-design/references/examples/
git commit -m "feat(track-design): add Clarity + Self-Leadership example tracks"
```

---

## Task 5: Author references/member-personas.md

**Files:**
- Create: `skills/track-design/references/member-personas.md`

- [ ] **Step 1: Write the panel**

Create `skills/track-design/references/member-personas.md`. Panel = the 5 Self-Leadership registers as named member personas + 2 edge personas. For EACH: name, register code, age/stage, current relationship to the topic, what they want, what makes them drop off, their candor style.
- A — **Maya**, Student (19, college sophomore): time-fragmented, motivated in bursts, allergic to anything that feels like homework.
- B — **Devin**, Early Pro (26, 3 yrs in): wants leverage/efficiency, skeptical of fluff, will bounce if a step feels generic.
- C — **Patricia**, Established (41, director): time-poor, high standards, resents being talked down to.
- D — **Theo**, Transitional (21, gap year, retail): low confidence, needs orientation and small wins, shame-sensitive.
- E — **Grace**, Returning (37, back in school): juggling, pragmatic, wants relevance to her actual life now.
- Edge 1 — **Sam**, the content-drifter: feels little pull; tests whether the track respects "I'm fine" without shaming (the off-ramp check).
- Edge 2 — **Jordan**, the completionist: rushes to finish, picks what sounds good (self-reporting bias); tests recognition-vs-recall and fatigue.

Add a **facilitation protocol**: present the Phase-2 outline; each persona answers (1) where would you drop off? (2) does the tone fit you? (3) which step is doing too much? (4) where would AI content feel generic vs. "that's me"? (5) what's missing? Then a synthesis: top friction themes + concrete outline changes. Personas speak with authentic, unsanitized friction.

- [ ] **Step 2: Verify**

Run: `grep -ciE "register|drop off|Maya|Devin|Patricia|Theo|Grace|Sam|Jordan|facilitation" skills/track-design/references/member-personas.md`
Expected: count ≥ 8.

- [ ] **Step 3: Commit**

```bash
git add skills/track-design/references/member-personas.md
git commit -m "feat(track-design): add Society member focus-group personas"
```

---

## Task 6: Build the JSON validator (TDD)

**Files:**
- Create: `skills/track-design/scripts/validate-track-json.test.mjs`
- Create: `skills/track-design/scripts/validate-track-json.mjs`

- [ ] **Step 1: Write the failing test suite**

Create `skills/track-design/scripts/validate-track-json.test.mjs`:

```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { validateTracks } from "./validate-track-json.mjs";

const goodTracks = [
  {
    id: "trk_demo",
    title: "Demo Track",
    steps: [
      {
        id: "stp_0",
        title: "Start",
        substeps: [
          { id: "ss_name", slug: "name", title: "Name", prompt: "What should we call you?", type: "collect", fieldType: "text" },
          { id: "ss_hi", slug: "hi", title: "Hi", prompt: "Hi {name}, welcome.", type: "say", fieldType: "banner" }
        ]
      }
    ]
  }
];

test("valid track passes with no errors", () => {
  const { errors } = validateTracks(goodTracks);
  assert.deepEqual(errors, []);
});

test("missing required substep field is an error", () => {
  const t = structuredClone(goodTracks);
  delete t[0].steps[0].substeps[0].prompt;
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /prompt/.test(e) && /ss_name/.test(e)));
});

test("leaked auto-managed field is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].order = 0;
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /order/.test(e) && /auto-managed/.test(e)));
});

test("duplicate substep slug within a step is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].slug = "name";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /duplicate slug/i.test(e) && /name/.test(e)));
});

test("duplicate id anywhere is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].id = "ss_name";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /duplicate id/i.test(e) && /ss_name/.test(e)));
});

test("invalid type is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].type = "speak";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /invalid type/i.test(e) && /speak/.test(e)));
});

test("forward token reference is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].prompt = "Your dream job is {dream-job-selection}.";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /token/i.test(e) && /dream-job-selection/.test(e)));
});

test("assumed token from a prerequisite track passes", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].prompt = "Building on your {career-statement}...";
  const { errors } = validateTracks(t, { assume: ["career-statement"] });
  assert.deepEqual(errors, []);
});

test("unknown fieldType is a warning, not an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].fieldType = "hologram";
  const { errors, warnings } = validateTracks(t);
  assert.deepEqual(errors, []);
  assert.ok(warnings.some((w) => /hologram/.test(w)));
});

test("top level must be an array", () => {
  const { errors } = validateTracks({ id: "x" });
  assert.ok(errors.some((e) => /array/i.test(e)));
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd skills/track-design/scripts && node --test`
Expected: FAIL — `Cannot find module './validate-track-json.mjs'` / `validateTracks is not a function`.

- [ ] **Step 3: Implement the validator**

Create `skills/track-design/scripts/validate-track-json.mjs`:

```javascript
// Validates an ignite-next importable track JSON array against the schema
// contract and the ontology token-ordering rule.
// Usage (CLI): node validate-track-json.mjs <path-to-tracks.json> [--assume slugA,slugB] [--assume-clarity]

const VALID_TYPES = new Set(["say", "collect", "generate", "chat", "ai-process"]);
const KNOWN_FIELD_TYPES = new Set([
  "text", "textarea", "select", "multi-select", "image-multiselect",
  "dropdown-with-checkboxes", "currency", "education", "work", "banner",
  "banner-multiple", "celebration", "assessment-results", "dream-job-select",
  "dream-job-requirements", ""
]);
// Fields the seed manages positionally / automatically — must NOT appear in import JSON.
const AUTO_FIELDS = new Set([
  "order", "version", "isDraft", "isActive", "trackId", "stepId",
  "trackGroupId", "createdAt", "updatedAt"
]);
// Profile slugs produced by the Clarity track (available if Clarity is a prerequisite).
export const CLARITY_TOKENS = [
  "name", "age", "gender", "location", "education", "work-experience",
  "direction-clarity", "job-acquisition-confidence", "your-personality-profile",
  "strengths-selection", "inspirations-selection", "work-environment-result",
  "living-environment-result", "value-selection-3", "monthly-target",
  "annual-target", "dream-job-selection", "dream-job-requirements",
  "career-statement", "major"
];

const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/g;

function slugify(s) {
  return String(s).toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

// Recursively collect every string value in an object/array.
function collectStrings(value, out) {
  if (typeof value === "string") out.push(value);
  else if (Array.isArray(value)) for (const v of value) collectStrings(v, out);
  else if (value && typeof value === "object") for (const v of Object.values(value)) collectStrings(v, out);
  return out;
}

function tokensIn(substep) {
  // Exclude structural id/slug fields from token scanning.
  const { id, slug, ...rest } = substep;
  const strings = collectStrings(rest, []);
  const found = new Set();
  for (const s of strings) {
    for (const m of s.matchAll(TOKEN_RE)) found.add(m[1]);
  }
  return found;
}

export function validateTracks(tracks, opts = {}) {
  const errors = [];
  const warnings = [];
  const assumed = new Set([
    ...(opts.assume || []),
    ...(opts.assumeClarity ? CLARITY_TOKENS : [])
  ]);

  if (!Array.isArray(tracks)) {
    errors.push("Top level must be an array of track objects.");
    return { errors, warnings };
  }

  const allIds = new Map(); // id -> location label
  const seen = (id, label) => {
    if (allIds.has(id)) errors.push(`Duplicate id "${id}" (at ${label} and ${allIds.get(id)}).`);
    else allIds.set(id, label);
  };

  // Flat, ordered list of substeps to enforce token ordering.
  const orderedSubsteps = []; // { sub, slug, label }
  const producedBefore = new Set();

  for (const [ti, track] of tracks.entries()) {
    const tlabel = `track[${ti}]`;
    if (!track || typeof track !== "object") { errors.push(`${tlabel} is not an object.`); continue; }
    if (!track.id) errors.push(`${tlabel} missing required "id".`);
    else seen(track.id, tlabel);
    if (!track.title) errors.push(`${tlabel} missing required "title".`);
    if (!Array.isArray(track.steps)) { errors.push(`${tlabel} missing required "steps" array.`); }
    for (const f of Object.keys(track)) if (AUTO_FIELDS.has(f)) errors.push(`${tlabel} has auto-managed field "${f}" — remove it (seed sets it).`);

    const stepSlugs = new Set();
    for (const [si, step] of (track.steps || []).entries()) {
      const slabel = `${tlabel}.step[${si}]`;
      if (!step || typeof step !== "object") { errors.push(`${slabel} is not an object.`); continue; }
      if (!step.id) errors.push(`${slabel} missing required "id".`); else seen(step.id, slabel);
      if (!step.title) errors.push(`${slabel} missing required "title".`);
      if (!Array.isArray(step.substeps)) errors.push(`${slabel} missing required "substeps" array.`);
      for (const f of Object.keys(step)) if (AUTO_FIELDS.has(f)) errors.push(`${slabel} has auto-managed field "${f}" — remove it.`);
      const sSlug = step.slug || slugify(step.title || "");
      if (sSlug) { if (stepSlugs.has(sSlug)) errors.push(`${slabel} duplicate slug "${sSlug}" within track.`); else stepSlugs.add(sSlug); }

      const subSlugs = new Set();
      for (const [bi, sub] of (step.substeps || []).entries()) {
        const blabel = `${slabel}.substep[${bi}] (id=${sub && sub.id})`;
        if (!sub || typeof sub !== "object") { errors.push(`${blabel} is not an object.`); continue; }
        for (const req of ["id", "title", "prompt", "type"]) {
          if (sub[req] === undefined || sub[req] === null || sub[req] === "") errors.push(`${blabel} missing required "${req}".`);
        }
        if (sub.id) seen(sub.id, blabel);
        if (sub.type && !VALID_TYPES.has(sub.type)) errors.push(`${blabel} invalid type "${sub.type}" (allowed: ${[...VALID_TYPES].join(", ")}).`);
        if (sub.fieldType !== undefined && sub.fieldType !== null && !KNOWN_FIELD_TYPES.has(sub.fieldType)) warnings.push(`${blabel} unknown fieldType "${sub.fieldType}".`);
        for (const f of Object.keys(sub)) if (AUTO_FIELDS.has(f)) errors.push(`${blabel} has auto-managed field "${f}" — remove it.`);
        const bSlug = sub.slug || slugify(sub.title || "");
        if (bSlug) { if (subSlugs.has(bSlug)) errors.push(`${blabel} duplicate slug "${bSlug}" within step.`); else subSlugs.add(bSlug); }
        orderedSubsteps.push({ sub, slug: bSlug, label: blabel });
      }
    }
  }

  // Token-ordering pass over the flat ordered list.
  for (const { sub, slug, label } of orderedSubsteps) {
    for (const tok of tokensIn(sub)) {
      const available = assumed.has(tok) || producedBefore.has(tok);
      if (!available) {
        errors.push(`${label} uses token {${tok}} before any earlier substep produces it (and it isn't an assumed prerequisite token). ` +
          `Collect {${tok}} earlier, or pass it via --assume.`);
      }
    }
    // This substep now produces its own slug for downstream tokens (collect/generate produce data).
    if (slug && (sub.type === "collect" || sub.type === "generate")) producedBefore.add(slug);
  }

  return { errors, warnings };
}

// ---- CLI ----
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const file = args.find((a) => !a.startsWith("--"));
  const assumeArg = args.find((a) => a.startsWith("--assume="))?.split("=")[1]
    || (args.includes("--assume") ? args[args.indexOf("--assume") + 1] : undefined);
  const assumeClarity = args.includes("--assume-clarity");
  if (!file) { console.error("Usage: node validate-track-json.mjs <tracks.json> [--assume a,b] [--assume-clarity]"); process.exit(2); }
  const { readFileSync } = await import("node:fs");
  let data;
  try { data = JSON.parse(readFileSync(file, "utf8")); }
  catch (e) { console.error(`Could not read/parse ${file}: ${e.message}`); process.exit(2); }
  const { errors, warnings } = validateTracks(data, {
    assume: assumeArg ? assumeArg.split(",").map((s) => s.trim()).filter(Boolean) : [],
    assumeClarity
  });
  for (const w of warnings) console.warn(`WARN  ${w}`);
  for (const e of errors) console.error(`ERROR ${e}`);
  if (errors.length) { console.error(`\n${errors.length} error(s), ${warnings.length} warning(s).`); process.exit(1); }
  console.log(`OK — valid (${warnings.length} warning(s)).`);
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd skills/track-design/scripts && node --test`
Expected: all tests PASS (10 pass, 0 fail).

- [ ] **Step 5: Smoke-test the CLI against a real exported track**

Run: `node skills/track-design/scripts/validate-track-json.mjs /Users/k/code/ignite-next/src/data/tracks-export.json --assume-clarity`
Expected: exits 0 (`OK — valid ...`) OR prints specific ERROR lines. If it errors on the real export, investigate whether the export legitimately contains auto fields (the export includes fields seed ignores). If so, relax `AUTO_FIELDS` to only the fields seed truly rejects on import and note it in the schema reference. Document the outcome in the commit message.

- [ ] **Step 6: Commit**

```bash
git add skills/track-design/scripts/validate-track-json.mjs skills/track-design/scripts/validate-track-json.test.mjs
git commit -m "feat(track-design): add track JSON validator (TDD, node:test)"
```

---

## Task 7: Write the SKILL.md body (the orchestrator)

**Files:**
- Modify: `skills/track-design/SKILL.md`

- [ ] **Step 1: Write the body after the frontmatter**

Append the body to `skills/track-design/SKILL.md`. It MUST include:

1. **Intro + when to use / not use.** Society (ignite-next) tracks only. One-line statement of the two outputs.
2. **Operating rules (top of file):**
   - Gated-but-skippable: run phases in order; a builder may skip a phase only on explicit request; when skipped, record it in the final handoff note (heartbeat — never skip silently).
   - Read the relevant `references/` file at the phase that needs it (cite exact path); never design from memory.
   - Maintain a working scratchpad (the evolving frame → outline → authored content) so the builder can stop/resume.
3. **The 7 phases**, each with: purpose, what to read, the gate/checkpoint, and the output. Mirror the spec exactly:
   - **Phase 0 Frame** — read `references/track-ontology.md` (value-promise section). Pin value promise (HARD GATE). Classify artifact vs practice. Prereqs + assumed tokens (these become the `--assume` list for the validator). Registers.
   - **Phase 1 Research** — invoke `web-research` for domain best-practices; study `references/examples/*` for borrowable patterns. Output: research brief naming borrowed patterns.
   - **Phase 2 Brainstorm shape** — apply the ontology 6-step framework; produce the ordered step/substep outline + tokens-produced map.
   - **Phase 3 Member focus group** — read `references/member-personas.md`; run the facilitation protocol against the outline; iterate; log "what members said / what changed."
   - **Phase 4 UX validation** — invoke `ux-audit` (Design Validation Layer, Society brand); apply fixes.
   - **Phase 5 Author + emit** — read `references/track-json-schema.md`. Expand every substep (prompts+tokens, CHAT system prompts, GENERATE configs, celebrations, options). Emit BOTH: (a) the Student Experience Doc via `gdoc-build` (format mirrors `references/examples/`), and (b) the importable JSON array.
   - **Phase 6 Validate + handoff** — run `node scripts/validate-track-json.mjs <emitted.json> --assume <prereq tokens>` (or `--assume-clarity` if Clarity is a prereq); fix all ERRORs, review WARNs; write the handoff note (load via `tracks-export.json` + `pnpm db:seed`; what's auto-generated; any phases skipped).
4. **A "Reference index" table** mapping each phase → the reference file(s) it reads and the skill(s) it invokes.
5. **Definition of done:** both artifacts exist; validator exits 0; value promise + token rule satisfied; handoff note written.

- [ ] **Step 2: Verify structure and cross-references resolve**

Run:
```bash
grep -ciE "Phase 0|Phase 1|Phase 2|Phase 3|Phase 4|Phase 5|Phase 6|value promise|HARD GATE|handoff" skills/track-design/SKILL.md
for f in references/track-ontology.md references/track-json-schema.md references/member-personas.md references/examples scripts/validate-track-json.mjs; do
  grep -q "$f" skills/track-design/SKILL.md && echo "OK ref: $f" || echo "MISSING ref: $f"
done
```
Expected: grep count ≥ 9; every `OK ref:` line (no `MISSING ref:`).

- [ ] **Step 3: Verify the skill loads (frontmatter parses, description triggers)**

Run: `head -20 skills/track-design/SKILL.md` and confirm valid YAML frontmatter (name + description), body starts with `# Track Design`.

- [ ] **Step 4: Commit**

```bash
git add skills/track-design/SKILL.md
git commit -m "feat(track-design): write 7-phase orchestrator body"
```

---

## Task 8: End-to-end dry-run + plugin discoverability check

**Files:**
- (verification only; no new files unless a fixture is added)

- [ ] **Step 1: Confirm the skill is discoverable by the plugin**

Check how sibling skills are registered (they are plain dirs under `skills/`). Run:
`ls skills/ | grep track-design && cat .claude-plugin/plugin.json 2>/dev/null | head -40 || cat plugin.json 2>/dev/null | head -40`
Expected: `track-design` listed. If the plugin manifest enumerates skills explicitly, add `track-design` to it following the existing pattern; if skills are auto-discovered from `skills/`, no change needed. Record which is true.

- [ ] **Step 2: Generate a tiny fixture track and validate it (proves the emit→validate loop)**

Create a throwaway `/tmp/demo-track.json`:

```json
[
  { "id": "trk_ai_basics", "title": "Use AI Effectively", "slug": "use-ai-effectively",
    "steps": [
      { "id": "stp_frame", "title": "Why AI, Why You",
        "substeps": [
          { "id": "ss_intro", "slug": "intro", "title": "Intro", "prompt": "Most people use AI like a search box. You're going to learn to use it like a thinking partner.", "type": "say", "fieldType": "banner" },
          { "id": "ss_usecase", "slug": "use-case", "title": "Use Case", "prompt": "What's one thing you do regularly that you'd love AI to help with?", "type": "collect", "fieldType": "text" },
          { "id": "ss_reflect", "slug": "reflect", "title": "Reflect", "prompt": "Great — we'll build around {use-case}.", "type": "say", "fieldType": "banner" }
        ] } ] }
]
```

Run: `node skills/track-design/scripts/validate-track-json.mjs /tmp/demo-track.json`
Expected: `OK — valid (0 warning(s)).` (exit 0). Then break it (add `"order": 0` to a substep) and re-run; expect an ERROR about an auto-managed field and exit 1. Delete `/tmp/demo-track.json`.

- [ ] **Step 3: Re-run the validator unit tests once more (regression)**

Run: `cd skills/track-design/scripts && node --test`
Expected: all PASS.

- [ ] **Step 4: Commit any manifest change (if Step 1 required one)**

```bash
git add -A && git commit -m "chore(track-design): register skill in plugin manifest" || echo "no manifest change needed"
```

---

## Task 9: Finalize — PR

- [ ] **Step 1: Push the branch and open a PR (per org PR-gated workflow)**

```bash
git push -u origin track-design-skill
gh pr create --title "Add track-design skill" --body "$(cat <<'EOF'
Adds the `track-design` skill: a 7-phase guided pipeline (frame → research →
brainstorm → member focus group → UX validation → author+emit → validate+handoff)
that turns a raw idea into a Society track — a Student Experience Doc and an
importable ignite-next JSON object.

Includes bundled references (ontology, ignite-next JSON schema, member personas,
Clarity + Self-Leadership examples) and a dependency-free Node validator with a
node:test suite enforcing the schema contract + token-ordering rule.

Spec: docs/superpowers/specs/2026-06-01-track-design-skill-design.md
Plan: docs/superpowers/plans/2026-06-01-track-design-skill.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 2: Wait for the Macroscope status check; address comments if any (per repo rule), then it's ready to merge.**

- [ ] **Step 3: Post-merge follow-ups (note, do not block PR):** update the builder-toolkit onboarding Google Doc to list the new skill; bump the "27+ skills" count if tracked.

---

## Self-Review

**Spec coverage:**
- Purpose / two artifacts → Tasks 1, 7 (Phase 5). ✓
- 7-phase pipeline → Task 7. ✓
- Bundled references (ontology, schema, member-personas, examples) → Tasks 2–5. ✓
- Importable ignite-next JSON contract → Task 2 + validator Task 6. ✓
- Member focus group, bundled → Task 5 + Phase 3. ✓
- ux-audit / web-research / gdoc-build orchestration → Task 7 phases. ✓
- Validator (required fields, types, unique ids/slugs, auto-field leak, token-ordering) → Task 6 tests + impl. ✓
- Gated-but-skippable + heartbeat on skip → Task 7 operating rules. ✓
- Org plugin home + PR workflow → Tasks 1, 9. ✓
- Testing (validator units + e2e smoke) → Tasks 6, 8. ✓

**Placeholder scan:** Validator code + tests are complete and runnable; content tasks specify exact sections, sources (file ids/paths), and grep-based verification. No "TBD"/"handle edge cases"/"similar to". ✓

**Type/name consistency:** `validateTracks(tracks, opts)` returns `{ errors, warnings }` consistently across tests, impl, CLI, and Phase 6 invocation. `--assume` / `--assume-clarity` and `CLARITY_TOKENS` are consistent between impl and Phase 0/6 usage. Reference paths used in SKILL.md (Task 7) match the files created in Tasks 2–6 and are verified in Task 7 Step 2. ✓
