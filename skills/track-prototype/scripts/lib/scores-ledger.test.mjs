import { test } from "node:test";
import assert from "node:assert/strict";
import { renderRow, appendRow, HEADER } from "./scores-ledger.mjs";

const sc = { total: 9, composite: "9/16", dimensions: { value:{met:2}, pacing:{met:2}, copy:{met:3}, fit:{met:2} } };

test("renderRow emits a markdown table row with dims + total + doc link", () => {
  const row = renderRow({ version: "v1", date: "2026-06-04", scorecard: sc, docUrl: "https://doc" });
  assert.match(row, /\| v1 \| 2026-06-04 \| 9\/16 \| 2\/4 \| 2\/4 \| 3\/4 \| 2\/4 \|/);
  assert.match(row, /https:\/\/doc/);
});

test("renderRow falls back to total/16 when composite is missing (never 'undefined')", () => {
  const noComposite = { total: 9, dimensions: sc.dimensions };
  const row = renderRow({ version: "v1", date: "d", scorecard: noComposite, docUrl: "" });
  assert.match(row, /\| 9\/16 \|/);
  assert.doesNotMatch(row, /undefined/);
});

test("appendRow seeds the header once, then appends", () => {
  const first = appendRow("", renderRow({ version: "v1", date: "d", scorecard: sc, docUrl: "" }));
  assert.ok(first.includes(HEADER));
  const second = appendRow(first, renderRow({ version: "v2", date: "d", scorecard: sc, docUrl: "" }));
  assert.equal((second.match(/\| v\d /g) || []).length, 2);
  assert.equal((second.match(/Total \| D1/g) || []).length, 1);   // header not duplicated
});
