# Interview guide — the Customer Forces method, operationalized

Used by `bet-research` Step R3. This is `references/customer-interview-playbook-notes.md`
(Ash Maurya's method) turned into a warm-channel playbook: who to call, what
to ask, how to grade what comes back, and exactly how a conversation becomes
a `log_evidence` row.

## Who to talk to

**Recent switchers over interested people** — past behavior is the only
honest predictor. Someone who says "that sounds interesting" has given you an
opinion; someone who recently changed `relationship_state` or replaced a tool
has given you evidence. Cast broad-match first to find where pain clusters,
then narrow-match on the sharpest segment — stop when you stop being
surprised. A precise target beats a long contact list.

For warm B2B bets, the call list already exists: `references/self-serve-research.md`'s
dimension 3 produces the target shortlist (with buyer-title stakeholder
matches via `target_shortlist`), and that shortlist doubles as the interview
list. "Recent switchers" for this channel ≈ schools that recently changed
`relationship_state` or replaced a tool — a criterion the market DB can
actually query, not a vibe.

## Three acts

1. **Set the scene** — get them talking about their day, their role, the
   territory the problem lives in.
2. **Walk the struggle, step by step** — including every workaround. Don't
   skip to the punchline; the workaround IS the evidence.
3. **Surface the switch** — did anything actually change? What, when, why
   then and not before?

**Past tense only, throughout.** The moment a question drifts into "would
you..." or "do you think you'd...", the interview has stopped producing
evidence and started producing opinion.

## Four forces + the switch equation

1. **Push** — what was broken or frustrating about the old way
2. **Pull** — the outcome they wanted and couldn't get
3. **Friction** — the effort and worry of changing ("will this even work for
   me?")
4. **Inertia** — habit, comfort of the status quo

People switch only when push + pull outweighs friction + inertia — **inertia
is heavy**, so a merely attractive pull rarely beats it on its own.

**The switching trigger** is the single most predictive thing in the whole
interview — the specific moment the old way failed badly enough to make them
actually act. No trigger means you're hearing a nice-to-have, not a switch.
Always ask for it directly if it hasn't surfaced by act three: "what was the
moment that made you finally do something about this?"

## Three ways to ruin an interview

- **Leading** — "don't you hate it when...?" hands them the answer.
- **Hypothetical** — "would you use...?" breaks the past-tense rule; stay in
  what actually happened.
- **Pitching** — the moment you describe the idea, they stop telling the
  truth and start protecting your feelings. Don't pitch until the interview
  is over, if at all.

Look for **workarounds, not "problems."** When someone goes out of their way
— a spreadsheet nobody asked for, a manual step they invented, a person they
loop in every time — that effort IS the problem worth solving. A described
"problem" with no workaround behind it usually isn't painful enough to have
forced one yet.

## The warm-channel twist

NSLS partners are extra-polite. They will say "that sounds interesting" or
"we'd want that" to almost anything, out of genuine warmth, not calculation —
and we often don't know their budget or their priorities going in. That makes
trigger-hunting and workaround-hunting matter MORE here than in a cold
interview, not less: politeness is noise, and this channel produces more of
it than a stranger would.

Standing questions to ask on every warm B2B interview:
- Who owns the budget for this problem?
- What do they spend on it today — time, headcount, a tool, duct tape?
- What would they cancel to fund this?

Buyer budget/priority is a standing customer-risk assumption on every warm
B2B bet — if it isn't already in `strategy_assumptions`, it belongs there.

## The verbatim anti-sycophancy block

```
NEVER say: "that's an interesting approach" / "there are many ways to think
about this" / "you might want to consider" / "that could work" / "I can see
why you'd think that."
ALWAYS: take a position and state what evidence would change it. Push once,
then push again — the first answer is the polished version. Name failure
patterns by name: "solution in search of a problem", "interest ≠ demand".
The status quo is the real competitor: if "nothing" is the current solution,
the problem isn't painful enough.
```

This governs how the interview guide is drafted and how the resulting story
is graded — not just tone in conversation with the human.

## Grading — the commitment ladder → `signal_strength` (verbatim)

```
"oooh, interesting" is interest; asking about price/timeline unprompted is
exploration; a named budget line, pilot agreement, or LOI is commitment;
money is payment. Gates count exploration+ only, and ONLY when the row
carries a source link (Fathom timestamp / roadshow report page) — unlinked
grades are self-attested by the party that wants the bet to advance and
never satisfy a gate. Internal enthusiasm is interest, never market demand.
A fifty-dollar pre-order is worth more than fifty people saying "I'd
totally use this." bet-review spot-audits grades against linked recordings.
```

Grade from what was said and done in the conversation, never from how warm
the summary reads.

## `data.problem_confirmed`

True only when a real switching trigger + workarounds were heard
**unprompted** — never for enthusiasm, and never because the interviewer
pitched an idea and got a nod back. If the trigger or workaround only
surfaced after the interviewer suggested it, mark `false` and say so; a
prompted "yes, that happens" is not confirmation.

## The rep → system evidence path

Reps are not strategy authors. The relevant conversations happen inside
their regular buyer meetings, Fathom-recorded as a matter of course. The
**bet owner** — not the rep — logs each one via this skill from the
recording or its summary, choosing `signal_strength` and the source link
themselves. This is the same ingestion pattern the roadshow pipeline already
proves out (see `references/roadshow-sprint.md`): a person has a
conversation, the system captures it, the owner turns it into evidence.

## The Customer Forces Story → `log_evidence` recipe

One story per interview — a book report, not a transcript.

```
log_evidence(
  bet_id, kind: "interview",
  title: "<person/title> @ <institution> — <one-line trigger or verdict>",
  notes_md: |
    ## Customer Forces Story
    Push: … / Pull: … / Friction: … / Inertia: …
    Switching trigger: … (or "none heard — nice-to-have")
    Workarounds heard: …
    Supporting evidence: …   | Disconfirming evidence: …
  link: "<Fathom timestamp URL or roadshow report page>",   // REQUIRED for exploration+
  data: { problem_confirmed: true|false },
  signal_strength: "interest"|"exploration"|"commitment"|"payment",
  entity_type: "college"|"school", entity_id: "<ipeds/nces id>",
  evidence_tag: "data",   // a real conversation IS data — grade honestly anyway
  via: "bet-research")
```

Disconfirming evidence is forced side-by-side with supporting evidence in
every story — ask, out loud, which list the data actually backs before
writing it down.

## Saturation rule

Most markets have 3–5 recurring stories. When new interviews stop changing
the stories — same trigger, same workaround, same forces — you've heard
enough. The ≥5-conversation gate (`references/gate-progress.md`) is the
floor; saturation is the ceiling. Say it plainly: "stop interviewing when the
stories stop changing," not "keep going until the gate number is hit and one
more for luck."
