import { test } from "node:test";
import assert from "node:assert/strict";
import {
  scoreAssessment,
  resolveAnswerIds,
  buildCards,
} from "./assessment-score.mjs";

// A tiny, self-contained weights set with KNOWN-correct expected types.
// Two answers that both push toward E / N / F / P, type7 (enneagram),
// I (DISC), Artistic+Social+Enterprising (holland), high openness (big5).
const WEIGHTS = [
  {
    answerId: "a1",
    optionText: "Go with the flow",
    myersBriggs: { E: 1, N: 1, F: 1, P: 1 },
    disc: { I: 1 },
    big5: { openness: 1 },
    hollandCode: { A: 1, S: 0.5 },
    enneagram: { type7: 1 },
  },
  {
    answerId: "a2",
    optionText: "Rally the team",
    myersBriggs: { E: 1, F: 0.5 },
    disc: { I: 1 },
    big5: { openness: 0.5, neuroticism: -1 },
    hollandCode: { E: 1, S: 0.5 },
    enneagram: { type7: 0.5 },
  },
  {
    answerId: "a3",
    optionText: "Plan it all out",
    myersBriggs: { I: 5, S: 5, T: 5, J: 5 }, // a NON-chosen answer; must NOT count
    disc: { C: 5 },
    big5: { conscientiousness: 5 },
    hollandCode: { C: 5 },
    enneagram: { type1: 5 },
  },
];

const TYPES = {
  myersBriggs: [
    { id: "ENFP", name: "ENFP\n(...)", description: "Enthusiastic and creative." },
  ],
  DISC: [{ id: "I", name: "Influence (I)", description: "Charismatic." }],
  enneagram: [{ id: "type7", name: "Type 7: The Enthusiast", description: "Fun-loving." }],
  big5: [],
  hollandCode: [
    { name: "Artistic", description: "Creative.", combinations: { ASE: "Imaginative Empathic Leader" } },
    { name: "Social", description: "Empathetic." },
    { name: "Enterprising", description: "Persuasive." },
  ],
};

test("scoreAssessment sums weights for chosen answerIds and resolves each framework type", () => {
  const r = scoreAssessment({ answerIds: ["a1", "a2"], weights: WEIGHTS, types: TYPES });
  // MBTI: E(2)>I(0), N(1)>S(0), F(1.5)>T(0), P(1)>J(0) => ENFP
  assert.equal(r.myersBriggs, "ENFP");
  // Enneagram: type7 highest
  assert.equal(r.enneagram, "type7");
  // DISC: I highest
  assert.equal(r.disc, "I");
  // Holland top-3: A(1) S(1.0) E(1) — order by score desc; A and S and E.
  // A=1, S=0.5+0.5=1, E=1 -> ties broken by Object.entries insertion order R,I,A,S,E,C
  assert.equal(r.hollandCode.length, 3);
  assert.match(r.hollandCode, /^[ASE]{3}$/);
  // Big5: openness>0 -> High Openness; neuroticism<0 -> Low Neuroticism
  assert.match(r.big5, /High Openness/);
  assert.match(r.big5, /Low Neuroticism/);
  // The non-chosen answer a3 must not leak in
  assert.doesNotMatch(r.big5, /Conscientiousness/);
});

test("scoreAssessment ignores answerIds with no matching weight (graceful)", () => {
  const r = scoreAssessment({ answerIds: ["a1", "nope"], weights: WEIGHTS, types: TYPES });
  assert.equal(r.myersBriggs.length, 4);
});

test("resolveAnswerIds maps player text answers to answerIds via track options", () => {
  const track = {
    steps: [
      {
        slug: "discover-your-personality",
        substeps: [
          { slug: "q1", type: "collect", fieldType: "image-multiselect",
            options: [
              { text: "Go with the flow", answerId: "a1" },
              { text: "Plan it all out", answerId: "a3" },
            ] },
          { slug: "q2", type: "collect", fieldType: "image-multiselect",
            options: [{ text: "Rally the team", answerId: "a2" }] },
          // non-assessment substep should be ignored even if it has options
          { slug: "intro", type: "say", fieldType: "text" },
        ],
      },
    ],
  };
  // Player stores chosen option text(s) joined by ", " keyed by substep slug.
  const answers = { q1: "Go with the flow", q2: "Rally the team", other: "noise" };
  const ids = resolveAnswerIds(track, answers);
  assert.deepEqual(ids.sort(), ["a1", "a2"]);
});

