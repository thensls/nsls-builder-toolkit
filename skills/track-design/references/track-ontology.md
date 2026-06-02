# Track Ontology & Design Framework

A distilled, builder-facing reference for designing Society tracks. Based on "How Tracks Work — A plain-language guide to the Society track model."

---

## The Three Levels

| Level | One-line job |
|-------|-------------|
| **Track** | Deliver a named value promise to the student |
| **Step** | Group related substeps into a themed chapter of accomplishment |
| **Substep** | Present a single screen — one interaction |

Everything nests: a Track contains Steps; a Step contains Substeps.

---

## Tracks

**A track is a value promise.** Before designing anything, complete this sentence:

> "When a student finishes this track, they will have __________ that they didn't have before."

If you can't answer that clearly, the track isn't ready to design.

**What a track contains:**
- Title and description (student-facing)
- Ordered list of steps
- Entry and completion behaviors (messages, triggers)
- Status: active / locked (requires prerequisites) / coming soon

**Tracks are sequential.** Steps must be completed in order. Each step's output is raw material for later steps — skipping breaks the chain.

**Tracks can have dependencies (prerequisites).** A track can require completion of another track before it unlocks. Example: a Connections Track requires Clarity Track completion, because personalized introductions require a populated profile to personalize against.

---

## Steps

**A step is a themed chapter — the unit of accomplishment.** When a student finishes a step, they've done something worth celebrating.

> The Strengths step: you now know your top 3 strengths, named and added to your profile.
> The Values step: you now know your 6 core values, arrived at through real prioritization.

**What a step contains:**
- Title and description
- Optional entry message (what the coach says when the student arrives)
- Completion message / celebration screen (summary of what was accomplished)
- Ordered list of substeps
- Status: active or inactive

**The single-theme rule.** A well-designed step has one clear theme. The student should be able to answer "what was that step about?" in one sentence. If the answer needs "and also..." — the step is doing too much.

**The 4-part arc.** Every step should follow this structure:

| Phase | What happens |
|-------|-------------|
| **Orient** | One SAY substep explaining what this step is and why it matters |
| **Collect / Explore** | The core COLLECT substeps — aim for 4–8 questions; 10+ without a break risks fatigue |
| **Synthesize** | A GENERATE or CHAT substep that reflects back what was learned |
| **Celebrate** | A celebration SAY substep naming what was accomplished and previewing what comes next |

---

## Substeps

**A substep is a single screen — one interaction.** Every question asked, every message shown, every selection made, every AI response generated happens at the substep level.

Two properties define a substep's behavior: **type** (the mode) and **field type** (the UI format).

### The Three Modes (Types)

**SAY** — A content page. The student reads; no input required. Content can be:
1. Written by a person (static copy)
2. Written by a person with `{tokens}` inserted from the student profile (personalized copy)
3. Generated entirely by AI using profile data in the prompt (**GENERATE** — see below)

Used for: orientation banners, celebration screens, assessment results displays, AI-generated summaries, transition messages.

**COLLECT** — The student provides input; the platform captures and stores it to the profile. Used for: free-response text, single-choice selects, multi-selects, image-choice questions, currency inputs, education/work history, dream job selection.

**CHAT** — An open coaching conversation. The AI responds in real time with the student's full profile context loaded via a system prompt. Used for: post-assessment reflection, deepening a topic, open-ended coaching at the end of a step.

### GENERATE (AI-authored SAY)

GENERATE is a SAY substep where the content is written by AI in real time, using profile data in the generation prompt. The student reads the result and can accept, refine, or discuss it.

