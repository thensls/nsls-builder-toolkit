// Compare predicted focus-group scores to real PostHog outcomes: pull ScoreRuns +
// PostHogActuals from the "Track Previews" base, join by (slug, content_hash↔
// live_track_version), and report rank correlation (Spearman/Kendall) of checks-met.
// Reads AIRTABLE_API_KEY + AIRTABLE_BASE_ID from env.
//
// PRIMARY TARGET = per-step continuation (length-normalized retention), NOT raw
// completion. The n=3 seed showed raw completion anti-correlates with the rubric because
// it's dominated by track length, position, and commitment — a short mandatory intake
// form tops completion while scoring lowest on experience quality. Per-step continuation
// is what the rubric's "predicts" column was designed for (step-to-step continuation +
// next-track uptake). Raw completion is still reported, as a CONTRAST, under `vsCompletion`.
//
// This is a RANKING sanity check, not a calibrated prediction: synthetic personas
// overstate adoption, and a meaningful coefficient needs ~15-30+ paired tracks. With a
// handful it only answers "does the rubric rank the more-retentive track higher?".
import { spearman, kendallTau, joinByVersion } from "./lib/calibration.mjs";

// Pure: given Airtable-shaped ScoreRuns + PostHogActuals rows, produce the joined pairs
// and the coefficients. Testable without the network.
export function summarize(scoreRuns, actuals) {
  const runs = scoreRuns.map((r) => ({ slug: r.track, content_hash: r.content_hash, total: r.checks_met }));
  const acts = actuals.map((a) => ({ slug: a.track, live_track_version: a.live_track_version, completion_rate: a.completion_rate, step_to_step_continuation: a.step_to_step_continuation }));
  const pairs = joinByVersion(runs, acts);
  const n = pairs.length;
  const baseNote = n < 15 ? "DIRECTIONAL ONLY — n<15; not a reliable coefficient" : "interpret with care; synthetic personas overstate adoption";
  if (n < 2) return { n, pairs, primaryMetric: "step_to_step_continuation", spearman: null, kendall: null, note: "need >=2 paired tracks to correlate" };
  const predicted = pairs.map((p) => p.predicted);
  const haveCont = pairs.every((p) => typeof p.continuation === "number");
  const cont = pairs.map((p) => p.continuation);
  const comp = pairs.map((p) => p.completion);
  const result = {
    n, pairs,
    primaryMetric: "step_to_step_continuation",
    spearman: haveCont ? spearman(predicted, cont) : null,
    kendall: haveCont ? kendallTau(predicted, cont) : null,
    vsCompletion: {
      spearman: spearman(predicted, comp),
      kendall: kendallTau(predicted, comp),
      note: "raw completion is length/position/commitment-confounded — reported for contrast, NOT the calibration target",
    },
    note: (haveCont ? "" : "step_to_step_continuation missing on some PostHogActuals rows — populate it; primary coefficient is null until then. ") + baseNote,
  };
  return result;
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
