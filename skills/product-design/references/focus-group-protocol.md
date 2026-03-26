# Focus Group Protocol

Run simulated focus groups with personas dynamically generated from DESIGN.md customer segments. This protocol replaces hardcoded persona panels with segment-specific persona generation.

## Step 1: Read Customer Segments

Read the Customers section from the repo's DESIGN.md. Each segment defines:
- Who they are
- Their context when encountering the automation
- Which flows they use

Only include segments affected by the proposed change. If a change affects the Friday journal prompt, include All Employees but not necessarily Managers (unless their flow is also changing).

## Step 2: Generate Personas

For each affected segment, generate 3-5 personas that span the diversity within that group.

### Attributes to Vary

- **Tech comfort**: from "struggles with Slack" to "could build this themselves"
- **Tenure**: new employee to long-tenured
- **Attitude**: enthusiastic adopter, neutral complier, quiet skeptic
- **Role specifics**: varies by department, team size, workload

### Persona Format

Each persona gets:
- **Name and role** (e.g., "Sofia Reyes — Content Strategist, Marketing")
- **Context quote**: One sentence capturing their mindset (e.g., "I have too much to report and no clear framework for what's important enough")
- **Relationship to automation**: How they currently use it, what they think of it

### Scope-Specific Guidance

**Internal: All Employees** — vary by department, tenure, tech comfort. Include at least one person who actively resists new tools and one who champions them.

**Internal: Managers** — vary by team size, management style, trust level. Include someone who sees the tool as useful for their 1:1s and someone who sees it as administrative overhead.

**Internal: SLT** — vary by strategic focus, time pressure, change fatigue. Include someone protective of their team and someone focused on data visibility.

**Customer Facing: Advisors** — school professionals managing many students. Vary by school size (small private vs. large state university), tech comfort, years in role, workload intensity. They expect polished, professional tools and have low tolerance for confusion. They didn't choose this tool — it was provided to them.

**Customer Facing: Members** — college students. Vary by year in school, engagement level with NSLS, device preference (mobile-first), familiarity with the platform. They expect consumer-app quality. If friction is high, they abandon rather than complain. They compare everything to Instagram, Venmo, and Canvas.

## Step 3: Present the Proposed Change

Before running the panel, clearly state:
- **What changes**: specific description of the proposed change
- **Who it affects**: which customer segments
- **Before vs. after**: what the experience looks like now vs. what it would look like

## Step 4: Run the Panel

For each persona, capture:
- **Gut reaction**: immediate emotional response
- **Friction points**: what's confusing, off-putting, or adds unwanted complexity
- **Predicted behavior**: would they engage fully, comply minimally, or quietly drift away?
- **One question**: what they'd need answered before accepting this change

Group responses by segment. Personas in later segments may reference earlier segments' reactions when it's natural (e.g., a manager thinking about how their team would react).

## Step 5: Synthesize

After all personas have spoken:

**Cross-segment agreement**: What did all segments flag? These are high-confidence findings.

**Cross-segment divergence**: Where do segments disagree? These reveal trade-offs — a change that helps managers might annoy ICs, or vice versa.

**UX principle check**: Map findings back to the numbered UX principles in DESIGN.md. Which principles did the panel flag as at risk?

## Step 6: Produce the Report

```markdown
## Focus Group Report: [Proposed Change]

### Panel Composition

**[Segment Name]** (N personas)
- **[Name]** — [Role] — "[Context quote]"
- ...

### Reactions by Segment

#### [Segment Name]
- **[Name]**: [Gut reaction]. [Friction]. [Predicted behavior: engage/comply/drift].
  - Question: "[Their question]"
- ...

### Cross-Segment Synthesis
- **Agreement**: [What all segments flagged]
- **Divergence**: [Where segments disagree and why — name the trade-off]

### Risk Flags
- UX Principle #N: [Specific principle text] — [How the proposed change threatens it]
- ...

### Suggestions
1. [Alternative approach] — [Why it addresses the panel's concerns]
2. ...

### Verdict
[One of: Proceed as-is / Modify (with specifics) / Rethink]
[One sentence explaining the reasoning]
```

The report is conversational by default. If the builder asks, append a summary to DESIGN.md's change log.
