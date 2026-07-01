---
name: value-moment
description: >-
  Use when authoring or improving a Society (ignite-next) learning track and you
  want to hand personalized value back to the member from data they already
  entered — turning a collected field (major, location, strengths, goal) into an
  insight nugget that teaches them something and pulls them deeper. Called by
  track-brief and track-design; also use directly to add or audit the value
  moments in an existing track. Triggers: "value moment", "insight nugget",
  "personalize this step", "make this field pay off", "what can we tell them
  after they enter X".
---

# value-moment

## Purpose

Every field a member fills in is an opening to hand value *back*. They tell us
their major — we can show them where that major leads. They tell us their state —
we can show them what changes if they're open to relocating. Done well, each
input visibly returns insight, so the member *wants* to keep going. This
sub-skill invents and ranks those moments for a track and emits them as authored
`generate` substeps. Its reason to exist is one hard rule most authors get wrong
under pressure: **a personalized insight is only valuable if it's true.** A
confident-sounding fabricated statistic doesn't build trust — it destroys the
exact trust the moment was meant to earn. This skill makes grounded the default
and makes ungrounded precision impossible to ship by accident.

## The faithfulness rule (the core constraint — read this first)

Every value-moment candidate MUST declare a `grounding`, and its
`prompt_template` MUST match that grounding. Three grounding levels, in
preference order:

- **grounded** — backed by a real data source (BLS OEWS by SOC/area, O*NET
  bright-outlook / growth, cost-of-living by metro, or a dataset we wire in). The
  real figures are supplied to the prompt as a `{data}` context payload; the
  prompt is instructed to *phrase* them, never to invent. **Preferred.**
- **model-reasoned** — qualitative and defensible from general knowledge
  ("marketing majors commonly move into brand, growth, and product roles").
  Allowed, but framed as general — **no precise statistics.**
