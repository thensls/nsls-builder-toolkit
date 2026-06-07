export const HEADER =
  "| Version | Date | Total | D1 Value | D2 Pacing | D3 Copy | D4 Fit | Doc |\n" +
  "|---------|------|-------|----------|-----------|---------|--------|-----|";

export function renderRow({ version, date, scorecard, docUrl }) {
  const d = scorecard.dimensions;
  const link = docUrl ? `[doc](${docUrl})` : "";
  // buildScorecard always sets composite; fall back to total/16 so the ledger never
  // renders "undefined" if a caller passes a scorecard without it.
  const total = scorecard.composite || (Number.isInteger(scorecard.total) ? `${scorecard.total}/16` : "—");
  return `| ${version} | ${date} | ${total} | ${d.value.met}/4 | ${d.pacing.met}/4 | ${d.copy.met}/4 | ${d.fit.met}/4 | ${link} |`;
}

export function appendRow(existing, row) {
  const base = existing && existing.includes("| Version |") ? existing.trimEnd() : HEADER;
  return base + "\n" + row + "\n";
}
