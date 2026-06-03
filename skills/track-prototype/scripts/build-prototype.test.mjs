import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSite } from "./build-prototype.mjs";

const track = { id: "t", title: "Demo", steps: [{ id: "s", title: "S", substeps: [
  { id: "ss1", slug: "name", title: "Name", prompt: "Your name?", type: "collect", fieldType: "text" },
  { id: "ss2", title: "Hi", prompt: "Hi {name}!", type: "say", fieldType: "banner" },
  { id: "ss3", slug: "cs", title: "Draft", prompt: "Here's a draft:", type: "generate", fieldType: "text" },
]}]};

test("buildSite returns index.html with injected track + screens", () => {
  const { indexHtml, screens } = buildSite(track, { samples: { cs: "Sample draft." }, date: "2026-06-03" });
  assert.equal(screens.length, 3);
  assert.match(indexHtml, /window\.__TRACK__ =/);
  assert.match(indexHtml, /built 2026-06-03/);
  // baked sample present in the generate screen
  assert.ok(screens.some((s) => s.includes("Sample draft.")));
  // {name} token preserved raw for runtime interpolation
  assert.ok(screens.some((s) => s.includes("Hi {name}!")));
});

test("escapes < in injected JSON so track copy containing </script> can't break out", () => {
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "</script><b>x</b>", type: "say", fieldType: "banner" },
  ]}]};
  const { indexHtml } = buildSite(t, {});
  assert.doesNotMatch(indexHtml, /<\/script><b>/); // raw breakout sequence must not survive
  assert.match(indexHtml, /\\u003c/);              // < was escaped in the injected JSON
});

test("buildSite throws on a token used before it is produced", () => {
  const bad = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "Hi {name}", type: "say", fieldType: "banner" },
  ]}]};
  assert.throws(() => buildSite(bad, {}), /\{name\}/);
});
