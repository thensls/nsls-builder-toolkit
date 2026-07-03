import { test } from "node:test";
import assert from "node:assert/strict";
import { setStage, findTrackBySlug, STAGES } from "./set-stage.mjs";

const page = (records, offset) => ({ ok: true, json: async () => ({ records, offset }) });
const rec = (id, slug, stage) => ({ id, fields: { slug, stage } });

test("findTrackBySlug paginates until it finds the slug (client-side match)", async () => {
  const calls = [];
  const fetchImpl = async (url) => {
    calls.push(String(url));
    return calls.length === 1
      ? page([rec("rec1", "welcome", "live")], "off2")
      : page([rec("rec2", "career-clarity", "live")], undefined);
  };
  const hit = await findTrackBySlug({ apiKey: "k", baseId: "appX", slug: "career-clarity", fetchImpl });
  assert.equal(hit.id, "rec2");
  assert.equal(calls.length, 2);
  assert.match(calls[1], /offset=off2/);
});

test("setStage PATCHes the record with typecast and returns the transition", async () => {
  let patch;
  const fetchImpl = async (url, opts = {}) => {
    if (opts.method === "PATCH") {
      patch = { url: String(url), body: JSON.parse(opts.body) };
      return { ok: true, json: async () => ({ id: "recB" }) };
    }
    return page([rec("recB", "snt", "backlog")], undefined);
  };
  const out = await setStage({ apiKey: "k", baseId: "appX", slug: "snt", stage: "in-development", fetchImpl });
  assert.deepEqual(out, { recordId: "recB", from: "backlog", to: "in-development", fields: { stage: "in-development" } });
  assert.match(patch.url, /\/v0\/appX\/Tracks\/recB$/);
  assert.deepEqual(patch.body, { fields: { stage: "in-development" }, typecast: true });
});

test("setStage live also sets is_live and current_version when a version is given", async () => {
  let patch;
  const fetchImpl = async (url, opts = {}) => {
    if (opts.method === "PATCH") { patch = JSON.parse(opts.body); return { ok: true, json: async () => ({}) }; }
    return page([rec("recC", "snt", "in-development")], undefined);
  };
  await setStage({ apiKey: "k", baseId: "appX", slug: "snt", stage: "live", liveVersion: "abc123def456", fetchImpl });
  assert.deepEqual(patch.fields, { stage: "live", is_live: true, current_version: "abc123def456" });
});

test("setStage rejects unknown stages and missing slugs; PATCH failures throw", async () => {
  await assert.rejects(
    () => setStage({ apiKey: "k", baseId: "appX", slug: "x", stage: "shipped", fetchImpl: async () => page([], undefined) }),
    /stage must be one of/
  );
  assert.deepEqual(STAGES, ["backlog", "in-development", "live", "optimization"]);
  await assert.rejects(
    () => setStage({ apiKey: "k", baseId: "appX", slug: "ghost", stage: "live", fetchImpl: async () => page([], undefined) }),
    /No Tracks row with slug "ghost"/
  );
  const fetchImpl = async (url, opts = {}) =>
    opts.method === "PATCH"
      ? { ok: false, status: 422, text: async () => "INVALID_MULTIPLE_CHOICE_OPTIONS" }
      : page([rec("recD", "snt", "backlog")], undefined);
  await assert.rejects(
    () => setStage({ apiKey: "k", baseId: "appX", slug: "snt", stage: "live", fetchImpl }),
    /Airtable 422: INVALID_MULTIPLE_CHOICE_OPTIONS/
  );
});
