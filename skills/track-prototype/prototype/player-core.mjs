// Pure state helpers for the prototype player. No DOM, no globals — node-testable.
export function flattenSubsteps(track) {
  const out = [];
  for (const step of track.steps || []) for (const sub of step.substeps || []) out.push(sub);
  return out;
}
// n <= 0 (a version with no substeps — e.g. a fresh /new-track starter draft)
// must yield 0, never -1: `advance()` assigns state.i = nextIndex(...), and a
// negative index makes render() paint screens[-1] — the literal string
// "undefined". (clampIndex's old form already returned 0 for n <= 0 via the
// outer Math.max — the guard there is for explicitness; nextIndex was the
// actual -1 producer.)
export function nextIndex(i, n) { return n <= 0 ? 0 : Math.min(i + 1, n - 1); }
export function prevIndex(i, n) { return Math.max(i - 1, 0); }
export function clampIndex(i, n) { return n <= 0 ? 0 : Math.max(0, Math.min(i, n - 1)); }
export function progressPct(i, n) { return n <= 1 ? 100 : Math.round((i / (n - 1)) * 100); }
