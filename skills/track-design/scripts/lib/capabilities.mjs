// Loads the ignite-next capability manifest (track-capabilities.json), vendored
// into this skill's data/ directory. NEVER throws and never blocks authoring: a
// missing, malformed or stale manifest degrades to null plus a warning, and the
// caller falls back to its previous behaviour.
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEFAULT_PATH = join(HERE, "..", "..", "data", "track-capabilities.json");
const DAY_MS = 86_400_000;

export function loadCapabilities({ path = DEFAULT_PATH, maxAgeDays = 30, now = Date.now() } = {}) {
  const warnings = [];
  if (!existsSync(path)) {
    warnings.push(
      `capability manifest not found at ${path} — field-type checks fall back to the built-in list. ` +
        `Refresh it with track-studio's scripts/sync-capabilities.mjs.`,
    );
    return { manifest: null, warnings };
  }
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(path, "utf8"));
  } catch (err) {
    warnings.push(`capability manifest at ${path} could not be read: ${err.message}`);
    return { manifest: null, warnings };
  }
  if (!parsed?.fieldTypes?.declared || !parsed?.fieldTypes?.rendered) {
    warnings.push(`capability manifest at ${path} is missing fieldTypes.declared/rendered`);
    return { manifest: null, warnings };
  }
  const age = now - Date.parse(parsed.generatedAt ?? "");
  if (Number.isFinite(age) && age > maxAgeDays * DAY_MS) {
    warnings.push(
      `capability manifest is stale (generated ${String(parsed.generatedAt).slice(0, 10)}) — ` +
        `it may not reflect what ignite-next supports today.`,
    );
  }
  return { manifest: parsed, warnings };
}
