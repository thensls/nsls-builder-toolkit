// Build-time check: every {slug} referenced in a substep must be produced by an
// earlier collect/generate substep (or passed via opts.assume). Mirrors the rule in
// track-design/scripts/validate-track-json.mjs, scoped to the flat substep order.
const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/g;

function collectStrings(value, out) {
  if (typeof value === "string") out.push(value);
  else if (Array.isArray(value)) for (const v of value) collectStrings(v, out);
  else if (value && typeof value === "object") for (const v of Object.values(value)) collectStrings(v, out);
  return out;
}

function tokensIn(substep) {
  const { id, slug, ...rest } = substep;
  const found = new Set();
  for (const s of collectStrings(rest, [])) for (const m of s.matchAll(TOKEN_RE)) found.add(m[1]);
  return found;
}

export function findOrderingErrors(tracks, opts = {}) {
  const errors = [];
  const produced = new Set(opts.assume || []);
  for (const track of tracks) {
    for (const step of track.steps || []) {
      for (const sub of step.substeps || []) {
        for (const tok of tokensIn(sub)) {
          if (!produced.has(tok)) {
            errors.push(`substep "${sub.id}" uses {${tok}} before any earlier substep produces it.`);
          }
        }
        if (sub.slug && (sub.type === "collect" || sub.type === "generate")) produced.add(sub.slug);
      }
    }
  }
  return errors;
}
