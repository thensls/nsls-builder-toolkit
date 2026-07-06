import { test } from "node:test";
import assert from "node:assert/strict";
import { canonicalize, contentHash } from "./content-hash.mjs";

test("key-order independent, 12 hex — parity with track-studio lib/versions.ts", () => {
  const a = { b: 1, a: [{ y: 2, x: 1 }], c: null };
  const b = { c: null, a: [{ x: 1, y: 2 }], b: 1 };
  assert.equal(canonicalize(a), canonicalize(b));
  assert.equal(contentHash(a), contentHash(b));
  assert.match(contentHash(a), /^[0-9a-f]{12}$/);
  // pinned vector — if this changes, the cross-system join key broke
  assert.equal(contentHash({ slug: "snt", steps: [], title: "SMOKE - delete me" }), "ece22e181eeb");
});
