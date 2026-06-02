import { test } from "node:test";
import assert from "node:assert/strict";
import { validateTracks, parseArgs } from "./validate-track-json.mjs";

const goodTracks = [
  {
    id: "trk_demo",
    title: "Demo Track",
    steps: [
      {
        id: "stp_0",
        title: "Start",
        substeps: [
          { id: "ss_name", slug: "name", title: "Name", prompt: "What should we call you?", type: "collect", fieldType: "text" },
          { id: "ss_hi", slug: "hi", title: "Hi", prompt: "Hi {name}, welcome.", type: "say", fieldType: "banner" }
        ]
      }
    ]
  }
];

test("valid track passes with no errors", () => {
  const { errors } = validateTracks(goodTracks);
  assert.deepEqual(errors, []);
});

test("missing required substep field is an error", () => {
  const t = structuredClone(goodTracks);
  delete t[0].steps[0].substeps[0].prompt;
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /prompt/.test(e) && /ss_name/.test(e)));
});

test("leaked auto-managed field is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].order = 0;
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /order/.test(e) && /auto-managed/.test(e)));
});

test("duplicate substep slug within a step is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].slug = "name";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /duplicate slug/i.test(e) && /name/.test(e)));
});

test("duplicate id anywhere is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].id = "ss_name";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /duplicate id/i.test(e) && /ss_name/.test(e)));
});

test("invalid type is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[1].type = "speak";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /invalid type/i.test(e) && /speak/.test(e)));
});

test("forward token reference is an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].prompt = "Your dream job is {dream-job-selection}.";
  const { errors } = validateTracks(t);
  assert.ok(errors.some((e) => /token/i.test(e) && /dream-job-selection/.test(e)));
});

test("assumed token from a prerequisite track passes", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].prompt = "Building on your {career-statement}...";
  const { errors } = validateTracks(t, { assume: ["career-statement"] });
  assert.deepEqual(errors, []);
});

test("unknown fieldType is a warning, not an error", () => {
  const t = structuredClone(goodTracks);
  t[0].steps[0].substeps[0].fieldType = "hologram";
  const { errors, warnings } = validateTracks(t);
  assert.deepEqual(errors, []);
  assert.ok(warnings.some((w) => /hologram/.test(w)));
});

test("top level must be an array", () => {
  const { errors } = validateTracks({ id: "x" });
  assert.ok(errors.some((e) => /array/i.test(e)));
});

// ---- parseArgs tests ----

test("parseArgs: space-form --assume picks correct file", () => {
  const result = parseArgs(["--assume", "a,b", "tracks.json"]);
  assert.deepEqual(result, { file: "tracks.json", assume: ["a", "b"], assumeClarity: false });
});

test("parseArgs: equals-form --assume=a,b picks correct file", () => {
  const result = parseArgs(["--assume=a,b", "tracks.json"]);
  assert.deepEqual(result, { file: "tracks.json", assume: ["a", "b"], assumeClarity: false });
});

test("parseArgs: --assume-clarity flag with file", () => {
  const result = parseArgs(["tracks.json", "--assume-clarity"]);
  assert.deepEqual(result, { file: "tracks.json", assume: [], assumeClarity: true });
});

test("parseArgs: file only", () => {
  const result = parseArgs(["tracks.json"]);
  assert.deepEqual(result, { file: "tracks.json", assume: [], assumeClarity: false });
});
