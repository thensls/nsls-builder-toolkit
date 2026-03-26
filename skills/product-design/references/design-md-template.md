# DESIGN.md Template

Use this template when generating a DESIGN.md for an automation repo. Walk the builder through each section via guided conversation, then output the populated file.

---

```markdown
# [Automation Name]

## What This Is (for the user)

<!-- Write 2-3 sentences describing the experience from the user's perspective.
     No technical details. No system names. Written so someone outside the org
     could understand what this does for them. -->

## Customers

<!-- Define each customer segment separately. An automation can serve multiple
     segments with different flows. Each segment gets its own subsection.
     Focus groups pull personas from these segments. -->

### [Segment Name] ([count] people)
- **Who**: Description of this group — role, tech comfort, characteristics
- **Context**: When and how they encounter this automation, their mindset at that moment
- **Flows**: Which specific interactions they use

### [Another Segment] ([count] people)
- **Who**: ...
- **Context**: ...
- **Flows**: ...

## UX Principles

<!-- Numbered rules that every proposed change gets evaluated against.
     Each principle must be specific enough to produce a yes/no judgment
     about a proposed change. Focus on what the user experiences, not
     technical implementation. Aim for 4-7 principles. -->

1. [Principle about interaction simplicity]
2. [Principle about time/effort required]
3. [Principle about language and clarity]
4. [Principle about error handling from user's perspective]
5. [Principle about emotional tone]

## What This Should NOT Become

<!-- Explicit guardrails against scope creep. Name the anti-patterns.
     Write as things this automation must never turn into — not technical
     constraints, but experience-level boundaries. -->

- [Anti-pattern that would change the nature of the experience]
- [Feature that seems helpful but would add unwanted complexity]
- [Adjacent purpose that should be a separate automation]

## Interaction Surface

<!-- Where and how the user touches this automation. Be specific. -->

- **Channel**: Where the user interacts (Slack DM, Slack channel, email, web, etc.)
- **Trigger**: What kicks off the interaction (scheduled, user-initiated, event-driven)
- **User actions**: What the user actually does (reply, click, fill in, choose)
- **Output the user sees**: What comes back to them (confirmation, summary, link, etc.)

## Measuring Success

### Adoption
- **What "adopted" looks like**: [Concrete behavior that indicates real usage, not just compliance]
- **Current adoption**: [X of Y target users — update periodically]
- **Adoption goal**: [Target number within timeframe]

### Satisfaction
- **How we'll know**: [Observable signals that users find this valuable vs. annoying]
- **Signals to watch**: [Specific metrics: response rate, time-to-complete, opt-out rate, unsolicited feedback]
- **Red flags**: [What would tell us this isn't working — be specific]

## Change Log

| Date | Change | Reviewed |
|------|--------|----------|
| YYYY-MM-DD | Initial design intent | [Name] |
```

---

## Worked Example: Quick Notes Weekly Journal

```markdown
# Quick Notes Weekly Journal

## What This Is (for the user)
Every Friday, the bot asks you a few simple questions about your week.
You answer in Slack. It writes a journal entry and links it to your ScoreCard.

## Customers

### All Employees (~60 people)
- **Who**: Everyone at NSLS, mixed tech comfort, many non-technical
- **Context**: End of a busy week, low patience for friction
- **Flows**: Friday journal prompt, ScoreCard link

### Managers (~12 people)
- **Who**: Department managers, comfortable with Slack, moderate tech comfort
- **Context**: Need visibility into their team without adding work for reports
- **Flows**: (future) Team digest, review nudges

### SLT (6 people)
- **Who**: Senior leadership, time-constrained, high expectations for signal-to-noise
- **Context**: Strategic focus, want summaries not raw data
- **Flows**: (future) L3 goal updates, coaching prompts

## UX Principles
1. One question at a time — never a wall of text
2. Answering should take under 3 minutes total
3. No jargon, no internal system names surfaced to the user
4. If something fails, the user should never see an error — retry silently or escalate to Kevin
5. The bot should feel like a friendly colleague, not a form

## What This Should NOT Become
- A performance review tool
- Something that requires training to use
- A multi-step wizard with branching logic
- Anything that makes Friday afternoons feel heavier

## Interaction Surface
- **Channel**: Slack DM
- **Trigger**: Scheduled Friday reminder
- **User actions**: Reply to prompts in natural language
- **Output the user sees**: Confirmation message with link to their journal

## Measuring Success

### Adoption
- **What "adopted" looks like**: Employee completes their Friday journal at least 3 out of 4 weeks
- **Current adoption**: 45 of 60 employees responding weekly
- **Adoption goal**: 50+ within 90 days of full rollout

### Satisfaction
- **How we'll know**: Employees respond promptly (within 2 hours of prompt), don't ask "how do I use this?", occasionally give unsolicited positive feedback
- **Signals to watch**: Response rate per week, average time from prompt to completion, number of support questions
- **Red flags**: Response rate drops below 60%, multiple employees asking the same "how do I..." question, employees asking to opt out

## Change Log
| Date | Change | Reviewed |
|------|--------|----------|
| 2026-03-25 | Initial design intent | Kevin |
```
