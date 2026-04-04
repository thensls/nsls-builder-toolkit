---
name: skill-creation
description: >-
  Use when you've just finished a complex, multi-step process with Claude
  Code and realize it could be a template others can follow. The experience
  is fresh, the micro details are still in context, the pattern is visible.
  This skill codifies the rubric for building skills that find their full
  shape — safety, purpose, diagnostic loops, cross-system awareness, and
  the micro/macro synthesis at every level.
---

# /skill-creation — The Rubric

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (reading existing skills, analyzing patterns, researching MCP packages) — runs without friction.
2. **Configuration** (creating new skill files, modifying SKILL.md content) — ask permission, explain what will be created and where.
3. **Write to external systems** — never proactively offered. If explicitly requested: explain the risks, confirm, then proceed.

## Purpose

This skill codifies the fractal pattern that emerged from building `/data-intel`, `/connect`, `/slack`, and every other skill in this toolkit. Every well-built skill follows the same structure. This skill makes that structure followable by anyone — so the next person building a skill doesn't have to discover the pattern from scratch.

Every skill in the toolkit is an instance of this pattern — `/connect`, `/data-intel`, `/slack`, all of them. This skill codifies the pattern itself. And even this list of elements is not exhaustive — the rubric invites you to discover what's missing, not just follow what's here.

## The Pattern

Every skill that finds its full shape has these elements. Not every element applies to every skill — but every element should be consciously considered.

### 1. Safety Block (FIRST SECTION — always)

Adapt the three-tier permission model to the skill's domain. See the safety block at the top of this skill (or `/connect` for a detailed example). The safety block goes FIRST — before purpose, before content, before anything. It sets the behavioral contract for the entire skill. Each tier should name the specific operations that fall into it for THIS skill's domain.

### 2. Purpose (the soul)

One paragraph that says why this skill is alive — not just what it does, but what makes it more than a reference doc. What intelligence does it create that didn't exist before?

Bad: "Query PostHog analytics."
Good: "Makes PostHog's full analytical power accessible through conversation — not just running queries, but knowing which queries to run, what the results mean, and what to try next when the data doesn't look right."

The purpose statement is where the skill declares its reason to exist.

### 3. Trigger Moment (the frontmatter description)

The frontmatter `description:` field determines WHEN Claude invokes the skill. It should capture the moment — not summarize the workflow.

Bad: "Step 1: detect connections. Step 2: configure MCP. Step 3: verify."
Good: "Use when a skill says its tools aren't available, when MCP tools aren't loading, or when you want to add a new system."

The skill body describes HOW. The frontmatter description captures WHEN. Claude reads the description to decide whether to invoke the skill — if the description contains how-to steps, Claude may follow the description instead of reading the full SKILL.md.

### 4. Macro/Micro Synthesis

Every skill delivers both the big picture AND the grounding details. Macro without micro is a dashboard. Micro without macro is an anecdote. The synthesis — where the whole is greater than the sum of its parts — is intelligence.

What micro looks like depends on the domain:
- `/data-intel`: user quotes, individual engagement patterns, specific error reasons
- `/connect`: exact config JSON blocks, specific env var names, the precise error message from a failed MCP startup
- `/posthog`: HogQL dialect gotchas, property name casing, the FunnelsQuery OR limitation
- `/slack`: channel names, reaction emoji patterns, who said what
- `/skill-creation`: this list you're reading right now — concrete examples from real skills

### 5. Domain-Specific Micro

The deep, hard-won details that are unique to this skill's domain. These can't be invented — they come from actually using the system and hitting walls.

Examples of domain micro that can only come from real experience:
- PostHog's `$host` is null on server-side events (you discover this when your funnel returns 0 rows)
- n8n's tool names have an `n8n_` prefix (you discover this when your predicted permission entries don't match)
- Slack's first-party OAuth connector silently fails in VS Code (you discover this by sitting there for 10 minutes watching nothing happen)
- Customer.io's `opened` metric is inflated by email client pre-fetches (you discover this when open rates look impossibly high)

You can't write good domain micro from documentation alone. You have to use the system, fail, diagnose, and learn. That's why the best time to build a skill is right after you've been through that process.

### 6. Service Awareness (the hierarchy)

Every skill exists in a hierarchy:

