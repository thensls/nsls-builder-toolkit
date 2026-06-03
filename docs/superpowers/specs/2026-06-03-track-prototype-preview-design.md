# Track Prototype Preview — Design Spec

**Date:** 2026-06-03
**Status:** Draft for review
**Extends:** `skills/track-design/` (NSLS Builder Toolkit), shipped 2026-06-01 (PR #47)
**Prior spec:** `docs/superpowers/specs/2026-06-01-track-design-skill-design.md`

---

## 0. Enhancement Summary — Deepened 2026-06-03

Deepened with 10 parallel research/review agents: 2 repo explorers (app AI runtime, PostHog instrumentation), 4 best-practices researchers (secure LLM proxy, design-kit/vanilla-player, LLM-as-judge scoring, Netlify/CORS/Playwright), 3 spec reviewers (security, architecture, simplicity), 1 institutional-learnings search. Original spec (§1–§13) is preserved below; this section records what changed and what now needs a decision.

### Findings that change the design

1. **The app's AI is Braintrust, not a raw OpenAI call — the "mirrors production" claim is false.** ignite-next runs `generate`/`chat` through **Braintrust-managed prompts invoked by `substepId`**, multi-model (gpt-4o / gpt-4o-mini / gpt-4-turbo / claude-3-opus selected *per prompt in Braintrust*), with the system prompt assembled server-side by `buildUserContext` — **not** from the `track.json` template. A generic `gpt-4o` relay fed the authored template produces different output via a different path. **Revision:** drop "matches production"; frame prototype AI as **illustrative**, and scope the AI-dependent rubric dimensions (D5 personalization, D6 copy, D7 peak-end) as illustrative-only for calibration. (Mirroring Braintrust-by-`substepId` only works for already-seeded substeps and re-introduces the live-app coupling the baked kit avoids — rejected for v1.) Refs: `src/app/api/chat/stream/route.ts`, `src/services/braintrustStreamingInvoke.ts`, `src/utils/aiContextBuilder.ts`.

2. **`gpt-4o` is being retired (Feb 2026).** Pin the **GPT-5.1 family — `gpt-5.1-mini` as the cost default** — to a dated snapshot verified against the models endpoint at build time. Do not hardcode `gpt-4o`.

3. **OpenAI budget limits are now soft/alert-only — NOT a hard cap.** This makes the proxy's own controls the *only* real ceiling. **Pre-ship requirement (security C1+H1):** a **dedicated OpenAI project + key** with a low cap, **plus a server-enforced daily request/token budget + kill switch** (Redis counter; env-var threshold) in the proxy. Origin allowlist + embedded token + per-IP rate limit are *friction*, not the boundary — the spend cap + kill switch is. Also: scope the origin allowlist tighter than all of `*.netlify.app` (that's every Netlify site on earth); render streamed AI output as **text, not HTML** (XSS); seed prototypes from **synthetic personas only, never real member data** (egresses to OpenAI).

4. **PostHog is sparsely instrumented — the calibration loop has a prerequisite.** Only ~6 events, **step-level not substep-level**, with **no** `track_started`/`track_completed`/chat/generate/celebration events. Of the 8 rubric metrics, only ~2–3 (step-1 drop-off, step-to-step continuation, partial completion) are measurable today; the rest need **new instrumentation in ignite-next first.** **Revision:** the calibration job is gated on instrumenting the app. Add a **Phase A** that's available *now*: validate the judge against 5–10 **human-scored** tracks (target Spearman ρ ≥ ~0.7 vs humans) to prove the rubric measures the right thing before any PostHog data exists.

5. **Scoring methodology upgrades (adopted into Phase 8 — see revised §8):** LLM-as-judge is self-inconsistent and synthetic personas **systematically overstate adoption**. Bake in: **independent scoring before any discussion** (kill sequential cross-referencing — it manufactures groupthink); **median of 3 samples per dimension**; **temperature split** (personas warm ~0.7–1.0 for reaction diversity, expert scorers cool ~0.1 for stability); an explicit **adversarial/skeptic agent** arguing the failure case; **evidence-citation + justification-before-number**; treat scores as **relative ranking + ship-bar gate, not calibrated prediction**; **ship-bar fires on median < 7 OR high dispersion** (high dispersion → route to human). Calibration metrics: Spearman/Kendall (rank is what matters), Gwet's AC2 if outcomes skew; need **15–30+ tracks** before a coefficient means anything.

