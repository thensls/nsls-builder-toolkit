import test from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { validateAnswers, unwrapTrack, loadAndValidate } from "./validate-answers.mjs";

// --- tiny synthetic track exercising every fieldType branch ---
function fixtureTrack() {
  return {
    steps: [
      {
        slug: "intro",
        substeps: [
          { slug: "name", type: "collect", fieldType: "text" },
          { slug: "rent", type: "collect", fieldType: "currency" },
          {
            slug: "mood",
            type: "collect",
            fieldType: "select",
            options: [{ text: "Calm" }, { text: "Busy" }],
          },
          {
            slug: "tags",
            type: "collect",
            fieldType: "multi-select",
            multiselectMinSelections: 2,
            multiselectMaxSelections: 3,
            options: [{ text: "A" }, { text: "B" }, { text: "C" }, { text: "D" }],
          },
          {
            slug: "ab",
            type: "collect",
            fieldType: "image-multiselect",
            autoProgressOnSelect: true,
            options: [{ text: "Left" }, { text: "Right" }],
          },
          { slug: "say-thing", type: "say", fieldType: "banner" }, // ignored
        ],
      },
      {
        slug: "money",
        substeps: [
          {
            slug: "narrow",
            type: "collect",
            fieldType: "multi-select",
            optionsSourceSlug: "tags",
            multiselectMinSelections: 2,
          },
        ],
      },
    ],
  };
}

const goodAnswers = {
  name: "Maya",
  rent: "850",
  mood: "Calm",
  tags: ["A", "B", "C"],
  ab: ["Left"],
  narrow: ["A", "B"],
};

test("valid answer-set passes clean", () => {
  assert.deepEqual(validateAnswers(fixtureTrack(), goodAnswers), []);
});

test("missing collect slug is flagged", () => {
  const a = { ...goodAnswers };
  delete a.name;
  const p = validateAnswers(fixtureTrack(), a);
  assert.ok(p.some((x) => x.startsWith("MISSING") && x.includes("name")));
});

test("unknown answer key is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, bogus: "x" });
  assert.ok(p.some((x) => x.startsWith("UNKNOWN") && x.includes("bogus")));
});

test("zero currency is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, rent: "0" });
  assert.ok(p.some((x) => x.startsWith("CURRENCY")));
});

test("non-numeric currency is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, rent: "free" });
  assert.ok(p.some((x) => x.startsWith("CURRENCY")));
});

test("select value not in options is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, mood: "Sleepy" });
  assert.ok(p.some((x) => x.startsWith("OPTION") && x.includes("mood")));
});

test("multi-select value not in options is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, tags: ["A", "Z"] });
  assert.ok(p.some((x) => x.startsWith("OPTION") && x.includes("Z")));
});

test("multi-select below min is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, tags: ["A"] });
  assert.ok(p.some((x) => x.startsWith("MINSEL")));
});

test("multi-select above max is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, tags: ["A", "B", "C", "D"] });
  assert.ok(p.some((x) => x.startsWith("MAXSEL")));
});

test("autoProgress single-pick rejects 2 selections", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, ab: ["Left", "Right"] });
  assert.ok(p.some((x) => x.startsWith("SINGLEPICK")));
});

test("optionsSourceSlug narrowing validates against upstream answer", () => {
  // "C" is in tags, but Maya narrowed to a subset; choose something NOT in upstream
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, tags: ["A", "B"], narrow: ["A", "C"] });
  assert.ok(p.some((x) => x.startsWith("OPTION") && x.includes("narrow")));
});

test("select given an array is flagged", () => {
  const p = validateAnswers(fixtureTrack(), { ...goodAnswers, mood: ["Calm"] });
  assert.ok(p.some((x) => x.startsWith("SHAPE") && x.includes("mood")));
});

test("unwrapTrack handles array wrapper and bare object", () => {
  const obj = { steps: [] };
  assert.equal(unwrapTrack([obj]), obj);
  assert.equal(unwrapTrack(obj), obj);
});

// --- integration: real Clarity track + the authored Maya answers (if present) ---
const CLARITY = "/tmp/track-calib/clarity.json";
const MAYA = new URL("./maya.answers.json", import.meta.url).pathname;

test("Maya answers validate clean against the real Clarity track", { skip: !existsSync(CLARITY) }, async () => {
  const problems = await loadAndValidate(CLARITY, MAYA);
  assert.deepEqual(problems, [], "Maya answers should validate clean: " + problems.join("; "));
});
