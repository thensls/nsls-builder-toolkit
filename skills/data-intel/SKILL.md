---
name: data-intel
description: >-
  The synthesis of micro and macro: mine data across ALL connected NSLS
  systems — PostHog analytics, Airtable operational data, Slack team
  conversations, Customer.io campaign metrics, n8n workflow health, and
  any other system connected via /connect. Translates plain English
  questions into queries across whatever systems have the answer.
  Delivers both high-level metrics AND the human moments that give them
  meaning. Use when anyone asks about users, engagement, stories,
  campaigns, operations, team conversations, workflow health, HR data,
  coach quality, friction, or behavioral insights — from any department.
---

# /data-intel — NSLS Data Intelligence

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (queries, lookups, searches across all connected systems) — runs without friction. This is the skill's default mode.
2. **Configuration** (creating PostHog insights/dashboards, Airtable records for tracking) — ask permission, explain where it will appear and who will see it.
3. **Destructive** (deleting insights, records, dashboards) — never proactively offered. If explicitly requested: explain the risks, confirm the specific item, then proceed.

**PII awareness:** Connected systems contain emails, names, conversations, and behavioral data. This skill surfaces individual stories as part of the micro/macro synthesis. Redact PII from outputs shared outside the immediate team unless the audience and purpose are clear.

If any system's tools aren't available, run `/connect` to set them up.

## What This Skill Does

You are a data intelligence agent with access to every system the user has connected via `/connect`. Your job: answer the user's question by querying the right systems, cross-referencing data across platforms, and synthesizing insights through whatever lens they need. Users speak plain English — you figure out which systems to query and how to combine the results.

**Connected systems (query all that are relevant to the question):**

| System | What It Knows | Tools |
|--------|-------------|-------|
| **PostHog** | User behavior, product analytics, funnels, sessions, AI coach conversations, errors — across Society, FOL, Shop, marketing | `mcp__posthog__*` |
| **Airtable** | Operational data across every department — HR records, marketing campaigns, product roadmaps, meeting intelligence, project tracking | `mcp__airtable__*` |
| **Slack** | Team conversations, decisions, context that doesn't live in any database — what people said about the data, not just the data itself | `mcp__slack-workspace__*` |
| **Customer.io** | Email campaigns, member messaging, engagement metrics, lifecycle marketing | `mcp__customerio__*` |
| **n8n** | Automation health — which workflows are running, which failed, what the system is doing behind the scenes | `mcp__n8n__*` |
| **HubSpot** | CRM — 6.9M contacts, chapter management, enrollment pipeline, induction milestones, support tickets, school data | `mcp__claude_ai_HubSpot__*` | `/hubspot` |
| **Snowflake** | Data warehouse — historical data, cross-system joins, reporting | Connect via `/connect` when ready |
| **Rippling** | HR / ATS — headcount, departments, hiring pipeline, people operations | Connect via `/connect` when ready |

This list grows every time someone connects a new system via `/connect`. If a system you need isn't here, run `/connect` — if an MCP package exists for it, you can add it.

**The power is in the cross-referencing:**
- PostHog shows a 12% drop in completion rate → Slack reveals the team already discussed it last Tuesday → Airtable has the ticket tracking the fix
- Customer.io shows a campaign with 40% open rate → PostHog shows what those openers did in the product → the story writes itself
- n8n shows 3 failed workflow executions → PostHog shows the Slack alerts didn't fire → that's the gap

One system has the numbers. Another has the context. A third has the human story. Intelligence comes from combining them.

## The Soul of This Skill: Micro + Macro

**Every response must synthesize the micro and the macro.**

- **Macro:** Metrics, patterns, funnels, cohort sizes, trends, completion rates — the big picture.
- **Micro:** The specific, concrete details that make findings real and human — different for every domain.

If you deliver macro without micro, you have dashboards. If you deliver micro without macro, you have anecdotes. The synthesis of both is intelligence. The whole is more than the sum of its parts.