### Implementation depth captured (folded into the build plan)
- **Netlify:** `netlify deploy --dir=<abs> --no-build --json`; parse `deploy_url` (draft) vs `url` (prod); CLI sets font/`.mjs` MIME correctly (the zip-API path is what corrupts them). Streaming needs `X-Accel-Buffering: no` + `Cache-Control: no-transform` or Railway buffers the whole stream. `file://` breaks `fetch`/modules → serve locally with `npx serve`. Answer `OPTIONS` preflight 2xx **above** any auth middleware.
- **Design kit:** keep `oklch`/`color-mix(in oklab, …)` math (Tailwind v4 opacity modifiers compile to `color-mix`, not `opacity`); variable fonts need `font-weight: <range>` in `@font-face`; convert the *variable* ttf, woff2 is enough. **Mechanically extract the token layer** from `globals.css` (94 custom properties, 5 `@font-face`) between marker comments so drift is a re-run, not a hand-diff; hand-author component HTML/CSS only; **pin SYNC to the ignite-next commit SHA** (local clone is 3+ mo stale — `git fetch` first). `SubStepRenderer.tsx` is ~1,600 lines / ~15 fieldType branches — the real mirroring surface.
- **Player:** framework-free state machine (`{index, answers}` + `render()`), single-pass `{slug}` interpolation with HTML-escaping + leave-unknown-tokens-literal, build-time ordering lint, `localStorage` versioned key + clamp, streamed render via `getReader()` + `TextDecoder({stream:true})`, SSE frame buffering on `\n\n`.
- **Playwright:** role/text selectors over a generated DOM, generic input fill, end-detection via content-hash stability + iteration cap, per-step assertions (blank screen, unresolved `{token}`, no advance button, console errors), screenshot gallery; use `domcontentloaded` not `networkidle` for streaming pages.
- **Airtable (MEMORY gotchas):** primary field `singleLineText`; `filterByFormula` uses field **names** (or Python-filter); select values as plain strings when keyed by field ID; base needs `workspaceId`; create fields via API but **formula fields must be UI**; use a **base-scoped token**.
- **gdoc-build:** `python-docx` (never pandoc); **new draft doc, never overwrite shared**; org-restricted sharing.
- **Doppler** is source of truth for the Railway secret (attach to an existing project); reuse the deploy-notify pattern for a **spend alert** to Kevin.

