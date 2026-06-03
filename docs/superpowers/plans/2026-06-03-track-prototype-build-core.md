# Track Prototype — Build Core (Plan 1 of 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new `track-prototype` skill that turns a validated ignite-next `track.json` into a clickable, self-contained static prototype using a hand-mirrored copy of the Ignite Next design language, runnable locally and deployable to Netlify.

**Architecture:** A new org skill (`skills/track-prototype/`) sibling to `track-design`, gated on the `track-design` Phase-6 validator. A pure-Node generator (`build-prototype.mjs`) reads `track.json` (+ optional Claude-authored AI samples + a sample persona) and emits a `prototype-build/` folder. The folder bundles a baked **design kit** (CSS tokens mechanically extracted from ignite-next `globals.css`, hand-authored component CSS, local variable fonts), an HTML chrome shell, and a framework-free **player** (vanilla state machine: advance/back, progress, `{slug}` token substitution, `localStorage`). This plan ships the **baked-only** path — `generate`/`chat` substeps render Claude-authored sample content. (Live AI via the Railway proxy is Plan 2; the focus group + rubric + calibration is Plan 3.)

**Tech Stack:** Node v22 ESM (`.mjs`), Node built-in test runner (`node:test` + `node:assert/strict`) — matching `track-design/scripts/validate-track-json.test.mjs`. Plain CSS (no Tailwind build), framework-free browser JS (ES modules). `npx serve` for local run, the `netlify-deploy` skill for deploy, `playwright` for the smoke walkthrough.

**Source of truth for the design language:** `/Users/k/code/ignite-next` (remote `thensls/ignite-next`). Confirmed tokens: primary `#f16b68`, light `#fff7f1`, dark `#003250`, medium `#f2e8e0`, mediumPlus `#e9ddd3`, mocha `#c1b7af`, success `#8eaf86`; fonts Hanken Grotesk (variable), HermeneusOne (static), Rand (variable) in `public/fonts/`; substep renderers in `src/components/SubStepRenderer.tsx` + `src/components/fields/`.

**Spec:** `docs/superpowers/specs/2026-06-03-track-prototype-preview-design.md` (decisions in §14; this plan implements decision A's new skill, baked path only).

---

## File Structure

```
skills/track-prototype/
  SKILL.md                         # Phase 1 (Build & Deploy) only; Phase 2 added in Plan 3
  scripts/
    extract-tokens.mjs             # ignite-next globals.css -> design-kit/tokens.css (marker block)
    extract-tokens.test.mjs
    build-prototype.mjs            # track.json (+samples,+persona) -> prototype-build/
    build-prototype.test.mjs
    lib/
      interpolate.mjs              # {slug} -> value, escape, leave-unknown-literal  (shared build+browser)
      interpolate.test.mjs
      ordering-lint.mjs            # assert every {slug} is produced by an earlier substep
      ordering-lint.test.mjs
      render-substep.mjs           # one substep -> HTML string, routed by type/fieldType
      render-substep.test.mjs
      player-core.mjs              # pure state-machine fns (nextIndex/capture/clamp) — node-testable
      player-core.test.mjs
  prototype/
    template.html                  # chrome shell: header, progress bar, phone frame, #screen mount, watermark
    player.js                      # browser entry (ES module): imports player-core + interpolate, wires DOM
    design-kit/
      tokens.css                   # GENERATED (extract-tokens) — colors, radius, fonts vars
      components.css               # hand-authored: buttons, inputs, selects, multiselect, banner, celebration, chat
      wizard.css                   # layout, progress bar, phone frame, watermark, streaming caret
      fonts/                       # HankenGrotesk-Variable.{woff2,ttf}, HermeneusOne-Regular.*, Rand-Variable.*
      gallery.html                 # static component gallery for visual QA (not shipped in builds)
    SYNC.md                        # how to re-mirror from ignite-next (pinned commit SHA)
```

Each `prototype-build/` output looks like: `index.html` (template + injected `window.__TRACK__`), `player.js`, `design-kit/` (copied), `fonts/` (copied).

---

## Task 0: Skill scaffold + SKILL.md (Phase 1 only)

**Files:**
- Create: `skills/track-prototype/SKILL.md`
- Create (dirs): `skills/track-prototype/scripts/lib/`, `skills/track-prototype/prototype/design-kit/fonts/`

- [ ] **Step 1: Create the directory tree**

Run:
```bash
mkdir -p ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype/scripts/lib \
         ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype/prototype/design-kit/fonts
```

- [ ] **Step 2: Write `SKILL.md`**

Create `skills/track-prototype/SKILL.md`:
```markdown
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
```

- [ ] **Step 3: Commit**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/SKILL.md
git commit -m "feat(track-prototype): scaffold skill + Phase 1 SKILL.md"
```

---

## Task 1: `interpolate.mjs` — `{slug}` token substitution

**Files:**
- Create: `skills/track-prototype/scripts/lib/interpolate.mjs`
- Test: `skills/track-prototype/scripts/lib/interpolate.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `scripts/lib/interpolate.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { interpolate, escapeHtml } from "./interpolate.mjs";

test("replaces a known token with its value", () => {
  assert.equal(interpolate("Hi {name}.", { name: "Marcus" }), "Hi Marcus.");
});

test("leaves an unknown token literal (does not blank it)", () => {
  assert.equal(interpolate("Hi {name}.", {}), "Hi {name}.");
});

test("escapes HTML in substituted values (XSS guard)", () => {
  assert.equal(interpolate("X {v}", { v: "<b>z</b>" }), "X &lt;b&gt;z&lt;/b&gt;");
});

test("single pass — does not re-substitute a value that contains a token", () => {
  assert.equal(interpolate("{a}", { a: "{b}", b: "BAD" }), "{b}");
});

test("escapeHtml handles the five entities", () => {
  assert.equal(escapeHtml(`&<>"'`), "&amp;&lt;&gt;&quot;&#39;");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype && node --test scripts/lib/interpolate.test.mjs`
Expected: FAIL — `Cannot find module './interpolate.mjs'`.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/lib/interpolate.mjs`:
```javascript
// Replace {slug} tokens with captured values. Single non-recursive pass.
// Unknown tokens are left literal so mis-ordering is visible, not silently blank.
const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/gi;

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function interpolate(text, answers) {
  return String(text).replace(TOKEN_RE, (match, slug) =>
    Object.prototype.hasOwnProperty.call(answers, slug) ? escapeHtml(answers[slug]) : match
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/lib/interpolate.test.mjs`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/scripts/lib/interpolate.mjs skills/track-prototype/scripts/lib/interpolate.test.mjs
git commit -m "feat(track-prototype): {slug} interpolation with escape + leave-unknown-literal"
```

---

## Task 2: `ordering-lint.mjs` — token-ordering validation

**Files:**
- Create: `skills/track-prototype/scripts/lib/ordering-lint.mjs`
- Test: `skills/track-prototype/scripts/lib/ordering-lint.test.mjs`

- [ ] **Step 1: Write the failing test**

Create `scripts/lib/ordering-lint.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { findOrderingErrors } from "./ordering-lint.mjs";

const track = (substeps) => [{ id: "t", title: "T", steps: [{ id: "s", title: "S", substeps }] }];

test("no errors when token is produced before use", () => {
  const errs = findOrderingErrors(track([
    { id: "a", slug: "name", title: "N", prompt: "?", type: "collect" },
    { id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" },
  ]));
  assert.deepEqual(errs, []);
});

test("flags a token used before it is produced", () => {
  const errs = findOrderingErrors(track([
    { id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" },
    { id: "a", slug: "name", title: "N", prompt: "?", type: "collect" },
  ]));
  assert.equal(errs.length, 1);
  assert.match(errs[0], /\{name\}/);
});

test("assumed tokens (prereq) are allowed", () => {
  const errs = findOrderingErrors(
    track([{ id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" }]),
    { assume: ["name"] }
  );
  assert.deepEqual(errs, []);
});

test("only collect/generate substeps produce their slug", () => {
  // a 'say' substep with slug 'foo' does NOT satisfy a later {foo}
  const errs = findOrderingErrors(track([
    { id: "x", slug: "foo", title: "F", prompt: "hello", type: "say" },
    { id: "y", slug: "bar", title: "B", prompt: "{foo}", type: "say" },
  ]));
  assert.equal(errs.length, 1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/lib/ordering-lint.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/lib/ordering-lint.mjs`:
```javascript
// Build-time check: every {slug} referenced in a substep must be produced by an
// earlier collect/generate substep (or passed via opts.assume). Mirrors the rule in
// track-design/scripts/validate-track-json.mjs, scoped to the flat substep order.
const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/gi;

function collectStrings(value, out) {
  if (typeof value === "string") out.push(value);
  else if (Array.isArray(value)) for (const v of value) collectStrings(v, out);
  else if (value && typeof value === "object") for (const v of Object.values(value)) collectStrings(v, out);
  return out;
}

function tokensIn(substep) {
  const { id, slug, ...rest } = substep;
  const found = new Set();
  for (const s of collectStrings(rest, [])) for (const m of s.matchAll(TOKEN_RE)) found.add(m[1]);
  return found;
}

export function findOrderingErrors(tracks, opts = {}) {
  const errors = [];
  const produced = new Set(opts.assume || []);
  for (const track of tracks) {
    for (const step of track.steps || []) {
      for (const sub of step.substeps || []) {
        for (const tok of tokensIn(sub)) {
          if (!produced.has(tok)) {
            errors.push(`substep "${sub.id}" uses {${tok}} before any earlier substep produces it.`);
          }
        }
        if (sub.slug && (sub.type === "collect" || sub.type === "generate")) produced.add(sub.slug);
      }
    }
  }
  return errors;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/lib/ordering-lint.test.mjs`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/track-prototype/scripts/lib/ordering-lint.*
git commit -m "feat(track-prototype): build-time token-ordering lint"
```

---

## Task 3: `render-substep.mjs` — substep → HTML, routed by type/fieldType

**Files:**
- Create: `skills/track-prototype/scripts/lib/render-substep.mjs`
- Test: `skills/track-prototype/scripts/lib/render-substep.test.mjs`

Routing mirrors `SubStepRenderer.tsx`: `assessment-results` first; then `type` `chat` / `generate`; then `say` (banner/celebration); then `collect` routed on `fieldType`. The output is static HTML with design-kit classes; the player attaches behavior by `[data-*]` hooks. Tokens are NOT interpolated here (the player does that at runtime against captured answers) — render emits the raw `{slug}` so the browser can fill it live.

- [ ] **Step 1: Write the failing test**

Create `scripts/lib/render-substep.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderSubstep } from "./render-substep.mjs";

test("say/banner renders prompt + a Continue button", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "Welcome", type: "say", fieldType: "banner" }, {});
  assert.match(html, /Welcome/);
  assert.match(html, /data-next/);
  assert.match(html, /class="[^"]*tp-btn/);
});

