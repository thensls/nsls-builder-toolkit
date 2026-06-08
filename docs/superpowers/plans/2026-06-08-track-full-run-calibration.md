# Full-Run Track Calibration — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or executing-plans to implement task-by-task. Steps use `- [ ]` tracking.

**Goal:** Score the two live tracks (Personal Insights, Clarity) from a *real, complete* run-through — not a 25-screen partial walk with hand-built samples — so the rubric→PostHog calibration measures the actual experience instead of harness artifacts.

**Architecture:** Two phases. **Phase A** fixes the prototype + walker so a full, faithful run is possible inside our own pipeline (also repairs real bugs the skill needs for previewing *unbuilt* tracks). **Phase B** drives the real ignite-next app end-to-end for a production-faithful run (real personality scores, real Braintrust AI) to calibrate the live tracks against existing PostHog data.

**Tech Stack:** Node 22 ESM, Playwright, the track-prototype skill (`build-prototype.mjs`, `player.js`, `render-substep.mjs`, `walk-gallery.mjs`), `track-preview-proxy` (Express/AI SDK on Railway), ignite-next (Next + Prisma/Postgres + next-auth + Braintrust), Airtable base `appzDWu6GowvnACtv`, PostHog.

---

## Background — why the v1 seed was discarded

The 2026-06-07 seed (PI 5/16, Clarity 9/16) was deleted: every Value-killing finding was a **harness artifact**, not a track property.
1. **PI assessment results render as a stub** — `renderAssessmentResults()` emits literal "Assessment results display"; the real personality scores never appear, so the panel saw no artifact.
2. **Clarity financial summary = all-zeros** — the test profile skipped the monthly-expense collects; a real user fills them.
3. **Clarity career-statement `413`** — the preview-proxy body-size guard tripped on a hand-built prompt; production uses Braintrust, not this proxy.
4. **Walker `MAX_STEPS = 25`** — stopped at 25 of ~130 screens by design; autofill was "type 'Marcus', click first option," no stream-waiting.
5. **Panel workflow stalled** — the synth agent emitting 4×3 full 16-check verdicts never completed for Clarity; recovered via a lightweight adversarial-flip pass.

---

## Phase A — Faithful prototype + full walker

### Task A1: Render real assessment results (kills the #1 artifact)
**Files:** Create `scripts/lib/assessment-score.mjs` (+ test); Modify `scripts/lib/render-substep.mjs` (`renderAssessmentResults`), `prototype/player.js` (compute + inject on render), `scripts/build-prototype.mjs` (bake scoring data).
- [ ] Port the scoring contract from ignite-next `src/data/assessment-scoring-weights.json` + `assessment-types.json` (both on HEAD) into a pure `scoreAssessment(answers, weights, types)` → `{ typeScores, primaryType, summary }`.
- [ ] Write failing test with a known answer-set → expected type scores; implement; pass.
- [ ] Bake the weights/types JSON into the build (like `window.__SCREENS__`); in `player.js`, when rendering an `assessment-results` substep, compute scores from `state.answers` and render the real scores/type (not the stub).
- [ ] Verify in a served build: the personality step ends on visible scores, not placeholder text.

### Task A2: Coherent persona answer-set
**Files:** Create `scripts/personas/maya.answers.json` (every collect slug → realistic value, incl. the personality A/B picks, expense collects, multi-selects).
- [ ] Enumerate every `collect` slug across both segments (`extract-segments.mjs` already lists them) and author a consistent Maya answer for each — so generates + assessment get real, non-empty input.
- [ ] Validate: no collect slug missing; expense collects are non-zero; multi-selects meet min counts.

### Task A3: Full autofill walker
**Files:** Modify `scripts/walk-gallery.mjs` (or add `scripts/walk-full.mjs` extending it) + test the pure helpers.
- [ ] Remove `MAX_STEPS = 25`; drive the loop by `window.__SCREENS__` length (cap at length + small slack; keep loop/stuck detection).
- [ ] Per-`fieldType` autofill from the persona answer-set: text/textarea (value), currency (number), select (click matching option), multi-select/image-multiselect/dropdown-with-checkboxes (click N matching options), education/work/dream-job composites (fill sub-inputs).
- [ ] **Wait for live streams:** on a `generate` screen, wait until `.tp-ai-output` stops growing (stream complete) before screenshot + advance; on a `chat` screen, type the persona reply, click `[data-chat-send]`, wait for the reply bubble to finish, then Continue.
- [ ] Verify: a served full build walks to the last screen (~130), 0 BLANK/UNRESOLVED-TOKEN problems, every generate screenshot shows real streamed text.

