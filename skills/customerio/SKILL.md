---
name: customerio
description: >-
  Query Customer.io for member data, campaign performance, message history,
  and activity feeds. NSLS uses Customer.io for lifecycle marketing, onboarding
  emails, and member communications. Trigger phrases: customer.io, customerio,
  email campaign, member lookup, campaign metrics, message history, who opened,
  email clicks, segment, broadcast, CIO, look up member, check campaign.
  Includes gotchas: prefetch_opened vs human_opened, UTM auto-append,
  App API vs Track API, cio_id vs id.
---

# Customer.io

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (App API queries — person lookup, campaign metrics, message history) — runs without friction. The App API is read-only by design.
2. **Configuration** (creating segments, modifying campaign settings) — ask permission, explain what changes.
3. **Write operations** (Track API — sending events, modifying person attributes) — never proactively offered. The Track API is a separate key and a separate concern. If explicitly requested: explain what will be written to Customer.io, confirm the target person/segment, then proceed.

## Purpose

This skill turns Customer.io from a campaign dashboard into a queryable intelligence layer — cross-referencing email engagement with product behavior (via `/posthog`), tracking campaign attribution through the identity chain, and surfacing which messages actually drive action vs. which inflate metrics with prefetch noise. If Customer.io tools aren't available, run `/connect` first.

## NSLS Customer.io Context

NSLS uses Customer.io for lifecycle marketing: onboarding email sequences, chapter outreach, re-engagement campaigns, and member communications. The workspace (ID: 183998) contains campaigns, segments, and person records for all NSLS members.

## API Reference

- **NSLS Customer.io workspace ID:** 183998
- **API docs:** https://docs.customer.io/integrations/api/app/
- **Base URL:** `https://api.customer.io/v1/`

## Person Lookup

**Search by email:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/customers?email=user@example.com" | python3 -m json.tool
```

**Get profile (attributes):**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/attributes" | python3 -m json.tool
```

**Get message history:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/messages" | python3 -m json.tool
```

**Get activity feed:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/activities?limit=100" | python3 -m json.tool
```

**Workflow:** Search by email → get `cio_id` from results → use `cio_id` for all subsequent calls.

### Message Metric Types

Each message carries these metrics: `sent`, `delivered`, `opened`, `prefetch_opened`, `human_opened`, `clicked`, `human_clicked`, `converted`.

**Important:** `prefetch_opened` = email client pre-fetch (NOT a human). Always use `human_opened` / `human_clicked` for real engagement numbers.

## Campaign Analytics

**List all campaigns:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/campaigns" | python3 -m json.tool
```

**Get campaign metrics:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/campaigns/{campaign_id}/metrics" | python3 -m json.tool
```

Key metrics: sent, delivered, opened, human_opened, clicked, human_clicked, converted, unsubscribed, bounced.

**Pattern:** List campaigns → find the one you care about → get metrics → compare against previous campaigns.

## Segments

**List segments:**
```bash
curl -s -H "Authorization: Bearer $APP_API_KEY" \
  "https://api.customer.io/v1/segments" | python3 -m json.tool
```

Segments are pre-defined groups of customers based on attributes or behavior. Useful for understanding who's in a campaign audience.

## Cross-Tool Investigation (PostHog + Customer.io)

### "Did this user come from our email?"

1. Search PostHog for the person by email → get their events
2. Check `$current_url` for UTM params (`utm_source=customer.io`)
3. Search Customer.io for same email → get message history
4. Cross-reference timestamps: CIO email sent → CIO click → PostHog pageview

### "Which campaign drove the most signups?"

1. Get campaign metrics from CIO
2. Get campaign click timestamps
3. Cross-reference with PostHog `$identify` events (signup = identity established)

**Timezone note:** Customer.io uses UTC for all timestamps.

## Diagnostic Loop (When Lookups Return Empty or Wrong)

1. **Person not found by email?** Try partial match. Check if they were suppressed (deleted people still appear with a suppressed flag). Try searching by `cio_id` if you have it from another source.
2. **Campaign metrics look inflated?** You're probably looking at `opened` instead of `human_opened`. Email clients pre-fetch images — always use `human_opened` / `human_clicked`.
3. **UTM attribution missing in PostHog?** Customer.io auto-appends UTM params at the click-tracking redirect, but client-side redirects in the app can strip them. Check PostHog's `$current_url` for the UTM params — they may be on the landing page pageview but not on subsequent pages.
4. **API returns 401?** The App API key may have expired or been rotated. Generate a new one in Customer.io Settings → API Keys.
5. **Can't find a campaign?** List all campaigns and search — campaign names in the API may differ from what the marketing team calls them in Slack.

## Output Guidelines

- **For marketing:** Lead with engagement rates (human_opened, human_clicked, converted). Compare against previous campaigns. Flag statistical significance if sample sizes are small.
- **For product:** Focus on the user journey: which email → which click → what happened in the product (cross-reference with PostHog).
- **For leadership:** One sentence: "The March onboarding sequence converted 23% of openers into active users, up from 18% in February."
- **Timezone:** All Customer.io timestamps are UTC. Convert for the audience if needed.

## Gotchas & Trapdoors

- **`prefetch_opened` is NOT a real open.** Email clients (Apple Mail, Gmail) pre-fetch images, inflating open rates. Always use `human_opened` / `human_clicked` for real numbers.
- **Customer.io auto-appends UTM params at click-tracking redirect** even if the HTML links don't contain them. So `utm_source=customer.io` appears in the URL but may not make it into PostHog person properties if the app has client-side redirects.
- **`cio_id` is different from `id`.** The API returns both. Use `cio_id` for subsequent lookups — it's the stable internal identifier.
- **Rate limits exist** but are generous for read operations. Batch person lookups if querying more than ~50 people.
- **App API key ≠ Track API key.** The App API (read) is separate from the Track API (write events). This skill uses the App API. Don't use it to send events — that's the Track API.
- **Deleted people aren't gone.** Customer.io "suppresses" them. They may still appear in search results with a suppressed flag.
