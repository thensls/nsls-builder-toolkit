import { test } from "node:test";
import assert from "node:assert/strict";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readFileSync, rmSync } from "node:fs";
import { postScoreRun, updateScoresMd } from "./ledger-write.mjs";

const sc = { total: 11, composite: "11/16", dimensions: { value:{met:3}, pacing:{met:2}, copy:{met:3}, fit:{met:3} } };

test("postScoreRun posts to the ScoreRuns endpoint with auth + fields, returns the record id", async () => {
  let captured;
  const fetchImpl = async (url, opts) => {
    captured = { url, opts };
    return { ok: true, json: async () => ({ id: "recABC" }) };
  };
  const id = await postScoreRun({ apiKey: "k", baseId: "appX", fields: { track: "clarity" }, fetchImpl });
  assert.equal(id, "recABC");
  assert.match(captured.url, /\/v0\/appX\/ScoreRuns$/);
  assert.equal(captured.opts.headers.Authorization, "Bearer k");
  assert.deepEqual(JSON.parse(captured.opts.body), { fields: { track: "clarity" } });
});

test("postScoreRun throws (does not swallow) on a non-2xx", async () => {
  const fetchImpl = async () => ({ ok: false, status: 422, text: async () => "bad field" });
  await assert.rejects(
    () => postScoreRun({ apiKey: "k", baseId: "appX", fields: {}, fetchImpl }),
    /Airtable 422: bad field/
  );
});

test("updateScoresMd seeds a header then appends one row per call", () => {
  const p = join(tmpdir(), `scores-test-${process.pid}.md`);
  rmSync(p, { force: true });
  updateScoresMd(p, { version: "v1", date: "2026-06-07", scorecard: sc, gdocUrl: "" });
  updateScoresMd(p, { version: "v2", date: "2026-06-07", scorecard: sc, gdocUrl: "" });
  const out = readFileSync(p, "utf8");
  assert.equal((out.match(/\| v\d /g) || []).length, 2);
  assert.equal((out.match(/Total \| D1/g) || []).length, 1);   // header once
  rmSync(p, { force: true });
});
