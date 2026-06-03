// Pure state helpers for the prototype player. No DOM, no globals — node-testable.
export function flattenSubsteps(track) {
  const out = [];
  for (const step of track.steps || []) for (const sub of step.substeps || []) out.push(sub);
  return out;
}
export function nextIndex(i, n) { return Math.min(i + 1, n - 1); }
export function prevIndex(i, n) { return Math.max(i - 1, 0); }
export function clampIndex(i, n) { return Math.max(0, Math.min(i, n - 1)); }
export function progressPct(i, n) { return n <= 1 ? 100 : Math.round((i / (n - 1)) * 100); }
