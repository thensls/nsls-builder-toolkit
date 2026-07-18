# Experiment design — sell-first, channel-aware, threshold-honest

Used by `bet-plan` Step P3. This is how the proof plan gets built: which
instrument to run, how to write a hypothesis that can actually fail, and how
to set thresholds the owner would actually act on.

## The channel decision + sell-first doctrine (verbatim)

```
Experiment design defaults to SELL-FIRST, instrument chosen by channel:

Warm B2B (existing partner relationships) → rep-led pre-sale asks
(kind: pre_sale), a roadshow sprint (kind: roadshow), or paid-pilot
commitments (kind: pilot). Success thresholds are stated in
commitment/payment signals — never meeting counts. Warm partners say yes
to meetings for free; the experiment measures what they'll GIVE UP.

Cold segments / B2C → landing page or fake door (kind: landing_page),
concierge (kind: concierge). Anchor expectations at ~3–5% cold conversion —
a landing page beating 5% is a real signal; 0.5% is the market answering.

We try to sell it before we build it. A build-first experiment
(kind: build) requires stated rationale — and for internal-origin
(dogfood) bets, "we are the customer and already built/are building it
for ourselves" is a FIRST-CLASS rationale, not a waiver: the build was
justified by internal need, and the experiment tests the separate
question of external willingness to pay.
```

## Choosing the channel

Read the bet's motion, buyer, and relationship counts in
`market.current_data` (populated by `bet-research`'s `size_segment` /
`target_shortlist` pulls):

- **Warm B2B** — an existing partner relationship, a rep who already has the
  door open, a buyer this org has sold to before. Instrument: `pre_sale`,
  `roadshow`, or `pilot`.
- **Cold / B2C** — no existing relationship, a segment reached only through
  marketing or self-serve signup. Instrument: `landing_page` or `concierge`.

Say the channel-and-origin reasoning out loud before choosing the
instrument — this is the step of the whole skill most worth arguing with,
and a silent choice here is the easiest place for a bet to quietly dodge the
sell-first doctrine.

## Experiment recipe

```
add_experiment(
  bet_id,
  name,
  kind,                       # roadshow | pre_sale | concierge | landing_page | pilot | build
  hypothesis: "<falsifiable, with a number>",
  rationale: <required when kind == "build">,
  investment: "<dollars + people-weeks>",
  milestones: [{ "title": "...", "due": "YYYY-MM-DD", "status": "pending" }],
  via: "bet-plan"
)
```

**One primary experiment.** Add more only if they test a genuinely
DIFFERENT assumption — never as a hedge against the primary experiment
failing, and never to make the proof plan look busier than it is.

## Three thresholds

Write `proof.threshold_continue`, `proof.threshold_accelerate`, and
`proof.threshold_stop` with `update_section`, each carrying numeric `data`
**where possible**:

```json
{ "metric": "paid pilots signed", "op": ">=", "value": 3, "by": "2026-12-31" }
```

`content_md` states the same thing in prose, plus the reasoning behind the
number — why 3, why that date, what happens if it lands at 2 instead.

Prose-only thresholds are allowed when the metric genuinely resists a
number (a qualitative signal like "procurement explicitly names budget for
this line item") — say so explicitly in the content rather than inventing a
number to fill the `data` shape. False precision is worse than an honest
prose threshold.

**`threshold_stop` must be one the owner is actually willing to act on.** A
stop threshold nobody would honor when it's hit is decoration, not a gate —
it exists to connect back to the downside case in `econ.cases`: if the stop
threshold fires, the downside case is the world the bet is now living in.
Ask the owner directly whether they'd really kill the bet at that number
before writing it down.

## Investment ask (`proof.investment`)

The 2026 ask stated in dollars, named people (not roles-in-the-abstract —
"40% of Jordan's time," not "a part-time PM"), and duration. Close by naming
what the continue threshold buys next — what happens, concretely, if the
experiment clears `threshold_continue`.

## `proof.experiment_2026` and `proof.milestones`

- `proof.experiment_2026` narrates the primary experiment in prose — what's
  being run, on whom, and why this instrument for this channel.
- `proof.milestones` mirrors the experiment's own milestone list (the same
  `[{title, due, status}]` array passed to `add_experiment`) — don't let the
  two drift; if a milestone slips, update both places.
