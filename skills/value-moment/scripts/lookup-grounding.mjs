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
 * Snapshot resolution order: --snapshot → $GROUNDING_SNAPSHOT →
 * ~/code/track-studio/data/grounding-snapshot.json. If none is found, this prints
 * how to point at it and exits 0 — the author then keeps the nugget qualitative
 * (the faithfulness fallback), never fabricating a number.
 */
import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

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
    join(homedir(), "code/track-studio/data/grounding-snapshot.json"),
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
const norm = (s) => (s ?? "").trim().toLowerCase();

if (has("--list")) {
  const majors = Object.entries(snap.majors).map(([cip, m]) => `  ${m.title}  [${cip}]`);
  console.log(`Majors covered in the snapshot (${majors.length}):\n${majors.join("\n")}`);
  console.log(`\nVintage: ${snap.vintage?.oews ?? "n/a"}`);
  process.exit(0);
}

if (!major) {
  console.log('Pass a major, e.g.  node lookup-grounding.mjs "Marketing"   (or --list)');
  process.exit(0);
}

let hit = null;
for (const [cip, m] of Object.entries(snap.majors)) {
  if (norm(m.title) === norm(major)) { hit = { cip, ...m }; break; }
}
if (!hit) {
  console.log(
    `"${major}" is not in the snapshot yet. Covered majors: ` +
    Object.values(snap.majors).map((m) => m.title).join(", ") + ".\n" +
    "For an uncovered major, keep the nugget qualitative (model-reasoned) or extend " +
    "TARGET_CIPS in track-studio's scripts/ingest-grounding.py and re-ingest.",
  );
  process.exit(0);
}

if (has("--json")) {
  console.log(JSON.stringify({ cip: hit.cip, major: hit.title, careers: hit.careers,
    vintage: snap.vintage, attribution: snap.attribution }, null, 2));
  process.exit(0);
}

console.log(`REAL grounding data for "${hit.title}" (CIP ${hit.cip}) — use these figures verbatim:\n`);
for (const c of hit.careers) {
  const wage = c.medianWageAnnual
    ? `national median $${c.medianWageAnnual.toLocaleString()} (${c.wageYear})`
    : "wage not available — describe qualitatively";
  const growth = c.growthPct != null ? `, projected growth ${c.growthPct}%` : "";
  console.log(`  • ${c.title} (SOC ${c.soc}): ${wage}${growth}`);
}
console.log(`\nVintage: ${snap.vintage?.oews ?? "n/a"}  |  Growth: ${snap.vintage?.growth ?? "not yet ingested"}`);
console.log(`Attribution (carry into the doc): ${snap.attribution.join(" ")}`);
console.log(
  "\nUse ONLY these figures in the nugget's example_output. Anything not listed → " +
  "describe qualitatively, invent no number (the faithfulness rule).",
);
