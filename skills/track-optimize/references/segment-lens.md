# The Segment Lens — who is dropping, not just where

Optimization hypotheses name a **segment**. "We lose 36% at step 2" is a fact;
"Accelerators drop at step 2 at 1.7× the Seeker rate because the 42-question
quiz reads as a delay to people whose job-to-be-done is speed" is a hypothesis
you can act on and measure.

**Canonical source of truth:** `track-studio` `lib/segments.ts` (rendered live
at studio.nsls.org/audience). If this file and that one disagree, that one
wins — update this copy. Spec: track-studio
`docs/specs/2026-07-03-audience-segmentation.md`.

## The segments

Needs-based (never demographics): defined by the member's own Welcome-track
answers — **career clarity × job confidence**, both 1–10 wheels.
**High = ≥ 8** (decided 2026-07-03: the median member rates 7; self-report
scales cluster high, so 7 is a "passive").

| Segment | Clarity | Confidence | Job-to-be-done | Needs |
|---|---|---|---|---|
| **Seeker** | low | low | "Help me figure out what I even want." | Direction and reassurance before skills |
| **Explorer** | low | high | "Help me choose among my options." | Focus, comparison, commitment devices |
| **Doubter** | high | low | "Help me prove I can get it." | Skills, credentials, evidence, reps |
| **Accelerator** | high | high | "Help me get there faster." | Velocity, connections, visibility |
| Unsegmented | — | — | Hasn't answered both wheels | Treat as coverage gap, never guess |

Live mix (2026-07-03, full history): Seeker 834 (50%) · Accelerator 351 (21%) ·
Doubter 286 (17%) · Explorer 196 (12%) · Unsegmented 43% of all members.
"Doubter" is internal vocabulary — never member-facing.

## Reading segment membership from PostHog

Ratings live in three events; take the **latest value per person** across all
of them (project 128379, HogQL via `/posthog`):

- `substep_save_result` (server-side, since 2026-03-15) — value in the answer
  JSON as `{"dropdown": N}` (`properties.answer` — verified by execution
  against project 128379 on 2026-07-03: 2,526 of 2,855 clarity-slug events
  carry a `dropdown` key); match by `properties.substep_slug`:
  clarity = `direction-clarity`, `direction-clarity-rating`;
  confidence = `job-acquisition-confidence`, `job-acquisition-confidence-rating`.
  (The unsuffixed slugs are the pre-May-2026 combined substeps — ~40% of
  answers; do not drop them.)
- `confidence_score_set` (client, since 2026-06-22) — `properties.value`;
  match by `properties.attribute_key`:
  clarity = `4ccf3e56-2a94-46a3-bc5d-94f32690caa7`,
  confidence = `82a1f742-4067-48da-a92f-369ab92dbf58`.
- `confidence_score_edited` (profile surface) — `properties.new_value`, same
  attribute keys.

The shared per-person CTE (paste as the `WITH` head of the queries below):

```sql
per_person AS (
  SELECT person_id,
    argMaxIf(v, timestamp, dim = 'clarity') AS clarity,
    argMaxIf(v, timestamp, dim = 'confidence') AS confidence
  FROM (
    SELECT person_id, timestamp,
      multiIf(
        properties.attribute_key = '4ccf3e56-2a94-46a3-bc5d-94f32690caa7', 'clarity',
        properties.attribute_key = '82a1f742-4067-48da-a92f-369ab92dbf58', 'confidence',
        properties.substep_slug IN ('direction-clarity','direction-clarity-rating'), 'clarity',
        properties.substep_slug IN ('job-acquisition-confidence','job-acquisition-confidence-rating'), 'confidence',
        '') AS dim,
      multiIf(
        event = 'confidence_score_set', toFloat(properties.value),
        event = 'confidence_score_edited', toFloat(properties.new_value),
        JSONExtractFloat(properties.answer, 'dropdown')) AS v
    FROM events
    WHERE (
        (event IN ('confidence_score_set','confidence_score_edited')
          AND properties.attribute_key IN ('4ccf3e56-2a94-46a3-bc5d-94f32690caa7','82a1f742-4067-48da-a92f-369ab92dbf58'))
        OR (event = 'substep_save_result'
          AND properties.substep_slug IN ('direction-clarity','direction-clarity-rating','job-acquisition-confidence','job-acquisition-confidence-rating')
          AND JSONHas(properties.answer, 'dropdown'))
      )
      AND timestamp >= toDateTime('2026-03-01') -- launch-era anchor: covers ALL rating history (events begin 2026-03-15). A rolling now()-interval would silently age members out into 'unsegmented'.
  )
  WHERE dim != '' AND v >= 1
  GROUP BY person_id
)
```

And the bucket expression (mirror of `segmentCaseExpr`; the `coalesce` matters —
HogQL LEFT JOINs yield NULL, and NULL comparisons fall through `multiIf` to the
default branch):