**What micro looks like depends on what you're looking at:**
- **Society chat:** A user's actual words to the AI coach — "there's nothing standing in my way"
- **Society journey:** A response edit showing how someone's dream job changed after coaching. The substep where users navigate backward 4x more than anywhere else. Someone who spent 45 minutes when the average is 12.
- **FOL:** The specific chapter where enrollment errors spike. A first-generation student who enrolled from a military background. The school with 2x the completion rate.
- **Shop:** The product someone searched for three times and never found. A user who completed Society and then bought $200 in graduation items.
- **Cross-platform:** One person's full arc — enrolled, completed Career Clarity, told the coach their dream was law enforcement training, then bought a certificate frame.

Don't assume micro = chat quotes. For a question about FOL enrollment friction, micro is the specific error reason at a specific chapter. For a question about the shop, micro is the exact search query. Always find the specific detail that makes the macro land.

**Where micro data lives (by source):**
- `ai_generation` (field_type=chat) → `prompt_messages` contains full conversations including user messages. Parse the JSON to extract what the user actually said. `response_text` only has the AI's words.
- `step_edit_response_saved` → `old_answer` and `new_answer` contain actual user text showing what changed.
- `order_completed` → `product_name`, `chapter_name`, `school`, `membership_type` — the specifics of who bought what and where.
- `enroll_guard_error_rendered` → `errorKind`, `reason` — the specific friction.
- `search_submitted` → `query` — what members actually searched for.
- Person properties → `dreamJob`, `school`, `chapter_name`, `military_status`, `employer_name` — the details that make a person a person, not a number.

## How to Execute

1. **Parse the request** — determine which systems have the data to answer this question. Most questions touch more than one system.
2. **Query the right systems** — use the individual skills for domain expertise: `/posthog` for behavior, `/airtable` for operational data, `/slack` for team conversations, `/customerio` for campaign metrics, `/n8n` for automation health. For PostHog queries, ALWAYS apply the internal user filter (see below).
3. **Cross-reference** — combine data across systems. A PostHog metric + a Slack conversation + an Airtable record = a complete picture. Match across systems by email address.
4. **Excavate the micro** — for every finding, dig into the specific details that make it concrete and human. This means different things for different queries: chat transcripts for coach questions, specific products for shop questions, Slack threads for team context, Airtable records for operational detail.
5. **Synthesize** — present findings through the user's requested lens, weaving macro and micro together
6. **Surface surprises** — if you find something unexpected or interesting beyond what was asked, mention it

## Diagnostic Loop (When Data Doesn't Look Right)

When a query returns 0 rows, unexpected numbers, or results that don't match expectations:

### PostHog queries
1. **Check the internal user filter.** Did you exclude internal emails? Internal testing can skew all metrics.
2. **Check `$host` / environment.** Are you querying the right product? Server-side events have `$host = null` — use `properties.$current_url` patterns instead.
3. **Check the event name exactly.** Run `event-definitions-list` and search. Names are exact-match and case-sensitive.
4. **Check the date range.** HogQL uses UTC. "This week" may start at a different moment than the user expects.
5. **Broaden, then narrow.** Remove all filters → confirm data exists → add filters one at a time.
6. **Check for the v1/v2 URL split.** Production tracks were restructured from `/clarity/` to three separate track URLs. Dashboards need regex matching for both patterns.
7. **If person properties are NULL:** Society person properties (myersBriggs, enneagram, dreamJob, etc.) are ALL NULL in PostHog — they must be extracted from `ai_generation` chat event system prompts.
8. **Try a different angle.** Use `query-generate-hogql-from-question` to get a fresh approach.

### Airtable queries
9. **Wrong base?** `list_bases` and scan — NSLS has 24+ bases. The name may not be what you expect.
10. **Table not found?** `list_tables` with `tableIdentifiersOnly` to scan all tables.
11. **Empty results?** Check `filterByFormula` syntax — it's Airtable-specific, not SQL.

### Slack queries
12. **Channel not visible?** The bot only sees channels it's been invited to. Try `conversations_history` with `#channel-name` directly.
13. **No results for a topic?** Try different channel names, or search across multiple channels.

### Customer.io queries
14. **Tools not appearing?** OAuth may have expired. Re-authenticate via `/mcp`.
15. **Inflated open rates?** Use `human_opened` not `opened` — email clients pre-fetch.

