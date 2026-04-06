---
name: data-model-discovery
description: >-
  Use when a new data source has been connected and you need to understand
  what's in it, how it maps to what you already have, and where the join
  keys are. The systematic process of exploring an unknown system, mapping
  its objects and properties, discovering what it knows that nothing else
  does, and integrating it into the skill architecture. Every new MCP
  connection should trigger this. The output is a landscape doc, a platform
  skill, and updated cross-platform templates in /data-intel.
  Trigger phrases: new data source, what's in hubspot, explore this system,
  map the data, find the join keys, what properties exist, data model,
  landscape, discover what's there, connect and explore.
---

# /data-model-discovery — Map What's There

## Purpose

Every time a new system gets connected, someone has to answer the same questions: What objects exist? What properties matter? What does this system know that nothing else does? How does it connect to what we already have? What are the join keys?

This skill is that process, codified. It was born from the HubSpot exploration session (Apr 5, 2026) where we connected HubSpot, discovered 6.9M contacts with IPEDS numbers that partially solved an open GitHub issue, mapped 27 deal pipelines nobody had documented, and found 357K support tickets that are the voice of the customer at a scale no other system captures.

The failure mode it prevents: connecting a new system and then only using 5% of it because nobody mapped what's actually there.

## When to Trigger

- A new MCP connection was just established via `/connect`
- Someone says "what's in [system]?" or "can we use [system] for X?"
- A new data source appears in the toolkit and nobody has explored it yet
- You're building a cross-platform query and realize you don't know what the other system's properties look like

## The Process

### Phase 1: Authentication & Access Audit

Before exploring data, establish what you can do.

1. **Confirm the connection works.** Call the system's equivalent of "get me" or "list objects" — whatever proves the tools are live.
2. **Document the access level.** Read-only? Read-write? Which object types are available? Are any blocked or require reauthorization?
3. **Record the account identity.** Who is authenticated? What org/account? This matters for understanding what data is visible.

**Output:** One paragraph in the landscape doc. Auth status, access level, account identity.

### Phase 2: Object Discovery

Cast the widest net. Don't assume you know what matters.

1. **List all object types.** Every CRM has contacts/companies/deals. But what ELSE? Custom objects? Tickets? Subscriptions? Products? The unexpected object types are often the most valuable.
2. **Count everything.** Raw counts tell you where the data mass is. 6.9M contacts vs 11K companies tells a different story than 50K contacts vs 500K companies.
3. **Sample each object type.** Pull 3-5 records with default properties. Don't filter. See what the system returns by default — this reveals what the system considers important.

**Output:** Object type table with counts and descriptions.

### Phase 3: Property Discovery

This is where the gold is. Every system has standard properties AND custom properties. The custom ones are where the org's specific knowledge lives.

1. **Search for org-specific properties.** Use the org name, product names, internal jargon as keywords. For NSLS: "nsls", "chapter", "feather", "induction", "enrollment".
2. **Search for integration properties.** Look for IDs from other systems — Stripe IDs, Drupal IDs, Salesforce migration artifacts, IPEDS numbers. These are join keys waiting to be found.
3. **Categorize what you find.** Group properties by domain: identity, academic, lifecycle, financial, engagement, etc. This structure becomes the platform skill's property reference.
4. **Note what's sparse.** Not all properties are populated on all records. A property that exists on 3% of contacts is different from one on 95%.

**Output:** Categorized property inventory with descriptions and sparsity notes.

### Phase 4: Relationship Mapping

How does this system connect to everything else? Map discoveries against `/system-of-record` to identify which SoR domains the new data covers.

1. **Find the join keys.** Email is almost always one. But look for direct ID bridges (like Society's `hubSpotId` → HubSpot's `hs_object_id`), legacy IDs (like `nsls_uid` → Feather), and institutional IDs (like `unitid` → IPEDS).
2. **Map to existing systems.** For each join key, trace it: where does it come from? Where is it stored? Is it actively maintained or a write-once artifact?
3. **Identify what this system knows that nothing else does.** This is the unique value. HubSpot has pre-Society lifecycle data. PostHog has real-time behavioral data. The unique data is why this system matters.
4. **Identify what's duplicated.** If two systems both have "school name" but in different formats, that's a reconciliation problem to flag.

**Output:** Join key table + "what's unique to this system" section.

### Phase 5: Pipeline & Workflow Discovery

Many systems have structured workflows (pipelines, stages, funnels, sequences). These encode business processes that may not be documented anywhere else.

1. **List all pipelines/workflows.** In HubSpot: deal pipelines. In n8n: workflow definitions. In customer.io: campaign sequences.
2. **Document the stages.** What are the steps? What do the stage names mean in NSLS context?
3. **Note who owns what.** Team accounts, automated systems, individual owners — the ownership structure reveals organizational topology.

**Output:** Pipeline/workflow inventory with stages and ownership.

### Phase 6: Cross-Reference with Open Work

Check if what you found addresses any existing needs.

1. **Scan open GitHub issues.** Does any discovered data solve or partially solve an open issue?
2. **Check the roadmap.** Does any discovered data unblock a planned feature?
3. **Identify the biggest gap.** What integration issue SHOULD exist but doesn't?

**Output:** Issue map linking discoveries to open work.

### Phase 7: Artifact Creation

The exploration produces three artifacts:

1. **Landscape doc** (`~/.claude/memory/{system}-landscape.md`) — reference memory file with everything discovered: object types, property inventory, join keys, pipelines, unique data.

2. **Platform skill** (`~/.claude/skills/{system}/SKILL.md`) — following the builder toolkit pattern: safety tiers, purpose, MCP tools, properties, diagnostic loop, gotchas. References `/connect` for setup and `/data-intel` for cross-system intelligence.

3. **Data-intel integration** — update `/data-intel` with:
   - New row in the connected systems table
   - Cross-platform query templates showing how to join this system with existing ones
   - New value streams if the discovered data enables them

## Diagnostic Loop

When exploration hits walls:

1. **Property search returns nothing?** Try different keywords. Every org names things differently. Search for the concept, not the expected field name.
2. **Objects seem empty?** Check if you need to request specific properties. Many APIs return minimal default fields.
3. **Counts seem wrong?** Check if there's a filter you didn't notice. Some APIs default to "my records" not "all records."
4. **Can't find the join key?** It might not be a property — it might be an association. Check object relationships, not just properties.
5. **System has too many properties to read?** Search by keyword batches (max 5 per call for HubSpot). Don't try to read everything at once.

## Output Format

The final report to the user should include:

### 1. The Numbers
Object types, counts, scale context.

### 2. The Gold
What this system knows that nothing else does. The specific properties, the unique data, the join keys found.

### 3. The Connections
How it maps to existing systems. Join key table. What's bridged, what's not.

### 4. The Immediate Wins
Open issues that are partially solved. Features that could be accelerated. Data that was assumed missing but actually exists.

### 5. The Artifacts Created
Links to landscape doc, platform skill, data-intel updates.

## The Pattern

This skill is an instance of the same fractal that runs through `/full-shape`, `/investigation`, and `/data-intel`:

**Breadth first** — explore every object type, every property category, every pipeline. Don't assume you know what matters.

**Depth second** — when you find something (IPEDS numbers on 88% of schools, 357K support tickets, Feather sync artifacts), follow it all the way down.

**Synthesis third** — weave the findings into the existing system: landscape doc, platform skill, data-intel integration, issue map.

The output of this skill is not just knowledge — it's infrastructure. Every run produces artifacts that make the entire skill system more capable.
