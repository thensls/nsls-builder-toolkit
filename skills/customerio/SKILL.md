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

Query Customer.io for member data, campaign performance, message history, and activity feeds.

## Setup

- **NSLS Customer.io workspace ID:** 183998
- **API docs:** https://docs.customer.io/integrations/api/app/

### Get an App API Key

1. Log in to Customer.io
2. Go to Settings → API Keys → Create App API Key
3. Store it securely in macOS Keychain:

```bash
security add-generic-password -a "customerio" -s "customerio-app-api" -w "YOUR_KEY"
```

### Usage

Retrieve the key at the start of each call:
```bash
CIO_KEY=$(security find-generic-password -a "customerio" -s "customerio-app-api" -w)
```

- **Base URL:** `https://api.customer.io/v1/`
- **Auth header:** `Authorization: Bearer $CIO_KEY`

## Person Lookup

**Search by email:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/customers?email=user@example.com" | python3 -m json.tool
```

**Get profile (attributes):**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/attributes" | python3 -m json.tool
```

**Get message history:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/messages" | python3 -m json.tool
```

**Get activity feed:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/customers/{cio_id}/activities?limit=100" | python3 -m json.tool
```

**Workflow:** Search by email → get `cio_id` from results → use `cio_id` for all subsequent calls.

### Message Metric Types

Each message carries these metrics: `sent`, `delivered`, `opened`, `prefetch_opened`, `human_opened`, `clicked`, `human_clicked`, `converted`.

**Important:** `prefetch_opened` = email client pre-fetch (NOT a human). Always use `human_opened` / `human_clicked` for real engagement numbers.

## Campaign Analytics

**List all campaigns:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/campaigns" | python3 -m json.tool
```

**Get campaign metrics:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
  "https://api.customer.io/v1/campaigns/{campaign_id}/metrics" | python3 -m json.tool
```

Key metrics: sent, delivered, opened, human_opened, clicked, human_clicked, converted, unsubscribed, bounced.

**Pattern:** List campaigns → find the one you care about → get metrics → compare against previous campaigns.

## Segments

**List segments:**
```bash
curl -s -H "Authorization: Bearer $CIO_KEY" \
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

## Gotchas & Trapdoors

- **`prefetch_opened` is NOT a real open.** Email clients (Apple Mail, Gmail) pre-fetch images, inflating open rates. Always use `human_opened` / `human_clicked` for real numbers.
- **Customer.io auto-appends UTM params at click-tracking redirect** even if the HTML links don't contain them. So `utm_source=customer.io` appears in the URL but may not make it into PostHog person properties if the app has client-side redirects.
- **`cio_id` is different from `id`.** The API returns both. Use `cio_id` for subsequent lookups — it's the stable internal identifier.
- **Rate limits exist** but are generous for read operations. Batch person lookups if querying more than ~50 people.
- **App API key ≠ Track API key.** The App API (read) is separate from the Track API (write events). This skill uses the App API. Don't use it to send events — that's the Track API.
- **Deleted people aren't gone.** Customer.io "suppresses" them. They may still appear in search results with a suppressed flag.
