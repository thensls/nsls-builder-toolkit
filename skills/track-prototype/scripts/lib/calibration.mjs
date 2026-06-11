// Rank correlation for predicted-score vs actual-outcome calibration.
// Uses AVERAGE ranks for ties (standard Spearman) — important here because checks-met
// totals are integers 0..16 and tie often; sequential ranks would manufacture spurious
// correlation (a constant series would rank 1,2,3 and look perfectly correlated).
function rank(xs) {
  const idx = xs.map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]);
  const r = Array(xs.length);
  let i = 0;
  while (i < idx.length) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;   // span of equal values
    const avg = (i + j) / 2 + 1;                                      // mean of ranks (i+1..j+1)
    for (let k = i; k <= j; k++) r[idx[k][1]] = avg;
    i = j + 1;
  }
  return r;
}
function pearson(a, b) {
  const n = a.length, ma = a.reduce((s, v) => s + v, 0) / n, mb = b.reduce((s, v) => s + v, 0) / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) { const x = a[i] - ma, y = b[i] - mb; num += x * y; da += x * x; db += y * y; }
  return da && db ? num / Math.sqrt(da * db) : 0;
}
export const spearman = (a, b) => pearson(rank(a), rank(b));
export function kendallTau(a, b) {
  let c = 0, d = 0;
  for (let i = 0; i < a.length; i++) for (let j = i + 1; j < a.length; j++) {
    const s = Math.sign(a[i] - a[j]) * Math.sign(b[i] - b[j]);
    if (s > 0) c++; else if (s < 0) d++;
  }
  return c + d ? (c - d) / (c + d) : 0;
}
// joinByVersion: match a ScoreRun to its PostHog actuals by (slug + the version the score
// was computed against). Drops runs with no matching actuals so calibration only compares
// a prediction to the version it actually scored.
export function joinByVersion(runs, actuals) {
  return runs.map((r) => {
    const m = actuals.find((x) => x.slug === r.slug && x.live_track_version === r.content_hash);
    return m ? {
      slug: r.slug, version: r.content_hash, predicted: r.total,
      // continuation = length-normalized per-step retention (the rubric's intended target);
      // completion = raw end-to-end rate (length/position-confounded — kept for contrast).
      continuation: m.step_to_step_continuation ?? null,
      completion: m.completion_rate ?? null,
      actual: m.completion_rate, // back-compat alias
    } : null;
  }).filter(Boolean);
}
