---
name: track-prototype
description: >-
  Use after track-design produces a validated track.json, when a builder wants to
  click through and run their Society (ignite-next) track as a real, deployable
  prototype. Triggers: "preview my track", "run through my track", "build a prototype
  of this track", "deploy my track preview", "see my track on Netlify". For the
  Society (ignite-next) app ONLY. Input contract: a track.json that passes
  track-design's validate-track-json.mjs (Phase 6).
---

# Track Prototype

Turn a validated ignite-next `track.json` into a clickable, deployable prototype that
mirrors the real Society (ignite-next) design language, so a builder can feel the experience they
authored before it ships.

**Input gate:** the track must pass `track-design`'s validator first:
`node ../track-design/scripts/validate-track-json.mjs <track.json> [--assume-clarity]`
must exit 0. If it does not, stop and send the builder back to track-design Phase 6.

## Phase 1 — Build & Deploy Prototype

1. **Pick a sample persona.** Choose one from `../track-design/references/member-personas.md`
   (e.g., the anxious first-gen student) to seed `{slug}` token values and AI samples.
   Record which persona in the handoff note.
2. **Author AI samples.** For every `generate` and `chat` substep, write a realistic
   sample output (using the substep's authored template/system prompt + the persona) into
   a `samples.json` keyed by substep slug: `{ "<slug>": "sample text", ... }`. These are
   illustrative — the real app runs on Braintrust, so do not claim production fidelity.
3. **Build:**
   `node scripts/build-prototype.mjs <track.json> --persona "<name>" --samples samples.json --out prototype-build/ --assets <ignite-next>/public`
   (`--assets` copies ONLY the images/videos the track references into the build so
   `/img/...` and `/video/...` URLs resolve — without it they 404. Never copy the whole
   public dir by hand; the flag's collector handles referenced-files-only.)
4. **Run locally:** `npx serve prototype-build -p 3000` then open `http://localhost:3000`.
   (Opening `index.html` via `file://` breaks ES modules and fetch — always serve over HTTP.)
5. **Deploy:** invoke the `netlify-deploy` skill on `prototype-build/`. Record the URL.

   **Live AI (optional):** pass `--proxy-url <url> --proxy-token <token>` to the build command
   to enable real streaming responses. Set these once, org-wide, and share the same build flags.
   Without them the prototype is baked-only (AI samples are pre-written). With them:
   - `generate` substeps auto-stream a fresh draft when the screen loads.
   - `chat` substeps are an interactive multi-turn exchange.
   - Any proxy failure (network, auth, timeout) automatically falls back to the baked sample —
     reviewers always see something, never a blank screen.
   AI output is illustrative: the real app runs on Braintrust with different prompts and
   guardrails. Do not present prototype AI output as production fidelity.

   The `netlify-deploy` skill handles auth and the CLI. For a prebuilt folder use:
   `netlify deploy --dir=<abs>/prototype-build --no-build --json`
   Default to a DRAFT deploy (omit --prod) for review links — and for a draft, the
   preview URL is **`deploy_url`** in the JSON, NOT `url` (which is the existing prod
   URL). Use `url` only when you deployed with `--prod`. (CLI deploy sets font/.mjs MIME
   correctly — never use the zip-API path, which serves everything as text/plain.) Only
   --prod when the builder approves. Tear down old draft deploys when a review round closes.
6. **Handoff note:** persona used, local command, live URL, and the
   "approximate preview" caveat (this mirrors the app's design, it is not the live app).

## Phase 2 — Walkthrough & Focus Group (opt-in)

Gate: a working Phase-1 build (local or deployed). **Turn live AI ON** (build with `--proxy-url`/`--proxy-token`) — the panel scores the *live* `generate`/`chat` output, not the baked fallback. The deployed proxy is `https://track-preview-proxy-production.up.railway.app` (token in Doppler `track-preview-proxy/prd` → `PROXY_TOKEN`).

1. **Walkthrough:** `node scripts/walk-gallery.mjs <served-url> focus-group/v{N}` → a screenshot per screen + `report.json`. (Requires Playwright installed.) If `report.json.problems` is non-empty (blank screen, unresolved `{token}`, stuck/no-advance, console error), **STOP and fix the build before the panel runs** — don't score a broken prototype.

2. **Panel** (full protocol in `references/focus-group-panel.md`) — run as parallel sub-agents in isolated contexts, staged to fight groupthink:
   - **Stage 1** — member personas (`../track-design/references/member-personas.md`) react INDEPENDENTLY from the screenshots, **warm temp**, structured to `references/schemas/persona-reaction.json`.
   - **Stage 2** — the 4 experts score all 16 sub-checks BLIND, **3 samples each at low temp**, evidence-cited, structured to `references/schemas/expert-verdict.json`.
   - **Stage 3** — experts revise INFORMED by the *aggregated, anonymized* persona reactions.
   - **Stage 4** — the adversarial skeptic argues over-scoring / the abandonment case; experts respond.
   - **Stage 5** — **expert roundtable**: the 4 experts discuss the track *together* (one agent), grounded in their Stage-2 verdicts + the anonymized persona distribution + the skeptic case, and converge on the top 3 recommendations. Structured to `references/schemas/expert-roundtable.json`. **Synthesis only — it does NOT feed `scorecard.mjs`** (the score is fixed by Stages 2+4). It produces the readable expert discussion + converged recs for the doc.
   - Use a different model family for the judges than for any generated track copy.

3. **Aggregate + emit:**
   - Feed the **blind + adversarial** expert verdict samples (NOT the roundtable) to `scorecard.mjs` → MET/UNMET/**CONTESTED** per sub-check → dimension rollup → checks-met total → ship-bar.
   - `recommendations.mjs` → write `focus-group/v{N}/recommendations.md` (one rec per UNMET; CONTESTED = human-review flag).
   - Write `focus-group/v{N}/conversation.md` (persona dialogue + the **expert roundtable**) and `scorecard.md` (sub-checks + total).
   - Google Doc via **`gdoc-build`** (python-docx; **new draft, org-restricted, never overwrite a shared doc**): per-attribute scorecard + per-persona summary + persona conversation + **expert roundtable** (dialogue + converged top-3) + adversarial skeptic + ranked optimization plan.
   - **Ledger:** `AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=appzDWu6GowvnACtv node scripts/ledger-write.mjs <run.json>` — POSTs the ScoreRun to the "Track Previews" base and appends the local `scores.md`. `run.json` = `{ trackSlug, version, contentHash, date, scorecard, gdocUrl, persona, buildUrl, scoresMdPath }`.

4. **Handoff:** the Google Doc link + the scorecard + the checks-met total.

5. **Ship = flip the board.** When a run clears the ship-bar AND the version actually ships to members (merged + deployed in ignite-next), advance the Studio stage so the board stays truthful:
   ```
   AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=appzDWu6GowvnACtv \
     node scripts/set-stage.mjs <slug> live --live-version <contentHash>
   ```
   Sets `stage=live`, `is_live`, `current_version` (the hash `PostHogActuals.live_track_version` joins on for calibration). **Gate pass alone is not Live** — run this at the actual ship moment; if shipping happens later or by someone else, say so in the handoff and leave the stage as-is until it ships.

### The iteration loop
Builder says **"implement the focus-group changes"** → read `recommendations.md`, edit `track.json` per each `fix` rec's `change` (CONTESTED `review` recs go to a human, not auto-applied), re-run Phase 1 → Phase 2 → a v{N+1} ScoreRun showing the delta. **Scores are a ranking + ship-bar gate, NOT a calibrated prediction** — celebrate green checks; don't over-read the number (synthetic personas overstate adoption).

### Calibration (accruing; needs PostHog)
Every Phase-2 run adds a ScoreRun. Once a track is live in PostHog, add its actuals to the `PostHogActuals` table, then run `node scripts/calibrate.mjs` (Spearman/Kendall via `scripts/lib/calibration.mjs`, joining by slug + `content_hash`).

**The calibration target is per-step continuation, NOT raw completion.** The n=3 seed (welcome / personal-insights / career-clarity, 2026-06-11) showed raw completion *anti*-correlates with the rubric (Spearman −0.5) because it's dominated by track length, position, and commitment — a short mandatory intake form tops completion while scoring lowest on experience quality. Against **per-step continuation** (length-normalized retention — the metric the rubric's "predicts" column was designed for), the same n=3 ranks **+1**. So `calibrate.mjs` reports continuation as the primary coefficient and raw completion only under `vsCompletion` as a contrast. Populate `step_to_step_continuation` on each `PostHogActuals` row. Still **directional only** — n is tiny; ~15–30+ paired tracks before a coefficient means anything.

## Reference Index
| Phase | Reads | Invokes / scripts |
|-------|-------|-------------------|
| 1 | `../track-design/references/member-personas.md` | `build-prototype.mjs`, `netlify-deploy` |
| 2 | `focus-group-rubric.md`, `focus-group-panel.md`, `schemas/`, `member-personas.md` | `walk-gallery.mjs`, `lib/{scorecard,recommendations,scores-ledger,airtable-record,calibration}.mjs`, `ledger-write.mjs`, `gdoc-build`, `playwright` |

## Definition of Done
- **Phase 1:** a `prototype-build/` that renders with Society (ignite-next) styling and runs through end-to-end (locally and on Netlify); live AI streams when built with the proxy flags, baked fallback otherwise.
- **Phase 2:** a focus-group Google Doc (draft, org-restricted) + `recommendations.md` + `scorecard.md` under `focus-group/v{N}/`, a new ScoreRun in the Airtable base + a row in local `scores.md`, and `"implement the focus-group changes"` actionable from `recommendations.md`.

## Operating Rules
- Never seed the prototype with real member data — prototype input is illustrative and **egresses to OpenAI via the proxy** when live AI is on. Use only synthetic personas.
- The design kit is the REAL ignite-next theme: `design-kit/app.css` is compiled from the app's Tailwind theme by `scripts/build-design-kit.mjs`, fonts are the app's font files, and `--assets <ignite-next>/public` copies the track's referenced images/videos into the build. Re-sync steps: `prototype/SYNC.md`.
- AI output is illustrative (the app runs Braintrust), and focus-group scores are a relative ranking + gate, not a prediction.
