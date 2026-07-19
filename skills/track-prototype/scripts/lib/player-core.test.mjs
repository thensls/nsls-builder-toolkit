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

test("clampIndex: empty screen list clamps to 0, never -1 (screens[-1] → \"undefined\")", () => {
  assert.equal(clampIndex(0, 0), 0);
  assert.equal(clampIndex(5, 0), 0);
  assert.equal(clampIndex(-3, 0), 0);
});

test("nextIndex: empty screen list yields 0, never -1 (advance() on an empty track)", () => {
  // Regression: nextIndex(0, 0) was Math.min(1, -1) = -1 — advance() assigned
  // it to state.i and render() painted screens[-1] as the string "undefined".
  assert.equal(nextIndex(0, 0), 0);
  assert.equal(nextIndex(3, 0), 0);
});

test("flattenSubsteps: /new-track starter shape (1 step, 0 substeps) flattens to []", () => {
  assert.deepEqual(flattenSubsteps({ steps: [{ slug: "s1", substeps: [] }] }), []);
});