```sql
multiIf(
  coalesce(p.clarity, 0) < 1 OR coalesce(p.confidence, 0) < 1, 'unsegmented',
  p.clarity < 8 AND p.confidence < 8, 'seeker',
  p.clarity < 8 AND p.confidence >= 8, 'explorer',
  p.clarity >= 8 AND p.confidence < 8, 'doubter',
  'accelerator') AS segment
```

### Recipe — per-step drop-off by segment (the lens on the weak step)

```sql
WITH per_person AS ( … as above … ),
steps AS (
  SELECT person_id, toInt(properties.step_number) AS step_number
  FROM events
  WHERE event = 'step_completed'
    AND properties.track_slug = '<track-slug>'
    AND timestamp >= toDateTime('2026-03-01')
  GROUP BY person_id, step_number
)
SELECT <bucket expression> , s.step_number, count(DISTINCT s.person_id) AS members
FROM steps s LEFT JOIN per_person p ON s.person_id = p.person_id
GROUP BY segment, step_number ORDER BY segment, step_number
```

Read it as: per segment, members completing step 1, 2, 3… — the step-to-step
ratio per segment is the continuation. The segment whose ratio falls furthest
below its peers at the weak step is the **target segment**.

Worked example (personal-insights, 2026-07-03): step 1→2 continuation —
Seeker 563/613 = 92% · Doubter 195/217 = 90% · Explorer 123/137 = 90% ·
**Accelerator 229/265 = 86%**. Accelerators lose ~1.7× the Seeker rate at the
42-question quiz: the segment whose JTBD is speed meets the track's slowest
step first.

## Running the focus-group as a segment

The panel (`../track-design/references/member-personas.md`) is
**register-based** (sophistication axis). The segment lens is an **overlay**,
not new personas — when diagnosing for a target segment, instruct each Stage-1
persona to react *as a member of that segment*:

> You are [persona] — everything about your register stands. Additionally, you
> are a **[Segment]**: you rated your career clarity N and job confidence M
> [sample a plausible pair from the segment's live distribution — e.g. a Seeker
> at 4/3, an Accelerator at 9/8]. Your job-to-be-done for Society is
> "[segment JTBD]". React to this step through that need.

Keep the register diversity (a Seeker Maya and a Seeker Patricia leave for
different reasons); vary the sampled ratings across the panel. Note the overlay
in the run's handoff note and `persona_used` (e.g. `Maya+seeker(4/3)`).

### Recipe — next-track adoption by segment (the between-track leak)

The audit found the biggest losses are BETWEEN tracks, not within them. A
hypothesis about a track's ending (story, payoff, bridge) predicts this metric:

```sql
WITH per_person AS ( … as above … ),
journeys AS (
  SELECT person_id,
    countIf(properties.track_slug = '<this-track>' AND properties.action = 'complete') > 0 AS completed_a,
    minIf(timestamp, properties.track_slug = '<this-track>' AND properties.action = 'complete') AS completed_a_at,
    countIf(properties.track_slug = '<next-track>' AND properties.action = 'start') > 0 AS started_b,
    minIf(timestamp, properties.track_slug = '<next-track>' AND properties.action = 'start') AS started_b_at
  FROM events
  WHERE event = 'session_lifecycle'
    AND timestamp >= toDateTime('2026-03-01')
  GROUP BY person_id
)
SELECT <bucket expression>,
  countIf(j.completed_a) AS completed_a,
  -- ordering gate: B's first start must follow A's first completion, else a
  -- member who tried B before finishing A inflates continuation
  countIf(j.completed_a AND j.started_b AND j.started_b_at >= j.completed_a_at) AS continued,
  round(100 * countIf(j.completed_a AND j.started_b AND j.started_b_at >= j.completed_a_at) / countIf(j.completed_a), 1) AS pct
FROM journeys j LEFT JOIN per_person p ON j.person_id = p.person_id
WHERE j.completed_a GROUP BY segment
```

**Auto-progression caveat (verified 2026-07-03):** between the live
foundational tracks, next-track *starts* run ~98–99% for every segment —
auto-progression carries completers forward. So for those transitions the
real between-track metric is next-track **completion** (swap `start` for
`complete` on track B). The adoption recipe as written matters for
non-automatic transitions (SNT unlock, future electives/upsells).

## The hypothesis workshop (walk the author through it)

An optimization ships as a **pre-registered experiment**: the version is tagged
with a hypothesis and a predicted number, stated *before* it ships. When
running this skill, walk the author through these five questions in order —
brainstorm with them, but every answer must land concretely:

