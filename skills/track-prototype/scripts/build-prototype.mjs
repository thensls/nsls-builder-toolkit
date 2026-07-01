import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { renderSubstep, computeAssessmentProgress, safeUrl } from "./lib/render-substep.mjs";
import { findOrderingErrors } from "./lib/ordering-lint.mjs";
import { buildPrereqProfile } from "./lib/synth-profile.mjs";
import { flattenSubsteps } from "../prototype/player-core.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PROTO = join(HERE, "..", "prototype");
const DATA = join(HERE, "data");

// Vendored assessment scoring data (copied from ignite-next). Baked into the page so
// the player can compute personality results client-side. Read lazily so a missing
// file doesn't break non-assessment builds.
function loadAssessmentData() {
  try {
    return {
      weights: JSON.parse(readFileSync(join(DATA, "assessment-scoring-weights.json"), "utf8")),
      types: JSON.parse(readFileSync(join(DATA, "assessment-types.json"), "utf8")),
    };
  } catch {
    return null;
  }
}

// Stringify for embedding inside a <script> tag: escape "<" so a value containing
// "</script>" can't close the tag early (the raw track object is injected unescaped
// into window.__TRACK__). Standard hardening for JSON-in-HTML.
function jsonForScript(value) {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}

// ---------------------------------------------------------------------------
// Asset resolution — REAL app images/videos in the build.
// Tracks reference assets by root-relative URL (e.g. /img/intro/intro-1.png,
// /video/x.mp4). collectAssetPaths() walks the track for every such reference;
// copyTrackAssets() copies ONLY those files from an assets root (ignite-next's
// public/ dir) into the build, preserving paths so the URLs resolve when the
// build dir is served at root. Missing files are skipped gracefully + reported.
// ---------------------------------------------------------------------------
export function collectAssetPaths(track) {
  const paths = new Set();
  const consider = (u) => {
    const s = safeUrl(u);
    // Only root-relative app assets are copyable (http(s)/data: pass through untouched).
    // Reject any "../" traversal segment — a crafted imageUrl must not escape the assets
    // root (read) or the build dir (write). Track JSON can come from shared sources.
    if (s && s.startsWith("/") && !s.startsWith("//") && !s.split("/").includes("..")) paths.add(s);
  };
  for (const sub of flattenSubsteps(track)) {
    consider(sub.imageUrl);
    for (const o of sub.options || []) {
      if (o && typeof o === "object") consider(o.imageUrl);
    }
  }
  return [...paths].sort();
}

export function copyTrackAssets(track, assetsRoot, outDir) {
  const wanted = collectAssetPaths(track);
  const copied = [];
  const missing = [];
  const skipped = [];
  const rootR = resolve(assetsRoot) + sep;
  const outR = resolve(outDir) + sep;
  const within = (p, base) => { const r = resolve(p); return r === base.slice(0, -1) || r.startsWith(base); };
  for (const rel of wanted) {
    const src = join(assetsRoot, rel); // rel starts with "/" — join normalizes
    const dest = join(outDir, rel);
    // Defense in depth: even though collectAssetPaths drops ".." segments, confirm the
    // resolved src/dest stay inside their roots before any fs read/write.
    if (!within(src, rootR) || !within(dest, outR)) { skipped.push(rel); continue; }
    if (!existsSync(src)) { missing.push(rel); continue; }
    mkdirSync(dirname(dest), { recursive: true });
    cpSync(src, dest);
    copied.push(rel);
  }
  return { copied, missing, skipped };
}

export function buildSite(input, opts = {}) {
  // A canonical track.json (what validate-track-json accepts) is a top-level ARRAY of
  // tracks. Preview targets one track — unwrap a single-element array. Throw clearly on
  // an ambiguous multi-track array rather than silently previewing only the first.
  let track = input;
  if (Array.isArray(input)) {
    if (input.length !== 1) throw new Error(`Expected one track, got an array of ${input.length}. Pass a single track or a 1-element array.`);
    track = input[0];
  }
  const errs = findOrderingErrors([track], { assume: opts.assume || [] });
  if (errs.length) throw new Error("Token ordering errors:\n" + errs.join("\n"));

  // Personality progress (PersonalityProgressTracker fallback) is computed per
  // STEP — the app derives it from the current step's substeps.
  const progress = {};
  for (const step of track.steps || []) {
    Object.assign(progress, computeAssessmentProgress(step.substeps || []));
  }

  const ctx = { samples: opts.samples || {}, progress };
  const screens = flattenSubsteps(track).map((sub) => renderSubstep(sub, ctx));
  const template = readFileSync(join(PROTO, "template.html"), "utf8");
  // opts.assessment lets tests inject a tiny fixture; default to the vendored data.
  const assessment = opts.assessment !== undefined ? opts.assessment : loadAssessmentData();
  // Use FUNCTION replacers: a string replacement would interpret $&, $`, $$, $n in the
  // value as special patterns, corrupting JSON whose content contains a literal "$&" etc.
  const indexHtml = template
    .replace("%%TRACK%%", () => jsonForScript(track))
    .replace("%%SCREENS%%", () => jsonForScript(screens))
    .replace("%%PROXY%%", () => jsonForScript(opts.proxy || null))
    .replace("%%ASSESSMENT%%", () => jsonForScript(assessment || null))
    .replace("%%PREREQ%%", () => jsonForScript(opts.prereqProfile || {}))
    .replace("__TRACK_TITLE__", () => String(track.title || "Track Preview").replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])))
    .replace("__DATE__", () => opts.date || "");
  return { indexHtml, screens };
}

