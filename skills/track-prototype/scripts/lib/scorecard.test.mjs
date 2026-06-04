import { test } from "node:test";
import assert from "node:assert/strict";
import { aggregateSubcheck, buildScorecard } from "./scorecard.mjs";

test("aggregateSubcheck: majority MET/UNMET, else CONTESTED", () => {
  assert.equal(aggregateSubcheck(["MET", "MET", "MET"]), "MET");
  assert.equal(aggregateSubcheck(["UNMET", "UNMET", "MET"]), "UNMET");
  assert.equal(aggregateSubcheck(["MET", "UNMET", "MET"]), "MET");
  assert.equal(aggregateSubcheck(["MET", "UNMET"]), "CONTESTED");
});

test("buildScorecard rolls up dims, total, and ship-bar list", () => {
  const allMet = () => ["MET", "MET", "MET"];
  const dims = ["value", "pacing", "copy", "fit"];
  const samples = {};
  for (const d of dims) for (const k of ["a","b","c","d"]) samples[`${d}.${k}`] = allMet();
  samples["value.c"] = ["UNMET","UNMET","MET"];   // one UNMET
  samples["copy.b"] = ["MET","UNMET"];            // one CONTESTED
  const sc = buildScorecard(samples, dims);
  assert.equal(sc.total, 14);
  assert.equal(sc.dimensions.value.met, 3);
  assert.equal(sc.shipBar.length, 1);
  assert.equal(sc.contested.length, 1);
  assert.equal(sc.composite, "14/16");
});
