---
type: correction
tags: [airtable, api, filter-formulas, scoped-tokens, silent-failures, metadata-api]
confidence: high
created: 2026-04-19
updated: 2026-04-19
source: "Accumulated from multiple Airtable automation builds — documented in personal memory 2026-Q1. 2026-04-19: corrected to remove incorrect claim that returnFieldsByFieldId=true enables field IDs inside filterByFormula (flagged by Macroscope on PR #18)."
---

# `filterByFormula` uses field names, not field IDs

Airtable's `filterByFormula` parameter silently returns **zero results** when you use field IDs like `{fldJleDMJFfcj5gPN}` instead of field names like `{status}`. No error, no warning — just an empty response that looks like the data doesn't match.

## Context

While building people-ops bots and automation queries, field IDs are the stable reference (names can be renamed in the UI). Natural instinct: use field IDs everywhere for resilience. But `filterByFormula` breaks that — it wants display names.

## Implication

When writing any Airtable query that uses `filterByFormula`:

1. **Default to field names.** `filterByFormula=AND({status}='Active',{owner}='Kevin')` — this works.
2. **There is no API flag that lets field IDs work inside `filterByFormula`.** `returnFieldsByFieldId=true` only changes the **response** key format (records come back keyed by field ID instead of name). It does not affect how the formula parser reads `{…}` references. If you need stability against field renames, fetch the current field-ID → name mapping via the Metadata API (`GET /v0/meta/bases/{baseId}/tables`) and substitute names into the formula at query time.
3. **Field IDs still work fine** in `fields[]` query params and record payloads. The limitation is specific to `filterByFormula`.
4. **When a filter returns 0 results and you expected matches,** check this first. Zero-result-with-no-error is the signature failure mode.

## Related gotchas

Several other Airtable API quirks live in the same neighborhood — fetch schemas, field-ID vs name handling, scoped-token limits, `fields[]` on single-record GET. See `MEMORY.md` in your Claude Code memory or the `/airtable` skill's references for the full list.