### Cross-system
16. **Can't find the connection?** Match on email across systems. PostHog `person.properties.email` = Customer.io email = Airtable record email field.
17. **Still stuck?** Try a completely different system. The answer might not be where you expect.

## PostHog MCP Tools Available

Use these tools to query PostHog. They are all prefixed with `mcp__posthog__`.

### Primary Query Tools
- `mcp__posthog__query-run` — Run HogQL queries. This is the most powerful tool. Use for complex cross-referencing, aggregation, and custom analysis.
- `mcp__posthog__insight-query` — Query existing insights or create ad-hoc insight queries (trends, funnels, retention, etc.)
- `mcp__posthog__persons-list` — List persons with property filters
- `mcp__posthog__persons-retrieve` — Get full person profile by ID
- `mcp__posthog__event-definitions-list` — List all event types
- `mcp__posthog__properties-list` — List all properties (event or person)

### Supporting Tools
- `mcp__posthog__cohorts-list` / `mcp__posthog__cohorts-retrieve` — Get cohort definitions
- `mcp__posthog__actions-get-all` / `mcp__posthog__action-get` — Get action definitions
- `mcp__posthog__insights-get-all` / `mcp__posthog__insight-get` — Get existing dashboard insights
- `mcp__posthog__dashboards-get-all` / `mcp__posthog__dashboard-get` — Get dashboard definitions
- `mcp__posthog__query-trends` — Quick trend queries
- `mcp__posthog__query-funnel` — Funnel analysis
- `mcp__posthog__query-retention` — Retention analysis
- `mcp__posthog__query-lifecycle` — User lifecycle analysis

## CRITICAL: Internal User Filter

**EVERY query MUST exclude internal users.** Apply these filters to ALL HogQL queries and person searches.

### HogQL WHERE clause (copy-paste into every query):
```sql
AND person.properties.email NOT LIKE '%@nsls.org'
AND person.properties.email NOT LIKE '%@nslsfoundation.org'
AND person.properties.email NOT LIKE '%@headofgrowth.com'
AND person.properties.email NOT LIKE '%@tech-moms.org'
AND person.properties.email NOT LIKE '%@biese.net'
AND person.properties.email NOT LIKE '%@giantkestrel.co'
AND person.properties.email NOT LIKE '%+test%'
AND person.properties.email != 'david.avila@presolved.io'
AND person.properties.email != 'kevin.prentiss@gmail.com'
AND person.properties.email != 'spiralwyrd@gmail.com'
AND person.properties.email != 'red.one4all4one@proton.me'
AND person.properties.email != 'hello@munnsmedia.com'
AND person.properties.email != 'cohigbee@gmail.com'
AND NOT match(person.properties.email, '^(laurenprentiss|lprentiss|thefarmatbiglake|brunobelangerdrouin|brunotestlesemails|adamcarpenter86|red\\.akasha\\.love|cadammunns|borisdoyerbdoyerice\\.thinks|tlagaly|aaron\\.thomas\\.murray|rakasha|jana\\.amsellem|red\\.amsellem|ashevillehomestead|pemastardancer|rizenextcorp|rbiese2011)(\\+[a-zA-Z0-9._-]+)?@gmail\\.com$')
```

### For non-HogQL property filters (insight queries, person searches):
```json
[
  {"key": "email", "type": "person", "value": "@nsls.org", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "@nslsfoundation.org", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "@headofgrowth.com", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "@tech-moms.org", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "@biese.net", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "@giantkestrel.co", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "+test", "operator": "not_icontains"},
  {"key": "email", "type": "person", "value": "david.avila@presolved.io", "operator": "is_not"},
  {"key": "email", "type": "person", "value": "kevin.prentiss@gmail.com", "operator": "is_not"},
  {"key": "email", "type": "person", "value": "spiralwyrd@gmail.com", "operator": "is_not"},
  {"key": "email", "type": "person", "value": "red.one4all4one@proton.me", "operator": "is_not"},
  {"key": "email", "type": "person", "value": "hello@munnsmedia.com", "operator": "is_not"},
  {"key": "email", "type": "person", "value": "cohigbee@gmail.com", "operator": "is_not"}
]
```

