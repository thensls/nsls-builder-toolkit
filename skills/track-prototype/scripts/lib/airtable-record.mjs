// Build the Airtable "ScoreRuns" record payload. Keys are field NAMES (per the NSLS
// Airtable gotcha: field-ID filterByFormula silently returns nothing; the CLI does
// name-based or Python-side filtering, never field-ID formulas). content_hash makes the
// row version-aware so calibration compares a score to the version it actually scored.
export function buildScoreRunFields({ trackSlug, version, contentHash, date, scorecard, gdocUrl, persona, buildUrl }) {
  const d = scorecard.dimensions;
  return {
    track: trackSlug, version, content_hash: contentHash, date,
    checks_met: scorecard.total, checks_total: 16,
    d1_value: `${d.value.met}/4`, d2_pacing: `${d.pacing.met}/4`,
    d3_copy: `${d.copy.met}/4`, d4_fit: `${d.fit.met}/4`,
    contested_count: scorecard.contested.length,
    gdoc_url: gdocUrl || "", persona_used: persona || "", build_url: buildUrl || "",
  };
}
