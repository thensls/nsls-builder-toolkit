// Compare predicted focus-group scores to real PostHog outcomes: pull ScoreRuns +
// PostHogActuals from the "Track Previews" base, join by (slug, content_hash↔
// live_track_version), and report rank correlation (Spearman/Kendall) of checks-met
// vs completion-rate. Reads AIRTABLE_API_KEY + AIRTABLE_BASE_ID from env.
//
// This is a RANKING sanity check, not a calibrated prediction: synthetic personas
// overstate adoption, and a meaningful coefficient needs ~15-30+ paired tracks. With a
// handful it only answers "does the rubric rank the better-performing track higher?".
import { spearman, kendallTau, joinByVersion } from "./lib/calibration.mjs";

// Pure: given Airtable-shaped ScoreRuns + PostHogActuals rows, produce the joined pairs
// and the coefficients. Testable without the network.
export function summarize(scoreRuns, actuals) {
  const runs = scoreRuns.map((r) => ({ slug: r.track, content_hash: r.content_hash, total: r.checks_met }));
  const acts = actuals.map((a) => ({ slug: a.track, live_track_version: a.live_track_version, completion_rate: a.completion_rate }));
  const pairs = joinByVersion(runs, acts);
  const n = pairs.length;
  if (n < 2) return { n, pairs, spearman: null, kendall: null, note: "need >=2 paired tracks to correlate" };
  const predicted = pairs.map((p) => p.predicted);
  const actual = pairs.map((p) => p.actual);
  return {
    n, pairs,
    spearman: spearman(predicted, actual),
    kendall: kendallTau(predicted, actual),
    note: n < 15 ? "DIRECTIONAL ONLY — n<15; not a reliable coefficient" : "interpret with care; synthetic personas overstate adoption",
  };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const apiKey = process.env.AIRTABLE_API_KEY, baseId = process.env.AIRTABLE_BASE_ID;
  if (!apiKey || !baseId) { console.error("Usage: AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=… node calibrate.mjs"); process.exit(2); }
  const list = async (table) => {
    const out = [];
    let offset;
    do {
      const u = new URL(`https://api.airtable.com/v0/${baseId}/${table}`);
      if (offset) u.searchParams.set("offset", offset);
      const res = await fetch(u, { headers: { Authorization: `Bearer ${apiKey}` } });
      if (!res.ok) throw new Error(`Airtable ${res.status}: ${await res.text()}`);
      const j = await res.json();
      for (const rec of j.records) out.push(rec.fields);
      offset = j.offset;
    } while (offset);
    return out;
  };
  const [runs, actuals] = await Promise.all([list("ScoreRuns"), list("PostHogActuals")]);
  const s = summarize(runs, actuals);
  console.log(JSON.stringify(s, null, 2));
}
