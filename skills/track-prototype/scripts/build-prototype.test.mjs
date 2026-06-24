import { test } from "node:test";
import assert from "node:assert/strict";
import { buildSite, collectAssetPaths, copyTrackAssets } from "./build-prototype.mjs";

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

// --- Fidelity pass: real app assets in the build -----------------------------

test("collectAssetPaths gathers substep + option image/video URLs, root-relative only", () => {
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/intro/intro-1.png" },
    { id: "b", slug: "q", title: "B", prompt: "P", type: "collect", fieldType: "image-multiselect",
      options: [{ text: "X", imageUrl: "/img/assessment/x.png" }, { text: "Y", imageUrl: "https://cdn.example.com/y.png" }, "plain"] },
    { id: "c", title: "C", prompt: "", type: "say", fieldType: "celebration", imageUrl: "/video/done.mp4" },
    { id: "d", title: "D2", prompt: "P", type: "say", fieldType: "banner", imageUrl: "javascript:alert(1)" },
  ]}]};
  assert.deepEqual(collectAssetPaths(t), ["/img/assessment/x.png", "/img/intro/intro-1.png", "/video/done.mp4"]);
});

test("collectAssetPaths de-dupes repeated references", () => {
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/same.png" },
    { id: "b", title: "B", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/same.png" },
  ]}]};
  assert.deepEqual(collectAssetPaths(t), ["/img/same.png"]);
});

test("copyTrackAssets copies only referenced files, reports missing ones gracefully", async () => {
  const { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } = await import("node:fs");
  const { join } = await import("node:path");
  const { tmpdir } = await import("node:os");
  const srcRoot = mkdtempSync(join(tmpdir(), "tp-assets-src-"));
  const outDir = mkdtempSync(join(tmpdir(), "tp-assets-out-"));
  mkdirSync(join(srcRoot, "img", "intro"), { recursive: true });
  writeFileSync(join(srcRoot, "img", "intro", "intro-1.png"), "png-bytes");
  writeFileSync(join(srcRoot, "img", "unreferenced.png"), "should-not-copy");
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/intro/intro-1.png" },
    { id: "b", title: "B", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/intro/missing.png" },
  ]}]};
  const { copied, missing } = copyTrackAssets(t, srcRoot, outDir);
  assert.deepEqual(copied, ["/img/intro/intro-1.png"]);
  assert.deepEqual(missing, ["/img/intro/missing.png"]);
  assert.ok(existsSync(join(outDir, "img", "intro", "intro-1.png")));   // path preserved
  assert.ok(!existsSync(join(outDir, "img", "unreferenced.png")));      // never wholesale
  rmSync(srcRoot, { recursive: true, force: true });
  rmSync(outDir, { recursive: true, force: true });
});

test("copyTrackAssets refuses path traversal (no read/write outside the roots)", async () => {
  const { mkdtempSync, mkdirSync, writeFileSync, existsSync, rmSync } = await import("node:fs");
  const { join } = await import("node:path");
  const { tmpdir } = await import("node:os");
  const base = mkdtempSync(join(tmpdir(), "tp-trav-"));
  const srcRoot = join(base, "app", "assets"); mkdirSync(srcRoot, { recursive: true });
  const outDir = join(base, "build"); mkdirSync(outDir, { recursive: true });
  // a sibling secret outside both roots
  mkdirSync(join(base, "shared"), { recursive: true });
  writeFileSync(join(base, "shared", "secret.png"), "exfiltrate-me");
  const t = { id: "t", title: "D", steps: [{ id: "s", title: "S", substeps: [
    { id: "a", title: "A", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/../../shared/secret.png" },
  ]}]};
  // collectAssetPaths drops the traversal path entirely
  assert.deepEqual(collectAssetPaths(t), []);
  const { copied, skipped } = copyTrackAssets(t, srcRoot, outDir);
  assert.deepEqual(copied, []);                                  // nothing copied
  assert.ok(!existsSync(join(base, "shared", "secret.png.bak"))); // (sanity)
  // the secret must NOT have been written anywhere under outDir or base via traversal
  assert.ok(!existsSync(join(base, "secret.png")));
  rmSync(base, { recursive: true, force: true });
});

test("buildSite injects the track title into the chrome header", () => {
  const { indexHtml } = buildSite(track, {});
  assert.match(indexHtml, />Demo<\/h1>/);
});

test("buildSite escapes a hostile track title in the chrome header", () => {
  const t = { ...track, title: '<img src=x onerror=alert(1)>' };
  const { indexHtml } = buildSite(t, {});
  assert.doesNotMatch(indexHtml, /<img src=x/);
  assert.match(indexHtml, /&lt;img src=x/);
});
