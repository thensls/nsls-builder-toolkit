import { test } from "node:test";
import assert from "node:assert/strict";
import { planFill, isStreamStable } from "./walk-autofill.mjs";

// --- planFill: free-text family --------------------------------------------

test("text input → fill with the string value", () => {
  const plan = planFill({ slug: "name", fieldType: "text", hasInput: true }, "Maya");
  assert.deepEqual(plan, { action: "fill", value: "Maya" });
});

test("currency input → fill with the numeric string", () => {
  const plan = planFill({ slug: "housing-costs", fieldType: "currency", hasInput: true }, "850");
  assert.deepEqual(plan, { action: "fill", value: "850" });
});

test("free-text answered with an array joins into one string", () => {
  const plan = planFill({ slug: "x", fieldType: "text", hasInput: true }, ["a", "b"]);
  assert.equal(plan.action, "fill");
  assert.equal(plan.value, "a, b");
});

test("text input with no answer → generic fallback + problem", () => {
  const plan = planFill({ slug: "mystery", fieldType: "text", hasInput: true }, undefined);
  assert.equal(plan.action, "fill");
  assert.equal(plan.value, "Maya");
  assert.match(plan.problem, /no persona answer/);
});

// --- planFill: single select ------------------------------------------------

test("select → click exactly the one matching option", () => {
  const plan = planFill(
    { slug: "familiarity", fieldType: "select", optionValues: ["Mix of both", "New"] },
    "Mix of both"
  );
  assert.equal(plan.action, "click-options");
  assert.deepEqual(plan.values, ["Mix of both"]);
  assert.equal(plan.autoProgress, false);
});

// --- planFill: multi-select -------------------------------------------------

test("multi-select → click each matching option", () => {
  const plan = planFill(
    { slug: "strengths", fieldType: "multi-select", optionValues: ["A", "B", "C", "D"] },
    ["A", "C"]
  );
  assert.equal(plan.action, "click-options");
  assert.deepEqual(plan.values, ["A", "C"]);
});

test("multi-select reports a problem when some values don't match", () => {
  const plan = planFill(
    { slug: "strengths", fieldType: "multi-select", optionValues: ["A", "B"] },
    ["A", "Z"]
  );
  assert.deepEqual(plan.values, ["A"]);
  assert.match(plan.problem, /matched no option/);
});

// --- planFill: comma-bearing option text (must NOT split on commas) ---------

test("image-multiselect autoProgress: matches whole comma-bearing data-value", () => {
  const opt = "Aim for more abstract, exciting possibilities";
  const plan = planFill(
    { slug: "question-13", fieldType: "image-multiselect", autoProgress: true, optionValues: [opt, "Stay concrete"] },
    [opt]
  );
  assert.equal(plan.action, "click-options");
  assert.deepEqual(plan.values, [opt]); // single, whole string, not split
  assert.equal(plan.autoProgress, true);
});

test("autoProgress single-pick clicks only the first match even if answer is array", () => {
  const plan = planFill(
    { slug: "q", fieldType: "image-multiselect", autoProgress: true, optionValues: ["X", "Y"] },
    ["X"]
  );
  assert.deepEqual(plan.values, ["X"]);
});

// --- planFill: dropdown-with-checkboxes single string -----------------------

test("dropdown-with-checkboxes with a matching single-string option", () => {
  const plan = planFill(
    { slug: "direction-clarity", fieldType: "dropdown-with-checkboxes", optionValues: ["1", "2", "3", "4"] },
    "4"
  );
  assert.equal(plan.action, "click-options");
  assert.deepEqual(plan.values, ["4"]);
});

test("empty option grid → action none with a problem note (not a crash)", () => {
  const plan = planFill(
    { slug: "direction-clarity", fieldType: "dropdown-with-checkboxes", optionValues: [] },
    "4"
  );
  assert.equal(plan.action, "none");
  assert.match(plan.problem, /empty/);
});

// --- planFill: option grid with no answer → first option fallback -----------

test("option grid with no answer selects the first option and flags it", () => {
  const plan = planFill(
    { slug: "x", fieldType: "select", optionValues: ["A", "B"] },
    undefined
  );
  assert.equal(plan.action, "click-options");
  assert.deepEqual(plan.values, ["A"]);
  assert.match(plan.problem, /no persona answer/);
});

// --- planFill: banner (no input, no grid) → none -----------------------------

test("banner-like screen (no input, no options) → action none", () => {
  const plan = planFill({ slug: undefined, fieldType: undefined, hasInput: false, optionValues: [] }, undefined);
  assert.deepEqual(plan, { action: "none" });
});

// --- isStreamStable ---------------------------------------------------------

test("not enough samples → not stable", () => {
  assert.equal(isStreamStable([10, 10], 3), false);
});

test("flat tail of window length → stable", () => {
  assert.equal(isStreamStable([5, 20, 40, 40, 40], 3), true);
});

test("still growing in the tail → not stable", () => {
  assert.equal(isStreamStable([10, 20, 30], 3), false);
});

test("grew then settled exactly at the window edge → stable", () => {
  assert.equal(isStreamStable([0, 50, 100, 100, 100], 3), true);
});

test("window clamps to a minimum of 2", () => {
  assert.equal(isStreamStable([7, 7], 1), true);
});

test("non-array input → not stable", () => {
  assert.equal(isStreamStable(null, 3), false);
});