### Task A4: Raise the proxy size limit (kills the #3 artifact)
**Files:** Modify `track-preview-proxy/src/config.mjs` + `src/app.mjs` (express json limit) (+ test); redeploy via Railway.
- [ ] Add a configurable max prompt/body size (env, sane default well above the largest chat system prompt); return a clear 413 only when genuinely abusive.
- [ ] Test the limit boundary; deploy; re-verify career-statement + the large personality-chat system prompt stream instead of 413.

### Task A5: Faithful full run + re-score
- [ ] Rebuild both segments with the persona answer-set + proxy flags; run the full walker → complete screenshot gallery + report.json.
- [ ] Re-run the focus-group panel on the faithful run (see Task C1 for the stall fix); emit scorecards + recommendations + conversation.md.

---

## Phase B — Real ignite-next app run (production-faithful)

### Task B1 (SPIKE): Stand up ignite-next locally
**Files:** ignite-next `.env` (from `.env.example`).
- [ ] `pnpm install`; `pnpm db:start` (local Postgres on :5433); set `DATABASE_URL`, `BRAINTRUST_API_KEY` (+ project/model), `AUTH_SECRET`, auth vars; `pnpm db:migrate` + `pnpm db:seed`.
- [ ] Confirm the seed includes the Personal Insights + Clarity tracks (or import them). Confirm a usable test login (the `dev:test` script + e2e setup likely seed one).
- [ ] **Output of spike:** documented run recipe + whether existing `test/e2e` has track-walk page objects to reuse.

### Task B2: Full e2e track walk with screenshots
**Files:** Extend ignite-next `test/e2e/` (a new spec) — do NOT modify app code.
- [ ] Using the seeded account, drive each track end-to-end with the Maya answer-set, screenshotting each screen (real assessment scores + real Braintrust generates render here).
- [ ] Export a `report.json`-shaped gallery compatible with the panel (reuse the walk-gallery report contract).

### Task B3: Score the real run + calibrate
- [ ] Run the focus-group panel on the real-app gallery → faithful ScoreRuns for both tracks → write to base `appzDWu6GowvnACtv` (content_hash from the real track version).
- [ ] (Gated on PostHog restart) Pull PI + Clarity completion/drop-off into `PostHogActuals`; run `calibrate.mjs`; report Spearman/Kendall with the directional-only caveat.

---

## Phase C — Panel tooling fix (shared)

### Task C1: De-stall the panel synth stage
**Files:** Modify the panel orchestration (the Phase-2 procedure / a committed `panel-workflow` variant) + SKILL.md.
- [ ] Replace the heavy "4 experts × 3 full re-verdicts" synth with the proven **lightweight adversarial-flip** pass (skeptic names MET→UNMET flips; tiny output), applied symmetrically per segment. Keep Stages 1–2 (independent personas, blind experts) as-is.
- [ ] Document the recovery path (salvage StructuredOutput from `subagents/workflows/<runId>/agent-*.jsonl`) in the SKILL troubleshooting notes.

---

## Sequencing & Definition of Done
- **A1 → A3 → A5** is the critical path for an in-pipeline faithful run; A2/A4/C1 feed it. Do Phase A first (also fixes the skill for unbuilt-track previews).
- **B** after A, for the production-faithful calibration of the live tracks.
- **Done:** both tracks scored from a complete run (every screen, real assessment scores, real streamed AI), ScoreRuns in the base with real content hashes, and — once PostHog is back — a calibrate.mjs result. No score in the base derived from a partial walk or hand-built sample.

## Known risks / unknowns
- B1 is a genuine spike — Braintrust key availability, seed contents, and auth flow are unverified. If B is heavier than its worth, Phase A alone gives a far more faithful run than v1 and may suffice for a directional seed.
- AI fidelity ceiling in Phase A: the preview-proxy (OpenAI) ≠ production Braintrust prompts; Phase A is "illustrative," Phase B is faithful. Calibration of *live* tracks should prefer B.
