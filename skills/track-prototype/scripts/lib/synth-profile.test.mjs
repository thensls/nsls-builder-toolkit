import { test } from "node:test";
import assert from "node:assert/strict";
import { slugify, synthValue, extractProfileFields, buildPrereqProfile } from "./synth-profile.mjs";

test("slugify mirrors the validator's derivation", () => {
  assert.equal(slugify("Your Career Goal"), "your-career-goal");
  assert.equal(slugify("  Multi--Word! "), "multi-word");
});

test("synthValue: keyword match, fieldType fallback, multiselect is a joined string", () => {
  assert.equal(synthValue("major", "text"), "Marketing");
  assert.equal(synthValue("home-state", "text"), "Ohio");
  assert.equal(synthValue("top-strengths", "multiselect"), "Strategic; Empathetic; Analytical"); // keyword wins over fieldType
  assert.equal(synthValue("favorite-topics", "multiselect"), "<option A>, <option B>");            // no keyword → multiselect shape
  assert.equal(synthValue("whatever", "number"), "42");
  assert.equal(synthValue("obscure-slug", "text"), "<sample obscure-slug>");
});

test("extractProfileFields: collect + generate (slug derived) + assessment-results (explicit slug only)", () => {
  const track = { title: "T", steps: [{ substeps: [
    { type: "collect", slug: "major", fieldType: "text", title: "Major" },
    { type: "generate", title: "Career Statement" },                 // slug derived from title
    { type: "say", fieldType: "assessment-results", slug: "personality-profile", title: "Results" },
    { type: "say", fieldType: "assessment-results", title: "No slug" }, // dropped: no explicit slug
    { type: "say", fieldType: "banner", title: "Just a banner" },       // dropped: not data
  ]}]};
  const fields = extractProfileFields(track);
  assert.deepEqual(fields.map((f) => f.slug), ["major", "career-statement", "personality-profile"]);
  assert.equal(fields.find((f) => f.slug === "career-statement").source_type, "generated");
  assert.equal(fields.find((f) => f.slug === "personality-profile").source_type, "computed");
});

test("buildPrereqProfile: values + origin track, later track wins on slug collision", () => {
  const welcome = { title: "Welcome", steps: [{ substeps: [
    { type: "collect", slug: "welcome-goal", fieldType: "text", title: "Goal" }]}]};
  const pi = { title: "Personal Insights", steps: [{ substeps: [
    { type: "collect", slug: "favorite-topics", fieldType: "multiselect", title: "Topics" },
    { type: "collect", slug: "welcome-goal", fieldType: "text", title: "Goal again" }]}]};
  const profile = buildPrereqProfile([welcome, pi]);
  assert.equal(profile["favorite-topics"].value, "<option A>, <option B>");
  assert.equal(profile["favorite-topics"].from, "Personal Insights");
  // welcome-goal appears in both; the later track (Personal Insights) wins
  assert.equal(profile["welcome-goal"].from, "Personal Insights");
});
