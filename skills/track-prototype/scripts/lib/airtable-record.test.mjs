import { test } from "node:test";
import assert from "node:assert/strict";
import { buildScoreRunFields } from "./airtable-record.mjs";

test("builds a ScoreRun record keyed by field NAMES with content_hash", () => {
  const f = buildScoreRunFields({
    trackSlug: "clarity", version: "v2", contentHash: "abc123", date: "2026-06-04",
    scorecard: { total: 14, dimensions: { value:{met:4}, pacing:{met:3}, copy:{met:4}, fit:{met:3} }, contested: [{}] },
    gdocUrl: "https://doc", persona: "Marcus", buildUrl: "https://x.netlify.app",
  });
  assert.equal(f["track"], "clarity");
  assert.equal(f["version"], "v2");
  assert.equal(f["content_hash"], "abc123");
  assert.equal(f["checks_met"], 14);
  assert.equal(f["checks_total"], 16);
  assert.equal(f["d1_value"], "4/4");
  assert.equal(f["d4_fit"], "3/4");
  assert.equal(f["contested_count"], 1);
  assert.equal(f["gdoc_url"], "https://doc");
});

test("optional fields default to empty string when absent", () => {
  const f = buildScoreRunFields({ trackSlug: "t", version: "v1", contentHash: "h", date: "d",
    scorecard: { total: 0, dimensions: { value:{met:0}, pacing:{met:0}, copy:{met:0}, fit:{met:0} }, contested: [] } });
  assert.equal(f["gdoc_url"], "");
  assert.equal(f["persona_used"], "");
  assert.equal(f["build_url"], "");
  assert.equal(f["contested_count"], 0);
});