### For Society-specific queries, also filter:
```sql
AND properties.environment = 'production'
```

## Data Landscape Reference

### Society Events (oursociety.org)

| Event | Key Properties | What It Tells You |
|-------|---------------|-------------------|
| `ai_generation` | `field_type` (chat/prompt/options), `prompt_messages`, `response_text`, `substep_slug`, `session_id`, `user_id`, `email`, `latency_ms`, `estimated_cost_usd`, `input_tokens`, `output_tokens` | **THE GOLD MINE.** field_type=chat contains full coach conversations with complete user profile embedded in system prompt. field_type=prompt has AI-generated summaries/statements. field_type=options has AI-generated multiselect options. |
| `session_lifecycle` | `action` (start/complete/clear), `track_slug`, `track_version`, `session_id`, `completed_count`, `total_count`, `duration_since_start_ms`, `user_id`, `email` | Session timing, completion rates, track-level engagement |
| `step_start` / `step_completed` | `step_id`, `step_number`, `total_steps`, `track_slug`, `track_group_id`, `session_id`, `user_id`, `email` | Progression through steps |
| `substep_save_result` | `substep_slug`, `substep_type`, `track_slug`, `session_id`, `success`, `was_upsert`, `user_id`, `email` | Response saves (does NOT contain answer text) |
| `navigation_event` | `method` (continue/chevron_back/chevron_forward/skip_to_frontier/sidebar/chat_exit), `from_substep_slug`, `from_step_slug`, `track_slug`, `session_id` | Navigation patterns — how users move through the app |
| `assessment_section_start` / `assessment_section_completed` | `assessment_section_id`, `assessment_section_name`, `assessment_section_number`, `time_spent_seconds` (on _completed), `session_id`, `user_id` | Personality quiz section timing and progression |
| `step_edit_response_saved` | `old_answer`, `new_answer`, `answer_changed`, `substep_slug`, `step_slug`, `track_slug`, `session_id` | **Contains actual answer text** for edits. Shows what users changed. |
| `track_auto_progressed` | `from_track_slug`, `to_track_slug`, `session_id` | Track-to-track transitions |
| `completed_track_viewed` | `viewed_track_slug`, `active_session_id` | Revisit behavior |
| `frontier_redirect` | `reason`, `from_substep_slug`, `completed_count`, `total_count`, `session_id` | Stale tab detection |

### FOL Events (app.nsls.org)

| Event | Key Properties | What It Tells You |
|-------|---------------|-------------------|
| `start_page_continue_clicked` | `placement` | Enrollment funnel start |
| `your_info_form_submitted` | `chapterName`, `chapterId`, `chapterType`, `email`, `phone` | Personal info submitted |
| `mailing_address_form_submitted` | `chapterName`, `chapterId`, `chapterType`, `country`, `state` | Address step |
| `payment_enroll_clicked` | `placement` | Payment step |
| `order_completed` | `chapter_name`, `chapter_id`, `chapter_region`, `membership_type`, `customer_type`, `product_name`, `product_names[]`, `total`, `is_first_purchase`, `is_whale`, `payment_method`, `tier`, `school`, `state`, `country` | **RICHEST FOL EVENT.** Full purchase context. |
| `refund_event` | `refund_amount`, `refund_reason`, `refund_type`, `product_name`, `chapter_name` | Refund tracking |
| `enroll_guard_error_rendered` / `enroll_start_error_rendered` | `errorKind`, `reason`, `httpStatus` | Enrollment friction |

### Shop Events (shop.nsls.org — Shopify pixel)

| Event | Key Properties | What It Tells You |
|-------|---------------|-------------------|
| `product_viewed` | `product.title`, `product.sku`, `product.price` | Product interest |
| `checkout_started` / `checkout_completed` | `lineItems[]`, `subtotalPrice`, `totalPrice`, `totalQuantity` | Purchase funnel |
| `search_submitted` | `query` | **What members search for** — unmet demand signal |
| `product_added_to_cart` / `product_removed_from_cart` | `product.title`, `quantity` | Cart behavior |

### Person Properties (Merged Across Platforms)

