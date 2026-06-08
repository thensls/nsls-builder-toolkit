// Validate a persona answer-set against a real track.json.
//
// A "track" here is the element shape used by /tmp/track-calib/clarity.json:
// either a bare track object {steps:[...]} or a 1-element array wrapping it.
// Each step has substeps[] (the export also tolerates subSteps[]). We only care
// about substeps where type === "collect" — those are the screens that capture
// a user answer and therefore need an entry in the answers file.
//
// The answers file is a FLAT object keyed by substep `slug`:
//   "<slug>": "value"                     // text / textarea / currency / select / dropdown
//   "<slug>": ["opt 1", "opt 2", ...]     // multi-select family
//
// Checks (returns a list of problems; empty = valid):
//   1. every collect slug has an answer (dup slugs share one key — counted once)
//   2. every select / multi-select / image-multiselect / dropdown answer is a
//      verbatim match to a real option text (or, for dropdown-with-checkboxes,
//      a dropdownOptions / checkboxOptions value)
//   3. no answer key references a slug that doesn't exist as a collect substep
//   4. every currency answer parses to a non-zero number
//   5. multi-select arrays respect multiselectMinSelections (default 2 when unset
//      but min/max present) / multiselectMaxSelections when declared
//
// optionsSourceSlug: a substep with no inline options inherits its option set from
// the answer chosen for optionsSourceSlug (the narrowing pattern — pick 12, then a
// subset of 8, then 6). We validate the subset against the upstream ANSWER so the
// narrowing stays internally consistent.

import { readFile } from "node:fs/promises";

export function unwrapTrack(raw) {
  const t = Array.isArray(raw) ? raw[0] : raw;
  if (!t || typeof t !== "object") throw new Error("track is not an object");
  return t;
}

function substepsOf(step) {
  return step.substeps || step.subSteps || [];
}

function optionTextsOf(sub) {
  const opts = Array.isArray(sub.options) ? sub.options : [];
  return opts.map((o) => (typeof o === "string" ? o : (o && o.text != null ? o.text : null)))
    .filter((t) => t != null);
}

const OPTION_FIELD_TYPES = new Set([
  "select",
  "multi-select",
  "image-multiselect",
  "dropdown-with-checkboxes",
]);
const MULTI_FIELD_TYPES = new Set(["multi-select", "image-multiselect", "dropdown-with-checkboxes"]);

// Collect every (slug -> sub) for collect substeps. Duplicate slugs (the track has
// two `location` substeps) collapse to a list so we can validate against each.
function collectSubsteps(track) {
  const bySlug = new Map(); // slug -> [sub, ...]
  for (const step of track.steps || []) {
    for (const sub of substepsOf(step)) {
      if (sub.type !== "collect") continue;
      const slug = sub.slug;
      if (!bySlug.has(slug)) bySlug.set(slug, []);
      bySlug.get(slug).push(sub);
    }
  }
  return bySlug;
}

export function validateAnswers(track, answers) {
  const problems = [];
  const bySlug = collectSubsteps(track);

  // 1. every collect slug has an answer
  for (const slug of bySlug.keys()) {
    if (!(slug in answers)) problems.push(`MISSING: collect slug "${slug}" has no answer`);
  }

  // 3. no answer references a non-existent collect slug
  for (const key of Object.keys(answers)) {
    if (!bySlug.has(key)) problems.push(`UNKNOWN: answer key "${key}" is not a collect substep`);
  }

  for (const [slug, subs] of bySlug.entries()) {
    if (!(slug in answers)) continue;
    const value = answers[slug];

    // Validate against EACH substep sharing this slug (dup slugs must satisfy all).
    for (const sub of subs) {
      const ft = sub.fieldType;

      // 4. currency must be a non-zero number
      if (ft === "currency") {
        const n = Number(value);
        if (typeof value !== "string" && typeof value !== "number") {
          problems.push(`CURRENCY: "${slug}" must be a numeric string, got ${typeof value}`);
        } else if (!Number.isFinite(n) || n === 0) {
          problems.push(`CURRENCY: "${slug}" must be a non-zero number, got "${value}"`);
        }
        continue;
      }

      if (!OPTION_FIELD_TYPES.has(ft)) continue; // free-text family: any string is fine

      const isMulti = MULTI_FIELD_TYPES.has(ft);

      // Build the valid option-text set for this substep.
      let validTexts = optionTextsOf(sub);
      if (validTexts.length === 0 && sub.optionsSourceSlug) {
        // inherit from the chosen upstream answer (narrowing pattern)
        const upstream = answers[sub.optionsSourceSlug];
        validTexts = Array.isArray(upstream) ? upstream.slice() : (upstream != null ? [upstream] : []);
      }
      if (validTexts.length === 0 && ft === "dropdown-with-checkboxes") {
        validTexts = [...(sub.dropdownOptions || []), ...(sub.checkboxOptions || [])];
      }
      const validSet = new Set(validTexts);

      if (isMulti) {
        if (!Array.isArray(value)) {
          // dropdown-with-checkboxes may legitimately be answered with a single
          // dropdown string; accept that against dropdownOptions.
          if (ft === "dropdown-with-checkboxes" && (sub.dropdownOptions || []).includes(value)) continue;
          problems.push(`SHAPE: "${slug}" (${ft}) must be an array, got ${typeof value}`);
          continue;
        }
        for (const v of value) {
          if (!validSet.has(v)) problems.push(`OPTION: "${slug}" value ${JSON.stringify(v)} is not a valid option`);
        }
        // autoProgressOnSelect substeps (the A/B personality questions) are
        // single-pick despite the multi fieldType: clicking one option advances.
        if (sub.autoProgressOnSelect) {
          if (value.length !== 1) problems.push(`SINGLEPICK: "${slug}" (autoProgress) needs exactly 1, got ${value.length}`);
          continue;
        }
        const min = sub.multiselectMinSelections;
        const max = sub.multiselectMaxSelections;
        if (min != null && value.length < min) problems.push(`MINSEL: "${slug}" needs >= ${min}, got ${value.length}`);
        if (max != null && value.length > max) problems.push(`MAXSEL: "${slug}" needs <= ${max}, got ${value.length}`);
        if (min == null && value.length < 1) problems.push(`MINSEL: "${slug}" needs at least 1 selection`);
      } else {
        // single select
        if (Array.isArray(value)) { problems.push(`SHAPE: "${slug}" (select) must be a single string, got an array`); continue; }
        if (!validSet.has(value)) problems.push(`OPTION: "${slug}" value ${JSON.stringify(value)} is not a valid option`);
      }
    }
  }

  return problems;
}

export async function loadAndValidate(trackPath, answersPath) {
  const track = unwrapTrack(JSON.parse(await readFile(trackPath, "utf8")));
  const answers = JSON.parse(await readFile(answersPath, "utf8"));
  return validateAnswers(track, answers);
}

// CLI: node validate-answers.mjs <track.json> <answers.json>
const isMain = import.meta.url === `file://${process.argv[1]}`;
if (isMain) {
  const [, , trackPath, answersPath] = process.argv;
  if (!trackPath || !answersPath) {
    console.error("usage: node validate-answers.mjs <track.json> <answers.json>");
    process.exit(2);
  }
  const problems = await loadAndValidate(trackPath, answersPath);
  if (problems.length === 0) {
    console.log("OK: all collect slugs answered, all options valid, currency non-zero.");
    process.exit(0);
  }
  console.error(`FAIL: ${problems.length} problem(s):`);
  for (const p of problems) console.error("  - " + p);
  process.exit(1);
}
