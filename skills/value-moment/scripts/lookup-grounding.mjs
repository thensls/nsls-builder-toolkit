#!/usr/bin/env node
/**
 * lookup-grounding.mjs — authoring-time preview of REAL grounding figures.
 *
 * When designing a value moment, run this to see the actual careers + BLS median
 * wages a major grounds against, so the candidate's `grounding` + `example_output`
 * use real numbers — not model-guesses. This reads the SAME baked snapshot the
 * runtime injects (`track-studio/data/grounding-snapshot.json`), so what you
 * preview here is what a member gets.
 *
 * Usage:
 *   node lookup-grounding.mjs "Marketing"            # figures for a major
 *   node lookup-grounding.mjs --list                 # majors currently covered
 *   node lookup-grounding.mjs "Marketing" --json     # structured output
 *   node lookup-grounding.mjs "Marketing" --snapshot /path/to/grounding-snapshot.json
 *
 * Snapshot resolution order: --snapshot → $GROUNDING_SNAPSHOT → a live
 * ~/code/track-studio checkout → the copy BUNDLED with this skill
 * (data/grounding-snapshot.json). track-studio's ingest is the source of record;
 * the bundled copy is refreshed from it (re-copy after re-ingesting), so the
 * lookup works in any toolkit checkout without track-studio present.
 */
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

const argv = process.argv.slice(2);
const flag = (f) => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : undefined; };
const has = (f) => argv.includes(f);
const major = argv.find((a) => !a.startsWith("--") && argv[argv.indexOf(a) - 1] !== "--snapshot");

function findSnapshot() {
  // An EXPLICIT --snapshot must exist — don't silently fall back to a different
  // (possibly stale) snapshot on a typo.
  const explicit = flag("--snapshot");
  if (explicit) return existsSync(explicit) ? explicit : { error: explicit };
  const candidates = [
    process.env.GROUNDING_SNAPSHOT,
    // A live track-studio checkout (freshest if the author maintains it)…
    join(homedir(), "code/track-studio/data/grounding-snapshot.json"),
    // …else the copy bundled with this skill, so the lookup always resolves.
    join(HERE, "..", "data", "grounding-snapshot.json"),
  ].filter(Boolean);
  return candidates.find((p) => existsSync(p)) || null;
}

const found = findSnapshot();
if (found && typeof found === "object") {
  console.error(`--snapshot path not found: ${found.error}. Fix the path or omit --snapshot to use the default.`);
  process.exit(1);
}
const path = found;
if (!path) {
  console.log(
    "No grounding snapshot found. Looked at: --snapshot, $GROUNDING_SNAPSHOT, " +
    "~/code/track-studio/data/grounding-snapshot.json.\n" +
    "Point at it with --snapshot <path>, or (re)build it: " +
    "`python3.12 scripts/ingest-grounding.py` in the track-studio repo.\n" +
    "Without it, keep the value moment qualitative (model-reasoned) — do NOT invent numbers.",
  );
  process.exit(0);
}

const snap = JSON.parse(readFileSync(path, "utf-8"));
const norm = (s) => (s ?? "").trim().toLowerCase().replace(/\.$/, "");
const primary = (t) => norm(String(t).split(/[/,;:]/)[0]);

// Minimal location → 2-letter state resolver, for --state (state-specific wages).
const STATES = { alabama:"AL",alaska:"AK",arizona:"AZ",arkansas:"AR",california:"CA",colorado:"CO",connecticut:"CT",delaware:"DE","district of columbia":"DC",florida:"FL",georgia:"GA",hawaii:"HI",idaho:"ID",illinois:"IL",indiana:"IN",iowa:"IA",kansas:"KS",kentucky:"KY",louisiana:"LA",maine:"ME",maryland:"MD",massachusetts:"MA",michigan:"MI",minnesota:"MN",mississippi:"MS",missouri:"MO",montana:"MT",nebraska:"NE",nevada:"NV","new hampshire":"NH","new jersey":"NJ","new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND",ohio:"OH",oklahoma:"OK",oregon:"OR",pennsylvania:"PA","rhode island":"RI","south carolina":"SC","south dakota":"SD",tennessee:"TN",texas:"TX",utah:"UT",vermont:"VT",virginia:"VA",washington:"WA","west virginia":"WV",wisconsin:"WI",wyoming:"WY","puerto rico":"PR" };
const ABBRS = new Set(Object.values(STATES));
function resolveState(loc) {
  const s = norm(loc);
  if (!s) return null;
  if (s.length === 2 && ABBRS.has(s.toUpperCase())) return s.toUpperCase();
  return STATES[s] || null;
}
const stateArg = flag("--state");
const st = resolveState(stateArg);
const stName = st ? Object.keys(STATES).find((n) => STATES[n] === st).replace(/\b\w/g, (c) => c.toUpperCase()) : null;

