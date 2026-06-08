// Pure, DOM-free helpers for the gallery walker (walk-gallery.mjs).
//
// Two responsibilities, both testable without a browser:
//   1. planFill(descriptor, answer) — decide WHAT to do on a collect screen,
//      given a screen descriptor read from the DOM and the persona answer.
//      Returns an action plan the Playwright glue executes. No clicking here.
//   2. isStreamStable(lengths, window) — given a rolling sequence of output text
//      LENGTHS sampled over time, decide whether a live AI stream has stopped
//      growing (so the walker can screenshot + advance).
//
// Keeping these pure means the fragile fieldType/option-matching and
// stream-settling logic is unit-tested, and walk-gallery.mjs stays thin glue.

// Field types whose collect screen renders an options GRID ([data-option]).
const OPTION_FIELD_TYPES = new Set([
  "select",
  "multi-select",
  "image-multiselect",
  "dropdown-with-checkboxes",
]);
// Of those, the ones that accept multiple picks.
const MULTI_FIELD_TYPES = new Set([
  "multi-select",
  "image-multiselect",
  "dropdown-with-checkboxes",
]);

// Normalise a persona answer to an array of option-value strings (for grids).
function toValues(answer) {
  if (Array.isArray(answer)) return answer.map((v) => String(v));
  if (answer == null) return [];
  return [String(answer)];
}

// planFill — decide the action for one collect screen.
//
// descriptor: {
//   slug,                // current substep slug (from [data-input]/grid data-slug)
//   fieldType,           // e.g. "text", "currency", "image-multiselect"
//   hasInput,            // a [data-input] is present on the screen
//   optionValues,        // array of data-value strings rendered in the grid
// }
// answer: the persona answer for this slug (string | string[] | undefined)
//
// Returns one of:
//   { action: "fill",   value }                         // type into [data-input]
//   { action: "click-options", values: [...] }          // click matching [data-option]s
//   { action: "none" }                                  // nothing to fill (banner-like / empty grid)
// plus { problem } (a non-fatal note string) when the answer can't be satisfied,
// so the caller can record it and fall back gracefully.
export function planFill(descriptor, answer) {
  const d = descriptor || {};
  const ft = d.fieldType;

  const isOptionGrid = OPTION_FIELD_TYPES.has(ft) || (Array.isArray(d.optionValues) && d.optionValues.length > 0 && !d.hasInput);

  if (isOptionGrid) {
    const available = Array.isArray(d.optionValues) ? d.optionValues : [];
    const wanted = toValues(answer);
    // Exact data-value matches only — do NOT split on commas (option texts may
    // contain commas, e.g. "Aim for more abstract, exciting possibilities").
    const availableSet = new Set(available);
    const matched = wanted.filter((v) => availableSet.has(v));
    const isMulti = MULTI_FIELD_TYPES.has(ft);

    if (available.length === 0) {
      // Grid rendered with no clickable options (e.g. a dropdown-with-checkboxes
      // whose options weren't rendered). Nothing to click — screen still advances
      // via Continue. Flag as a note, not a hard failure.
      return { action: "none", problem: `slug "${d.slug}" (${ft}): option grid is empty, nothing to select` };
    }

    if (answer === undefined || answer === null) {
      // No persona answer — fall back to selecting the first option (old behavior)
      // so the screen can advance, and flag it. The early-return above guarantees
      // available[0] is defined.
      return {
        action: "click-options",
        values: [available[0]],
        problem: `slug "${d.slug}" (${ft}): no persona answer, selected first option as fallback`,
      };
    }

    if (matched.length === 0) {
      // Answer present but none matched a real option — flag and fall back to first.
      return {
        action: "click-options",
        values: [available[0]],
        problem: `slug "${d.slug}" (${ft}): answer ${JSON.stringify(answer)} matched no option, selected first as fallback`,
      };
    }

    // multi-select: click every matched option. single-select: click the first match.
    const values = isMulti ? matched : [matched[0]];
    const out = { action: "click-options", values };
    if (matched.length < wanted.length) {
      out.problem = `slug "${d.slug}" (${ft}): ${wanted.length - matched.length} answer value(s) matched no option`;
    }
    return out;
  }

  // Free-text family (text / textarea / currency / default) — fill the input.
  if (d.hasInput) {
    if (answer === undefined || answer === null) {
      return { action: "fill", value: "Maya", problem: `slug "${d.slug}" (${ft}): no persona answer, filled generic fallback` };
    }
    // A composite/free-text slug answered with an array — join into one string.
    const value = Array.isArray(answer) ? answer.join(", ") : String(answer);
    return { action: "fill", value };
  }

  // No input and not an option grid → banner-like screen, nothing to fill.
  return { action: "none" };
}

// isStreamStable — given a sequence of sampled output-text lengths (oldest →
// newest) and a stability window N, return true when the last N samples are all
// equal AND non-trivial (we have at least N samples). A stream that has settled
// stops growing; once the tail is flat we treat it as complete.
//
// Returns false when there aren't yet N samples, or the tail is still growing.
export function isStreamStable(lengths, window = 3) {
  if (!Array.isArray(lengths)) return false;
  if (window < 2) window = 2;
  if (lengths.length < window) return false;
  const tail = lengths.slice(-window);
  const first = tail[0];
  return tail.every((n) => n === first);
}
