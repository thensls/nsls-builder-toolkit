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
mirrors the real Ignite Next design language, so a builder can feel the experience they
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
   `node scripts/build-prototype.mjs <track.json> --persona "<name>" --samples samples.json --out prototype-build/`
4. **Run locally:** `npx serve prototype-build -p 3000` then open `http://localhost:3000`.
   (Opening `index.html` via `file://` breaks ES modules and fetch — always serve over HTTP.)
5. **Deploy:** invoke the `netlify-deploy` skill on `prototype-build/`. Record the URL.
6. **Handoff note:** persona used, local command, live URL, and the
   "approximate preview" caveat (this mirrors the app's design, it is not the live app).

> Phase 2 (Walkthrough & Focus Group) is added by a later plan.

## Operating Rules
- Never seed the prototype with real member data — prototype input is illustrative and,
  once Plan 2 lands, egresses to an LLM. Use only synthetic personas.
- The design kit is hand-mirrored from ignite-next and drifts. See `prototype/SYNC.md`.
