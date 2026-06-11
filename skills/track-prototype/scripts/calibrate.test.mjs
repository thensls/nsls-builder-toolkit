import { test } from "node:test";
import assert from "node:assert/strict";
import { summarize } from "./calibrate.mjs";

test("summarize: n<2 -> no coefficient, explains why", () => {
  const r = summarize([{ track: "a", content_hash: "h", checks_met: 11 }], []);
  assert.equal(r.n, 0);
  assert.equal(r.spearman, null);
  assert.match(r.note, /need >=2/);
});

test("summarize: PRIMARY coefficient is vs per-step continuation; raw completion is a contrast", () => {
  const runs = [
    { track: "a", content_hash: "h1", checks_met: 14 },
    { track: "b", content_hash: "h2", checks_met: 9 },
    { track: "c", content_hash: "h3", checks_met: 12 },
  ];
  // continuation rank-aligned with checks-met (14>12>9 ~ .95>.90>.80) -> primary spearman 1.
  // completion INVERTED (the length/position confound: lowest-scored track completes highest)
  // -> vsCompletion spearman -1. This is the n=3 seed pattern in miniature.
  const actuals = [
    { track: "a", live_track_version: "h1", completion_rate: 0.40, step_to_step_continuation: 0.95 },
    { track: "b", live_track_version: "h2", completion_rate: 0.80, step_to_step_continuation: 0.80 },
    { track: "c", live_track_version: "h3", completion_rate: 0.60, step_to_step_continuation: 0.90 },
  ];
  const r = summarize(runs, actuals);
  assert.equal(r.n, 3);
  assert.equal(r.primaryMetric, "step_to_step_continuation");
  assert.equal(r.spearman, 1);               // checks-met vs continuation: perfectly aligned
  assert.equal(r.vsCompletion.spearman, -1); // checks-met vs raw completion: inverted (the confound)
  assert.match(r.note, /DIRECTIONAL ONLY/);  // n<15
});

test("summarize: primary coefficient is null (with a heads-up) when continuation missing", () => {
  const runs = [{ track: "a", content_hash: "h1", checks_met: 14 }, { track: "b", content_hash: "h2", checks_met: 9 }];
  const actuals = [
    { track: "a", live_track_version: "h1", completion_rate: 0.62 },
    { track: "b", live_track_version: "h2", completion_rate: 0.31 },
  ];
  const r = summarize(runs, actuals);
  assert.equal(r.spearman, null);              // no continuation -> no primary coefficient
  assert.equal(r.vsCompletion.spearman, 1);    // contrast still computes
  assert.match(r.note, /step_to_step_continuation missing/);
});

test("summarize: drops a run whose version has no matching actuals", () => {
  const runs = [{ track: "a", content_hash: "h1", checks_met: 14 }, { track: "z", content_hash: "zz", checks_met: 5 }];
  const actuals = [{ track: "a", live_track_version: "h1", completion_rate: 0.6 }];
  assert.equal(summarize(runs, actuals).n, 1);
});