```
/connect          → provides the connections
  /posthog        → deep PostHog expertise
  /slack          → deep Slack expertise
  /customerio     → deep Customer.io expertise
  /n8n            → deep n8n expertise
  /airtable       → deep Airtable expertise
  /braintrust-evals → deep Braintrust expertise
/data-intel       → orchestrates across ALL connected systems
/skill-creation   → the rubric that all skills follow
```

Every domain skill should:
- Reference `/connect` for setup: "If tools aren't available, run `/connect`"
- Reference `/data-intel` for cross-system intelligence: "For cross-system analysis, use `/data-intel`"
- Never duplicate setup instructions that belong in `/connect`
- Never duplicate cross-system orchestration that belongs in `/data-intel`

Setup → `/connect`. Domain expertise → individual skill. Cross-system intelligence → `/data-intel`. Respect the hierarchy.

### 7. Diagnostic Loop

**TRY → OBSERVE → DIAGNOSE → ADAPT → TRY AGAIN**

Every skill that interacts with external systems should have a diagnostic loop for when things don't work. Not a static troubleshooting FAQ — a live reasoning process.

The loop's character varies by domain:
- `/connect`: connection loop — try auth method → silent failure → diagnose environment → try different package
- `/data-intel`: query loop — run query → unexpected results → check filters → broaden → re-query
- `/posthog`: same as data-intel, plus HogQL-specific diagnostics
- `/n8n`: workflow loop — validate → find error → fix config → re-validate → test
- `/braintrust-evals`: eval loop — run experiment → low scores → check schema alignment → adjust → re-run
- `/slack`: search loop — channel not visible → try direct access → bot not invited → explain how to invite

The loop should never let the user stare at a screen that does nothing. It should never let them give up. There is always a path through.

### 8. Output Guidelines

Every skill should say how to format output for different audiences:
- Leadership wants narratives and decisions
- Engineering wants technical depth and reproducibility
- Marketing wants target lists and performance comparisons
- The board wants trends and revenue impact

Also: PII awareness, sample size warnings, source attribution when cross-referencing.

## Discovering the Full Shape

Before writing a skill, explore broadly at every level. The elements above are the columns (so far — you may discover more). The skill-creation process is about finding all the ROWS and all the CELLS.

For each element: cast the net wide. Find multiple examples. Each example is a seed. The more seeds you gather, the more complete the row. This is the micro/macro synthesis applied to the creation process itself — you can't write the macro (the pattern) until you've excavated enough micro (specific examples, edge cases, gotchas, things that surprised you).

The discovery IS the work. The breadth of the net determines the quality of the skill.

**How to know you've found the full shape:**
- Every element has been consciously considered (even if some don't apply)
- The domain micro comes from real experience, not documentation
- The diagnostic loop covers the actual failure modes you've encountered
- The cross-references point to the right skills in the hierarchy
- Setup lives in `/connect`, not duplicated in the skill
- The frontmatter description captures when to invoke, not how to use
- Someone who has never used this system could follow the skill and get real results

## The Fractal

The elements above are not a complete list. They're what emerged from the skills built so far. The next skill you build may reveal an element that isn't here yet — and that's by design. The rubric grows by being used.

The discipline is maintaining awareness of the whole web while working on any individual node — not losing sight of one level while focused on another. The pendulum swing between building the macro framework and testing it with micro examples IS the creation process. The system produces and maintains itself as a byproduct of doing the work.

## Practical Checklist

When building a new skill right now:

1. **Start with the experience.** What did you just do? What walls did you hit? What did you learn that isn't obvious?
2. **Draft the frontmatter.** Name and description. The description captures WHEN to invoke.
3. **Write the safety block FIRST.** Adapt the three-tier model to this domain. What's read-only? What's configuration? What's destructive?
4. **Write the purpose.** One paragraph. Why is this skill alive?
5. **Pour in the domain micro.** Every gotcha, every failure, every non-obvious detail. This is the hard-won knowledge that makes the skill valuable.
6. **Structure the macro.** Organize the micro into sections that tell a coherent story.
7. **Add the diagnostic loop.** What goes wrong? What do you try? What's the next thing after that?
8. **Add output guidelines.** Who will read this output? What do they need?
9. **Wire up the hierarchy.** Reference `/connect` for setup, `/data-intel` for cross-system, other domain skills for related expertise.
10. **Check the full shape.** Walk through every element in The Pattern. Is anything missing? Is anything duplicated from another skill? Did you discover a new element that should be added to the rubric?