### Open decisions surfaced by research (need Kevin — see §14)
- **A. Separate `track-prototype` skill vs. extend `track-design`** (architecture reviewer's top rec).
- **B. v1 scope: live proxy now, or baked-fallback-only first** (simplicity reviewer + the gpt-4o/soft-cap/Braintrust findings weaken the proxy's v1 value).
- **C. Rubric for v1: keep 8 weighted dimensions, or simplify** (methodology upgrades adopted regardless).

### References (selected)
LLM-as-judge: RULERS (arXiv 2601.08654), Rating Roulette (EMNLP 2025), Self-Preference Bias (arXiv 2410.21819), eugeneyan.com/writing/llm-evaluators. Proxy: OpenAI deprecations & "budgets are soft" (developers.openai.com/api/docs/deprecations, grafient.ai), AI SDK 5 streamText, Cloudflare Turnstile, express-rate-limit trust-proxy. Repo ground truth: ignite-next `braintrust*`, `instrumentation-client.ts`, `posthog-events.ts`.

---

## 1. Purpose

`track-design` today ends at two artifacts: a Student Experience Doc (Google Doc) and an importable `track.json`. Neither lets a builder *feel* the track they authored. You can't tell whether pacing drags, whether a celebration lands, or whether the copy reads right on screen by reading JSON.

This extension adds the ability to **render an authored track as a clickable, deployable prototype that uses the real Ignite Next design language**, run a builder through it (locally or on Netlify), and then **subject the rendered experience to a synthetic expert focus group that scores it on a rubric and produces actionable, version-tracked recommendations.**

The scores are framed as **predictions of adoption/engagement**. They are stored so that — once real tracks are live and instrumented in PostHog — we can compare predicted scores to actual performance and calibrate the rubric. That calibration job is out of scope for this build; storing the predictions in a joinable form is in scope.

### Value promise

> When a builder finishes authoring a track, they can click through a faithful, live prototype of it, get an expert focus group's scored critique and ranked recommendations, implement those changes, and watch their scores improve across versions.

---

## 2. Scope

### In scope
- Two new opt-in phases in the `track-design` pipeline:
  - **Phase 7 — Build & Deploy Prototype**
  - **Phase 8 — Experiential Focus Group, Scoring & Iteration Loop**
- A baked-in, hand-mirrored Ignite Next **design kit** (CSS + fonts + player JS + HTML template) living inside the skill.
- A **build script** that turns a validated `track.json` into a self-contained, deployable static site.
- A shared **Railway proxy** (`track-preview-proxy`) that holds the LLM API key so live `generate`/`chat` substeps work with zero per-builder secret setup.
- A **focus-group rubric** (8 dimensions, 1–10, composite) mapped to future PostHog metrics.
- A **four-expert synthesis panel** (UX, Educational, Copywriter, Product/Engagement Strategist) layered on member-persona reactions.
- Dual-format focus-group output: **Google Doc** (read-first) + **markdown twin** (machine-actionable `recommendations.md`).
- A **versioned score ledger**: canonical **Airtable** base + local `scores.md` mirror.

### Out of scope (designed-for, built-later)
- The **PostHog calibration job** that joins predicted scores to actual performance. No tracks built via this skill are live with PostHog yet. We store predictions in Airtable now so this loop can close later.
- Replicating runtime-only fidelity beyond what's needed for "feel": exact framer-motion physics, real session/auth, real DB persistence.
- A bidirectional sync between the prototype and the live app. The design kit is hand-mirrored and periodically re-synced by the maintainer (see §5).

---

## 3. Architecture decisions (locked during brainstorm)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Renderer model | **Baked-in design kit** (hand-mirrored from app) | Works for any builder, zero repo dependency; drifts slowly, maintainer re-syncs |
| Interactivity | **Full simulation** | Fillable inputs, advancing, token fill-in, localStorage persistence |
| Live AI source | **Live API at runtime via shared proxy** + Claude-written baked fallback | Truly live `generate`/`chat`; fallback covers proxy-down/offline |
| Secret handling | **Shared Railway proxy holds the key** | No per-builder env setup; one rotation point (Doppler); never in client bundle |
| Model | **OpenAI `gpt-4o`** | Mirrors what ignite-next uses (AI SDK), so preview matches production |
| Score store | **Airtable canonical + local `scores.md` mirror** | Cross-track, joinable with PostHog later; local view for fast iteration |
| Expert panel | **4 experts**: UX, Educational, Copywriter, Product/Engagement Strategist | Strategist lens is the one most tied to the adoption/engagement metrics |
| Rubric | **8 dimensions, 1–10, composite** (starting set) | Refined later once PostHog calibration tells us which predict performance |

---

## 4. Design language (mirrored from `/Users/k/code/ignite-next`)

Source of truth confirmed by repo exploration on 2026-06-03.

**Tokens** (from `src/app/globals.css`, `tailwind.config.ts`):
- Primary (coral) `#f16b68`; primary-foreground `#ffffff`
- Light bg `#fff7f1`; dark text `#003250`
- Medium `#f2e8e0`; mediumPlus `#e9ddd3`; mocha `#c1b7af`; success `#8eaf86`
- Base radius `0.5rem`
- Fonts (`public/fonts/`, loaded via `@font-face`): **Hanken Grotesk** (body, variable), **HermeneusOne** (display), **Rand** (secondary)

**Components to mirror as plain CSS** (from `src/components/ui/` + `src/components/fields/` + `SubStepRenderer.tsx`):
- Button (cva variants: default / outline / dashed / secondary / light / ghost / link / suggestion; sizes default / sm / lg / xl)
- Text input (`.step-input`), currency input
- Select, multi-checkbox, radio
- Multi-select grid (`grid grid-cols-2 gap-3`, selected = `bg-mediumPlus`)
- Image-multiselect tiles (image + text row, `ring` on select, success checkmark badge)
- Banner / banner-multiple (staggered fade-in)
- Celebration (hero image, tasks list, next-steps, confetti, button)
- Chat bubble interface
- Track chrome: header + progress bar + phone-frame container

**Substep routing** (mirror the cascade in `SubStepRenderer.tsx`): `fieldType === "assessment-results"` → results; else `type === "chat"` → chat; `type === "generate"` → AI generate; `type === "say"` → banner/continue; `type === "collect"` → route on `fieldType`.

**Runtime-only (faked or stubbed):** live AI content (→ proxy + fallback), confetti physics (→ `react-confetti-explosion` is JS; prototype uses a lightweight CSS/canvas burst or the same lib via CDN), framer-motion transitions (→ CSS transitions), real persistence (→ localStorage).

---

## 5. Skill file layout

```
skills/track-design/
  SKILL.md                         # +Phase 7, +Phase 8, updated Reference Index & DoD
  prototype/
    design-kit.css                 # mirrored tokens + component styles
    fonts/                         # Hanken Grotesk, HermeneusOne, Rand (from public/fonts)
    player.js                      # advance/back, progress, token substitution,
                                   #   localStorage, fetch() to the proxy, fallback swap
    template.html                  # app chrome shell; build injects the track data
    SYNC.md                        # maintainer note: how to re-mirror from ignite-next
  scripts/
    validate-track-json.mjs        # (existing)
    build-prototype.mjs            # track.json -> prototype-build/ (NEW)
  references/
    member-personas.md             # (existing — reused by Phase 8)
    focus-group-rubric.md          # 8 dimensions, anchors, PostHog mapping (NEW)
    focus-group-panel.md           # the 4 expert roles + facilitation protocol (NEW)
    track-ontology.md              # (existing)
    track-json-schema.md           # (existing)
    examples/                      # (existing)
```

**Companion repo (not in the skill):** `thensls/track-preview-proxy` — the Railway service.

### Drift management (`SYNC.md`)
The design kit is hand-mirrored, so it drifts when the app's design changes. `SYNC.md` documents the exact source files in ignite-next to diff against (`globals.css`, `tailwind.config.ts`, `button.tsx`, the field renderers) and a checklist to re-mirror. Maintainer (Kevin / toolkit owner) runs this when the app's visual language moves. The prototype carries a visible "approximate preview — built {date}" watermark so no one mistakes it for the real app.

---

## 6. Phase 7 — Build & Deploy Prototype

**Gate:** Phase 6 validator must exit 0 (need valid JSON to render).

**Inputs:** the validated `track.json`; a chosen **sample persona** (from `member-personas.md`) to seed token values and AI prompts so the run-through has realistic data.

**Process:**
1. `node scripts/build-prototype.mjs <track.json> --persona <slug> --out prototype-build/`
   - Emits one screen per substep using the design-kit component matched by `type`/`fieldType`.
   - Copies `design-kit.css`, `fonts/`, `player.js`, `template.html` into the output.
   - Bakes the proxy endpoint URL and the build-embedded access token into `player.js`.
   - For each `generate`/`chat` substep, **Claude writes a fallback sample** (using the authored template + sample persona) embedded as static content. Live calls override it at runtime when the proxy is reachable.
2. **Local run:** `npx serve prototype-build/` (a static server; needed for `fetch` CORS). Builder clicks through.
3. **Deploy:** invoke the **`netlify-deploy`** skill on `prototype-build/`; capture the URL.
4. *(Optional)* invoke **`add-domain`** for a branded URL.

**Player behavior (`player.js`):**
- Renders/advances substeps; Back and progress bar.
- Captures input into an in-memory + `localStorage` profile keyed by substep slug.
- Resolves `{slug}` tokens downstream from captured input + seeded persona values.
- `generate`/`chat`: `fetch(PROXY_URL + "/api/generate")` with the authored template + accumulated profile; streams the result. On non-200/timeout/offline → render the baked fallback.

**Output:** `prototype-build/` folder + a live URL recorded in the handoff note.

---

## 7. Railway proxy — `track-preview-proxy`

**Purpose:** hold the LLM key server-side so every prototype gets live AI with no per-builder secret setup.

**Shape:**
- Node service on Railway, secrets via **Doppler** (project shared with related preview infra). `OPENAI_API_KEY` lives only here.
- Single endpoint `POST /api/generate` → calls OpenAI `gpt-4o` (AI SDK) → streams response.
- **Guardrails (must ship — it is otherwise an open LLM relay):**
  - **Origin allowlist:** `*.netlify.app` + `localhost`/`127.0.0.1`.
  - **Build-embedded access token:** a shared token baked into each prototype, checked by the proxy. Low-secret (it's in the client) but raises the bar past trivial scraping.
  - **Per-IP rate limiting.**
  - **Hard caps:** model pinned to `gpt-4o`, small `max_tokens`, system-prompt shape constrained to track-preview use.
- Deploy notifications follow the existing workflow→bot pattern if wired; not required for v1.

**Branding:** none — prototypes call the raw Railway URL (`https://track-preview-proxy.up.railway.app`). Decided 2026-06-03: not worth a branded subdomain for an internal proxy endpoint.

---

## 8. Phase 8 — Experiential Focus Group, Scoring & Iteration Loop

**Gate:** a working Phase 7 build (local or deployed URL).

### 8.1 Walkthrough (mechanical)
Drive the rendered prototype with **Playwright** (`playwright` skill or `compound-engineering:test-browser`): click every substep, fill fields, trigger live AI, screenshot each screen. Assert: no dead-ends, no blank/unstyled screens, every token resolves, celebration fires. Failures are reported as build defects before the focus group runs.

### 8.2 Member reactions (synthetic conversation)
The personas from `member-personas.md` (5 registers + 2 edge personas) walk the screenshots and **talk** — reacting screen by screen and to each other. Real back-and-forth, surfacing drop points, delight, confusion. Special weight to the edge personas (anxious first-gen, skeptical returning member).

### 8.3 Expert synthesis (4 experts)
Four experts read the conversation + screenshots, debate, and converge on **ranked recommendations**:
- **UX Designer** — cognitive load, pacing, interaction clarity, peak-end
- **Educational Designer** — does the learning land; scaffolding; is the deliverable real
- **Copywriter** — voice, tone, Society brand fit, resonance
- **Product/Engagement Strategist** — adoption/retention mechanics, value-promise strength, predicted drop-off (most tied to the rubric metrics)

### 8.4 Scoring (rubric)
The panel scores the track on **8 dimensions, 1–10 each**, judged **from the run-through** (screenshots + click-through), not from the JSON. **7 is the ship bar** per dimension. Full anchors live in `references/focus-group-rubric.md`; summarized here:

| # | Dimension | Predicts (PostHog, once live) | Weight |
|---|-----------|-------------------------------|--------|
| 1 | Value clarity at entry | Track start rate | ×1.5 |
| 2 | First-step ease | Step-1 drop-off | ×1.25 |
| 3 | Cognitive load & pacing | Mid-track drop-off, time-per-substep | ×1.0 |
| 4 | Motivation & momentum (celebrations) | Step-to-step continuation rate | ×1.25 |
| 5 | Personalization payoff | Engagement depth (chat turns, generate accepts) | ×1.0 |
| 6 | Copy resonance & tone | Completion + sentiment | ×1.0 |
| 7 | Perceived value at completion (peak-end) | Completion rate + next-track uptake | ×1.5 |
| 8 | Trust & fit (first-gen / skeptical) | Drop-off in at-risk segments | ×1.0 |

**Anchors (1–2 / 5–6 / 9–10):**
1. **Value clarity** — no/vague promise · promise present but generic or buried · concrete deliverable + compelling reason on screen 1, repeatable in one sentence.
2. **First-step ease** — cold-opens heavy free-text/long form · moderate first ask, mild hesitation · near-frictionless first win, instant momentum.
3. **Load & pacing** — 10+ collects no break, walls of text · mostly fine, 1–2 heavy spots · every step single-themed (4–8 collects) with synthesis breaks, effortless rhythm.
4. **Momentum** — no/generic celebration · present but bland, win not named · each milestone named specifically + previews next, pulls you forward.
5. **Personalization payoff** — none or tokens empty/awkward · surface only ("Hi {name}") · later screens build on earlier answers, AI output feels specifically theirs.
6. **Copy resonance** — off-brand/corporate/condescending · serviceable but flat · warm, specific, peer-level, sounds like Society; a skeptic softens.
7. **Peak-end value** — ends abruptly, no takeaway · takeaway underwhelms vs effort · ends on a high with a real artifact they'll reference, wants the next track.
8. **Trust & fit** — assumes privilege, invasive early · neutral, neither alienates nor reassures · actively meets at-risk members where they are, safe/optional, edge personas stay in.

**Composite** = weighted average using the weights above (sum of weights = 9.5), normalized to a 1–10 **adoption/engagement index**. Weights are tunable once PostHog calibration data lands.

**Ship-bar rule:** any dimension scoring **< 7 automatically generates a ranked recommendation**, even when the composite is high — so a single weak spot (e.g., a flat ending) can't hide behind a good average.

### 8.5 Outputs
- **Google Doc** (`gdoc-build`): full conversation + expert synthesis + ranked recommendations + scorecard. The read-first artifact for the designer.
- **Markdown twin** in `track-dir/focus-group/v{N}/`:
  - `conversation.md` — the member + expert dialogue
  - `recommendations.md` — **structured, machine-actionable**: each rec = `{id, dimension, severity, substep, change}`. This is what a builder points at: *"implement the focus-group changes."*
  - `scorecard.md` — the 8 scores + composite + rationale
- **Score ledger row** (see §9).

### 8.6 The loop
```
build v1 → focus group → scores{v1} + recommendations.md
   ↓  builder: "implement the focus-group changes"  (Claude edits track.json from recommendations.md)
build v2 → focus group → scores{v2}   ← compared to v1 in scores.md
   ↓  ...
[later, track live] → PostHog actuals → predicted vs real (calibration job, future)
```

---

## 9. Score ledger & data model

### Local mirror — `track-dir/focus-group/scores.md`
A running table for at-a-glance iteration progress:

| Version | Date | Composite | D1 | D2 | … | D8 | Doc |
|---------|------|-----------|----|----|----|----|-----|
| v1 | 2026-06-03 | 6.2 | 7 | 5 | … | 6 | [link] |
| v2 | 2026-06-04 | 7.8 | 8 | 7 | … | 8 | [link] |

### Canonical — Airtable base "Track Previews"
- **Tracks**: `slug` (PK), `title`, `type`, `current_version`
- **ScoreRuns**: `track` (link), `version`, `date`, `composite`, `dim_1`…`dim_8`, `gdoc_url`, `recommendations_count`, `persona_used`, `build_url`
- **PostHogActuals** *(populated later by the calibration job)*: `track` (link), `period`, `start_rate`, `completion_rate`, `dropoff_by_step` (json), `engagement_metrics` (json)

The ScoreRuns ↔ PostHogActuals join (by track + time window) is what the future calibration job consumes. Storing per-dimension predicted scores now makes that join possible without a later migration.

---

## 10. Pipeline & SKILL.md changes

Updated pipeline:
```
0 Frame → 1 Research → 2 Brainstorm → 3 Member focus group → 4 UX validation →
5 Author+emit → 6 Validate → 7 Build & Deploy Prototype (NEW, opt-in) →
8 Walkthrough & Focus Group (NEW, opt-in)
```

- **Reference Index** gains: Phase 7 → `prototype/`, `netlify-deploy`; Phase 8 → `focus-group-rubric.md`, `focus-group-panel.md`, `member-personas.md`, `playwright`, `gdoc-build`.
- **Definition of Done** gains an optional line: "If Phase 7/8 ran, the handoff note contains the live preview URL, the focus-group Google Doc link, and the current scorecard."
- Phases 7–8 are opt-in; a builder may stop at Phase 6. Skipping is recorded by name in the handoff note (existing heartbeat rule).

---

## 11. Implementation sequencing

Per "after we get the build right":
1. **Design kit + `build-prototype.mjs`** — get a real example track (clarity / self-leadership) rendering and clicking through cleanly with baked fallback content. No proxy yet.
2. **`track-preview-proxy` on Railway** + wire live AI in `player.js`; verify live generate/chat, verify fallback on proxy-down.
3. **Phase 8** — Playwright walkthrough, then the panel + rubric + dual-format output + Airtable/`scores.md` ledger, on top of a known-good build.
4. **(Future)** PostHog calibration job.

---

## 12. Risks & open items

- **Open LLM relay risk** — mitigated by origin allowlist + embedded token + rate limit + hard caps (§7). Accept residual risk as internal preview tooling; revisit if abused.
- **Design drift** — hand-mirrored kit will lag the app; mitigated by `SYNC.md` + visible "approximate preview" watermark.
- **Rubric validity unproven** — the 8 dimensions are a hypothesis until PostHog calibration; that's the explicit point of storing predictions.
- **Cost** — live AI per run-through costs tokens; rate limiting + small `max_tokens` + baked fallback bound it.

---

## 14. Open decisions surfaced by the deepen-plan research

These three forks came out of the research and need a call before the spec is final. The methodology upgrades in §0.5 are adopted regardless of how these land.

**A. Separate skill vs. extend track-design.** The architecture review's top recommendation: extract Phases 7–8 into a sibling `track-prototype` skill rather than bolting them onto `track-design`. Rationale: `track-design` is pure text + one pure-function validator — safe to auto-ship org-wide via PR; Phases 7–8 are live infra (Railway, Airtable, a drift-prone design kit, 3 dependent skills) that can break independently and shouldn't widen the authoring skill's blast radius. The Phase-6-validator-exit gate is already a clean skill boundary. *Counter:* one skill keeps the builder's journey seamless and discoverable.

**B. v1 proxy scope.** Three research threads converge against shipping the live proxy in v1: (1) it doesn't mirror production anyway (Braintrust), so "live" buys little over a baked sample for a feel-of-it preview; (2) gpt-4o retiring + soft budget caps mean real hardening work (dedicated key, Redis budget, kill switch) before it's safe to expose; (3) the baked Claude-written fallback is already in scope and shows pacing/copy/flow fine. The simplicity review estimates cutting the proxy removes a whole repo + the riskiest third of the player. *Counter (your earlier call):* you explicitly wanted it genuinely live. Option: **baked-only v1, proxy as a fast-follow Phase 7.5** once a builder says the canned answer blocks judgment.

**C. Rubric for v1.** Keep the 8 weighted dimensions (your call), or simplify to ~4 unweighted for v1 since the weights are admittedly unprovable until calibration data exists. Either way we adopt: independent-scoring, median-of-3, adversarial agent, evidence-citation, ranking-not-prediction framing, ship-bar on median<7 OR high dispersion, and the Phase-A human-validation step.

---

## 13. Definition of Done (for this extension)

1. A validated example track builds into a clickable `prototype-build/` that renders with recognizable Ignite Next styling and runs through end-to-end locally.
2. The same build deploys to Netlify via `netlify-deploy` and works there.
3. Live `generate`/`chat` substeps call `track-preview-proxy` and stream real output; with the proxy unreachable, the baked fallback renders instead.
4. Phase 8 produces, for a build: a focus-group Google Doc, a markdown twin (`conversation.md` + structured `recommendations.md` + `scorecard.md`), and a new row in both `scores.md` and the Airtable ScoreRuns table.
5. `"implement the focus-group changes"` is actionable from `recommendations.md`, and a re-run produces a v2 row showing score deltas.
6. `SKILL.md` reflects Phases 7–8, the Reference Index, and the updated DoD; `SYNC.md` documents the re-mirror process.
