// The canonical content hash — MUST stay byte-identical to track-studio's
// lib/versions.ts (canonicalize → sha256 → first 12 hex). This is the join
// key across the whole system: TrackVersions.content_hash =
// ScoreRuns.content_hash = Tracks.current_version = PostHogActuals.
// live_track_version. Prefer getting the hash FROM the Studio MCP
// `save_draft` verb (it saves AND returns this hash); this script is the
// offline fallback:  node content-hash.mjs <track.json>
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

export function canonicalize(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([k, v]) => `${JSON.stringify(k)}:${canonicalize(v)}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value);
}

export function contentHash(trackJson) {
  return createHash("sha256").update(canonicalize(trackJson)).digest("hex").slice(0, 12);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const file = process.argv[2];
  if (!file) { console.error("Usage: node content-hash.mjs <track.json>"); process.exit(2); }
  const raw = JSON.parse(readFileSync(file, "utf8"));
  console.log(contentHash(Array.isArray(raw) ? raw[0] : raw));
}
