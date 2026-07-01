#!/usr/bin/env node
/**
 * list_studio_tracks.mjs — list Track Studio tracks grouped by lifecycle stage.
 *
 * Reads the Studio's Airtable base (the same data the studio.nsls.org dashboard
 * uses) and prints tracks under Backlog / In Development / Live / Optimization,
 * so the track-studio router can show "here's what's in the studio" and let the
 * builder pick one.
 *
 * Usage:  AIRTABLE_API_KEY=pat... node list_studio_tracks.mjs [--json]
 *   --json  emit structured JSON instead of the readable grouping.
 *
 * Token: set AIRTABLE_API_KEY (a PAT with data.records:read + schema.bases:read
 * on this base). If tools/keys aren't available, run /connect or /airtable.
 */
const BASE = "appzDWu6GowvnACtv"; // Track Studio ("Track Previews")
const TABLE = "Tracks";
const STAGE_ORDER = ["backlog", "in-development", "live", "optimization"];
const STAGE_LABEL = {
  backlog: "Backlog", "in-development": "In Development",
  live: "Live", optimization: "Optimization",
};

async function main() {
  const key = process.env.AIRTABLE_API_KEY;
  if (!key) {
    console.error("Set AIRTABLE_API_KEY (PAT with read on base " + BASE + "). See /connect or /airtable.");
    process.exit(1);
  }
  const fields = ["slug", "title", "stage", "owner", "audience", "is_live",
    "brief_doc_url", "outcomes_doc_url"];
  const params = new URLSearchParams();
  params.set("pageSize", "100");
  for (const f of fields) params.append("fields[]", f);

  const rows = [];
  let offset;
  do {
    if (offset) params.set("offset", offset);
    const res = await fetch(`https://api.airtable.com/v0/${BASE}/${TABLE}?${params}`, {
      headers: { Authorization: `Bearer ${key}` },
    });
    if (!res.ok) {
      console.error(`Airtable ${res.status}: ${(await res.text()).slice(0, 300)}`);
      process.exit(1);
    }
    const json = await res.json();
    for (const r of json.records) rows.push(r.fields);
    offset = json.offset;
  } while (offset);

  // Derive stage the same way the model does: explicit stage wins, else is_live.
  const deriveStage = (f) => {
    const s = (f.stage || "").trim().toLowerCase();
    if (STAGE_ORDER.includes(s)) return s;
    return f.is_live ? "live" : "in-development";
  };
  const groups = Object.fromEntries(STAGE_ORDER.map((s) => [s, []]));
  for (const f of rows) if ((f.slug || "").trim()) groups[deriveStage(f)].push(f);

  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(groups, null, 2));
    return;
  }
  for (const s of STAGE_ORDER) {
    const list = groups[s];
    console.log(`\n${STAGE_LABEL[s]} (${list.length})`);
    for (const t of list) {
      const owner = t.owner ? ` · ${t.owner}` : " · unowned";
      console.log(`  - ${t.title || t.slug} [${t.slug}]${owner}`);
    }
  }
}

main();
