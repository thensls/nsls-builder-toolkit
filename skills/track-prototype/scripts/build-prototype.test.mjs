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

test("does not misinterpret $ patterns in track content (replace() footgun)", () => {
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", slug: "x", title: "A", prompt: "win $5 & $& and $` here", type: "collect", fieldType: "text" },
  ]}]};
  const { indexHtml } = buildSite(t, {});
  assert.match(indexHtml, /\$&/);              // literal $& preserved in injected JSON
  assert.doesNotMatch(indexHtml, /%%TRACK%%/);  // not expanded to the matched-substring pattern
});

test("buildSite unwraps a 1-element array (canonical track.json shape)", () => {
  const { screens } = buildSite([track], { samples: { cs: "x" } });
  assert.equal(screens.length, 3);
});

test("buildSite throws on a multi-track array rather than silently previewing one", () => {
  assert.throws(() => buildSite([track, track], {}), /array of 2/);
});

test("buildSite throws on a token used before it is produced", () => {
  const bad = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "Hi {name}", type: "say", fieldType: "banner" },
  ]}]};
  assert.throws(() => buildSite(bad, {}), /\{name\}/);
});

test("bakes proxy config when provided; null when absent", () => {
  const withProxy = buildSite(track, { proxy: { url: "https://p", token: "t" } });
  assert.match(withProxy.indexHtml, /window\.__PROXY__ = \{"url":"https:\/\/p","token":"t"\}/);
  const without = buildSite(track, {});
  assert.match(without.indexHtml, /window\.__PROXY__ = null/);
});

test("bakes assessment weights + types into window.__ASSESSMENT__ (vendored data by default)", () => {
  const { indexHtml } = buildSite(track, {});
  assert.match(indexHtml, /window\.__ASSESSMENT__ =/);
  assert.doesNotMatch(indexHtml, /%%ASSESSMENT%%/); // placeholder fully replaced
  // vendored data is present: an answerId from the real weights file and a framework type
  assert.match(indexHtml, /"answerId"/);
  assert.match(indexHtml, /"myersBriggs"/);
});

test("assessment bake is overridable (test fixture) and < is escaped", () => {
  const fixture = { weights: [{ answerId: "x", optionText: "</script>" }], types: { myersBriggs: [] } };
  const { indexHtml } = buildSite(track, { assessment: fixture });
  assert.match(indexHtml, /window\.__ASSESSMENT__ =/);
  assert.match(indexHtml, /\\u003c\/script>/);          // < escaped, no real breakout
  assert.doesNotMatch(indexHtml, /<\/script>"\}\];/);
});
