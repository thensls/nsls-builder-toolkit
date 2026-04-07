---
name: investigation
description: >-
  Use when you need ground truth — not guesses, not pattern-matching, not
  "it should be." When someone reports a bug, asks what's happening, wants
  to understand a system, or needs to verify a claim. When the cost of being
  wrong is trust. Cast the widest net across every accessible source, follow
  every thread to its actual data, and report exactly what you found and
  where you found it.
---

# /investigation — Find What's Actually True

## Purpose

You are not here to guess. You are not here to pattern-match from what sounds plausible. You are here to find out what is actually true by going and looking at actual data in every single place you have access to look, and going back again to look deeper until you know exactly what happened and can show proof, not just evidence.

The failure mode this skill prevents: **confident fabrication.** Saying "this is probably X" when you haven't checked. Narrating what you think is happening based on vibes. Presenting a plausible-sounding story as fact. These failures cost trust — especially in front of teams, during incidents, and when someone is relying on your answer to make a decision.

The success mode: **"I checked these 7 places. Here's what I found in each one. Here's what it means together. Here are the 2 things I couldn't verify and why."**

## The Core Rule

**QUERY FIRST. EXPLAIN SECOND. ALWAYS.**

Before you offer ANY explanation, hypothesis, or narrative:
1. Identify every source you can check
2. Go check them
3. Report what you actually found
4. THEN synthesize

If you haven't verified it, say **"I don't know yet, let me check."** Never fill the gap with a plausible-sounding story.

## How to Investigate

### Phase 1: Cast the Net — Identify All Sources

Before you touch a single query, list every source that COULD contain relevant information. Don't assume you know which ones matter — the one you skip is often the one that has the answer.

**Sources to always consider:**

| Source | How to Access | What It Contains |
|--------|--------------|-----------------|
| **Local codebase** | Read, Grep, Glob | Implementation truth — what the code actually does |
| **Git history** | git log, git blame, git diff | When things changed, who changed them, why |
| **GitHub issues/PRs** | gh issue list/view, gh pr list/view | Decisions, requirements, bug reports, discussions |
| **Memory files** | Read ~/.claude/memory/ | Cross-session context, prior findings, team info |
| **PostHog** | MCP tools (mcp__posthog__*) | User behavior, events, person properties, errors |
| **Airtable** | MCP tools (mcp__airtable__*) | Work tracking, roadmap, structured records |
| **HubSpot** | MCP tools (mcp__claude_ai_HubSpot__*) | CRM contacts, companies, deals, member lifecycle |
| **customer.io** | App API via Keychain | Campaign activity, email engagement, segments |
| **n8n** | MCP tools (mcp__n8n__*) | Workflow state, execution logs, automation |
| **Prisma schema** | Read prisma/schema.prisma | Database truth — what fields actually exist |
| **Database** | Prisma Studio or direct query | Actual data state — what values are stored |
| **Vercel** | Dashboard or CLI | Deployment state, env vars, build logs |
| **Web** | WebSearch, WebFetch | Documentation, forums, API docs, external data |
| **Conversation history** | Grep ~/.claude/projects/ .jsonl files | Prior conversation context |

**Not every investigation needs every source.** But you must CONSIDER each one and consciously decide whether it's relevant — not skip it because it seems unlikely.

### Phase 2: Go Look — Query Every Relevant Source

For each source you identified as relevant:

1. **Run the actual query.** Not "I think this is what it would show" — run it.
2. **Record exactly what you found.** Copy the actual data, the actual values, the actual error messages.
3. **Record where you found it.** File path and line number. Dashboard name and insight ID. API endpoint and response. The specific git commit.
4. **Record what you DIDN'T find.** If you searched and it wasn't there, that's data too.

**Do not paraphrase data.** If the error message says "NSLS API returned error status: 502", report that exact string. Don't say "the API had an error."

**Do not infer from screenshots.** If a screenshot shows a timestamp that says "5 minutes ago," you don't know if that means "created 5 minutes ago" or "last updated 5 minutes ago" or "last fired 5 minutes ago." Say what the screenshot shows and what you can't determine from it.

### Phase 3: Follow Threads — Go Deeper Where It Matters

During Phase 2, some findings will open new questions. Follow them:

- A PostHog event shows an error → grep the codebase for that error string → find the code path → check git blame for when it was introduced
- A user reports stuck progress → check their PostHog events → check their session state → check their responses → check for version crossing issues
- A config field shows an unexpected value → check who set it → check if it was overridden → check if there's a migration that changed it

**The thread-following rule:** When you find something that raises a new question, pursue it immediately — don't note it for later. The answer to the first question often depends on the answer to the second.