test("collect/text renders an input bound by data-input + data-slug", () => {
  const html = renderSubstep({ id: "x", slug: "name", title: "Name", prompt: "Your name?", type: "collect", fieldType: "text" }, {});
  assert.match(html, /data-input/);
  assert.match(html, /data-slug="name"/);
});

test("collect/multi-select renders one option button per option", () => {
  const sub = { id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "multi-select",
    options: [{ text: "A" }, { text: "B" }] };
  const html = renderSubstep(sub, {});
  assert.equal((html.match(/data-option/g) || []).length, 2);
});

test("generate renders the baked sample when provided", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" },
    { samples: { cs: "Your career statement draft." } });
  assert.match(html, /Your career statement draft\./);
});

test("generate without a sample renders a clearly-marked placeholder", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" }, {});
  assert.match(html, /tp-ai-placeholder/);
});

test("unknown fieldType falls back to a generic text screen (no throw)", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "P", type: "collect", fieldType: "totally-new" }, {});
  assert.match(html, /P/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/lib/render-substep.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/lib/render-substep.mjs`:
```javascript
// Render one substep to static HTML using design-kit classes (tp- prefix to avoid
// collisions). The player wires behavior via data-* hooks and does {slug} interpolation
// at runtime. ctx.samples[slug] supplies baked AI text for generate/chat.

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const continueBtn = (label = "Continue") =>
  `<button class="tp-btn tp-btn-default tp-btn-lg" data-next>${esc(label)}</button>`;

function renderSay(sub) {
  if (sub.fieldType === "celebration") return renderCelebration(sub);
  // banner / banner-multiple / default say
  const extra = (sub.bannerTexts || []).map((t) => `<p class="tp-banner-line" data-tpl>${esc(t)}</p>`).join("");
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p>${extra}</div>${continueBtn()}`;
}

function renderCelebration(sub) {
  const tasks = (sub.celebrationTasks || [])
    .map((t) => `<li class="tp-task">${esc(t)}</li>`).join("");
  const next = sub.celebrationNextStepsTitle
    ? `<div class="tp-next"><h3>${esc(sub.celebrationNextStepsTitle)}</h3><p data-tpl>${esc(sub.celebrationNextStepsDescription || "")}</p></div>`
    : "";
  return `<div class="tp-celebration">
    <div class="tp-confetti" data-confetti></div>
    <p class="tp-prose" data-tpl>${esc(sub.prompt)}</p>
    ${tasks ? `<ul class="tp-tasks">${tasks}</ul>` : ""}
    ${next}
  </div>${continueBtn(sub.celebrationButtonText || "Okay, got it!")}`;
}

function optionList(sub) {
  const opts = Array.isArray(sub.options) ? sub.options : [];
  return opts.map((o, i) => {
    const text = typeof o === "string" ? o : (o.text ?? "");
    const desc = typeof o === "object" && o.description ? `<span class="tp-opt-desc">${esc(o.description)}</span>` : "";
    const img = typeof o === "object" && o.imageUrl ? `<img class="tp-opt-img" src="${esc(o.imageUrl)}" alt="">` : "";
    return `<button class="tp-option" data-option data-value="${esc(text)}" data-index="${i}">${img}<span>${esc(text)}</span>${desc}</button>`;
  }).join("");
}

function renderCollect(sub) {
  const slug = esc(sub.slug || "");
  const prompt = `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div>`;
  switch (sub.fieldType) {
    case "select":
    case "multi-select":
    case "image-multiselect":
    case "dropdown-with-checkboxes":
      return `${prompt}<div class="tp-options tp-options-grid" data-slug="${slug}" data-multi="${sub.fieldType !== "select"}">${optionList(sub)}</div>${continueBtn()}`;
    case "currency":
      return `${prompt}<div class="tp-input-wrap"><span class="tp-currency">$</span><input class="tp-input tp-input-currency" type="number" data-input data-slug="${slug}" placeholder="0"></div>${continueBtn()}`;
    default: // text, textarea, work, education, dream-job-*, unknown -> generic text capture
      return `${prompt}<input class="tp-input" type="text" data-input data-slug="${slug}" placeholder="Type your answer…">${continueBtn()}`;
  }
}

function renderGenerate(sub, ctx) {
  const sample = ctx.samples && ctx.samples[sub.slug];
  const body = sample
    ? `<div class="tp-ai-output">${esc(sample)}</div>`
    : `<div class="tp-ai-placeholder">AI would write this from your answers. (No sample baked in.)</div>`;
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div>${body}${continueBtn()}`;
}

function renderChat(sub, ctx) {
  const sample = (ctx.samples && ctx.samples[sub.slug]) || "Tell me what's on your mind.";
  return `<div class="tp-chat">
    <div class="tp-bubble tp-bubble-ai" data-tpl>${esc(sub.prompt)}</div>
    <div class="tp-bubble tp-bubble-ai">${esc(sample)}</div>
  </div>${continueBtn("Continue")}`;
}

function renderAssessmentResults(sub) {
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div><div class="tp-results">Assessment results display</div>${continueBtn()}`;
}

export function renderSubstep(sub, ctx = {}) {
  const title = sub.showTitle && sub.title ? `<h2 class="tp-title">${esc(sub.title)}</h2>` : "";
  let inner;
  if (sub.fieldType === "assessment-results") inner = renderAssessmentResults(sub);
  else if (sub.type === "chat") inner = renderChat(sub, ctx);
  else if (sub.type === "generate") inner = renderGenerate(sub, ctx);
  else if (sub.type === "say") inner = renderSay(sub);
  else inner = renderCollect(sub);
  return `<section class="tp-screen" data-substep="${esc(sub.id)}">${title}${inner}</section>`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/lib/render-substep.test.mjs`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add skills/track-prototype/scripts/lib/render-substep.*
git commit -m "feat(track-prototype): substep -> HTML renderer routed by type/fieldType"
```

---

## Task 4: `player-core.mjs` — pure state-machine functions

**Files:**
- Create: `skills/track-prototype/prototype/player-core.mjs`
- Test: `skills/track-prototype/scripts/lib/player-core.test.mjs`

Pure, DOM-free functions so they're node-testable; `player.js` (Task 6) imports them and wires the DOM. Lives under `prototype/` so it ships in the build.

- [ ] **Step 1: Write the failing test**

Create `scripts/lib/player-core.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { flattenSubsteps, nextIndex, prevIndex, clampIndex, progressPct } from "../../prototype/player-core.mjs";

const track = { steps: [
  { substeps: [{ id: "a" }, { id: "b" }] },
  { substeps: [{ id: "c" }] },
] };

test("flattenSubsteps returns substeps in order across steps", () => {
  assert.deepEqual(flattenSubsteps(track).map((s) => s.id), ["a", "b", "c"]);
});

test("nextIndex advances but stops at the last", () => {
  assert.equal(nextIndex(0, 3), 1);
  assert.equal(nextIndex(2, 3), 2);
});

test("prevIndex goes back but stops at 0", () => {
  assert.equal(prevIndex(2, 3), 1);
  assert.equal(prevIndex(0, 3), 0);
});

test("clampIndex keeps index in range after the track shrinks", () => {
  assert.equal(clampIndex(9, 3), 2);
  assert.equal(clampIndex(-1, 3), 0);
});

test("progressPct is 0 at first and 100 at last", () => {
  assert.equal(progressPct(0, 3), 0);
  assert.equal(progressPct(2, 3), 100);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/lib/player-core.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `prototype/player-core.mjs`:
```javascript
// Pure state helpers for the prototype player. No DOM, no globals — node-testable.
export function flattenSubsteps(track) {
  const out = [];
  for (const step of track.steps || []) for (const sub of step.substeps || []) out.push(sub);
  return out;
}
export function nextIndex(i, n) { return Math.min(i + 1, n - 1); }
export function prevIndex(i, n) { return Math.max(i - 1, 0); }
export function clampIndex(i, n) { return Math.max(0, Math.min(i, n - 1)); }
export function progressPct(i, n) { return n <= 1 ? 100 : Math.round((i / (n - 1)) * 100); }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/lib/player-core.test.mjs`
Expected: PASS (5 tests).

- [ ] **Step 5: Run the whole suite to confirm nothing regressed**

Run: `cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype && node --test scripts/lib/*.test.mjs`
Expected: PASS (all suites).

- [ ] **Step 6: Commit**

```bash
git add skills/track-prototype/prototype/player-core.mjs skills/track-prototype/scripts/lib/player-core.test.mjs
git commit -m "feat(track-prototype): pure player state-machine helpers"
```

---

## Task 5: Design kit — tokens (generated), components, wizard CSS, fonts

**Files:**
- Create: `skills/track-prototype/scripts/extract-tokens.mjs`
- Test: `skills/track-prototype/scripts/extract-tokens.test.mjs`
- Create: `skills/track-prototype/prototype/design-kit/{components.css,wizard.css,gallery.html}`
- Create (copied assets): `skills/track-prototype/prototype/design-kit/fonts/*`

### 5a — token extractor (TDD)

- [ ] **Step 1: Write the failing test**

Create `scripts/extract-tokens.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { extractTokensCss } from "./extract-tokens.mjs";

const globals = `
:root {
  --primary: #f16b68;
  --color-light: #fff7f1;
  --radius: 0.5rem;
}
.dark { --primary: #000; }
@theme inline { --color-primary: var(--primary); }
`;

test("emits a :root block with the custom properties between markers", () => {
  const css = extractTokensCss(globals);
  assert.match(css, /GENERATED FROM ignite-next/);
  assert.match(css, /--primary:\s*#f16b68;/);
  assert.match(css, /--color-light:\s*#fff7f1;/);
  assert.match(css, /--radius:\s*0\.5rem;/);
});

test("does not include @theme inline mappings", () => {
  assert.doesNotMatch(extractTokensCss(globals), /--color-primary/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test scripts/extract-tokens.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

Create `scripts/extract-tokens.mjs`:
```javascript
// Mechanically lift the :root custom-property block from ignite-next globals.css into
// a standalone tokens.css. Run via SYNC.md when the app's design changes.
// Usage: node extract-tokens.mjs --from <path-to-ignite-next>/src/app/globals.css \
//          --out ../prototype/design-kit/tokens.css
import { readFileSync, writeFileSync } from "node:fs";

const START = "/* >>> GENERATED FROM ignite-next globals.css — DO NOT EDIT BY HAND <<< */";
const END = "/* <<< END GENERATED <<< */";

export function extractTokensCss(globalsSrc) {
  // first :root { ... } block only (not .dark, not @theme)
  const m = globalsSrc.match(/:root\s*\{([\s\S]*?)\}/);
  const body = m ? m[1] : "";
  const props = body
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => /^--[a-z0-9-]+\s*:/i.test(l));
  return `${START}\n:root {\n${props.map((p) => "  " + p).join("\n")}\n}\n${END}\n`;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const from = args[args.indexOf("--from") + 1];
  const out = args[args.indexOf("--out") + 1];
  if (!from || !out) { console.error("Usage: extract-tokens.mjs --from <globals.css> --out <tokens.css>"); process.exit(2); }
  writeFileSync(out, extractTokensCss(readFileSync(from, "utf8")));
  console.log(`Wrote ${out}`);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test scripts/extract-tokens.test.mjs`
Expected: PASS (2 tests).

- [ ] **Step 5: Generate the real tokens.css from the live app**

Run (requires the ignite-next clone; `git fetch` first per SYNC.md):
```bash
cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype
node scripts/extract-tokens.mjs --from /Users/k/code/ignite-next/src/app/globals.css --out prototype/design-kit/tokens.css
```
Expected: writes `prototype/design-kit/tokens.css` containing `--primary: #f16b68;` etc. Open it and confirm the brand colors are present.

### 5b — fonts

- [ ] **Step 6: Copy the variable fonts and append @font-face to tokens.css**

Run:
```bash
cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype/prototype/design-kit/fonts
cp /Users/k/code/ignite-next/public/fonts/HankenGrotesk-VariableFont_wght.ttf ./HankenGrotesk-Variable.ttf
cp /Users/k/code/ignite-next/public/fonts/HermeneusOne-Regular.ttf ./HermeneusOne-Regular.ttf
cp /Users/k/code/ignite-next/public/fonts/Rand-Regular.otf ./Rand-Regular.otf
ls -1
```
Expected: the three font files are present.

- [ ] **Step 7: Append `@font-face` declarations to `tokens.css`**

Append to `prototype/design-kit/tokens.css` (note the **weight range** on variable fonts — this is what lets the browser interpolate weights):
```css

/* Fonts (mirrored from ignite-next/public/fonts) */
@font-face {
  font-family: "Hanken Grotesk";
  src: url("./fonts/HankenGrotesk-Variable.ttf") format("truetype-variations");
  font-weight: 100 900;
  font-display: swap;
}
@font-face {
  font-family: "HermeneusOne";
  src: url("./fonts/HermeneusOne-Regular.ttf") format("truetype");
  font-weight: 400;
  font-display: swap;
}
@font-face {
  font-family: "Rand";
  src: url("./fonts/Rand-Regular.otf") format("opentype");
  font-weight: 400;
  font-display: swap;
}
:root { --tp-font-sans: "Hanken Grotesk", system-ui, -apple-system, sans-serif; }
```

### 5c — component + wizard CSS

These are hand-authored from the documented ignite-next classNames. **Translate Tailwind opacity modifiers (`bg-primary/90`) as `color-mix(in oklab, <var> 90%, transparent)`, not `opacity`.** Colors reference the `tokens.css` variables (use the exact var names produced in Step 5 — e.g. `--primary`, `--color-light`; adjust the names below to match what extract-tokens emitted).

- [ ] **Step 8: Write `components.css`**

Create `prototype/design-kit/components.css`:
```css
/* Buttons — mirrors src/components/ui/button.tsx cva variants */
.tp-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: .5rem;
  white-space: nowrap; border-radius: var(--radius, .5rem);
  font: 600 1rem/1.25 var(--tp-font-sans); cursor: pointer; border: 2px solid transparent;
  transition: background-color .3s ease, color .3s ease, box-shadow .3s ease;
}
.tp-btn:disabled { pointer-events: none; opacity: .5; }
.tp-btn-default { background: var(--primary); color: #fff; }
.tp-btn-default:hover { background: color-mix(in oklab, var(--primary) 90%, transparent); }
.tp-btn-lg { padding: 1rem 1.5rem; width: 100%; }

/* Text + currency inputs — mirrors .step-input */
.tp-input {
  width: 100%; box-sizing: border-box;
  border: 2px solid var(--color-mediumPlus, #e9ddd3); background: var(--color-light, #fff7f1);
  border-radius: .75rem; padding: 1rem; font: 1rem var(--tp-font-sans); color: var(--color-dark, #003250);
  transition: border-color .3s, background .3s;
}
.tp-input::placeholder { color: var(--color-mocha, #c1b7af); }
.tp-input:focus { outline: none; border-color: var(--color-mocha, #c1b7af); background: #fefaf7; }
.tp-input-wrap { position: relative; }
.tp-currency { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: var(--color-mocha, #c1b7af); }
.tp-input-currency { padding-left: 2rem; }

/* Option grids — mirrors MultiSelectInput / image-multiselect */
.tp-options-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: .75rem; }
.tp-option {
  display: flex; flex-direction: column; gap: .25rem; text-align: left;
  padding: .75rem; border-radius: .75rem; cursor: pointer;
  border: 2px solid var(--color-mediumPlus, #e9ddd3); background: var(--color-light, #fff7f1);
  color: var(--color-dark, #003250); transition: all .3s;
}
.tp-option:hover { border-color: var(--color-mocha, #c1b7af); background: var(--color-mediumPlus, #e9ddd3); }
.tp-option[aria-selected="true"] { background: var(--color-mediumPlus, #e9ddd3); box-shadow: 0 0 0 2px var(--color-mocha, #c1b7af); }
.tp-opt-desc { font-size: .75rem; color: var(--color-mocha, #c1b7af); }
.tp-opt-img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: .5rem; }

/* Banner / prose */
.tp-prose { font: 500 1rem/1.5 var(--tp-font-sans); color: var(--color-dark, #003250); margin-bottom: 1.5rem; }
.tp-banner-line { margin-top: 1rem; }

/* Celebration — mirrors CelebrationContent */
.tp-celebration { text-align: center; }
.tp-tasks { list-style: none; padding: .75rem 1rem; margin: 1rem 0; border-radius: .5rem;
  background: color-mix(in oklab, var(--color-success, #8eaf86) 10%, transparent); text-align: left; }
.tp-task::before { content: "✓ "; color: var(--color-success, #8eaf86); font-weight: 700; }
.tp-next { margin: 1.5rem 0; text-align: left; }

/* Chat bubbles — mirrors ChatInterface */
.tp-chat { display: flex; flex-direction: column; gap: .75rem; margin-bottom: 1.5rem; }
.tp-bubble { padding: .75rem 1rem; border-radius: 1rem; max-width: 85%; }
.tp-bubble-ai { background: var(--color-medium, #f2e8e0); color: var(--color-dark, #003250); align-self: flex-start; }

/* Generated AI output */
.tp-ai-output { padding: 1rem; border-radius: .75rem; background: var(--color-medium, #f2e8e0);
  color: var(--color-dark, #003250); margin-bottom: 1.5rem; white-space: pre-wrap; }
.tp-ai-placeholder { padding: 1rem; border: 2px dashed var(--color-mediumPlus, #e9ddd3);
  border-radius: .75rem; color: var(--color-mocha, #c1b7af); margin-bottom: 1.5rem; }

/* Streaming caret (used in Plan 2) */
.tp-ai-output.is-writing::after { content: "▋"; animation: tp-blink 1s steps(2) infinite; }
@keyframes tp-blink { 50% { opacity: 0; } }
```

> **Remaining fieldType components to add as encountered**, each translated from its source (do NOT invent styling — copy the documented classNames): `education` & `work` (structured forms — `src/components/SubStepRenderer.tsx` inline `EducationInput`/`WorkInput`), `dream-job-select` & `dream-job-requirements` (accordion — `src/components/fields/DreamJob*Input.tsx`), `dropdown-with-checkboxes` (`WheelWithCheckboxesInput`), `assessment-results` (`AssessmentResultsField`). For Plan 1 these render via the generic collect/text and results fallbacks already in `render-substep.mjs`; promote them to bespoke components only when a track that uses them is previewed.

- [ ] **Step 9: Write `wizard.css`**

Create `prototype/design-kit/wizard.css`:
```css
* { box-sizing: border-box; }
body { margin: 0; background: var(--color-medium, #f2e8e0); font-family: var(--tp-font-sans); }
.tp-frame { max-width: 480px; margin: 2rem auto; background: var(--color-light, #fff7f1);
  min-height: 80vh; border-radius: 1.5rem; box-shadow: 0 10px 40px rgba(0,0,0,.12);
  display: flex; flex-direction: column; overflow: hidden; }
.tp-header { padding: 1rem 1.25rem; }
.tp-progress { height: 6px; background: var(--color-mediumPlus, #e9ddd3); border-radius: 999px; overflow: hidden; }
.tp-progress-bar { height: 100%; width: 0; background: var(--primary, #f16b68); transition: width .3s ease; }
.tp-body { flex: 1; padding: 1.5rem 1.25rem; }
.tp-screen { animation: tp-fade .3s ease; }
@keyframes tp-fade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.tp-footer { padding: 1rem 1.25rem; display: flex; gap: .5rem; }
.tp-back { background: none; border: none; color: var(--color-mocha, #c1b7af); cursor: pointer; font: 1rem var(--tp-font-sans); }
.tp-watermark { position: fixed; bottom: 8px; right: 8px; z-index: 9999; font: 11px/1 var(--tp-font-sans);
  padding: 4px 8px; border-radius: 4px; background: rgba(0,0,0,.06); color: var(--color-mocha, #c1b7af); pointer-events: none; }
```

- [ ] **Step 10: Write the static `gallery.html` for visual QA**

Create `prototype/design-kit/gallery.html` — a static page that includes `tokens.css`, `components.css`, `wizard.css` and shows one of each component (a `.tp-btn-default`, a `.tp-input`, a `.tp-options-grid` with two `.tp-option`s, a celebration block, a chat bubble). Use it only to eyeball the kit.
```html
<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="tokens.css"><link rel="stylesheet" href="components.css"><link rel="stylesheet" href="wizard.css">
</head><body><div class="tp-frame"><div class="tp-body">
  <button class="tp-btn tp-btn-default tp-btn-lg">Continue</button>
  <p></p><input class="tp-input" placeholder="Type your answer…">
  <div class="tp-options-grid" style="margin-top:1rem">
    <button class="tp-option"><span>Option A</span><span class="tp-opt-desc">desc</span></button>
    <button class="tp-option" aria-selected="true"><span>Option B</span></button>
  </div>
  <div class="tp-celebration" style="margin-top:1rem"><p class="tp-prose">You did it!</p>
    <ul class="tp-tasks"><li class="tp-task">Mapped your values</li></ul></div>
  <div class="tp-chat"><div class="tp-bubble tp-bubble-ai">Hi, let's talk.</div></div>
</div></div></body></html>
```

- [ ] **Step 11: Visually verify the kit with Playwright**

Run:
```bash
cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype/prototype/design-kit
npx --yes serve . -p 4100 &
sleep 1
npx --yes playwright screenshot --viewport-size=480,900 http://localhost:4100/gallery.html /tmp/tp-gallery.png
```
Then open `/tmp/tp-gallery.png` and confirm: coral Continue button (`#f16b68`), cream background (`#fff7f1`), navy text, the selected option has the mocha ring, Hanken Grotesk is loading (rounded, not Times). Kill the server: `kill %1`.

- [ ] **Step 12: Commit**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/scripts/extract-tokens.* skills/track-prototype/prototype/design-kit/
git commit -m "feat(track-prototype): design kit — generated tokens, fonts, component + wizard CSS"
```

---

## Task 6: `player.js` — browser entry that wires the DOM

**Files:**
- Create: `skills/track-prototype/prototype/player.js`

No unit test (DOM/browser); verified end-to-end by the Playwright walkthrough in Task 8. Imports the already-tested `player-core.mjs` and `interpolate.mjs`.

- [ ] **Step 1: Write `player.js`**

Create `prototype/player.js`:
```javascript
import { flattenSubsteps, nextIndex, prevIndex, clampIndex, progressPct } from "./player-core.mjs";
import { interpolate } from "../scripts/lib/interpolate.mjs"; // build copies this next to player — see Task 7

const KEY = "tp.v1";
const track = window.__TRACK__;            // injected by build (the full track object)
const screens = window.__SCREENS__;        // injected by build: array of pre-rendered HTML strings
const subs = flattenSubsteps(track);
const root = document.getElementById("tp-body");
const bar = document.getElementById("tp-progress-bar");

let state = load();

function load() {
  try { const s = JSON.parse(localStorage.getItem(KEY)); if (s) return { i: clampIndex(s.i, subs.length), answers: s.answers || {} }; }
  catch { /* corrupt — fall through */ }
  return { i: 0, answers: {} };
}
function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }

function render() {
  root.innerHTML = interpolate(screens[state.i], state.answers); // fill {slug} live
  bar.style.width = progressPct(state.i, subs.length) + "%";
  wire();
}

function captureCurrent() {
  const input = root.querySelector("[data-input]");
  if (input && input.dataset.slug) state.answers[input.dataset.slug] = input.value.trim();
  const grid = root.querySelector("[data-slug][data-multi]");
  if (grid) {
    const chosen = [...grid.querySelectorAll('[data-option][aria-selected="true"]')].map((b) => b.dataset.value);
    if (chosen.length) state.answers[grid.dataset.slug] = chosen.join(", ");
  }
}

function advance() { captureCurrent(); state.i = nextIndex(state.i, subs.length); persist(); render(); }
function back() { state.i = prevIndex(state.i, subs.length); persist(); render(); }

function wire() {
  root.querySelector("[data-next]")?.addEventListener("click", advance);
  document.getElementById("tp-back")?.toggleAttribute("disabled", state.i === 0);
  root.querySelectorAll("[data-option]").forEach((opt) => opt.addEventListener("click", () => {
    const grid = opt.closest("[data-slug]");
    const multi = grid?.dataset.multi === "true";
    if (!multi) grid.querySelectorAll("[data-option]").forEach((o) => o.setAttribute("aria-selected", "false"));
    opt.setAttribute("aria-selected", opt.getAttribute("aria-selected") === "true" ? "false" : "true");
  }));
  root.querySelector("[data-input]")?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); advance(); } });
}