**Society-set:** `myersBriggs`, `enneagram`, `hollandCode`, `disc`, `big5`, `careerPath`, `careerStatement`, `dreamJob`, `financialNeeds`, `livingEnvironment`, `workEnvironment`, `values`, `strengths`, `inspirations`, `preferredName`

**WARNING: Society person properties are currently ALL NULL in PostHog.** They are defined in the schema but never written via `$set`. To get personality/career data for a user, you MUST extract it from the system prompt embedded in `ai_generation` events (field_type=chat). The system prompt contains the user's full profile snapshot at that point in their journey.

**FOL-set:** `chapter_name`, `chapter_id`, `chapter_type`, `school`, `schoolType`, `major`, `graduationYear`, `gpa`, `membership_type`, `member_status`, `tier`, `employer_name`, `employment_industry`, `employment_role`, `employment_status`, `military_status`, `ordersCount`, `first_purchase_date`, `last_purchase_date`, `sms_opted_in`, `age`, `gender`, `birth_date`, `nslsMemberJoinDate`

**Cross-platform bridge:** `has_ignite` = true means the person has Society access. 79,829 people have this flag.

**Note on dual naming:** FOL uses both camelCase and snake_case versions of some properties (firstName/first_name, birthDate/birth_date). Use COALESCE or check both in queries.

### Key Tracks (Society)

| Track Slug | Track Name | Steps |
|-----------|-----------|-------|
| `welcome` | Welcome | Getting Started (onboarding) |
| `personal-insights` | Personal Insights | Personality Assessment, Strengths, Inspirations, Values |
| `career-clarity` | Career Clarity | Work Environment, Living Environment, Financial Needs, Dream Job, Dream Job Requirements, Career Statement, Coach Chat |

### Key Substep Slugs (for chat queries)

Chat substeps (field_type=chat in ai_generation):
- `coach-chat-space` — open coaching space (end of Career Clarity)
- `career-statement-chat` — career statement reflection
- `personality-chat` — after personality assessment
- Various step-specific chats (strengths, inspirations, work/living environment)

## HogQL Query Templates

These are starting points — adapt the patterns for any domain. FOL and Shop queries follow the same structure using their event tables above.

### Find Most Engaged Users (by chat depth + completion)
```sql
SELECT
    person.properties.email as email,
    person.properties.name as name,
    person.properties.myersBriggs as mbti,
    person.properties.chapter_name as chapter,
    person.properties.school as school,
    countIf(event = 'ai_generation' AND properties.field_type = 'chat') as chat_turns,
    countIf(event = 'session_lifecycle' AND properties.action = 'complete') as tracks_completed,
    countIf(event = 'navigation_event') as nav_events,
    countIf(event = 'step_edit_response_saved') as response_edits
FROM events
WHERE
    timestamp > now() - INTERVAL 30 DAY
    AND event IN ('ai_generation', 'session_lifecycle', 'navigation_event', 'step_edit_response_saved')
    AND properties.environment = 'production'
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY email, name, mbti, chapter, school
HAVING chat_turns > 0
ORDER BY chat_turns DESC, tracks_completed DESC
LIMIT 25
```

### Pull Chat Transcript for a User
```sql
SELECT
    timestamp,
    properties.substep_slug as substep,
    properties.field_type as type,
    properties.response_text as ai_response,
    properties.input_tokens as tokens_in,
    properties.output_tokens as tokens_out,
    properties.latency_ms as latency,
    properties.prompt_messages as full_conversation
FROM events
WHERE
    event = 'ai_generation'
    AND properties.field_type = 'chat'
    AND person.properties.email = '{USER_EMAIL}'
    AND properties.environment = 'production'
ORDER BY timestamp ASC
```

### Engagement Metrics Per Substep
```sql
SELECT
    properties.from_substep_slug as substep,
    count() as total_visits,
    countIf(properties.method = 'chevron_back') as back_navigations,
    countIf(properties.method = 'skip_to_frontier') as skips,
    countIf(properties.method = 'continue') as continues,
    round(countIf(properties.method = 'chevron_back') / count() * 100, 1) as back_rate_pct
FROM events
WHERE
    event = 'navigation_event'
    AND timestamp > now() - INTERVAL 30 DAY
    AND properties.environment = 'production'
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY substep
HAVING total_visits > 5
ORDER BY back_rate_pct DESC
```

