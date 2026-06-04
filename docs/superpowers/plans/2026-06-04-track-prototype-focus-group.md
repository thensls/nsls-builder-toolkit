# Track Prototype — Focus Group, Rubric & Calibration (Plan 3 of 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax. NOTE: this plan mixes two work types — **(A) authored skill content** (rubric + panel reference files + the Phase-2 procedure; not unit-testable) and **(B) pure testable libs** (scoring aggregation, recommendations, ledger, calibration stats). Each task is tagged [AUTHOR] or [TDD].

**Goal:** Add Phase 2 to the `track-prototype` skill: run a rendered prototype through a structured synthetic focus group (member personas + an adversarial skeptic + 4 experts), score it on a 4-dimension **binary MET/UNMET rubric**, emit a Google Doc + machine-actionable markdown + a versioned score ledger, drive the "implement the focus-group changes" iteration loop, and **seed calibration against the two live tracks** (Clarity, Personal Insights).

**Architecture:** A Playwright walkthrough produces a screenshot gallery + `report.json`. An orchestrated panel reacts and scores under a strict anti-groupthink protocol (independent reactions → blind expert scoring → informed revision → adversarial pass → aggregate). All judge output is **structured** so pure aggregation code (`scorecard.mjs`) turns raw verdicts into MET/UNMET/CONTESTED → dimension rollups → checks-met total → ship-bar recommendations. Results are written to a local `scores.md` and a canonical Airtable "Track Previews" base (version-aware join key) for the future PostHog calibration. Scores are **a relative ranking + ship-bar gate, not a calibrated prediction** — synthetic personas overstate adoption; the rubric's predictive validity is unproven until calibration data accrues.

**Tech Stack:** Node v22 ESM, `node:test`. Orchestration via parallel sub-agents with structured output (the skill instructs the run; warm temp for personas, low temp for expert scorers, median-of-N sampling). `gdoc-build` (python-docx) for the Doc; Airtable Web API for the ledger; the `posthog` skill (HogQL) for calibration actuals.

**Decisions carried in (spec §8, §9, §14-C):** 4 dimensions, no weights, binary anchored sub-checks; median-of-3; temperature split; explicit adversarial skeptic; evidence-citation; ranking-not-prediction; ship-bar fires on any UNMET; CONTESTED → human review. Airtable canonical + local `scores.md` mirror; version/content-hash join. Calibration seeds NOW against Clarity + Personal Insights (~1,000 users each) as a directional sanity check.

**Spec:** `docs/superpowers/specs/2026-06-03-track-prototype-preview-design.md` (§8.4 rubric, §9 ledger/calibration). **Builds on:** Plan 1 (the build + `walk.mjs`) and benefits from Plan 2 (live AI), but works against a baked-only build too.

---

## File structure (added to `skills/track-prototype/`)

