export function aggregateSubcheck(verdicts) {
  const met = verdicts.filter((v) => v === "MET").length;
  const frac = met / verdicts.length;
  if (frac >= 0.66) return "MET";
  if (frac <= 0.34) return "UNMET";
  return "CONTESTED";
}

const SUBCHECKS = ["a", "b", "c", "d"];

export function buildScorecard(samples, dims) {
  const dimensions = {};
  const shipBar = [];     // UNMET sub-checks -> recommendations
  const contested = [];   // CONTESTED -> human review
  let total = 0;
  for (const d of dims) {
    let met = 0;
    const checks = {};
    for (const k of SUBCHECKS) {
      const verdict = aggregateSubcheck(samples[`${d}.${k}`] || []);
      checks[k] = verdict;
      if (verdict === "MET") { met++; total++; }
      else if (verdict === "UNMET") shipBar.push({ dim: d, key: k });
      else contested.push({ dim: d, key: k });
    }
    dimensions[d] = { met, checks };
  }
  return { dimensions, total, composite: `${total}/${dims.length * 4}`, shipBar, contested };
}