function parseArgs(argv) {
  const get = (flag) => { const i = argv.indexOf(flag); return i !== -1 ? argv[i + 1] : undefined; };
  return { file: argv.find((a) => !a.startsWith("--") && a.endsWith(".json")),
    persona: get("--persona"), samplesPath: get("--samples"),
    out: get("--out") || "prototype-build", assume: (get("--assume") || "").split(",").filter(Boolean),
    proxyUrl: get("--proxy-url"), proxyToken: get("--proxy-token"),
    assets: get("--assets"),
    prereq: (get("--prereq") || "").split(",").map((s) => s.trim()).filter(Boolean) };
}

// fileURLToPath decodes percent-encoding so the check survives paths with spaces.
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const { file, samplesPath, out, assume, proxyUrl, proxyToken, assets, prereq } = parseArgs(process.argv.slice(2));
  if (!file) { console.error("Usage: build-prototype.mjs <track.json> [--persona name] [--samples samples.json] [--out dir] [--assume a,b] [--prereq prereqA.json,prereqB.json] [--proxy-url url] [--proxy-token token] [--assets <app-public-dir>]"); process.exit(2); }
  const raw = JSON.parse(readFileSync(file, "utf8"));
  const track = Array.isArray(raw) ? raw[0] : raw; // track files may be wrapped in a top-level array
  const samples = samplesPath ? JSON.parse(readFileSync(samplesPath, "utf8")) : {};
  const date = new Date().toISOString().slice(0, 10);
  const proxy = proxyUrl ? { url: proxyUrl, token: proxyToken || "" } : undefined;
  // Prerequisite tracks → a synthetic profile seeded into the demo so cross-track
  // generate/chat steps resolve. Each is a track.json (array-wrapped ok), in order.
  const prereqTracks = prereq.map((p) => {
    const r = JSON.parse(readFileSync(p, "utf8"));
    return Array.isArray(r) ? r[0] : r;
  });
  const prereqProfile = buildPrereqProfile(prereqTracks);
  if (prereq.length) console.log(`prereq: seeded ${Object.keys(prereqProfile).length} synthetic field(s) from ${prereq.length} track(s)`);
  // Prerequisite slugs are available as tokens (they're seeded into the profile),
  // so treat them as assumed for the ordering validator — union with explicit --assume.
  const assumeAll = [...new Set([...assume, ...Object.keys(prereqProfile)])];
  const { indexHtml } = buildSite(track, { samples, assume: assumeAll, date, proxy, prereqProfile });
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, "index.html"), indexHtml);
  cpSync(join(PROTO, "design-kit"), join(out, "design-kit"), { recursive: true });
  cpSync(join(PROTO, "player.js"), join(out, "player.js"));
  cpSync(join(PROTO, "player-core.mjs"), join(out, "player-core.mjs"));
  cpSync(join(HERE, "lib", "interpolate.mjs"), join(out, "interpolate.mjs"));
  cpSync(join(HERE, "lib", "assessment-score.mjs"), join(out, "assessment-score.mjs"));
  cpSync(join(HERE, "lib", "runtime-classes.mjs"), join(out, "runtime-classes.mjs"));

  // Real app assets (images/videos) — copy ONLY what the track references.
  // Heartbeat: always report what happened so a skipped step is visible.
  const wanted = collectAssetPaths(track);
  if (assets) {
    const { copied, missing } = copyTrackAssets(track, assets, out);
    console.log(`assets: ${copied.length}/${wanted.length} copied from ${assets}` +
      (missing.length ? ` — MISSING ${missing.length}: ${missing.slice(0, 5).join(", ")}${missing.length > 5 ? ", …" : ""}` : ""));
  } else {
    console.log(`assets: scanned ${wanted.length} referenced asset(s); no --assets dir provided, URLs left as-is (will 404 unless served elsewhere)`);
  }
  console.log(`Built ${out}/`);
}