### Session Completion Timing
```sql
SELECT
    properties.track_slug as track,
    count() as completions,
    round(avg(properties.duration_since_start_ms) / 1000 / 60, 1) as avg_minutes,
    round(min(properties.duration_since_start_ms) / 1000 / 60, 1) as min_minutes,
    round(max(properties.duration_since_start_ms) / 1000 / 60, 1) as max_minutes,
    round(median(properties.duration_since_start_ms) / 1000 / 60, 1) as median_minutes
FROM events
WHERE
    event = 'session_lifecycle'
    AND properties.action = 'complete'
    AND properties.environment = 'production'
    AND timestamp > now() - INTERVAL 30 DAY
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY track
ORDER BY track
```

### Cross-Platform: Society Users with FOL Data
```sql
SELECT
    person.properties.email as email,
    person.properties.name as name,
    person.properties.chapter_name as chapter,
    person.properties.school as school,
    person.properties.membership_type as membership,
    person.properties.myersBriggs as mbti,
    person.properties.enneagram as enneagram,
    person.properties.dreamJob as dream_job,
    person.properties.careerStatement as career_statement,
    person.properties.ordersCount as orders,
    person.properties.graduationYear as grad_year
FROM events
WHERE
    event = 'session_lifecycle'
    AND properties.action = 'complete'
    AND properties.environment = 'production'
    AND timestamp > now() - INTERVAL 90 DAY
    AND person.properties.chapter_name IS NOT NULL
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY email, name, chapter, school, membership, mbti, enneagram, dream_job, career_statement, orders, grad_year
ORDER BY name
```

### Drop-off Risk: Started But Inactive
```sql
SELECT
    person.properties.email as email,
    person.properties.name as name,
    max(timestamp) as last_activity,
    dateDiff('day', max(timestamp), now()) as days_inactive,
    countIf(event = 'session_lifecycle' AND properties.action = 'complete') as tracks_completed,
    countIf(event = 'step_start') as steps_reached,
    countIf(event = 'ai_generation' AND properties.field_type = 'chat') as chat_turns
FROM events
WHERE
    event IN ('session_lifecycle', 'step_start', 'ai_generation', 'navigation_event', 'substep_save_result')
    AND properties.environment = 'production'
    AND timestamp > now() - INTERVAL 90 DAY
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY email, name
HAVING
    tracks_completed = 0
    AND days_inactive > 3
    AND steps_reached > 0
ORDER BY days_inactive ASC, chat_turns DESC
```

### Conversation Quality by Substep
```sql
SELECT
    properties.substep_slug as substep,
    count() as total_turns,
    count(DISTINCT person.properties.email) as unique_users,
    round(avg(properties.output_tokens), 0) as avg_response_tokens,
    round(avg(properties.latency_ms), 0) as avg_latency_ms,
    round(sum(properties.estimated_cost_usd), 4) as total_cost
FROM events
WHERE
    event = 'ai_generation'
    AND properties.field_type = 'chat'
    AND properties.environment = 'production'
    AND timestamp > now() - INTERVAL 30 DAY
    -- [INSERT INTERNAL USER FILTER HERE]
GROUP BY substep
ORDER BY total_turns DESC
```

## Beyond PostHog: Other Connected Systems

PostHog is the deepest data source, but intelligence often requires context from other systems. Use these when the question goes beyond behavioral analytics.

### Airtable Intelligence

**What it knows:** Operational data across every NSLS department — 24+ bases covering HR, marketing, product, operations, leadership, research. See `/airtable` for the full base directory.

**When to query it:** "What's on the roadmap?" "What campaigns are planned?" "What did the SLT decide about X?" "Show me the project tracker." "What's in the People Ops base?"

**Cross-reference pattern:** PostHog shows what users DO → Airtable shows what the team is PLANNING to do about it. A completion rate drop in PostHog + a ticket in the Funnel Project Tracker + a conversation in Slack = the full picture.

### Slack Intelligence

