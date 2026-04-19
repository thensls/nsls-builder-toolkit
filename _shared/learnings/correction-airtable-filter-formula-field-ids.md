---
type: correction
tags: [airtable, api, filter-formulas, scoped-tokens, silent-failures]
confidence: high
created: 2026-04-19
source: "Accumulated from multiple Airtable automation builds — documented in personal memory 2026-Q1"
---

# `filterByFormula` uses field names, not field IDs

Airtable's `filterByFormula` parameter silently returns **zero results** when you use field IDs like `{fldJleDMJFfcj5gPN}` instead of field names like `{status}`. No error, no warning — just an empty response that looks like the data doesn't match.

## Context

While building people-ops bots and automation queries, field IDs are the stable reference (names can be renamed in the UI). Natural instinct: use field IDs everywhere for resilience. But `filterByFormula` breaks that — it wants display names.

## Implication

When writing any Airtable query that uses `filterByFormula`:

1. **Default to field names.** `filterByFormula=AND({status}='Active',{owner}='Kevin')` — this works.
2. **If you need field IDs for stability,** add `returnFieldsByFieldId=true` to the request. That flag makes field IDs work inside formulas.
3. **Field IDs still work fine** in `fields[]` query params and record payloads. The limitation is specific to `filterByFormula`.
4. **When a filter returns 0 results and you expected matches,** check this first. Zero-result-with-no-error is the signature failure mode.

## Related gotchas

Several other Airtable API quirks live in the same neighborhood — fetch schemas, field-ID vs name handling, scoped-token limits, `fields[]` on single-record GET. See `MEMORY.md` in your Claude Code memory or the `/airtable` skill's references for the full list.
