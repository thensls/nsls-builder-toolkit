// Write a focus-group ScoreRun to the Airtable "Track Previews" base, and (optionally)
// append the local scores.md mirror. Field names come from airtable-record.mjs (the
// base's columns match exactly). Reads AIRTABLE_API_KEY + AIRTABLE_BASE_ID from env, so
// no secret is hardcoded. The base id is appzDWu6GowvnACtv (Track Previews).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { buildScoreRunFields } from "./lib/airtable-record.mjs";
import { renderRow, appendRow } from "./lib/scores-ledger.mjs";

// POST one ScoreRun. fetchImpl is injectable for testing. Throws on a non-2xx so the
// caller can surface the real Airtable error (don't swallow ledger failures).
export async function postScoreRun({ apiKey, baseId, fields, fetchImpl = fetch }) {
  const res = await fetchImpl(`https://api.airtable.com/v0/${baseId}/ScoreRuns`, {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) throw new Error(`Airtable ${res.status}: ${await res.text()}`);
  return (await res.json()).id;
}

// Append a row to the local scores.md mirror (created with a header on first write).
export function updateScoresMd(path, run) {
  const existing = existsSync(path) ? readFileSync(path, "utf8") : "";
  const row = renderRow({ version: run.version, date: run.date, scorecard: run.scorecard, docUrl: run.gdocUrl });
  writeFileSync(path, appendRow(existing, row));
}

// CLI: node ledger-write.mjs <run.json>
// run.json = { trackSlug, version, contentHash, date, scorecard, gdocUrl?, persona?, buildUrl?, scoresMdPath? }
if (import.meta.url === `file://${process.argv[1]}`) {
  const runPath = process.argv[2];
  const apiKey = process.env.AIRTABLE_API_KEY;
  const baseId = process.env.AIRTABLE_BASE_ID;
  if (!runPath || !apiKey || !baseId) {
    console.error("Usage: AIRTABLE_API_KEY=… AIRTABLE_BASE_ID=… node ledger-write.mjs <run.json>");
    process.exit(2);
  }
  const run = JSON.parse(readFileSync(runPath, "utf8"));
  const id = await postScoreRun({ apiKey, baseId, fields: buildScoreRunFields(run) });
  console.log("ScoreRun:", id);
  if (run.scoresMdPath) { updateScoresMd(run.scoresMdPath, run); console.log("scores.md updated:", run.scoresMdPath); }
}
