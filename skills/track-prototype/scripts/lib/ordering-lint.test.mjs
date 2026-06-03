import { test } from "node:test";
import assert from "node:assert/strict";
import { findOrderingErrors } from "./ordering-lint.mjs";

const track = (substeps) => [{ id: "t", title: "T", steps: [{ id: "s", title: "S", substeps }] }];

test("no errors when token is produced before use", () => {
  const errs = findOrderingErrors(track([
    { id: "a", slug: "name", title: "N", prompt: "?", type: "collect" },
    { id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" },
  ]));
  assert.deepEqual(errs, []);
});

test("flags a token used before it is produced", () => {
  const errs = findOrderingErrors(track([
    { id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" },
    { id: "a", slug: "name", title: "N", prompt: "?", type: "collect" },
  ]));
  assert.equal(errs.length, 1);
  assert.match(errs[0], /\{name\}/);
});

test("assumed tokens (prereq) are allowed", () => {
  const errs = findOrderingErrors(
    track([{ id: "b", slug: "hi", title: "H", prompt: "Hi {name}", type: "say" }]),
    { assume: ["name"] }
  );
  assert.deepEqual(errs, []);
});

test("only collect/generate substeps produce their slug", () => {
  // a 'say' substep with slug 'foo' does NOT satisfy a later {foo}
  const errs = findOrderingErrors(track([
    { id: "x", slug: "foo", title: "F", prompt: "hello", type: "say" },
    { id: "y", slug: "bar", title: "B", prompt: "{foo}", type: "say" },
  ]));
  assert.equal(errs.length, 1);
});