test("resolveAnswerIds handles multi-select (comma-joined) values", () => {
  const track = {
    steps: [
      { slug: "discover-your-personality", substeps: [
        { slug: "q1", type: "collect", fieldType: "image-multiselect",
          options: [
            { text: "Go with the flow", answerId: "a1" },
            { text: "Rally the team", answerId: "a2" },
          ] },
      ] },
    ],
  };
  const ids = resolveAnswerIds(track, { q1: "Go with the flow, Rally the team" });
  assert.deepEqual(ids.sort(), ["a1", "a2"]);
});

test("resolveAnswerIds resolves a comma-bearing single-pick option (no shredding)", () => {
  // The dominant real case: a SINGLE-pick option whose text contains a comma.
  // A naive split(",") would shred it into pieces that match nothing.
  const track = {
    steps: [
      { slug: "discover-your-personality", substeps: [
        { slug: "q1", type: "collect", fieldType: "image-multiselect",
          options: [
            { text: "Aim for more abstract, exciting possibilities", answerId: "a1" },
            { text: "Stick to concrete, proven plans", answerId: "a3" },
          ] },
      ] },
    ],
  };
  // Player stored the whole single option text verbatim (with its comma).
  const ids = resolveAnswerIds(track, { q1: "Aim for more abstract, exciting possibilities" });
  assert.deepEqual(ids, ["a1"]);
});

test("resolveAnswerIds recovers a genuine multi-select of comma-free options", () => {
  const track = {
    steps: [
      { slug: "discover-your-personality", substeps: [
        { slug: "q1", type: "collect", fieldType: "image-multiselect",
          options: [
            { text: "Go with the flow", answerId: "a1" },
            { text: "Rally the team", answerId: "a2" },
            { text: "Plan it all out", answerId: "a3" },
          ] },
      ] },
    ],
  };
  const ids = resolveAnswerIds(track, { q1: "Go with the flow, Rally the team" });
  assert.deepEqual(ids.sort(), ["a1", "a2"]);
});

test("resolveAnswerIds recovers a multi-select whose members themselves contain commas", () => {
  // Greedy longest-match: both selected options carry their own ", ".
  const track = {
    steps: [
      { slug: "discover-your-personality", substeps: [
        { slug: "q1", type: "collect", fieldType: "image-multiselect",
          options: [
            { text: "Aim for more abstract, exciting possibilities", answerId: "a1" },
            { text: "Stick to concrete, proven plans", answerId: "a2" },
          ] },
      ] },
    ],
  };
  const joined = "Aim for more abstract, exciting possibilities, Stick to concrete, proven plans";
  const ids = resolveAnswerIds(track, { q1: joined });
  assert.deepEqual(ids.sort(), ["a1", "a2"]);
});

test("resolveAnswerIds: option text with stray surrounding whitespace still resolves", () => {
  // Regression: textToId used to key on the UNTRIMMED option text while the
  // matcher compares a TRIMMED answer — the answer silently dropped.
  const track = {
    steps: [
      {
        slug: "discover-your-personality",
        substeps: [
          {
            slug: "q1",
            options: [
              { text: "  Aim high  ", answerId: "a1" },
              { text: "Stay grounded", answerId: "a2" },
            ],
          },
        ],
      },
    ],
  };
  assert.deepEqual(resolveAnswerIds(track, { q1: "Aim high" }), ["a1"]);
  assert.deepEqual(resolveAnswerIds(track, { q1: "  Aim high  " }), ["a1"]);
  assert.deepEqual(resolveAnswerIds(track, { q1: "Stay grounded" }), ["a2"]);
});

test("resolveAnswerIds: multi-select join still recovers with trimmed keys", () => {
  const track = {
    steps: [
      {
        slug: "discover-your-personality",
        substeps: [
          {
            slug: "q1",
            options: [
              { text: "Aim for more abstract, exciting possibilities", answerId: "a1" },
              { text: " Keep it practical ", answerId: "a2" },
            ],
          },
        ],
      },
    ],
  };
  assert.deepEqual(
    resolveAnswerIds(track, { q1: "Aim for more abstract, exciting possibilities, Keep it practical" }),
    ["a1", "a2"],
  );
});

test("buildCards mirrors AssessmentResults content (title/result/description per framework)", () => {
  const r = scoreAssessment({ answerIds: ["a1", "a2"], weights: WEIGHTS, types: TYPES });
  const cards = buildCards(r, TYPES);
  const mb = cards.find((c) => c.title === "Myers Briggs");
  assert.equal(mb.result, "ENFP");
  assert.match(mb.description, /Enthusiastic/);
  const enn = cards.find((c) => c.title === "Enneagram");
  assert.equal(enn.result, "Type 7: The Enthusiast");
  const holland = cards.find((c) => c.title === "Holland Code");
  assert.match(holland.result, /\(/); // formatted "Name (CODE)..."
});