- **illustrative** — explicitly framed as an example or estimate ("roughly," "as
  an illustration," "in many markets") when no source exists. Never a bare,
  false-precise number presented as fact.

**The bright line:** a specific number (a percentage, a salary, a growth rate, a
ranking like "fastest-growing") may appear ONLY at `grounded` level, sourced to
real data supplied to the prompt. If you cannot supply the figure from a real
source, the candidate is not `grounded` — drop the number and reframe as
model-reasoned or illustrative, or cut the candidate. This is non-negotiable.

**Violating the letter of this rule violates its spirit.** A number that is
"probably about right," "a reasonable estimate," or "close enough to feel real"
is a fabrication. Plausibility is not grounding.

**Grounded but misleading is still wrong.** A real figure aimed at the wrong
frame deceives too — e.g. showing the *marketing-manager* median salary to a
first-year student as if it were a starting wage. When you supply a real number,
supply the one that matches the claim, and label what it is (role, year,
national vs. local, entry vs. experienced). Right number, wrong framing = still a
broken promise.

### Red flags — STOP

- Writing a percentage, salary, or "fastest-growing / most in-demand" claim you
  cannot point to a real source for.
- Telling yourself "the number just makes it feel credible" — that is the harm,
  not the value.
- "I'll mark it grounded and we'll wire the data later" — if the data isn't
  supplied to the prompt, it is NOT grounded. Mark it grounded only when `{data}`
  is real.
- Asserting a market trend ("digital roles are where the demand is," "Columbus is
  a marketing hub") as established fact with no source — that is a claim, not a
  vibe. Ground it or hedge it.
- A `prompt_template` that says "use specific figures" without supplying them —
  you have just instructed the model to fabricate.

If you catch yourself at any of these: downgrade the grounding, remove the
number, or cut the candidate.

## When to use

- Inside **track-brief** (Track Template Brief → "Value moments" section) or
  **track-design** (Phase 2 shape / Phase 5 authoring).
- Standalone, to add value moments to an existing track or audit the ones it has.
- NOT for the track's core teaching content — this is specifically the
  personalized, data-returning nuggets.

## Inputs

1. The track's **collected fields up to point N** — the answers known by the time
   a nugget would fire, in order (from the Track Template Brief's "what
   information will be collected," or by reading the track JSON's `collect`
   substeps).
2. The **audience** + value promise.
3. Optionally the existing track JSON, to place nuggets between real steps.

## Process

1. **List the capture points in order.** For each collected field (and each
   useful combination), ask: *what could we truthfully tell the member the moment
   they've entered this?*
2. **Draft candidates.** For each, fill the candidate table (below). Assign a
   grounding honestly at this step — decide where the facts come from before
   writing the prompt.
3. **Apply the faithfulness rule to every candidate.** Any precise number that
   isn't `grounded` with real supplied data gets removed or the candidate
   reframed. This is a gate, not a polish pass.
4. **Rank** by expected value to the member × groundedness × pull-along strength
   (fires right after the relevant capture). Prefer grounded over clever.
5. **Give each a rendered `example_output`** so a human can judge the value
   before it ships. The example must obey its own grounding (no invented numbers
   in a model-reasoned example).
6. **Propose the top 3–5.** The author picks; this skill proposes, never
   auto-inserts. **This ranked list — each candidate with its `example_output`
   and `grounding` — is the deliverable when called from `track-brief`.** Stop
   here in that context: the track structure doesn't exist yet, so there is
   nothing to emit `generate` JSON into. The list becomes the Track Template
   Brief's "Value moments" section.
7. **Emit the approved ones** as `generate` substeps — **only in `track-design`
   (Phase 5) or standalone track-editing, where the track structure already
   exists.** Open `references/generate-substep-emission.md` and the track schema;
   never author the JSON from memory.

## The candidate (output shape)

| Field | Meaning |
|---|---|
| `trigger` | the data known by this point, as tokens (e.g. `{major}`, `{location}`, `{major}+{strengths}`) — must be collected earlier or a prerequisite profile token |
| `insight_type` | career-options, demand-growth, salary-by-geo, peer-comparison, strength→role fit, … |
| `placement` | after which step it fires (the pull-along moment) |
| `prompt_template` | the authored AI prompt, using `{tokens}`, that generates the paragraph — carries the grounding contract in its own words |
| `example_output` | a rendered example so a human can judge the value |
| `grounding` | **REQUIRED** — `grounded` / `model-reasoned` / `illustrative`, plus where the facts come from and the exact honesty framing |
| `value_dim` | which focus-group **Value** sub-check it targets (`value.a` "returns something useful," `value.c` "personalized to me") |

## Worked example (career-clarity)

- **trigger:** `{major}` captured step 1.
- **insight_type:** career-options + demand-growth.
- **placement:** immediately after the major capture (pull-along).
- **grounding:** grounded (future target) — top SOC codes for the major + O*NET
  growth outlook, supplied as a real data block. Until the companion tool exists,
  ground by pasting the real figures as literal text (cite the source); do NOT
  emit a `{data}` token — it isn't a supported/resolvable token yet (see
  `references/generate-substep-emission.md`).
- **prompt_template:** *"The member's major is {major}. Using ONLY these figures
  — [paste real BLS/O\*NET rows here, cited] — write two short paragraphs: (1) the
  three most common careers for this major; (2) the two with the fastest
  projected demand growth. Warm, specific, second-person. Use only the provided
  figures; if one is missing, describe the trend qualitatively and invent no
  number."*
- **example_output:** *(rendered from real data at review time)*
- **value_dim:** value.a + value.c.

Contrast — the SAME idea done wrong (do not ship): *"Marketing grads earn
~$63,000 and the field is growing 19% — fastest in Ohio."* No source is supplied,
so those numbers are fabricated. Either supply real BLS figures (→ grounded) or
cut the numbers: *"Marketing degrees open a wide range of roles, and demand for
data-and-digital marketing skills has been climbing"* (→ model-reasoned).

## Companion (future): a data-fetch tool

To make `grounded` the default, a small tool will pull real labor-market data
(BLS OEWS by SOC/area, O*NET bright-outlook/growth, cost-of-living by metro) and
hand it to the `generate` prompt as `{data}`. This sub-skill proposes *which*
data each nugget needs; the fetch tool supplies it. Out of scope to build here —
but design every grounded prompt to accept a supplied `{data}` payload so it
drops in cleanly when the tool lands. Until then, a grounded moment requires the
figures to be pasted in from a real source at authoring time (cite it), or it is
not grounded.

## How it's scored

Value moments are scored by the focus-group rubric's **Value** dimension
(`value.a`, `value.c`) during the track-prototype walk, and calibrated by whether
they lift **per-step continuation** once live. A moment that tests well but can't
be grounded is a failed moment, not a shippable one.

## Rationalization table

| Excuse | Reality |
|---|---|
| "A specific number makes it feel credible." | A fabricated number makes it a lie that feels credible — the worst kind. Credibility comes from being right. |
| "It's probably about right / a reasonable estimate." | Probably-right precision is still fabrication. Ground it or drop the number. |
| "I'll mark it grounded and wire the real data later." | Grounded means the real figure is supplied to the prompt NOW. No data = not grounded. |
| "Everyone knows digital marketing is growing." | General trend, stated qualitatively = model-reasoned, fine. A percentage on it = needs a source. |
| "The prompt says 'use specific figures' — the model will know real ones." | The model will invent plausible ones. Supply the figures or forbid them. |
| "It's just an illustration, the number is fine." | Illustrative means explicitly framed as an example ("roughly," "for instance") — never a bare number presented as fact. |
