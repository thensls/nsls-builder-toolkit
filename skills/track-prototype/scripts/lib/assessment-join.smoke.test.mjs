// Real-data end-to-end smoke for THE JOIN (see assessment-score.mjs header).
//
// Guards the documented failure mode: a regression to text-joining silently
// drops ~1/3 of answers. With the real Clarity track + the vendored scoring
// weights, joining by answerId resolves 81/84 options vs. only 50/84 by text.
// We load the real fixture, run resolveAnswerIds() -> scoreAssessment(), and
// assert (a) a substantial majority of answers that carry an answerId resolve
// to a weighted answerId, and (b) the result is a coherent, non-empty profile.
//
// This is a real-data smoke, not a unit test: the fixture lives outside the
// repo (/tmp/track-calib/clarity.json), so the whole suite SKIPS gracefully
// when it is absent (e.g. in CI). The pure-logic guarantees are covered by
// assessment-score.test.mjs, which always runs.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  resolveAnswerIds,
  scoreAssessment,
  ASSESSMENT_STEP_SLUG,
} from "./assessment-score.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TRACK_FIXTURE = "/tmp/track-calib/clarity.json";
const WEIGHTS_PATH = join(HERE, "..", "data", "assessment-scoring-weights.json");
const TYPES_PATH = join(HERE, "..", "data", "assessment-types.json");

const haveFixture = existsSync(TRACK_FIXTURE);
const MBTI_RE = /^[EI][SN][TF][JP]$/;

function loadTrack() {
  // The calibration fixture wraps the track in a single-element array.
  const raw = JSON.parse(readFileSync(TRACK_FIXTURE, "utf8"));
  return Array.isArray(raw) ? raw[0] : raw;
}

function assessmentSubsteps(track) {
  const step = (track.steps || []).find((s) => s.slug === ASSESSMENT_STEP_SLUG);
  return step ? step.substeps || step.subSteps || [] : [];
}

test(
  "real Clarity track joins by answerId end-to-end (guards text-join regression)",
  { skip: haveFixture ? false : `fixture absent: ${TRACK_FIXTURE}` },
  () => {
    const track = loadTrack();
    const weights = JSON.parse(readFileSync(WEIGHTS_PATH, "utf8"));
    const types = JSON.parse(readFileSync(TYPES_PATH, "utf8"));

    const subs = assessmentSubsteps(track);
    assert.ok(subs.length > 0, "expected assessment substeps in the real track");

    const weightIds = new Set(weights.map((w) => w.answerId));
    const weightTexts = new Set(weights.map((w) => w.optionText));

    // Coverage of the real option set: answerId-join must dominate text-join.
    // This is the documented split (81/84 by id vs 50/84 by text) and is what
    // makes joining by answerId — not text — the correct design.
    let total = 0;
    let matchById = 0;
    let matchByText = 0;
    for (const sub of subs) {
      for (const o of sub.options || []) {
        if (o && typeof o === "object" && o.answerId != null && o.text != null) {
          total++;
          if (weightIds.has(o.answerId)) matchById++;
          if (weightTexts.has(o.text)) matchByText++;
        }
      }
    }
    assert.ok(total > 0, "expected options carrying an answerId in the real track");
    const idRate = matchById / total;
    assert.ok(
      idRate >= 0.9,
      `answerId-join rate ${matchById}/${total} (${idRate.toFixed(3)}) should stay >= 0.9`
    );
    assert.ok(
      matchById > matchByText,
      `answerId-join (${matchById}) must beat text-join (${matchByText}) — ` +
        "a regression to text-join would silently drop answers"
    );

    // Simulate a real single-select player walk: one chosen option per substep,
    // keyed by substep slug as player.js captureCurrent() stores it. Prefer a
    // comma-free text so the resolver's own ", " split (multi-select handling)
    // doesn't shred a single answer — that single-select path is what we score.
    const answers = {};
    let chosenWithId = 0;
    for (const sub of subs) {
      const opts = (sub.options || []).filter((o) => o && o.text != null);
      if (!opts.length) continue;
      const pick = opts.find((o) => !o.text.includes(",")) || opts[0];
      answers[sub.slug] = pick.text;
      if (pick.answerId != null) chosenWithId++;
    }
    assert.ok(chosenWithId > 0, "expected chosen answers carrying an answerId");

    const ids = resolveAnswerIds(track, answers);
    const resolveRate = ids.length / chosenWithId;
    assert.ok(
      resolveRate >= 0.9,
      `resolve rate ${ids.length}/${chosenWithId} (${resolveRate.toFixed(3)}) ` +
        "of answers-with-an-answerId should stay >= 0.9"
    );

    // (b) The join yields a coherent, non-empty profile.
    const r = scoreAssessment({ answerIds: ids, weights, types });
    assert.match(r.myersBriggs, MBTI_RE, "MBTI should be a valid 4-letter type");
    assert.equal(r.hollandCode.length, 3, "Holland code should be 3 letters");
    assert.ok(r.disc && r.disc.length >= 1, "DISC type should be non-empty");
    assert.ok(r.enneagram && /^type[1-9]$/.test(r.enneagram), "Enneagram should resolve to a type");
    assert.ok(Array.isArray(r.cards) && r.cards.length === 5, "should build all 5 framework cards");
    for (const c of r.cards) {
      assert.ok(c.title && c.result != null, `card "${c.title}" should have a title and result`);
    }
  }
);
