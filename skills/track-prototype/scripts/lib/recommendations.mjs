export function buildRecommendations(scorecard, rationales = {}) {
  const out = [];
  const push = (dim, key, severity) => {
    const r = rationales[`${dim}.${key}`] || {};
    out.push({ id: `${dim}-${key}-${severity}`, dimension: dim, sub_check: key, severity,
      substep: r.substep || null, rationale: r.rationale || "", change: r.change || "" });
  };
  for (const { dim, key } of scorecard.shipBar) push(dim, key, "fix");
  for (const { dim, key } of scorecard.contested) push(dim, key, "review");
  return out;
}
