# Data-source pull recipes

**Verification status (be honest with squads):**

| Source type | Status |
|---|---|
| `google_sheet` (gws) | ✅ Verified end-to-end (Shop squad, 2026-06) |
| `posthog` | ✅ Verified (enrollment) |
| `hubspot` | 📄 Documented, not yet run end-to-end here |
| `hex` (Slack bridge) | ⚠️ Documented; slow/flaky — prefer a mirroring source |
| `slack` | ✅ Verified for reads |
| `manual` / export-to-Sheet | ✅ Always works (squad provides the value) |

Expect rough edges on the first run of any 📄/⚠️ source. Fall back to export-to-Sheet or `manual`
rather than publishing an uncertain number.


Each `source` in `config.json` has a `type`. Here's how to pull each reliably, plus the
confirm step. **Always show pulled numbers to the squad and get confirmation before they go
live** (the pull-and-confirm gate). On any failure, **fail loud and keep the last confirmed
value** — never fabricate or interpolate.

## `google_sheet` (via the `gws` CLI — preferred for Google URLs)

```bash
GWS=~/.local/bin/gws; SID="<spreadsheet id>"
# Discover tabs:
$GWS sheets spreadsheets get --params "{\"spreadsheetId\":\"$SID\"}" --format json
# Read a range:
$GWS sheets +read --spreadsheet "$SID" --range "Tab Name!A1:L40" --format json
```
**Gotcha:** gws prints `Using keyring backend: keyring` to stdout before the JSON. Slice from
the first `{` before `JSON.parse`. Ranges are exact — if a number looks wrong/zero, the tab was
re-laid-out or renamed; re-read the structure and fix the `range` in config.

## `posthog` (via the PostHog MCP `exec`)

Experiment data: `experiment-get` (metric defs, uuids, variant_screenshot_media_ids) +
`experiment-results-get` (per-arm number_of_samples, step_counts, sum, denominator_sum,
total_exposures). See `/posthog` and `/enrollment-experiment-cleanup` Step 9b for the
extraction recipe and known result-shape gotchas. For ad-hoc metrics, HogQL via `execute-sql`.

## `hubspot` (via the HubSpot MCP)

`search_crm_objects` / `query_crm_data` for campaign + email metrics. See `/hubspot`. Note the
NSLS attribution gotchas (page_variant null-carrying, exposure vs pageview funnels) before
trusting a derived rate.

## `hex` (Hex MCP is blocked in this environment)

Query Andrew's / a squad's Hex dashboard via the **Hex Slack bridge** (DM channel
`D0B0S3DSV3N` — poll the thread for the answer, ~30s–5min). Slow. **Prefer a source that
mirrors the data** (e.g. the same email stats logged in a Google Sheet) and treat Hex as a
cross-check. Declare this precedence in the source `note`.

## `slack` (via the Slack MCP)

For human narrative inputs (e.g. an "EXPERIMENT ENDED:" post). Read the destination channel
and the verbatim text; don't summarize a squad's words into the narrative — that field is human.

## `manual`

The squad provides the value directly. Store it under `metrics` with `"source": "manual"` and
`confirmed: true` once they give it. Use for anything not reachable by tool.

## Confirm + store shape (content.json)

```json
"metrics": {
  "revenue_ytd": { "value": "$777,126", "goal": "$1,300,000", "pct_goal": "59.8%",
    "yoy25": "+9.8%", "confirmed": true, "source": "shop_tracker / Weekly Squad Reporting",
    "pulled_at": "2026-06-12" }
}
```
Refresh updates only `metrics`. `human` fields (narratives, statuses, judgment classifications)
are written only via the edit flow.