```
references/
  focus-group-rubric.md        # [AUTHOR] 4 dims × 4 sub-checks, MET/UNMET anchors, scoring protocol, PostHog map
  focus-group-panel.md         # [AUTHOR] member personas + 4 experts + adversarial; the staged anti-groupthink flow
  schemas/
    persona-reaction.json      # structured-output schema for a persona's screen-by-screen reactions
    expert-verdict.json        # structured-output schema: per-sub-check MET/UNMET + evidence + rationale
scripts/
  walk-gallery.mjs             # [extends walk.mjs] screenshots every screen + emits report.json
  lib/
    scorecard.mjs              # [TDD] verdicts -> MET/UNMET/CONTESTED -> dim rollup -> total -> ship-bar
    scorecard.test.mjs
    recommendations.mjs        # [TDD] scorecard + rationales -> structured recommendations.md model
    recommendations.test.mjs
    scores-ledger.mjs          # [TDD] render/append the local focus-group/scores.md row
    scores-ledger.test.mjs
    airtable-record.mjs        # [TDD] build the ScoreRun field payload (field NAMES; gotcha-safe)
    airtable-record.test.mjs
    calibration.mjs            # [TDD] spearman, kendallTau, gwetAC2, version-aware join
    calibration.test.mjs
  ledger-write.mjs             # CLI: POST a ScoreRun to Airtable (uses airtable-record + a base-scoped token)
  calibrate.mjs               # CLI: join ScoreRuns↔PostHogActuals, print rank-correlation + the spread
SKILL.md                       # + Phase 2 procedure, the iteration loop, the calibration-seed step
```
Per-run output (in the builder's track dir): `focus-group/v{N}/{conversation.md, recommendations.md, scorecard.md}`, `focus-group/scores.md`, plus screenshots under `focus-group/v{N}/shots/`.

---

## Task 1 [AUTHOR]: `references/focus-group-rubric.md`

**Files:** Create `skills/track-prototype/references/focus-group-rubric.md`

- [ ] **Step 1: Write the rubric reference.** Encode the 4 dimensions, each as 4 binary MET/UNMET sub-checks judged **from the run-through** (screenshots + click-through), with a one-line anchor per sub-check describing what MET looks like. Use the exact sub-checks from spec §8.4:

  - **D1 Value / payoff** — (a) deliverable named concretely on screen 1–2; (b) "why this matters to me" stated, not implied; (c) a tangible artifact/clarity exists at completion; (d) ending previews/motivates the next step.
  - **D2 Pacing & momentum** — (a) no step >~8 collects without a break; (b) no wall-of-text screen; (c) each step names the specific accomplishment; (d) the sequence creates forward pull.
  - **D3 Copy & tone** — (a) peer/coach voice, not corporate/condescending; (b) no unexplained jargon; (c) tokens read naturally; (d) on-brand for Society.
  - **D4 Friction & fit** — (a) low-friction first win; (b) later screens build on earlier answers; (c) nothing invasive/privilege-assuming early; (d) an anxious/skeptical edge persona would stay in.

  Then document the **scoring protocol**: each sub-check is judged by the median of 3 independent samples; majority MET/UNMET, else **CONTESTED**. **Ship-bar: any UNMET → a ranked recommendation; CONTESTED → a human-review flag.** The "score" is **checks-met / 16** (e.g., 11/16); progress = checks turning green across versions. Include the PostHog-metric map (D1→start rate, D2→mid-track drop-off/continuation, D3→completion/sentiment, D4→at-risk drop-off) and a bold caveat: **scores are a relative ranking + gate, NOT a calibrated prediction** — synthetic personas overstate adoption; validity is unproven until calibration.

- [ ] **Step 2: Commit** `docs(track-prototype): focus-group rubric reference (4 dims, binary sub-checks)`.

---

## Task 2 [AUTHOR]: `references/focus-group-panel.md` + the anti-groupthink protocol

**Files:** Create `skills/track-prototype/references/focus-group-panel.md`; create `references/schemas/persona-reaction.json`, `references/schemas/expert-verdict.json`

- [ ] **Step 1: Define the panel.** Member personas reuse `references/member-personas.md` (5 registers + 2 edge). Four experts: **UX Designer** (load/pacing/peak-end), **Educational Designer** (does the learning land; scaffolding; is the deliverable real), **Copywriter** (voice/tone/Society fit), **Product/Engagement Strategist** (adoption/retention mechanics, value-promise strength, predicted drop-off).

- [ ] **Step 2: Write the staged protocol** (the research's anti-groupthink design — this is the load-bearing part):
  1. **Stage 1 — Personas react INDEPENDENTLY.** Each persona, in its own isolated context (no shared thread), walks the screenshots and produces structured reactions. **Warm temperature (~0.7–1.0)** to preserve diversity. They do NOT see each other. Edge personas get explicit weight.
  2. **Stage 2 — Experts score BLIND.** Each of the 4 experts independently scores all 16 sub-checks from the run-through, **3 samples each at low temp (~0.1)**, justification-before-verdict, citing the specific screen as evidence. They do NOT see personas or each other.
  3. **Stage 3 — Experts revise INFORMED.** Experts now see the *aggregated, anonymized* persona reactions (not individual voices) and may revise, stating what changed and why.
  4. **Stage 4 — Adversarial pass.** A designated **skeptic** argues each dimension is over-scored and surfaces the abandonment/negative-experience case the others omit; experts respond. Counteracts the documented upward adoption bias of synthetic personas.
  5. **Stage 5 — Aggregate** (code, Task 3): per sub-check median across all expert samples → MET/UNMET/CONTESTED → dimension rollup → total → ship-bar.

  Encode anti-groupthink rules explicitly: independent commitment before any shared visibility; only aggregated/anonymized cross-agent visibility; mandatory contrarian; randomize sub-check order; use a different model family for judges than for any generated track copy (self-preference guard).

- [ ] **Step 3: Write the structured-output schemas.**
  `persona-reaction.json`: `{ persona, perScreen: [{ screen, reaction, wouldContinue: bool, friction?: string }], wouldDrop: bool, dropScreen?: number }`.
  `expert-verdict.json`: `{ expert, sample, dimensions: [{ dim, subChecks: [{ key, verdict: "MET"|"UNMET", evidenceScreen, rationale }] }] }`.

- [ ] **Step 4: Commit** `docs(track-prototype): focus-group panel + anti-groupthink protocol + output schemas`.

---

## Task 3 [TDD]: `scorecard.mjs` — verdict aggregation

**Files:** Create `scripts/lib/scorecard.mjs`; Test `scripts/lib/scorecard.test.mjs`

- [ ] **Step 1: Write the failing test**
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { aggregateSubcheck, buildScorecard } from "./scorecard.mjs";

test("aggregateSubcheck: majority MET/UNMET, else CONTESTED", () => {
  assert.equal(aggregateSubcheck(["MET", "MET", "MET"]), "MET");
  assert.equal(aggregateSubcheck(["UNMET", "UNMET", "MET"]), "UNMET");
  assert.equal(aggregateSubcheck(["MET", "UNMET", "MET"]), "MET");      // 2/3 -> MET
  assert.equal(aggregateSubcheck(["MET", "UNMET"]), "CONTESTED");        // no clear majority
});

test("buildScorecard rolls up dims, total, and ship-bar list", () => {
  // 4 dims × 4 sub-checks; feed verdict arrays per (dim,key)
  const allMet = (k) => ["MET", "MET", "MET"];
  const dims = ["value", "pacing", "copy", "fit"];
  const samples = {};
  for (const d of dims) for (const k of ["a","b","c","d"]) samples[`${d}.${k}`] = allMet();
  samples["value.c"] = ["UNMET","UNMET","MET"];   // one UNMET
  samples["copy.b"] = ["MET","UNMET"];            // one CONTESTED
  const sc = buildScorecard(samples, dims);
  assert.equal(sc.total, 14);                      // 16 - 1 unmet - 1 contested counted as not-met
  assert.equal(sc.dimensions.value.met, 3);
  assert.equal(sc.shipBar.length, 1);              // only UNMET fires a recommendation
  assert.equal(sc.contested.length, 1);            // CONTESTED -> human review
  assert.equal(sc.composite, "14/16");
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `scripts/lib/scorecard.mjs`**
```javascript
export function aggregateSubcheck(verdicts) {
  const met = verdicts.filter((v) => v === "MET").length;
  const frac = met / verdicts.length;
  if (frac >= 0.66) return "MET";
  if (frac <= 0.34) return "UNMET";
  return "CONTESTED";
}

const SUBCHECKS = ["a", "b", "c", "d"];

export function buildScorecard(samples, dims) {
  const dimensions = {};
  const shipBar = [];     // UNMET sub-checks -> recommendations
  const contested = [];   // CONTESTED -> human review
  let total = 0;
  for (const d of dims) {
    let met = 0;
    const checks = {};
    for (const k of SUBCHECKS) {
      const verdict = aggregateSubcheck(samples[`${d}.${k}`] || []);
      checks[k] = verdict;
      if (verdict === "MET") { met++; total++; }
      else if (verdict === "UNMET") shipBar.push({ dim: d, key: k });
      else contested.push({ dim: d, key: k });
    }
    dimensions[d] = { met, checks };
  }
  return { dimensions, total, composite: `${total}/${dims.length * 4}`, shipBar, contested };
}
```

- [ ] **Step 4: Run → PASS. Commit** `feat(track-prototype): scorecard aggregation (MET/UNMET/CONTESTED, ship-bar)`.

---

## Task 4 [TDD]: `recommendations.mjs` — structured, machine-actionable recs

**Files:** Create `scripts/lib/recommendations.mjs`; Test `scripts/lib/recommendations.test.mjs`

- [ ] **Step 1: Write the failing test**
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildRecommendations } from "./recommendations.mjs";

const scorecard = {
  shipBar: [{ dim: "value", key: "c" }],
  contested: [{ dim: "copy", key: "b" }],
};
const rationales = {
  "value.c": { rationale: "No tangible artifact at the end.", substep: "ss_done", change: "Add a saved summary card the student can reference." },
  "copy.b": { rationale: "Judges split on jargon in step 2.", substep: "ss_values", change: "Reviewers disagree — human check." },
};

test("UNMET -> fix rec; CONTESTED -> review rec; structured shape", () => {
  const recs = buildRecommendations(scorecard, rationales);
  assert.equal(recs.length, 2);
  const fix = recs.find((r) => r.severity === "fix");
  assert.deepEqual(
    { d: fix.dimension, s: fix.sub_check, sub: fix.substep },
    { d: "value", s: "c", sub: "ss_done" }
  );
  assert.ok(recs.some((r) => r.severity === "review" && r.dimension === "copy"));
  assert.ok(recs.every((r) => r.id));   // every rec has a stable id
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `scripts/lib/recommendations.mjs`**
```javascript
export function buildRecommendations(scorecard, rationales = {}) {
  const out = [];
  const push = (dim, key, severity) => {
    const r = rationales[`${dim}.${key}`] || {};
    out.push({ id: `${dim}-${key}-${severity}`, dimension: dim, sub_check: key, severity,
      substep: r.substep || null, rationale: r.rationale || "", change: r.change || "" });
  };
  for (const { dim, key } of scorecard.shipBar) push(dim, key, "fix");
  for (const { dim, key } of scorecard.contested) push(dim, key, "review");
  return out;
}
```
> `recommendations.md` is rendered from this array (each rec a checkbox block with dimension, sub-check, severity, substep, the change). The builder points "implement the focus-group changes" at it; the orchestrator edits `track.json` per the `change` lines, then re-runs Phases 1→2.

- [ ] **Step 4: Run → PASS. Commit** `feat(track-prototype): structured recommendations from scorecard`.

---

## Task 5 [TDD]: `scores-ledger.mjs` — local `scores.md`

**Files:** Create `scripts/lib/scores-ledger.mjs`; Test `scripts/lib/scores-ledger.test.mjs`

- [ ] **Step 1: Write the failing test**
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { renderRow, appendRow, HEADER } from "./scores-ledger.mjs";

const sc = { total: 9, composite: "9/16", dimensions: { value:{met:2}, pacing:{met:2}, copy:{met:3}, fit:{met:2} } };

test("renderRow emits a markdown table row with dims + total + doc link", () => {
  const row = renderRow({ version: "v1", date: "2026-06-04", scorecard: sc, docUrl: "https://doc" });
  assert.match(row, /\| v1 \| 2026-06-04 \| 9\/16 \| 2\/4 \| 2\/4 \| 3\/4 \| 2\/4 \|/);
  assert.match(row, /https:\/\/doc/);
});

test("appendRow seeds the header once, then appends", () => {
  const first = appendRow("", renderRow({ version: "v1", date: "d", scorecard: sc, docUrl: "" }));
  assert.ok(first.includes(HEADER));
  const second = appendRow(first, renderRow({ version: "v2", date: "d", scorecard: sc, docUrl: "" }));
  assert.equal((second.match(/\| v\d /g) || []).length, 2);
  assert.equal((second.match(/Total \| D1/g) || []).length, 1);   // header not duplicated
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `scripts/lib/scores-ledger.mjs`**
```javascript
export const HEADER =
  "| Version | Date | Total | D1 Value | D2 Pacing | D3 Copy | D4 Fit | Doc |\n" +
  "|---------|------|-------|----------|-----------|---------|--------|-----|";

export function renderRow({ version, date, scorecard, docUrl }) {
  const d = scorecard.dimensions;
  const link = docUrl ? `[doc](${docUrl})` : "";
  return `| ${version} | ${date} | ${scorecard.composite} | ${d.value.met}/4 | ${d.pacing.met}/4 | ${d.copy.met}/4 | ${d.fit.met}/4 | ${link} |`;
}

export function appendRow(existing, row) {
  const base = existing && existing.includes("| Version |") ? existing.trimEnd() : HEADER;
  return base + "\n" + row + "\n";
}
```

- [ ] **Step 4: Run → PASS. Commit** `feat(track-prototype): local scores.md ledger renderer`.

---

## Task 6 [TDD]: `calibration.mjs` — rank correlation + version-aware join

**Files:** Create `scripts/lib/calibration.mjs`; Test `scripts/lib/calibration.test.mjs`

- [ ] **Step 1: Write the failing test**
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { spearman, kendallTau, joinByVersion } from "./calibration.mjs";

test("spearman = 1 for perfectly rank-aligned series", () => {
  assert.equal(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1);
});
test("spearman = -1 for perfectly inverted", () => {
  assert.equal(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1);
});
test("kendallTau basic concordance", () => {
  assert.ok(kendallTau([1, 2, 3], [1, 2, 3]) === 1);
});
test("joinByVersion matches ScoreRuns to actuals on (slug, content_hash)", () => {
  const runs = [{ slug: "clarity", content_hash: "abc", total: 11 }];
  const actuals = [{ slug: "clarity", live_track_version: "abc", completion_rate: 0.42 }];
  const joined = joinByVersion(runs, actuals);
  assert.equal(joined.length, 1);
  assert.equal(joined[0].predicted, 11);
  assert.equal(joined[0].actual, 0.42);
});
test("joinByVersion drops a run whose version has no matching actuals", () => {
  assert.equal(joinByVersion([{ slug: "x", content_hash: "z", total: 9 }], []).length, 0);
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `scripts/lib/calibration.mjs`** (Spearman = Pearson on ranks; Kendall = (concordant−discordant)/pairs; `joinByVersion` matches `content_hash` to `live_track_version`). Include `gwetAC2(rater1, rater2)` for the bucketed (ship/revise/kill) case, since κ behaves badly under skew. Each is a small pure function with the standard formula.
```javascript
function rank(xs) {
  const sorted = [...xs].map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
  const r = Array(xs.length);
  for (let i = 0; i < sorted.length; i++) r[sorted[i][1]] = i + 1;
  return r;
}
function pearson(a, b) {
  const n = a.length, ma = a.reduce((s, v) => s + v, 0) / n, mb = b.reduce((s, v) => s + v, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) { const x = a[i] - ma, y = b[i] - mb; num += x * y; da += x * x; db += y * y; }
  return da && db ? num / Math.sqrt(da * db) : 0;
}
export const spearman = (a, b) => pearson(rank(a), rank(b));
export function kendallTau(a, b) {
  let c = 0, d = 0;
  for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) {
    const s = Math.sign(a[i] - a[j]) * Math.sign(b[i] - b[j]);
    if (s > 0) c++; else if (s < 0) d++;
  }
  return c + d ? (c - d) / (c + d) : 0;
}
export function joinByVersion(runs, actuals) {
  return runs.map((r) => {
    const m = actuals.find((x) => x.slug === r.slug && x.live_track_version === r.content_hash);
    return m ? { slug: r.slug, version: r.content_hash, predicted: r.total, actual: m.completion_rate } : null;
  }).filter(Boolean);
}
export function gwetAC2(r1, r2) { /* standard AC2 for two raters over a category set */ /* … */ }
```

- [ ] **Step 4: Run → PASS. Commit** `feat(track-prototype): calibration stats (spearman/kendall/gwet) + version-aware join`.

---

## Task 7 [TDD]: `airtable-record.mjs` — ScoreRun payload builder

**Files:** Create `scripts/lib/airtable-record.mjs`; Test `scripts/lib/airtable-record.test.mjs`

- [ ] **Step 1: Write the failing test** — assert the payload uses **field NAMES** (per MEMORY Airtable gotchas: field-ID `filterByFormula` silently returns nothing; select values keyed by field-ID must be plain strings) and includes the version-aware `content_hash`.
```javascript
import { test } from "node:test";
import assert from "node:assert/strict";
import { buildScoreRunFields } from "./airtable-record.mjs";

test("builds a ScoreRun record keyed by field NAMES with content_hash", () => {
  const f = buildScoreRunFields({
    trackSlug: "clarity", version: "v2", contentHash: "abc123", date: "2026-06-04",
    scorecard: { total: 14, dimensions: { value:{met:4}, pacing:{met:3}, copy:{met:4}, fit:{met:3} }, contested: [{}] },
    gdocUrl: "https://doc", persona: "Marcus", buildUrl: "https://x.netlify.app",
  });
  assert.equal(f["track"], "clarity");
  assert.equal(f["version"], "v2");
  assert.equal(f["content_hash"], "abc123");
  assert.equal(f["checks_met"], 14);
  assert.equal(f["d1_value"], "4/4");
  assert.equal(f["contested_count"], 1);
  assert.equal(f["gdoc_url"], "https://doc");
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `scripts/lib/airtable-record.mjs`** (pure object builder; the CLI `ledger-write.mjs` POSTs it with a base-scoped token, and does Python/JS-side filtering for existing-version checks rather than field-ID `filterByFormula`).
```javascript
export function buildScoreRunFields({ trackSlug, version, contentHash, date, scorecard, gdocUrl, persona, buildUrl }) {
  const d = scorecard.dimensions;
  return {
    track: trackSlug, version, content_hash: contentHash, date,
    checks_met: scorecard.total, checks_total: 16,
    d1_value: `${d.value.met}/4`, d2_pacing: `${d.pacing.met}/4`,
    d3_copy: `${d.copy.met}/4`, d4_fit: `${d.fit.met}/4`,
    contested_count: scorecard.contested.length,
    gdoc_url: gdocUrl || "", persona_used: persona || "", build_url: buildUrl || "",
  };
}
```

- [ ] **Step 4: Run → PASS. Commit** `feat(track-prototype): Airtable ScoreRun payload builder (field-name safe)`.

---

## Task 8 [extends walk.mjs]: `walk-gallery.mjs` — screenshot gallery + report.json

**Files:** Create `scripts/walk-gallery.mjs` (built on Plan 1's `walk.mjs`)

- [ ] **Step 1: Extend the walk harness** to, per screen: capture a full-page screenshot to `focus-group/v{N}/shots/step-NN.png`, record `{ step, title, kind, text, hasUnresolvedToken, screenshot }`, and on completion write `report.json` (`{ buildUrl, steps: [...], problems: [...] }`). Reuse the Plan-1 assertions (blank/unresolved-token/stuck/console-error). This `report.json` + the shots are the panel's input — the personas/experts judge from these, not from `track.json`.

- [ ] **Step 2: Verify** by building a track (Plan-1) and running `node scripts/walk-gallery.mjs <url> --out focus-group/v1` against a served prototype; confirm a shot per screen + a well-formed `report.json`. (Requires Playwright installed — same dependency note as `walk.mjs`.)

- [ ] **Step 3: Commit** `feat(track-prototype): walk-gallery harness (screenshots + report.json for the panel)`.

---

## Task 9 [AUTHOR]: Create the Airtable "Track Previews" base

**Files:** none in repo (Airtable setup) + note the IDs in `references/focus-group-rubric.md`

- [ ] **Step 1: Create the base** in the Operations workspace (needs `workspaceId` — find via Admin Panel per the gotcha). Tables/fields (create fields via the metadata API where possible; **formula fields and views must be made in the UI**):
  - **Tracks**: `slug` (primary, **singleLineText**), `title`, `type`, `current_version`, `is_live` (checkbox — needs `options.color`+`icon`), `posthog_track_key`.
  - **ScoreRuns**: `track` (link→Tracks), `version`, `content_hash`, `date`, `checks_met` (number), `checks_total` (number), `d1_value`/`d2_pacing`/`d3_copy`/`d4_fit` (singleLineText "n/4"), `contested_count` (number), `gdoc_url`, `persona_used`, `build_url`.
  - **PostHogActuals**: `track` (link), `period`, `live_track_version`, `completion_rate` (number), `step1_dropoff` (number), `step_to_step_continuation` (number), `dropoff_by_step` (long text JSON), `n_users` (number), `notes`.

- [ ] **Step 2: Provision a base-scoped token** (per gotcha: scoped tokens can't create new select options — add any select options in the UI first). Store it (Doppler or the skill's env), record the base ID in the rubric reference. Commit the doc note.

---

## Task 10 [AUTHOR]: SKILL.md Phase 2 — the orchestrated procedure + the loop

**Files:** Modify `skills/track-prototype/SKILL.md`

- [ ] **Step 1: Write Phase 2 — Walkthrough & Focus Group.** Gate: a working Phase-1 build (local or deployed URL). Procedure:
  1. **Walkthrough:** run `walk-gallery.mjs` → screenshots + `report.json`. If it reports mechanical defects (blank/unresolved-token/stuck), STOP and fix the build before the panel runs.
  2. **Panel (per `focus-group-panel.md`):** Stage 1 personas react independently (warm); Stage 2 experts score blind, 3 samples each (cool), structured to `expert-verdict.json`; Stage 3 informed revision; Stage 4 adversarial skeptic. Use parallel sub-agents with isolated contexts; a different model family for judges than for any generated copy.
  3. **Aggregate & emit:** feed verdict samples to `scorecard.mjs`; build `recommendations.mjs`; write `focus-group/v{N}/{conversation.md, recommendations.md, scorecard.md}`; render the Google Doc via `gdoc-build` (python-docx — full conversation + expert synthesis + ranked recs + scorecard; **new draft doc, org-restricted, never overwrite a shared doc**); append the row to `focus-group/scores.md` (`scores-ledger.mjs`) and POST a ScoreRun to Airtable (`ledger-write.mjs`).
  4. **Handoff:** the Google Doc link + scorecard + the checks-met total in the handoff note.

- [ ] **Step 2: Document the iteration loop.** Builder says *"implement the focus-group changes"* → the orchestrator reads `recommendations.md`, edits `track.json` per each `fix` rec's `change` (CONTESTED `review` recs are surfaced for a human call, not auto-applied), re-runs Phase 1 build → Phase 2 → a v{N+1} row in `scores.md` showing the delta. Emphasize: **scores are a ranking + gate, not a prediction** — celebrate green checks, don't over-read the number.

- [ ] **Step 3: Document the calibration-seed step** (points to Task 11). Commit `docs(track-prototype): SKILL Phase 2 — focus group, scoring, emit, iteration loop`.

---

## Task 11 [AUTHOR+TDD]: Calibration seed against the two live tracks

**Files:** Create `scripts/calibrate.mjs` (CLI over `calibration.mjs`); a one-time `docs/calibration-seed-2026.md` note

- [ ] **Step 1: Score the two live tracks.** Assemble `clarity.track.json` and `personal-insights.track.json` from the live app (or export), run Phase 1 build + Phase 2 focus group on each, and write their ScoreRuns (with `content_hash` of the scored JSON).

- [ ] **Step 2: Pull real outcomes via the `posthog` skill.** For each live track compute, over a fixed window: `completion_rate`, `step1_dropoff`, `step_to_step_continuation`, `dropoff_by_step` (HogQL over the app's `step_start`/`step_completed`/`end_of_track` events — note PostHog is step-level; substep metrics aren't available yet). Write these to PostHogActuals with `live_track_version` matching the scored `content_hash` (or note the version mismatch explicitly).

- [ ] **Step 3: Run `calibrate.mjs`** → `joinByVersion` then `spearman`/`kendallTau` over (checks_met vs completion_rate). **Record the result with the n=2 caveat:** this is a **directional sanity check, not a coefficient** — does the rubric rate the better-performing track higher? A meaningful Spearman needs ~15–30+ tracks (use Gwet's AC2 if outcomes are bucketed/skewed). Use any disagreement to tune the rubric anchors. Commit the seed note.

- [ ] **Step 4: Document the accruing loop:** every future Phase-2 run adds a ScoreRun; once a track goes live, add its PostHogActuals; re-run `calibrate.mjs` as n grows; only then consider claiming predictive validity or tuning the (currently absent) weights.

---

## Task 12 [AUTHOR]: Cross-platform, docs, PR

- [ ] **Step 1: Cross-platform check** — all new scripts are pure node (no `.sh`); `walk-gallery.mjs` documents its Playwright dependency. Add the new libs to the test run; confirm the full `node --test scripts/lib/*.test.mjs` suite is green.
- [ ] **Step 2: Reference Index + DoD** — update `SKILL.md`'s Reference Index (Phase 2 → `focus-group-rubric.md`, `focus-group-panel.md`, `member-personas.md`, `walk-gallery.mjs`, `gdoc-build`, `playwright`) and the Definition of Done (a Phase-2 run yields a Doc + `recommendations.md` + a `scores.md` row + an Airtable ScoreRun).
- [ ] **Step 3: Open the PR**, run the Macroscope loop (**read inline comments via `gh api repos/O/R/pulls/N/comments`**, not just `gh pr view`), fix, ship.

---

## Sequencing
Pure libs first (Tasks 3–7) — they're the deterministic core and unblock everything. Then the gallery harness (8) and the Airtable base (9). Then wire the orchestrated Phase-2 procedure (10) on top of working libs. Then the calibration seed (11) once Phase 2 runs end-to-end. The panel/orchestration (10) is the least testable and most prompt-sensitive — build it last, on a proven scoring/ledger foundation.

**Plan 3 depends on Plan 2 — live AI is part of the focus-group feedback loop (decided 2026-06-04).** The panel evaluates the **live** `generate`/`chat` output, not the baked fallback, and every iterate-pass regenerates it. So the deterministic libs (Tasks 3–7) can be built right after Plan 1, but the *end-to-end Phase-2 run* (Task 10) requires Plan 2's proxy live. Two consequences for the harness/protocol:
- **Capture, don't re-generate.** The Task-8 walkthrough must record each live AI generation into `report.json` so the panel scores a *fixed* artifact per run (re-querying the model mid-scoring would judge different text than the screenshots show).
- **Evaluation mode.** Run the proxy in a low-temperature mode during focus-group runs (Plan 2 should expose this) so a re-run's score delta reflects track changes, not AI randomness. Even so, treat AI-dependent sub-checks' deltas as noisier than structural ones.

## Risks
- **Synthetic-persona adoption bias** — mitigated by the adversarial skeptic (Stage 4) and the explicit ranking-not-prediction framing; do not present scores as predictions.
- **Judge self-inconsistency** — mitigated by median-of-3 + CONTESTED routing; report the spread, not just the point estimate.
- **Groupthink** — mitigated by independent-before-shared + anonymized aggregation + a different judge model family. The protocol is load-bearing; don't collapse the stages for speed.
- **Calibration over-claim** — n=2 is directional only; guard against reading a coefficient into it. Validity stays "unproven" until ~15–30+ tracks.
- **Airtable gotchas** — field NAMES not IDs in formulas; base-scoped token; formula fields/views in UI; primary singleLineText. All encoded in Tasks 7 & 9.
- **PostHog is step-level** — D-level metrics that need substep/chat/generate events aren't measurable until the app is instrumented (a separate effort); seed calibration with what's measurable (completion, step drop-off) and note the gaps.

## Self-Review
- 4-dim binary rubric + anchors + protocol → Tasks 1, 3. ✓
- Independent → blind → informed → adversarial flow → Task 2, 10. ✓
- median-of-3, CONTESTED→human, ship-bar on any UNMET → Tasks 1, 3. ✓
- Dual output (Google Doc + structured `recommendations.md` + `scorecard.md`) → Tasks 4, 10. ✓
- Versioned ledger: local `scores.md` + Airtable canonical, version/content-hash join → Tasks 5, 7, 9. ✓
- "implement the focus-group changes" loop → Task 10. ✓
- Calibration seeded against the 2 live tracks; directional-only caveat; Spearman/Kendall/Gwet → Tasks 6, 11. ✓
- Ranking-not-prediction framing throughout → Tasks 1, 10, 11. ✓
- Cross-platform + Macroscope inline-comment check → Task 12. ✓
