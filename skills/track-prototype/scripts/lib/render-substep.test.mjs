import { test } from "node:test";
import assert from "node:assert/strict";
import { renderSubstep } from "./render-substep.mjs";

test("say/banner renders prompt + a Continue button", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "Welcome", type: "say", fieldType: "banner" }, {});
  assert.match(html, /Welcome/);
  assert.match(html, /data-next/);
  assert.match(html, /class="[^"]*tp-btn/);
});

test("collect/text renders an input bound by data-input + data-slug", () => {
  const html = renderSubstep({ id: "x", slug: "name", title: "Name", prompt: "Your name?", type: "collect", fieldType: "text" }, {});
  assert.match(html, /data-input/);
  assert.match(html, /data-slug="name"/);
});

test("collect/multi-select renders one option button per option", () => {
  const sub = { id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "multi-select",
    options: [{ text: "A" }, { text: "B" }] };
  const html = renderSubstep(sub, {});
  assert.equal((html.match(/data-option/g) || []).length, 2);
});

test("generate renders the baked sample when provided", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" },
    { samples: { cs: "Your career statement draft." } });
  assert.match(html, /Your career statement draft\./);
});

test("generate without a sample renders a clearly-marked placeholder", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" }, {});
  assert.match(html, /tp-ai-placeholder/);
});

test("unknown fieldType falls back to a generic text screen (no throw)", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "P", type: "collect", fieldType: "totally-new" }, {});
  assert.match(html, /P/);
});
