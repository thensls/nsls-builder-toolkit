/**
 * synth-profile.mjs — shared profile-field inventory + synthetic values.
 *
 * One place for: deriving the profile fields a track produces, and filling each
 * with a representative synthetic value. Used by the prototype build to seed a
 * demo's prerequisite profile (so cross-track generate/chat steps resolve), and
 * intended as the shared module the prompt-pack skill converges on (spec
 * Component 5) so the demo's "prompt context note" and the dev prompt-pack show
 * the same values.
 *
 * Never real member data — synthetic, representative, labelled as sample.
 */

/** Mirror the track schema / validator: an omitted slug is derived from title. */
export function slugify(s) {
  return String(s).toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

/** A representative synthetic value: keyword match on slug, then fieldType, then a labelled fallback. */
export function synthValue(slug, fieldType) {
  const s = (slug || "").toLowerCase();
  // Keywords match whole hyphen-delimited slug segments (optional trailing "s"),
  // so e.g. "state" matches "home-state"/"states" but NOT "statement", and
  // "rent" won't match "current", "value" won't match "evaluate".
  const kw = [
    [/(^|-)(major|field-of-study)s?($|-)/, "Marketing"],
    [/(^|-)(state|location|region|city|address)s?($|-)/, "Ohio"],
    [/(^|-)(name|full-name|first-name)s?($|-)/, "Jordan Lee"],
    [/(^|-)(email)s?($|-)/, "jordan.lee@example.edu"],
    [/(^|-)(salary|income|target-pay|compensation)s?($|-)/, "$65,000"],
    [/(^|-)(cost|budget|expense|rent)s?($|-)/, "$2,400/month"],
    [/(^|-)(dream-job|target-role|role|job-title|occupation)s?($|-)/, "Product Manager"],
    [/(^|-)(goal|objective|aspiration)s?($|-)/, "Become a product manager within 18 months"],
    [/(^|-)(strength)s?($|-)/, "Strategic; Empathetic; Analytical"],
    [/(^|-)(value)s?($|-)/, "Growth; Integrity; Impact"],
    [/(^|-)(inspiration|motivation|interest)s?($|-)/, "Building things that help people"],
    [/(^|-)(personality|profile)s?($|-)/, "Analytical, people-oriented, driven"],
    [/(^|-)(school|college|university)s?($|-)/, "State University"],
    [/(^|-)(year|grad|class-of)s?($|-)/, "Junior"],
    [/(^|-)(mentor)s?($|-)/, "Alex Rivera, Director of Product"],
  ];
  for (const [re, v] of kw) if (re.test(s)) return v;
  switch (fieldType) {
    case "number": return "42";
    // Runtime stores multi-selects as a comma-joined string. The real field-type
    // strings are "multi-select" / "image-multiselect" (aliases kept tolerant).
    case "multi-select":
    case "image-multiselect":
    case "multiselect":
    case "multipleSelect": return "<option A>, <option B>";
    case "email": return "jordan.lee@example.edu";
    default: return `<sample ${slug || "value"}>`;
  }
}

/**
 * The profile fields a track produces (stored in the runtime profile), in order:
 *  - collect responses (member-entered)
 *  - generate outputs (validator treats these as downstream data)
 *  - an assessment-results substep with an explicit slug (computed profile)
 * Slug auto-derived from title when omitted (collect/generate); assessment-
 * results only when an explicit slug is set (the runtime gates on sub.slug).
 * Returns [{ slug, fieldType, source_type }].
 */
export function extractProfileFields(track) {
  const out = [];
  for (const step of track.steps || []) {
    for (const sub of step.substeps || []) {
      if (sub.type === "collect" || sub.type === "generate") {
        const slug = sub.slug || slugify(sub.title || "");
        if (slug) out.push({ slug, fieldType: sub.fieldType || "text",
          source_type: sub.type === "collect" ? "collected" : "generated" });
      } else if (sub.fieldType === "assessment-results" && sub.slug) {
        out.push({ slug: sub.slug, fieldType: "assessment-results", source_type: "computed" });
      }
    }
  }
  return out;
}

/**
 * Build a synthetic prerequisite profile from prerequisite tracks (in order).
 * Returns { slug: { value, from } } where `from` is the prerequisite track's
 * title — for the demo's "prompt context note" origin labels. Later tracks
 * override earlier ones on slug collision (last wins), matching accumulation.
 */
export function buildPrereqProfile(prereqTracks) {
  const profile = {};
  for (const track of prereqTracks) {
    const title = track.title || track.id || "prerequisite";
    for (const f of extractProfileFields(track)) {
      profile[f.slug] = { value: synthValue(f.slug, f.fieldType), from: title };
    }
  }
  return profile;
}
