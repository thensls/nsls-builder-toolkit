import { test } from "node:test";
import assert from "node:assert/strict";
import { renderSubstep, safeUrl } from "./render-substep.mjs";

test("safeUrl drops javascript: and other unsafe schemes, keeps safe ones", () => {
  assert.equal(safeUrl("javascript:alert(1)"), "");
  assert.equal(safeUrl("data:text/html,<x>"), "");
  assert.equal(safeUrl("/img/a.png"), "/img/a.png");
  assert.equal(safeUrl("https://x/y.png"), "https://x/y.png");
  assert.equal(safeUrl("intro.png"), "intro.png");
  assert.equal(safeUrl("data:image/png;base64,AAAA"), "data:image/png;base64,AAAA");
});

test("safeUrl strips control chars so a tab can't smuggle a javascript: scheme", () => {
  assert.equal(safeUrl("java\tscript:alert(1)"), "");
  assert.equal(safeUrl("java\nscript:alert(1)"), "");
});

test("option with a javascript: imageUrl emits no img tag", () => {
  const html = renderSubstep({ id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "image-multiselect",
    options: [{ text: "A", imageUrl: "javascript:alert(1)" }] }, {});
  assert.doesNotMatch(html, /javascript:/);
  assert.doesNotMatch(html, /<img/);
});

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

test("chat renders data-chat-log, data-chat-input, data-chat-send and a seed bubble", () => {
  const html = renderSubstep({ id: "x", slug: "coach", title: "Coach", prompt: "Hello!", type: "chat", fieldType: "text" },
    { samples: { coach: "I am your coach." } });
  assert.match(html, /data-chat-log/);
  assert.match(html, /data-chat-input/);
  assert.match(html, /data-chat-send/);
  assert.match(html, /I am your coach\./);   // seed bubble present
});

test("chat without a sample still renders the interactive hooks with a fallback seed", () => {
  const html = renderSubstep({ id: "x", slug: "coach", title: "Coach", prompt: "Hello!", type: "chat", fieldType: "text" }, {});
  assert.match(html, /data-chat-log/);
  assert.match(html, /data-chat-input/);
  assert.match(html, /data-chat-send/);
});