document.getElementById("tp-back").addEventListener("click", back);
document.getElementById("tp-reset")?.addEventListener("click", () => { localStorage.removeItem(KEY); state = { i: 0, answers: {} }; render(); });
render();
```

- [ ] **Step 2: Commit**

```bash
git add skills/track-prototype/prototype/player.js
git commit -m "feat(track-prototype): browser player wiring (advance/back/progress/capture)"
```

---

## Task 7: `build-prototype.mjs` — generator (track.json → prototype-build/)

**Files:**
- Create: `skills/track-prototype/prototype/template.html`
- Create: `skills/track-prototype/scripts/build-prototype.mjs`
- Test: `skills/track-prototype/scripts/build-prototype.test.mjs`

- [ ] **Step 1: Write `template.html`**

Create `prototype/template.html` (`__HEAD__`/`__DATA__` are replaced by the build):
```html
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Track Preview</title>
<link rel="stylesheet" href="design-kit/tokens.css">
<link rel="stylesheet" href="design-kit/components.css">
<link rel="stylesheet" href="design-kit/wizard.css">
</head><body>
<div class="tp-frame">
  <div class="tp-header"><div class="tp-progress"><div class="tp-progress-bar" id="tp-progress-bar"></div></div></div>
  <div class="tp-body" id="tp-body"></div>
  <div class="tp-footer"><button class="tp-back" id="tp-back">← Back</button></div>
