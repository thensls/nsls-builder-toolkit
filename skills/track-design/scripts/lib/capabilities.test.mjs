import { test } from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, mkdtempSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { loadCapabilities } from "./capabilities.mjs";

const write = (obj) => {
  const dir = mkdtempSync(join(tmpdir(), "caps-"));
  const p = join(dir, "track-capabilities.json");
  writeFileSync(p, JSON.stringify(obj));
  return p;
};

const valid = {
  generatedAt: new Date().toISOString(),
  commit: "abc1234",
  fieldTypes: { declared: ["text", "textarea"], rendered: ["text"], aiContext: [] },
  runtimeCapabilities: { grounding: false },
  substepFields: ["prompt"],
  responseModel: ["answer"],
};

test("loadCapabilities: returns the manifest with no warnings when fresh and valid", () => {
  const r = loadCapabilities({ path: write(valid) });
  assert.deepEqual(r.warnings, []);
  assert.deepEqual(r.manifest.fieldTypes.rendered, ["text"]);
});

test("loadCapabilities: a missing file degrades to null with a warning, never throws", () => {
  const r = loadCapabilities({ path: "/nope/track-capabilities.json" });
  assert.equal(r.manifest, null);
  assert.match(r.warnings[0], /capability manifest not found/i);
});

test("loadCapabilities: malformed JSON degrades to null with a warning", () => {
  const dir = mkdtempSync(join(tmpdir(), "caps-"));
  const p = join(dir, "track-capabilities.json");
  writeFileSync(p, "{ not json");
  const r = loadCapabilities({ path: p });
  assert.equal(r.manifest, null);
  assert.match(r.warnings[0], /could not be read/i);
});

test("loadCapabilities: a wrong-shaped manifest degrades to null", () => {
  const r = loadCapabilities({ path: write({ generatedAt: "x", commit: "y" }) });
  assert.equal(r.manifest, null);
  assert.match(r.warnings[0], /missing fieldTypes/i);
});

test("loadCapabilities: a stale manifest still loads but warns with its date", () => {
  const old = { ...valid, generatedAt: "2020-01-01T00:00:00.000Z" };
  const r = loadCapabilities({ path: write(old), maxAgeDays: 30 });
  assert.ok(r.manifest, "stale must still load — never block authoring");
  assert.match(r.warnings[0], /2020-01-01/);
});
