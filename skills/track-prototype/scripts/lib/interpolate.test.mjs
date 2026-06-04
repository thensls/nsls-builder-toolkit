import { test } from "node:test";
import assert from "node:assert/strict";
import { interpolate, escapeHtml } from "./interpolate.mjs";

test("replaces a known token with its value", () => {
  assert.equal(interpolate("Hi {name}.", { name: "Marcus" }), "Hi Marcus.");
});

test("leaves an unknown token literal (does not blank it)", () => {
  assert.equal(interpolate("Hi {name}.", {}), "Hi {name}.");
});

test("escapes HTML in substituted values (XSS guard)", () => {
  assert.equal(interpolate("X {v}", { v: "<b>z</b>" }), "X &lt;b&gt;z&lt;/b&gt;");
});

test("single pass — does not re-substitute a value that contains a token", () => {
  assert.equal(interpolate("{a}", { a: "{b}", b: "BAD" }), "{b}");
});

test("escapeHtml handles the five entities", () => {
  assert.equal(escapeHtml(`&<>"'`), "&amp;&lt;&gt;&quot;&#39;");
});