</div>
<div class="tp-watermark">approximate preview — mirrors app design, built __DATE__</div>
<script>window.__TRACK__ = __TRACK__; window.__SCREENS__ = __SCREENS__;</script>
<script type="module" src="player.js"></script>
</body></html>
```

- [ ] **Step 2: Write the failing test**

Create `scripts/build-prototype.test.mjs`:
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSite } from "./build-prototype.mjs";

const track = { id: "t", title: "Demo", steps: [{ id: "s", title: "S", substeps: [
  { id: "ss1", slug: "name", title: "Name", prompt: "Your name?", type: "collect", fieldType: "text" },
  { id: "ss2", title: "Hi", prompt: "Hi {name}!", type: "say", fieldType: "banner" },
  { id: "ss3", slug: "cs", title: "Draft", prompt: "Here's a draft:", type: "generate", fieldType: "text" },
]}]};

test("buildSite returns index.html with injected track + screens", () => {
  const { indexHtml, screens } = buildSite(track, { samples: { cs: "Sample draft." }, date: "2026-06-03" });
  assert.equal(screens.length, 3);
  assert.match(indexHtml, /window\.__TRACK__ =/);
  assert.match(indexHtml, /built 2026-06-03/);
  // baked sample present in the generate screen
  assert.ok(screens.some((s) => s.includes("Sample draft.")));
  // {name} token preserved raw for runtime interpolation
  assert.ok(screens.some((s) => s.includes("Hi {name}!")));
});

test("buildSite throws on a token used before it is produced", () => {
  const bad = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "Hi {name}", type: "say", fieldType: "banner" },
  ]}]};
  assert.throws(() => buildSite(bad, {}), /\{name\}/);
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `node --test scripts/build-prototype.test.mjs`
Expected: FAIL — module not found.

- [ ] **Step 4: Write minimal implementation**

Create `scripts/build-prototype.mjs`:
```javascript
import { readFileSync, writeFileSync, mkdirSync, cpSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { renderSubstep } from "./lib/render-substep.mjs";
import { findOrderingErrors } from "./lib/ordering-lint.mjs";
import { flattenSubsteps } from "../prototype/player-core.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PROTO = join(HERE, "..", "prototype");

export function buildSite(track, opts = {}) {
  const errs = findOrderingErrors([track], { assume: opts.assume || [] });
  if (errs.length) throw new Error("Token ordering errors:\n" + errs.join("\n"));
  const ctx = { samples: opts.samples || {} };
  const screens = flattenSubsteps(track).map((sub) => renderSubstep(sub, ctx));
  const template = readFileSync(join(PROTO, "template.html"), "utf8");
  const indexHtml = template
    .replace("__TRACK__", JSON.stringify(track))
    .replace("__SCREENS__", JSON.stringify(screens))
    .replace("__DATE__", opts.date || "");
  return { indexHtml, screens };
}

function parseArgs(argv) {
  const get = (flag) => { const i = argv.indexOf(flag); return i !== -1 ? argv[i + 1] : undefined; };
  return { file: argv.find((a) => !a.startsWith("--") && a.endsWith(".json")),
    persona: get("--persona"), samplesPath: get("--samples"),
    out: get("--out") || "prototype-build", assume: (get("--assume") || "").split(",").filter(Boolean) };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const { file, samplesPath, out, assume } = parseArgs(process.argv.slice(2));
  if (!file) { console.error("Usage: build-prototype.mjs <track.json> [--persona name] [--samples samples.json] [--out dir] [--assume a,b]"); process.exit(2); }
  const track = JSON.parse(readFileSync(file, "utf8"));
  const samples = samplesPath ? JSON.parse(readFileSync(samplesPath, "utf8")) : {};
  const date = new Date().toISOString().slice(0, 10);
  const { indexHtml } = buildSite(track, { samples, assume, date });
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, "index.html"), indexHtml);
  cpSync(join(PROTO, "design-kit"), join(out, "design-kit"), { recursive: true });
  cpSync(join(PROTO, "player.js"), join(out, "player.js"));
  cpSync(join(PROTO, "player-core.mjs"), join(out, "player-core.mjs"));
  mkdirSync(join(out, "scripts", "lib"), { recursive: true });
  cpSync(join(HERE, "lib", "interpolate.mjs"), join(out, "scripts", "lib", "interpolate.mjs"));
  console.log(`Built ${out}/`);
}
```

> Note: the CLI copies `interpolate.mjs` into the build at `scripts/lib/` so `player.js`'s `import "../scripts/lib/interpolate.mjs"` resolves from `prototype-build/`. The `gallery.html` is part of `design-kit/` and ships harmlessly.

- [ ] **Step 5: Run test to verify it passes**

Run: `node --test scripts/build-prototype.test.mjs`
Expected: PASS (2 tests).

- [ ] **Step 6: Run the full suite**

Run: `cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype && node --test scripts/**/*.test.mjs`
Expected: PASS across all suites.

- [ ] **Step 7: Commit**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/prototype/template.html skills/track-prototype/scripts/build-prototype.*
git commit -m "feat(track-prototype): static-site generator (track.json -> prototype-build/)"
```

