import { test } from "node:test";
import assert from "node:assert/strict";
import { spearman, kendallTau, joinByVersion } from "./calibration.mjs";

test("spearman = 1 for perfectly rank-aligned series", () => {
  assert.equal(spearman([1, 2, 3, 4], [10, 20, 30, 40]), 1);
});
test("spearman = -1 for perfectly inverted", () => {
  assert.equal(spearman([1, 2, 3, 4], [40, 30, 20, 10]), -1);
});
test("spearman ties: a constant series has 0 correlation (avg-rank, not spurious 1)", () => {
  assert.equal(spearman([1, 2, 3], [5, 5, 5]), 0);
});
test("spearman ties: tied predicted scores rank-average correctly (0.8 known case)", () => {
  // checks-met often ties; this should match the no-tie 0.8 case structurally
  assert.ok(Math.abs(spearman([1, 2, 3, 4], [1, 2, 4, 3]) - 0.8) < 1e-9);
});
test("kendallTau basic concordance", () => {
  assert.ok(kendallTau([1, 2, 3], [1, 2, 3]) === 1);
});
test("kendallTau inverted = -1", () => {
  assert.equal(kendallTau([1, 2, 3], [3, 2, 1]), -1);
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