### Phase 4: Synthesize — What Does This Mean Together?

Only after you've gathered actual evidence from actual sources:

1. **State what you know and how you know it.** "PostHog shows 3 session_lifecycle events for this user (query: [specific HogQL]). The most recent was at 2026-04-03T14:22:00Z with action=complete."
2. **State what you don't know and why.** "I can't determine whether the magic link was clicked because customer.io MCP auth is currently broken. The data would be in their message history."
3. **State your interpretation separately from the facts.** "Based on the 502 from NSLS API at 15:42 and the Neon cold start confirmed on Mar 29, this is consistent with a cold start failure. But I haven't confirmed the Neon compute state at that exact timestamp."
4. **Flag contradictions.** If two sources disagree, say so. Don't silently pick the one that fits your narrative.

## The Wide Net Principle

**Breadth first, depth second, synthesis third.**

This is the same pattern as /full-shape (dimensions of a concept) and /data-intel (data sources for intelligence), applied to truth-finding:

- **Breadth:** Identify all sources. Consider every dimension of the question. Don't assume you know where the answer lives.
- **Depth:** For each relevant source, go deep enough to get the actual data. Don't stop at the summary level.
- **Synthesis:** Weave the findings together. The answer is almost never in a single source — it's in the pattern across sources.

The failure you're preventing: looking at one source, finding a plausible answer, and stopping. The answer in one source might be contradicted by another. The thing that looks like a bug in the code might be correct behavior documented in a GitHub issue. The user who "never completed onboarding" might have a CompletedTrack record that tells a different story.

## Reporting Format

Every investigation report must include:

### 1. Sources Checked
List every source you actually queried, with specifics:
- "PostHog: ran HogQL query for session_lifecycle events filtered to user X (last 30 days)"
- "Codebase: grepped for hubSpotId across all files (15 matches in 6 files)"
- "GitHub: searched issues for 'high school' (2 results: #358, #359)"
- "Memory files: read active-work.md, posthog-analytics.md"

### 2. Findings (Facts)
What the data actually shows. No interpretation. Direct quotes, exact values, specific timestamps.

### 3. Sources NOT Checked (and why)
- "Did not check customer.io — auth is broken (known issue)"
- "Did not check Vercel build logs — not relevant to this question"
- "Did not check HubSpot — MCP not yet authenticated"

### 4. Interpretation
What you think this means, clearly labeled as interpretation. Include confidence level and what would change your mind.

### 5. Open Questions
What you still don't know. What would resolve it. What to check next.

## Anti-Patterns (Things That Have Actually Gone Wrong)

| Anti-Pattern | What Happened | The Rule |
|-------------|---------------|----------|
| **Guessing from error names** | Saw $exception alerts, guessed "browser extension noise" without querying PostHog. Team saw this. | Query first. Name the exact errors you found. |
| **Fabricating timelines** | Claimed alerts were "just created" based on a "5 minutes ago" label. Didn't verify creation time. | Don't infer from relative timestamps. Check the actual creation timestamp. |
| **Inferring from screenshots** | Assumed a PostHog screenshot showed current state. It showed cached/stale data. | Ask for fresh queries. Screenshots are frozen moments. |
| **Stopping at the first answer** | Found one plausible explanation, presented it as fact. A second source would have contradicted it. | Always check at least 2 independent sources for any important claim. |
| **Presenting hypotheses as conclusions** | "The issue is X" when it should have been "This is consistent with X, but I haven't ruled out Y." | Separate facts from interpretation. Always. |

## When Speed Matters (Incidents)

During active incidents, the temptation to skip verification is highest. This is when it matters most.

**Incident protocol:**
1. Say "Investigating now" — do NOT guess
2. Run the fastest diagnostic queries first (PostHog event counts, error rates)
3. Report raw numbers immediately: "I see 47 $exception events in the last hour. Checking details now."
4. Follow up with specifics as you find them
5. Never say "it's fine" or "it's just X" until you've actually confirmed it

The team would rather hear "I'm checking" than a wrong answer delivered confidently.

## The Fractal

This skill is an instance of the pattern it describes. It was created because the same failure mode (confident claims without verification) kept appearing in different contexts — debugging, analytics, incident response, data exploration. The specific anti-patterns listed above are real incidents, not hypotheticals. Each one taught a rule. The rules are the skill.

The same wide-net → deep-dive → synthesis pattern appears in /full-shape (conceptual) and /data-intel (analytical). /investigation is the truth-finding instance. All three are the same pattern: don't assume you know what matters. Go look at everything. Let the evidence tell you.
