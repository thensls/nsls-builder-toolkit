import { test } from "node:test";
import assert from "node:assert/strict";
import { summarize } from "./calibrate.mjs";

test("summarize: n<2 -> no coefficient, explains why", () => {
  const r = summarize([{ track: "a", content_hash: "h", checks_met: 11 }], []);
  assert.equal(r.n, 0);
  assert.equal(r.spearman, null);
  assert.match(r.note, /need >=2/);
});

test("summarize: joins on slug+hash and correlates checks-met vs completion-rate", () => {
  const runs = [
    { track: "a", content_hash: "h1", checks_met: 14 },
    { track: "b", content_hash: "h2", checks_met: 9 },
    { track: "c", content_hash: "h3", checks_met: 12 },
  ];
  const actuals = [
    { track: "a", live_track_version: "h1", completion_rate: 0.62 },
    { track: "b", live_track_version: "h2", completion_rate: 0.31 },
    { track: "c", live_track_version: "h3", completion_rate: 0.50 },
  ];
  const r = summarize(runs, actuals);
  assert.equal(r.n, 3);
  assert.equal(r.spearman, 1);          // perfectly rank-aligned (14>12>9, .62>.50>.31)
  assert.match(r.note, /DIRECTIONAL ONLY/);  // n<15
});

test("summarize: drops a run whose version has no matching actuals", () => {
  const runs = [{ track: "a", content_hash: "h1", checks_met: 14 }, { track: "z", content_hash: "zz", checks_met: 5 }];
  const actuals = [{ track: "a", live_track_version: "h1", completion_rate: 0.6 }];
  assert.equal(summarize(runs, actuals).n, 1);
});
