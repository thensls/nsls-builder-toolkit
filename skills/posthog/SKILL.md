---
name: posthog
description: >-
  Query PostHog analytics, build dashboards, create funnels, look up users,
  investigate errors, manage feature flags, and run HogQL queries. NSLS uses
  one PostHog project for all properties (FOL, Society, Shop, Marketing).
  Includes known gotchas: FunnelsQuery OR group limitation, server-side $host
  null, identity chain breaks, FOL error noise, UTC date math.
  Trigger phrases: posthog, analytics, dashboard, funnel, HogQL, insight,
  event, error tracking, feature flag, experiment, person lookup, user journey,
  who visited, how many users, conversion rate, drop-off, user behavior.
---

# PostHog Analytics

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (queries, lookups, listing) — runs without friction. No approval needed.
2. **Configuration** (creating dashboards, insights, feature flags) — ask permission, explain what will be created and where it will be visible.
3. **Destructive** (deleting insights, dashboards, experiments, feature flags) — never proactively offered. If explicitly requested: explain that deletion is permanent (no recycle bin for insights), confirm which specific item, confirm they understand it cannot be undone, then proceed.

## Purpose

This skill makes PostHog's full analytical power accessible through conversation — not just running queries, but knowing which queries to run, what the results mean in the NSLS context, and what to try next when the data doesn't look right. If PostHog tools aren't available, run `/connect` first. For cross-system intelligence that combines PostHog with Airtable, Slack, Customer.io, and more, use `/data-intel`.

## NSLS PostHog Landscape

One PostHog project (ID: 128379) covers all NSLS properties. If PostHog tools aren't available, run `/connect` to set up the connection.

| Domain | Product |
|--------|---------|
| `app.nsls.org` | FOL (legacy member platform) |
| `members.nsls.org` | Enrollment |
| `oursociety.org` | Society |
| `shop.nsls.org` | Shop |
| `www.nsls.org` | Marketing site |

**Always start by confirming the active project:**
```
mcp__posthog__projects-get
```

When querying for a specific product, filter by the `$host` property. Use `mcp__posthog__switch-project` if you need to change projects.

## Running Queries (HogQL)

`mcp__posthog__query-run` is the workhorse tool. It accepts HogQL — PostHog's SQL dialect.

### Common Query Patterns

**Count events by type (last 7 days):**
```sql
SELECT event, count()
FROM events
WHERE timestamp > now() - interval 7 day
GROUP BY event
ORDER BY count() DESC
```

**User activity timeline:**
```sql
SELECT distinct_id, event, timestamp
FROM events
WHERE person_id = '...'
ORDER BY timestamp
```

**Property analysis by domain:**
```sql
SELECT properties.$host, count()
FROM events
GROUP BY properties.$host
```

**Funnel conversion:** Build a FunnelsQuery JSON with ordered or unordered steps (see Dashboard section below).

### Natural Language to HogQL

Use `mcp__posthog__query-generate-hogql-from-question` to turn a plain English question into HogQL. Useful for complex queries — generate first, then refine the output.

### Date Filtering

- Relative: `timestamp > now() - interval N day`
- Absolute: `timestamp > toDateTime('2026-03-25')`
- Always include `$host` filter when the question is about a specific product.

## Dashboard & Insight Management

### Discovery

1. `mcp__posthog__dashboards-get-all` — list all dashboards
2. `mcp__posthog__dashboard-get` (with ID) — see all insights on a specific dashboard

### Creating & Managing Insights

- `mcp__posthog__insight-create-from-query` — pass a PostHog query JSON (TrendsQuery, FunnelsQuery, RetentionQuery, etc.)
- `mcp__posthog__insight-update` — modify the query, name, or description
- `mcp__posthog__add-insight-to-dashboard` — attach an insight to a dashboard
- `mcp__posthog__insight-delete` — permanently remove an insight (use when iterating)

**Recommended pattern:** Create → test → iterate → add to dashboard. Don't add to a dashboard until you're happy with the query.

### Funnel-Specific Notes

- **Ordered funnels:** Use when steps always happen in sequence.
- **Unordered funnels:** Use when step order varies across user populations (e.g., different product versions with different step ordering).
- **FunnelsQuery gotcha:** The `properties` field in EventsNode does NOT support OR property groups — only flat filter lists. For multi-pattern matching (e.g., matching both old and new URL structures), use the `regex` operator on a single property filter.

## Person Lookup & Investigation

- `mcp__posthog__persons-list` — search by email, distinct_id, or properties
- `mcp__posthog__persons-retrieve` — get full person profile with all properties and events
- `mcp__posthog__entity-search` — broader search across persons, events, sessions

**Investigation workflow:**
1. Get person by email
2. Check their events
3. Check their properties
4. Cross-reference with Customer.io for campaign attribution (see the `customerio` skill)