// Resolve free-text major → CIP (mirrors track-studio lib/grounding matchMajor):
// exact title → primary-term → substring, preferring "General" then shortest.
// Returns { cip, exact, alternatives } — exact=true when title/primary matched
// exactly (a picklist value); false for a loose substring match, where the
// author should eyeball the alternatives. (Canonical disambiguation of ambiguous
// common names — e.g. "Nursing" → Registered vs. Science — needs popularity
// ranking via IPEDS completions; a fast-follow. Figures are always real either way.)
function matchMajor(want) {
  want = norm(want);
  if (!want) return null;
  const entries = Object.entries(snap.majors);
  const rank = (list) => list.slice().sort((a, b) =>
    (b[1].popularity ?? 0) - (a[1].popularity ?? 0)          // most-awarded first (IPEDS)
    || (/general/i.test(a[1].title) ? 0 : 1) - (/general/i.test(b[1].title) ? 0 : 1)
    || a[1].title.length - b[1].title.length);

  const exactTitle = entries.find(([, m]) => norm(m.title) === want);
  if (exactTitle) return { cip: exactTitle[0], exact: true, alternatives: [] };
  const primaryExact = rank(entries.filter(([, m]) => primary(m.title) === want));
  if (primaryExact.length) return { cip: primaryExact[0][0], exact: true, alternatives: [] };

  let cands = rank(entries.filter(([, m]) => primary(m.title).includes(want)));
  if (!cands.length) cands = rank(entries.filter(([, m]) => norm(m.title).includes(want)));
  if (!cands.length) return null;
  return { cip: cands[0][0], exact: false, alternatives: cands.slice(1, 5).map(([cip, m]) => `${m.title} [${cip}]`) };
}

if (has("--list")) {
  const count = Object.keys(snap.majors).length;
  console.log(`Snapshot covers ${count} CIP majors (full catalog). Vintage: ${snap.vintage?.oews ?? "n/a"}.`);
  console.log(`Just look one up by name — free-text matching resolves it, e.g.:  node lookup-grounding.mjs "Marketing"`);
  const filter = flag("--list");
  if (filter) {
    const hits = Object.entries(snap.majors)
      .filter(([, m]) => m.title.toLowerCase().includes(filter.toLowerCase()))
      .slice(0, 40).map(([cip, m]) => `  ${m.title}  [${cip}]`);
    console.log(hits.length ? `\nTitles containing "${filter}":\n${hits.join("\n")}` : `\nNo titles contain "${filter}".`);
  }
  process.exit(0);
}

if (!major) {
  console.log('Pass a major, e.g.  node lookup-grounding.mjs "Marketing"   (or --list)');
  process.exit(0);
}

const m = matchMajor(major);
const hit = m ? { cip: m.cip, ...snap.majors[m.cip] } : null;
if (!hit) {
  console.log(
    `No CIP match for "${major}" in the snapshot (${Object.keys(snap.majors).length} majors). ` +
    "Try a broader term, or run --list to browse. For a genuinely uncovered major, keep the " +
    "nugget qualitative (model-reasoned) — never fabricate a number.",
  );
  process.exit(0);
}

if (has("--json")) {
  console.log(JSON.stringify({ cip: hit.cip, major: hit.title, careers: hit.careers,
    vintage: snap.vintage, attribution: snap.attribution }, null, 2));
  process.exit(0);
}

console.log(`REAL grounding data for "${hit.title}" (CIP ${hit.cip}) — use these figures verbatim:\n`);
if (!m.exact && m.alternatives.length) {
  console.log(`(Loose match on "${major}". If you meant another program, re-run with the exact title or CIP. Other matches: ${m.alternatives.join(", ")})\n`);
}
if (stateArg && !st) console.log(`(--state "${stateArg}" not recognized; showing national wages)\n`);
for (const c of hit.careers) {
  const stateWage = st ? snap.stateWages?.[c.soc]?.[st] : undefined;
  const median = stateWage != null ? stateWage : c.medianWageAnnual;
  const area = stateWage != null ? `${stName} median` : "national median";
  const wage = median != null
    ? `${area} $${median.toLocaleString()} (${c.wageYear || snap.vintage?.oews || ""})`
    : "wage not available — describe qualitatively";
  const growth = c.growthPct != null ? `, projected ${c.growthPct}% growth` : "";
  console.log(`  • ${c.title} (SOC ${c.soc}): ${wage}${growth}`);
}
console.log(`\nVintage: ${snap.vintage?.oews ?? "n/a"}  |  Growth: ${snap.vintage?.growth ?? "not yet ingested"}`);
console.log(`Attribution (carry into the doc): ${snap.attribution.join(" ")}`);
console.log(
  "\nUse ONLY these figures in the nugget's example_output. Anything not listed → " +
  "describe qualitatively, invent no number (the faithfulness rule).",
);
