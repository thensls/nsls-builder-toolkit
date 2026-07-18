# Self-serve research — the five dimensions

Used by `bet-research` Step R2. Five things a bet needs answered before it
can honestly claim readiness for the planned gate. All five are answerable
in-house, wherever NSLS's own data can carry the weight — work them in the
order the assumption agenda demands (riskiest first), not the order below.

## 1. Competition

Web research on alternatives, **including the status quo** — "keep doing the
workaround" is a real competitor and usually the toughest one. For each
alternative, capture: who it serves, pricing if public, why a buyer picks it,
why they'd leave it.

Write findings to `market.alternatives`:
- `evidence_tag: "estimate"` by default.
- `evidence_tag: "data"` only for verifiable facts with sources cited
  directly in the content — a pricing page URL, a review quote, a filed
  document. Don't upgrade the tag just because the finding feels solid.

Log each substantive finding as its own evidence row:
```
log_evidence(kind: "competitor", link: <source URL>, evidence_tag: "data"|"estimate")
```

## 2. Market size, both directions

**Top-down:** `size_segment(filter)`, built from the bet's segment, returns
`institutionCount`, `totalEnrollment`, `relationshipCounts`. This is the
outside-in number.

**Bottom-up:** composed by this skill — **never by the engine.**

```
bottom_up = reachable_institutions × expected_conversion × annual_price
```

Every factor is a NAMED assumption. Each one that's load-bearing also lands
in `strategy_assumptions` — a bottom-up estimate resting on an unrecorded
conversion-rate guess is a leap of faith wearing a spreadsheet.

Write the result:
```
update_section("market.obtainable",
  content_md: <narrative with named assumptions>,
  data: { top_down: <number>, bottom_up: <number>, divergence_note: "<why they differ>" },
  evidence_tag: "estimate")
```

The gate checks `typeof data.top_down === "number" && typeof data.bottom_up
=== "number"` — both fields must literally be numbers, not strings, not
ranges.

**Divergence flag:** if the two directions differ by more than roughly 3×,
say so out loud and name which single assumption is driving the gap (usually
`expected_conversion` or the reachable-institutions count). A silent 5×
divergence buried in prose is a red flag, not a nuance.

Log the sizing pull itself:
```
log_evidence(kind: "market_query", data: { filter, result }, evidence_tag: "data")
```

## 3. Our reach inside the market

`size_segment` gives the relationship rollup; `target_shortlist(filter,
buyer_title_buckets: <buyer's title_taxonomy_keys>, limit)` turns it into a
ranked outreach list — relationship counts, stakeholder coverage against the
bet's buyer title, member counts.

Write to `market.current_data` with `evidence_tag: "data"` — this IS our own
data, not an estimate.

Offer `save_targets` with per-entity reasons, **confirming with the owner
first** — it names real schools onto a rep-visible list, shared-systems
tier. For warm B2B bets, the saved shortlist doubles as the roadshow/rep call
list feeding Step R3 and R4.

## 4. Time to revenue

Months to first dollar, estimated with named assumptions: sales cycle length
for this buyer, procurement reality (RFP? single signature? committee?),
pilot-to-paid lag. Lands in `econ.revenue_drivers` content and feeds the
`time_to_revenue` rubric note directly — cite the same named assumptions in
both places rather than re-deriving the number twice.

## 5. Build-to-value risk

What has to exist before the value is even provable — in weeks and dollars.
Lands in `econ.cost_structure` content and the `build_to_value_risk` rubric
note. For internal-origin bets this is usually already low — say so plainly
and cite the internal system that already proves it works, rather than
re-estimating from zero.

## The `econ.*` first-draft rule

`bet-research` drafts **all five** `econ.*` fields to honest-estimate
completeness — `revenue_drivers`, `cost_structure`, `unit_economics`,
`model_2026_2028`, `cases` (the last two as clearly-labeled first-cut
estimates) — because the research→planned gate requires the econ page
non-empty. `bet-plan` hardens these into the full named-assumption model
later; this skill's job is an honest first draft, not a placeholder.

**Never leave an econ field empty "for bet-plan."** The gate checks for
non-empty `content_md` on all 5 `econ.*` keys — an empty field blocks the
gate regardless of intent to fill it later.

## `market.interviews` and `market.evidence_level`

- `market.interviews` — the rolling synthesis of Customer Forces Stories,
  updated after each logged conversation (Step R3). Not a re-paste of every
  story; a running synthesis of what they add up to.
- `market.evidence_level` — one honest paragraph on where the evidence
  stands, written in evidence-tag language: what's `data`, what's still
  `assumption` or `estimate`, and what would need to change to move a claim
  up a tag.
