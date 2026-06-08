import { readFileSync, writeFileSync, mkdirSync, cpSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { renderSubstep } from "./lib/render-substep.mjs";
import { findOrderingErrors } from "./lib/ordering-lint.mjs";
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
  const ctx = { samples: opts.samples || {} };
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
    .replace("__DATE__", () => opts.date || "");
  return { indexHtml, screens };
}

function parseArgs(argv) {
  const get = (flag) => { const i = argv.indexOf(flag); return i !== -1 ? argv[i + 1] : undefined; };
  return { file: argv.find((a) => !a.startsWith("--") && a.endsWith(".json")),
    persona: get("--persona"), samplesPath: get("--samples"),
    out: get("--out") || "prototype-build", assume: (get("--assume") || "").split(",").filter(Boolean),
    proxyUrl: get("--proxy-url"), proxyToken: get("--proxy-token") };
}

// fileURLToPath decodes percent-encoding so the check survives paths with spaces.
const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const { file, samplesPath, out, assume, proxyUrl, proxyToken } = parseArgs(process.argv.slice(2));
  if (!file) { console.error("Usage: build-prototype.mjs <track.json> [--persona name] [--samples samples.json] [--out dir] [--assume a,b] [--proxy-url url] [--proxy-token token]"); process.exit(2); }
  const raw = JSON.parse(readFileSync(file, "utf8"));
  const track = Array.isArray(raw) ? raw[0] : raw; // track files may be wrapped in a top-level array
  const samples = samplesPath ? JSON.parse(readFileSync(samplesPath, "utf8")) : {};
  const date = new Date().toISOString().slice(0, 10);
  const proxy = proxyUrl ? { url: proxyUrl, token: proxyToken || "" } : undefined;
  const { indexHtml } = buildSite(track, { samples, assume, date, proxy });
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, "index.html"), indexHtml);
  cpSync(join(PROTO, "design-kit"), join(out, "design-kit"), { recursive: true });
  cpSync(join(PROTO, "player.js"), join(out, "player.js"));
  cpSync(join(PROTO, "player-core.mjs"), join(out, "player-core.mjs"));
  cpSync(join(HERE, "lib", "interpolate.mjs"), join(out, "interpolate.mjs"));
  cpSync(join(HERE, "lib", "assessment-score.mjs"), join(out, "assessment-score.mjs"));
  console.log(`Built ${out}/`);
}