1. **What outcome are you trying to move?** The ladder:
   **adoption** (start → continue → complete → *next-track adoption*) →
   **satisfaction** → **revenue** (future: Society is freemium today; upsell
   conversion becomes a metric on this same ladder once charging starts — the
   Studio is the place those experiments will run).
   Pick ONE metric from the `metric` menu.

   **Measuring satisfaction without the survivor trap.** An end-of-track
   rating only hears from finishers — the member offended by page 2 who quit
   on page 3 never answers it. Three survivorship-aware measures:
   - **Abandonment hazard (behavioral, available now).** Where members quit
     and how fast IS their satisfaction signal. `substep_save_result` fires
     per answered substep with track context, so per-substep reach counts
     (distinct persons per `substep_slug`, ordered by the track.json substep
     order) give a quit-probability curve per version per segment. A
     satisfaction hypothesis reads: "the page-2 rewrite lowers the quit spike
     across pages 2–4" — measured for everyone, including leavers.
   - **Sampled one-tap pulse (light ignite-next feature, not yet built).**
     One tap ("worth your time so far?") shown to a random 1-in-N members at
     a random step boundary — satisfaction by position, comparable across
     versions at the same position.
   - **Clarity/confidence deltas (available now).** The ratings are a time
     series; "completion flat but they liked it more" can appear as a larger
     per-completer lift. Slowest signal; it's the *outcome* satisfaction the
     product promises.
   The lifecycle-nudge rail can additionally ask lapsed members one tap
   ("what made you stop?") — the only stated signal leavers can give.
2. **For whom?** Name the segment (or justify `all` — flat-across-segments is
   itself a finding, not a default).
3. **What's the baseline?** Pull the real number with the recipes above —
   sourced, segment-sliced, with n. Never a guess.
4. **What's the causal story?** One diagnosed cause (from the focus-group
   dimension) tied to the segment's job-to-be-done — one change per hypothesis.
5. **What's the prediction?** From X to Y, by when. Make the author commit to
   a number before shipping — a prediction you'd be embarrassed to miss is the
   right size. Example (the Welcome story hypothesis; baseline real as of
   2026-07-03, target illustrative):
   *"By telling the story of what Society does for members — with concrete
   value examples — in Welcome's close, Personal Insights completion among
   Seekers rises from 65% (344/527) to ≥72% within 30 days — Seekers most
   need to see the destination before the 42-question climb."*

Then log it in the Studio base (`appzDWu6GowvnACtv`) table **`Hypotheses`**
(`tbltuJGELNhvnLZeT`) — heartbeat: report the record:

| Field | What goes in |
|---|---|
| `hypothesis` | "[Segment] [drops/underuses] [where] because [cause]; [change] should lift [metric] because [mechanism]." |
| `track` | Link to the Tracks row |
| `segment` | `seeker` / `explorer` / `doubter` / `accelerator` / `all` |
| `metric` | One rung of the ladder (see menu) |
| `weak_step` | Step slug/number (or the track ending for adoption hypotheses) |
| `dimension` | Value / Pacing / Copy / Fit |
| `change` | The one concrete change |
| `predicted_outcome` | The pre-registered prediction: from X to Y, for whom, by when |
| `baseline` | The sourced numbers behind X, with n |
| `status` | `proposed` → `in-gate` (entered score→gate) → `shipped` → `validated` / `refuted` |
| `version` | The `content_hash` of the version carrying the change — **tag it at ship** so version ↔ hypothesis is queryable |
| `measure_query` | The exact HogQL that measures the metric — pre-registered so **Studio can watch**: the track's detail page re-runs it and shows "Results pending: current vs target". Return small labeled rows (e.g. segment, value) |
| `window_end` | ISO date the measurement window closes. Studio shows **Unclear** past this date until a conclusion is set |
| `result` | Post-ship measurement vs the prediction |
| `created` | ISO date |

Studio renders each track's hypothesis history on its detail page — every
change, its hypothesis, and a conclusion state (**Results pending →
Hypothesis confirmed / Proven false / Unclear**). Write rows knowing they are
the track's permanent experiment record.

After the tagged version has been live long enough for real n, re-run the same
recipe and fill `result` — **validated** if the predicted movement happened,
**refuted** if not. A refuted hypothesis is a finding, not a failure: the
prediction is what makes it one. Return to diagnosis with it.

## Guardrails

- **Segment n shrinks fast.** A track with 300 starters has ~35 Explorers.
  Report n with every segment figure; below ~30 starters in the target
  segment, say the slice is directional, not significant.
- **Flat is the baseline.** As of 2026-07-03 behavior barely differs by
  segment (no differentiated experience exists yet). Expect small gaps;
  the lens earns its keep when a change *creates* a gap — that's the win
  condition, and why `result` must be segment-sliced.
- **Unsegmented members are excluded from segment claims** — never fold them
  into a segment. Their volume is a coverage metric, not evidence.
- **Welcome is survivorship — its per-segment completion is tautological.**
  The wheels that ASSIGN segments live inside Welcome, so being segmented
  already implies surviving most of Welcome: segmented members complete it at
  ~99% while unrated starters complete at ~52% (verified 2026-07-03 — this is
  also why the Audience page's Welcome card reads ~99% per segment while the
  Board's overall completion says ~81%; the Board number includes everyone).
  For Welcome hypotheses, use the overall/unsegmented numbers or condition on
  "reached the wheels"; the segment lens starts being real from the track
  AFTER Welcome.
