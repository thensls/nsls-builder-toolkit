import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs, validateSlug, validateMeta, validateHtml, resolveToken, describeResponse, UsageError } from "./lib.mjs";

test("slug rules", () => {
  for (const ok of ["a", "fall-2026", "a1-b2-c3"]) assert.equal(validateSlug(ok), null, ok);
  for (const bad of ["", "Fall", "a--b", "-a", "a-", "a_b", "a b", "ph", "a".repeat(81)]) assert.ok(validateSlug(bad), bad);
  assert.equal(validateSlug("a".repeat(80)), null);
});
test("meta caps", () => {
  assert.ok(validateMeta({ title: "" }));
  assert.ok(validateMeta({ title: "x".repeat(201) }));
  assert.ok(validateMeta({ title: "t", description: "x".repeat(2001) }));
  assert.equal(validateMeta({ title: "x".repeat(200), description: "x".repeat(2000) }), null);
});
test("html: relaxed public mode", () => {
  assert.equal(validateHtml('<!DOCTYPE html><img src="https://cdn.example.com/a.png">'), null);
  assert.equal(validateHtml("﻿  <!-- c --><html><body></body></html>"), null);
  assert.ok(validateHtml(""));
  assert.ok(validateHtml("just text"));
  assert.ok(validateHtml("<html></html>", 26 * 1024 * 1024));
});
test("token precedence", () => {
  assert.deepEqual(resolveToken({ flag: "a", env: "b", fileContents: "c" }), { token: "a", source: "--token flag" });
  assert.equal(resolveToken({ env: "b", fileContents: "c" }).token, "b");
  assert.equal(resolveToken({ fileContents: " c\n" }).token, "c");
  assert.equal(resolveToken({ flag: "  ", env: "" }), null);
});
test("parseArgs", () => {
  const a = parseArgs(["--file", "x.html", "--slug=s", "--allow-production"]);
  assert.equal(a.file, "x.html"); assert.equal(a.slug, "s"); assert.equal(a.allowProduction, true); assert.equal(a.stage, "staging");
  assert.throws(() => parseArgs(["--bogus", "1"]), UsageError);
  assert.throws(() => parseArgs(["--file"]), UsageError);
});
test("response mapping", () => {
  assert.match(describeResponse(200, { publicUrl: "https://docs.nsls.org/x" }).message, /docs\.nsls\.org\/x/);
  for (const s of [400, 401, 409, 413, 502, 500]) assert.equal(describeResponse(s, {}).ok, false);
  assert.match(describeResponse(502, {}).message, /ALREADY BE PUBLISHED/);
});