**Identity gotchas:** PostHog creates new anonymous distinct_ids on page navigations that reset cookies. Magic link flows and redirects can break the identity chain. `$identify` events merge persons — but only if PostHog sees both distinct_ids in the same session.

## Error Tracking

- `mcp__posthog__list-errors` — see current exceptions
- `mcp__posthog__error-details` — drill into specific error fingerprints

**NSLS noise context:** The shared project sees ~260K total exceptions/week across all properties. Roughly 67% are FOL DOM CustomEvent errors misclassified by PostHog's error SDK. Always filter by `$host` to focus on the product you care about before drawing any conclusions.

**Setting up Slack alerts:** PostHog CDP destinations can POST to Slack on exception events. Filter by `$host` + `$exception_issue_id is set`.

## Feature Flags & Experiments

- `mcp__posthog__feature-flag-get-all` — list all flags
- `mcp__posthog__create-feature-flag` — create a new flag (percentage rollout, user targeting, etc.)
- `mcp__posthog__experiment-create` — set up A/B tests with metrics
- `mcp__posthog__experiment-results-get` — check experiment results

**Flag lifecycle:** create → test in dev → gradual rollout → full rollout → clean up

## Event Definitions & Properties

- `mcp__posthog__event-definitions-list` — see all events in the project
- `mcp__posthog__properties-list` — see what properties events carry

**Naming conventions:**
- NSLS custom events: snake_case (e.g., `step_start`, `ai_generation`)
- PostHog auto-captured: `$` prefix (e.g., `$pageview`, `$identify`)

Each product sends its own custom event properties — use `mcp__posthog__properties-list` to discover what's available for your domain.

## Observability Logs

- `mcp__posthog__logs-query` — query PostHog's internal log streams
- `mcp__posthog__logs-list-attributes` / `logs-list-attribute-values` — discover what's in the logs

Use these when debugging CDP destinations, checking webhook deliveries, or investigating data pipeline issues.

## Diagnostic Loop (When Queries Return Wrong Results)

When a query returns 0 rows, unexpected numbers, or doesn't match what you expected:

1. **Check the `$host` filter.** Are you filtering for the right product domain? Server-side events have `$host = null`.
2. **Check the event name.** Run `event-definitions-list` and search — event names are exact-match. `step_start` ≠ `stepStart` ≠ `step-start`.
3. **Check the date range.** HogQL uses UTC. "Today" for a US user started hours ago in UTC.
4. **Check the property name.** Run `properties-list` — property names vary by product and event type.
5. **Broaden, then narrow.** Remove all filters → confirm data exists → add filters one at a time to find which one eliminates results.
6. **Try `query-generate-hogql-from-question`** to get a different angle on the same question.
7. **Check if it's a funnel issue.** FunnelsQuery `properties` doesn't support OR groups — use `regex` operator instead.

## Output Guidelines

- **For leadership:** Lead with the insight, not the query. "Completion rate dropped 12% after the track split" not "SELECT count() FROM events WHERE..."
- **For engineering:** Include the exact HogQL query so they can reproduce and iterate.
- **For cross-team reports:** Include both the number AND a representative user story (see `/data-intel` for the micro/macro marriage pattern).
- **PII awareness:** PostHog contains emails, names, IP addresses. Don't include PII in outputs unless specifically requested and the audience is appropriate.

## Gotchas & Trapdoors

- **FunnelsQuery `properties` doesn't support OR groups.** You MUST use `regex` operator for multi-pattern matching. This is undocumented and will silently return wrong results if you try OR property groups.
- **Server-side events have `$host = null`.** You can't filter server-side events (step_start, ai_generation, etc.) by domain. Use client-side $pageview events with `$current_url` patterns for domain-specific funnels.
- **`insight-delete` is permanent.** No recycle bin. If you delete an insight that's on a dashboard, it disappears from the dashboard too.
- **FOL noise overwhelms error tracking.** 260K exceptions/week, 91% crash-free rate. ~67% are FOL DOM CustomEvent errors. Always filter by `$host` before drawing conclusions.
- **Identity chain breaks on redirects.** Client-side redirects (like `router.push`) create new anonymous distinct_ids. Magic link flows are especially fragile — the landing page and the callback page may be different "persons" in PostHog.
- **`prefetch_opened` ≠ human opened.** Email clients pre-fetch images, triggering false opens. Always use `human_opened` and `human_clicked` for real engagement metrics.
- **Date math in HogQL is UTC.** If you're looking at "today's events," remember NSLS users are in ET/CT/PT but PostHog timestamps are UTC.
- **Deleting a dashboard does NOT delete its insights.** They become orphaned. Clean up insights separately.