**Design principle:** The AI generates; the student judges. Never present AI output as final.
- Weak: "Here is your career statement." (implies it's done)
- Strong: "Here is a draft of your career statement — how does it feel to read it?" (invites ownership)

### Generate-then-Select Pattern

Some COLLECT substeps use AI to generate the list of options the student picks from, rather than a fixed list. The platform synthesizes personalized options from prior answers, then the student chooses.

Examples: strength archetypes (from six free-response answers + personality results), inspiration archetypes, dream job cards.

**Why this matters:**
- A fixed list produces **self-reporting bias** — students pick what sounds good.
- An AI-generated list produces **recognition** — students pick what feels true.

The difference: "which of these am I?" vs. "yes, that's me."

### Field Types (UI format)

| Field type | What it does |
|------------|-------------|
| Text (free response) | Student types anything. Best for open-ended reflection. |
| Select (single choice) | Student picks one option. Mutually exclusive choices. |
| Multi-select | Student picks multiple options. Values, strengths, interests. |
| Image multiselect | Binary visual choice — two illustrated options. Personality assessment. |
| Dropdown with checkboxes | Select with layered responses. Self-assessment questions. |
| Currency | Dollar amount input. Financial needs. |
| Education | Structured degree history and enrollment status. |
| Work | Structured work history and experience. |
| Dream job select | Card-based UI with AI-generated job options and expandable details. |
| Dream job requirements | Card-based UI with AI-generated requirements + student self-assessment. |
| Assessment results | Displays computed output of a multi-question assessment. |
| Celebration | Full-screen milestone screen with confetti, accomplishment summary, call to action. |
| Banner | Full-screen orientation/transition message. No input. |

---

## Personalization: The `{slug}` Token Pattern

**Tokens are `{slug}` placeholders** in any prompt, callout, or AI instruction. When the substep loads, the platform substitutes the student's actual profile value.

```
{name}        → Marcus
{major}       → Agriculture Science
{dream-job-selection} → Health-Equity UX Researcher
```

**Where tokens can appear:**
- Main prompt text of any substep (what the student reads)
- Callout text (supporting context alongside the prompt)
- AI system prompt for CHAT substeps (the invisible coach briefing)
- AI generation prompt for GENERATE substeps (the instruction that produces AI content)
- Celebration screen copy (summarizing what was captured)
- Entry and completion messages for steps and tracks

**The hard rule: a token cannot reference data not yet collected.**

A `{dream-job-selection}` token will be empty if the student hasn't reached the Dream Job step. Good track design ensures every token appears only downstream from where its field is captured. If Step 4 references `{strengths-selection}`, Step 2 must have collected it first.

Note: in practice, tokens appear most often inside CHAT and GENERATE system-prompt blobs rather than visible prompt text — but the ordering rule applies everywhere tokens appear.

---

## The AI's Three Roles & Design Principles

### 1. GENERATE — AI-authored content
The AI produces a draft; the student judges it. Frame every AI output as a starting point, not a conclusion.

### 2. Generate-then-Select — AI-generated options in COLLECT substeps
The AI synthesizes a personalized option list from what the student actually said. This produces recognition, not self-reporting bias. Fixed lists don't.

### 3. CHAT — Live coaching conversation
**Orient, don't constrain.** Give the student a clear starting point, but don't over-script the conversation.

**Inject profile data explicitly into the system prompt.** Don't assume the AI will infer context it wasn't given. A rich system prompt makes the difference between a generic response and one that says: "Marcus, given that your top value is Justice and your dream job is Health-Equity UX Research, the most important skill gap to close first is probably user interview technique."

CHAT is most valuable immediately after a reveal moment — when the student has just learned something new about themselves and is primed to reflect.

---

## The Student Profile

**The profile is the accumulating record** of everything a student has shared, generated, and selected across all tracks.

It serves two purposes simultaneously:

| For the student | For the AI coach |
|-----------------|-----------------|
| A mirror — a growing, organized representation of who they are and where they're headed | A briefing file — the context that makes every coaching conversation specific rather than generic |

**The profile grows over time.** A student who has only finished onboarding has name, age, location, education, and work experience. A student who has completed the full Clarity Track has 20+ fields populated.

**You can only use a token once its field exists.** A new track referencing `{career-statement}` requires the student to have completed the Clarity Track first.

### Common Profile Fields & Token Slugs

| Profile field | Token slug |
|---------------|-----------|
| Preferred name | `{name}` |
| Age | `{age}` |
| Major / field of study | `{major}` |
| Personality profile results | `{your-personality-profile}` |
| Top 3 strengths (selected) | `{strengths-selection}` |
| Top 3 inspirations (selected) | `{inspirations-selection}` |
| Top 6 values (final selection) | `{value-selection-3}` |
| Ideal work environment | `{work-environment-result}` |
| Ideal living environment | `{living-environment-result}` |
| Monthly expense target | `{monthly-target}` |
| Dream job selection | `{dream-job-selection}` |
| Dream job requirements | `{dream-job-requirements}` |
| Career statement | `{career-statement}` |

---

## The 6-Step "Designing a New Track" Framework

This is the design spine. Follow it in order.

### Step 1: Define the Value Promise

Write one sentence completing:

> "When a student finishes this track, they will have __________ that they didn't have before."

A vague value promise produces a vague experience. Don't proceed until this sentence is sharp.

### Step 2: Identify What the AI Coach Needs to Know

Ask: what information does the coach need to deliver on the value promise? That list is the data you must collect. Each major cluster of data becomes a candidate step.

### Step 3: Sequence the Steps Intentionally

Two sequencing rules:
1. **Simpler / factual before complex / reflective.** Students build trust and momentum before you ask for depth.
2. **Collect before you reference.** If Step 4 uses `{strengths-selection}`, Step 2 must have collected it.

### Step 4: Design Each Step's 4-Part Arc

For each step, build: Orient → Collect/Explore → Synthesize → Celebrate (see Step Arc above).

Aim for 4–8 COLLECT substeps per step. More than 10 without a synthesis break risks fatigue.

### Step 5: Write Substep Prompts with Personalization

For each substep prompt, ask:
- Is there already-collected profile data that would make this feel more specific? Use tokens.
- What new field does this substep produce, and what is its slug? Document every new field — it may be referenced in later substeps, AI prompts, or future tracks.

### Step 6: Design the AI System Prompts for CHAT Substeps

For every CHAT substep, the system prompt must include:
- Who the student is (name, relevant profile data via tokens)
- What just happened (which step was just completed, what was revealed)
- What the coach should focus on in this conversation
- What the coach should **not** do (e.g., don't re-ask questions already answered)

The system prompt is invisible to the student but is the single most important piece of content you will write for any CHAT substep.

---

## Quick-Reference Glossary

| Term | Definition |
|------|-----------|
| **Track** | A complete, named journey with a specific value promise. Contains multiple steps in sequence. |
| **Step** | A themed chapter within a track. Groups related substeps around a single topic. Has an entry message, substeps, and a celebration completion screen. |
| **Substep** | A single screen — one interaction. Has a type (SAY, COLLECT, CHAT) and a field type that controls its format. |
| **SAY** | A content page — text, image, or video presented to the student. No input required. Content can be static, personalized with tokens, or AI-generated (GENERATE). |
| **COLLECT** | Student provides input. Saves to the profile. Used for questions, selections, and assessments. |
| **CHAT** | Open AI coaching conversation. Coach receives full profile context via a system prompt. |
| **GENERATE** | A SAY substep where content is written by AI in real time using profile data. Student reads and reflects — never presented as final. |
| **Token** | A `{slug}` placeholder in any prompt text, replaced with the student's actual profile data when the substep loads. |
| **Profile** | The accumulating record of everything a student has shared, selected, and generated. Fuels personalization and AI coaching context. |
| **Field type** | The specific UI format of a substep (text, select, multi-select, currency, celebration, banner, etc.). |
| **Value promise** | The one-sentence outcome a track commits to delivering. The north star for all design decisions within the track. |