---

## Task 8: End-to-end on a real example track + Playwright walkthrough

**Files:**
- (uses) `skills/track-design/references/examples/clarity-track.md` as the content source
- Create (temp, not committed): a real `clarity.track.json`

The track-design examples are markdown walk-throughs, not raw JSON. For this end-to-end, hand-assemble a small valid `clarity.track.json` (5–8 substeps spanning `say`, `collect/text`, `collect/multi-select`, `generate`, and a `celebration`) from the clarity example. This is throwaway test input.

- [ ] **Step 1: Create a minimal real `clarity.track.json`**

Create `/tmp/clarity.track.json` with one track, one step, and substeps covering: a `say/banner` intro, a `collect/text` name capture (slug `name`), a `collect/multi-select` values pick (slug `values`), a `generate` that references `{name}` and `{values}`, and a `say/celebration`. Ensure tokens are produced before use (name + values before the generate).

- [ ] **Step 2: Validate it against the track-design validator (the input gate)**

Run:
```bash
cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype
node ../track-design/scripts/validate-track-json.mjs /tmp/clarity.track.json
```
Expected: `OK — valid`. If it errors, fix the JSON until it passes (this is the real Phase-6 gate).

- [ ] **Step 3: Author samples + build**

Create `/tmp/samples.json` = `{ "<generate-slug>": "Marcus, given your values of Justice and Growth, here's a first draft of your direction…" }`, then:
```bash
node scripts/build-prototype.mjs /tmp/clarity.track.json --persona "Marcus (anxious first-gen)" --samples /tmp/samples.json --out /tmp/clarity-build
```
Expected: `Built /tmp/clarity-build/`. Confirm `/tmp/clarity-build/index.html`, `design-kit/`, `player.js` exist.

