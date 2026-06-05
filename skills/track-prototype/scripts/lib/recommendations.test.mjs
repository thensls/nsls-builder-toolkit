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
  assert.ok(recs.every((r) => r.id));
});

test("missing rationale -> empty strings, null substep, still has id", () => {
  const recs = buildRecommendations({ shipBar: [{ dim: "fit", key: "a" }], contested: [] }, {});
  assert.equal(recs.length, 1);
  assert.equal(recs[0].substep, null);
  assert.equal(recs[0].change, "");
  assert.ok(recs[0].id);
});