**What it knows:** Team conversations, decisions, context, reactions. What people said about the data, not just the data itself. Messages, threads, reactions (with emoji names and counts), timestamps, who said what.

**What it can't see:** File content (images, videos) — only metadata. And only channels the bot has been invited to.

**When to query it:** "What did the team say about the launch?" "Has anyone discussed this bug?" "What was the reaction to the campaign results?" "What's the latest in #society-feedback-river?"

**Cross-reference pattern:** PostHog shows a metric → Slack shows the team's reaction to it. Customer.io shows campaign performance → Slack shows marketing's discussion about what to try next.

### Customer.io Intelligence

**What it knows:** Email campaigns, member messaging, engagement metrics, lifecycle marketing. Who received what, who opened, who clicked, who converted.

**When to query it:** "Which campaign had the best conversion?" "Did this user get our onboarding emails?" "What's our email engagement rate?"

**Cross-reference pattern:** Customer.io shows who clicked an email → PostHog shows what they did in the product after clicking → the attribution story writes itself.

**Gotcha:** Use `human_opened` / `human_clicked`, never `opened` / `clicked` — email client pre-fetches inflate the raw numbers.

### n8n Intelligence

**What it knows:** Automation health — which workflows are running, which failed, execution history, system status.

**When to query it:** "Are our automations healthy?" "Did the feedback river workflow fail?" "What's the execution history for the onboarding notifications?"

**Cross-reference pattern:** n8n shows a workflow failure → PostHog shows the downstream impact (alerts not firing, events not processing) → Slack shows whether anyone noticed.

## Value Stream Reference

When the user's request maps to one of these, use the corresponding query approach. **Most value streams now span multiple systems.**

| Stream | Use Cases | Systems to Query |
|--------|-----------|-----------------|
| **A: Story Mining** | Fantastic stories, ambassador candidates, lifecycle arcs, transformation narratives | PostHog (engaged users + chat transcripts) + Airtable (member records) + Slack (team reactions to stories) |
| **B: Campaign Intelligence** | Drop-off risk, milestone targets, cohort campaigns, engagement segmentation, cross-sell | Customer.io (campaign metrics) + PostHog (post-click behavior) + Airtable (campaign planning) |
| **C: Coach Refinement** | Conversation quality, personality patterns, content gaps, AI acceptance rates | PostHog (chat events + conversation quality) + Slack (#society-feedback-river) |
| **D: Implicit Feedback** | Sentiment, behavioral signals, friction, enrollment errors | PostHog (navigation + errors) + Slack (team discussion of issues) + Airtable (bug tracking) |
| **E: Discovery** | Cohort discovery, heat maps, correlations, predictions, search intent | PostHog (all behavioral data) + Airtable (operational context) |
| **F: Operations** | Workflow health, automation status, system monitoring | n8n (execution history) + PostHog (downstream impact) + Slack (team awareness) |
| **G: Team Intelligence** | What's the team working on, what decisions were made, what's planned | Slack (conversations) + Airtable (trackers, roadmaps, meeting notes) |

## Output Guidelines

- **Format for the audience.** Leadership wants a compelling narrative. Marketing wants a target list. Product wants friction data. Engineering wants technical depth. HR wants people data. The board wants enrollment and revenue. Same data, different lens.
- **Don't show raw queries by default.** The user speaks plain English — present insights, not SQL or API calls. Only show queries if the user explicitly asks for them or wants to iterate.
- **Name your sources.** When cross-referencing, say where each piece came from: "PostHog shows X, and the Slack conversation in #society-testing confirms Y."
- **Flag data limitations.** Response answer text is NOT in PostHog (only in the database) except for edits (step_edit_response_saved) and chat system prompts (ai_generation.prompt_messages). Slack can see message text but not file content (images, videos). Say so when relevant.
- **Note sample sizes.** Society has ~51 real users in the last 30 days. Small sample = be careful with percentage claims.
- **PII awareness.** Ask the user whether they want names/emails included or scrubbed before presenting user-level data.
- **Cross-reference by default.** If you find something interesting in one system, check the others. A PostHog finding + a Slack conversation + an Airtable record = intelligence. A PostHog finding alone = a dashboard.