- [ ] **Step 4: Serve and walk it with Playwright (the smoke test)**

Create `scripts/walk.mjs` (a one-off harness — commit it, it's reusable for Plan 3):
```javascript
import { chromium } from "playwright";
const URL = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 480, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(URL, { waitUntil: "domcontentloaded" });
const problems = [];
for (let step = 1; step <= 25; step++) {
  await page.waitForTimeout(300);
  const text = (await page.evaluate(() => document.body.innerText)).trim();
  if (text.length < 3) problems.push(`step ${step}: BLANK`);
  if (/\{[a-z0-9-]+\}/i.test(text)) problems.push(`step ${step}: UNRESOLVED TOKEN`);
  await page.screenshot({ path: `/tmp/tp-step-${String(step).padStart(2, "0")}.png` });
  const next = page.getByRole("button", { name: /continue|next|okay|got it/i });
  if (await next.count() === 0) break;
  // fill any visible text input so required-ish flows advance
  const input = page.locator("[data-input]");
  if (await input.count()) await input.first().fill("Marcus").catch(() => {});
  const before = await page.evaluate(() => document.body.innerText);
  await next.first().click().catch(() => {});
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => document.body.innerText);
  if (before === after) { problems.push(`step ${step}: STUCK (no advance)`); break; }
}
console.log(JSON.stringify({ problems, pageErrors: errors }, null, 2));
await browser.close();
if (problems.length || errors.length) process.exit(1);
```
Run:
```bash
cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype
npx --yes serve /tmp/clarity-build -p 3000 &
sleep 1
node scripts/walk.mjs http://localhost:3000
kill %1
```
Expected: `{"problems": [], "pageErrors": []}` and exit 0. Open `/tmp/tp-step-*.png` and confirm: the intro banner, the name input, the values multi-select, the generate screen showing the baked sample with `{name}`→"Marcus" resolved, and the celebration. If `UNRESOLVED TOKEN` appears, a `{slug}` is used before capture — fix the track or the interpolation path.

- [ ] **Step 5: Commit the reusable walk harness**

```bash
git add skills/track-prototype/scripts/walk.mjs
git commit -m "test(track-prototype): Playwright walk harness + verified clarity build end-to-end"
```

---

## Task 9: Netlify deploy wiring + SYNC.md + handoff

**Files:**
- Create: `skills/track-prototype/prototype/SYNC.md`
- Modify: `skills/track-prototype/SKILL.md` (deploy specifics)

- [ ] **Step 1: Write `SYNC.md`**

Create `prototype/SYNC.md`:
```markdown
# Syncing the design kit from ignite-next

The design kit is HAND-MIRRORED from ignite-next and drifts. Re-sync when the app's
visual language changes.

**Pinned source commit:** <record the ignite-next commit SHA the kit was last mirrored from>

## Steps
1. `cd /path/to/ignite-next && git fetch && git log -1 --format=%H` — note the new SHA.
   (The local clone may be months stale — always fetch first.)
2. Regenerate tokens:
   `node scripts/extract-tokens.mjs --from <ignite-next>/src/app/globals.css --out prototype/design-kit/tokens.css`
   A non-empty `git diff` on tokens.css is your drift alarm.
3. Diff the renderers since the pinned SHA:
   `git -C <ignite-next> diff <pinned-sha>..HEAD -- src/components/SubStepRenderer.tsx src/components/fields src/components/ui/button.tsx src/app/globals.css`
   Hand-update `components.css` / `render-substep.mjs` for any changed classNames.
4. Re-run `gallery.html` through Playwright (Task 5 Step 11) and eyeball.
5. Update the pinned SHA above and the watermark date.

## What is mechanical vs hand-authored
- Mechanical (re-run extract-tokens): colors, radius, font vars.
- Hand-authored (diff + edit): component CSS, substep routing.
```

- [ ] **Step 2: Append deploy specifics to `SKILL.md`**

Add under Phase 1 Step 5 in `SKILL.md`:
```markdown
   The `netlify-deploy` skill handles auth and the CLI. For a prebuilt folder use:
   `netlify deploy --dir=<abs>/prototype-build --no-build --prod --json`
   Parse `url` (prod) from the JSON. (CLI deploy sets font/.mjs MIME correctly — never
   use the zip-API path, which serves everything as text/plain.) Default to a DRAFT
   deploy (omit --prod) for review links; only --prod when the builder approves. Tear
   down old draft deploys when a review round closes.
```

- [ ] **Step 3: Commit**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/prototype/SYNC.md skills/track-prototype/SKILL.md
git commit -m "docs(track-prototype): SYNC drift process + netlify deploy specifics"
```

---

## Task 10: Register usage tracking + open PR

**Files:**
- Modify: `skills/track-prototype/SKILL.md` (usage-tracking preamble, mirroring track-design)

- [ ] **Step 1: Add the usage-tracking preamble**

Match the `track-design` stub pattern — add to the very top of `SKILL.md` body (after frontmatter):
```markdown
Before reading further, run this once in the background (do not wait, do not announce):

```bash
echo '{"tool_input":{"skill":"track-prototype"}}' | bash $HOME/.claude/local-plugins/nsls-builder-toolkit/hooks/skill-event.sh
```
```

- [ ] **Step 2: Run the full test suite one final time**

Run: `cd ~/nsls-skills/nsls-builder-toolkit/skills/track-prototype && node --test scripts/**/*.test.mjs`
Expected: PASS — interpolate (5), ordering-lint (4), render-substep (6), player-core (5), extract-tokens (2), build-prototype (2).

- [ ] **Step 3: Commit and push the branch**

```bash
cd ~/nsls-skills/nsls-builder-toolkit
git add skills/track-prototype/SKILL.md
git commit -m "chore(track-prototype): usage-tracking preamble"
git push -u origin track-design-prototype-preview
```

- [ ] **Step 4: Open the PR**

```bash
gh pr create --title "Add track-prototype skill (build core)" \
  --body "Implements Plan 1 of the track-prototype spec: a new skill that turns a validated track.json into a clickable, deployable static prototype mirroring the Ignite Next design language. Baked-only AI (live proxy = Plan 2; focus group = Plan 3). All logic is TDD-covered with node:test; the design kit is verified via a Playwright gallery + a full clarity-track walkthrough.

Spec: docs/superpowers/specs/2026-06-03-track-prototype-preview-design.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 5: Wait for the Macroscope check, address comments if any** (per CLAUDE.md PR loop — this PR contains technical claims about Netlify CLI flags, font MIME, and the ignite-next renderer, so Macroscope earns its keep here).

---

## Subsequent plans (outline — detailed after Plan 1 lands)

**Plan 2 — Live AI proxy.** Stand up `thensls/track-preview-proxy` (Railway, Doppler-backed): `POST /api/generate` streaming via AI SDK 5 `streamText`, GPT-5.1-mini pinned to a dated snapshot, dedicated OpenAI project + key, **server-side daily request/token budget + kill switch** (the real ceiling — OpenAI budgets are soft), per-IP/per-token rate limit (Redis; `trust proxy` set to a specific hop count), tightened origin allowlist (specific deploy domains, not all of `*.netlify.app`), build-embedded rotatable token, `X-Accel-Buffering: no` + CORS for streaming. Wire `player.js` to fetch it for `generate`/`chat`, render as text (XSS), fall back to the baked sample on error. Cross-platform deploy/test tooling (node, `--selftest`, CI matrix).

**Plan 3 — Focus group, rubric, scoring, ledger, calibration.** Phase 2 of the skill: extend `walk.mjs` into a full screenshot-gallery walkthrough; member personas (warm temp) react independently; an adversarial skeptic; 4 experts score the 4-dimension binary rubric (median-of-3, evidence-citation, CONTESTED→human); emit `conversation.md` + structured `recommendations.md` + `scorecard.md` + a `gdoc-build` Google Doc (python-docx, draft-only, org-restricted); write the Airtable "Track Previews" ledger (base-scoped token, version-aware `content_hash` join key) + render `scores.md`; the "implement the focus-group changes" loop. **Seed calibration now** by scoring Clarity + Personal Insights and pulling their real PostHog completion/drop-off as the first two directional rows.

---

## Self-Review

**Spec coverage (Plan 1 scope = decision A new skill + baked build path):**
- New `track-prototype` skill gated on Phase-6 validator → Task 0, Task 8 Step 2. ✓
- Baked-in design kit (tokens mechanically extracted, components hand-authored, local fonts) → Task 5. ✓
- Drift seam (extract-tokens + SYNC.md pinned to commit SHA + watermark) → Task 5, Task 9. ✓
- Vanilla player (state machine, token interpolation single-pass+escape+leave-literal, localStorage versioned+clamp, ordering lint) → Tasks 1,2,4,6. ✓
- Substep renderer routed by type/fieldType mirroring SubStepRenderer.tsx → Task 3. ✓
- Baked AI samples for generate/chat (illustrative, not production) → Task 3, Task 7, SKILL.md. ✓
- Build → local `npx serve` → Netlify deploy via netlify-deploy (`--no-build --json`) → Tasks 7,8,9. ✓
- Playwright walkthrough asserting no dead-ends / blank / unresolved tokens → Task 8. ✓
- "Seed only synthetic personas, never real member data" → SKILL.md Operating Rules. ✓
- Live proxy, focus group, Airtable, calibration → explicitly deferred to Plans 2 & 3. ✓ (out of Plan 1 scope by design)

**Placeholder scan:** No "TBD/handle errors/similar to". The one itemized "remaining fieldType components" note in Task 5 lists exact source files/classNames to translate and states the Plan-1 fallback behavior — actionable, not vague. ✓

**Type/name consistency:** `flattenSubsteps`, `nextIndex`, `prevIndex`, `clampIndex`, `progressPct` (player-core) used identically in player.js and build. `interpolate`/`escapeHtml` consistent. `renderSubstep(sub, ctx)` with `ctx.samples` consistent across render + build. `buildSite(track, opts)` returns `{indexHtml, screens}` used in test + CLI. data-hooks (`data-next`, `data-input`, `data-slug`, `data-option`, `data-multi`, `aria-selected`) consistent between render-substep and player.js. ✓
