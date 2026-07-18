# Causal-chain interrogation

Used by `bet-idea` step 4. Operationalizes Ash Maurya's framing that a Lean
Canvas isn't nine independent boxes — it's **a chain of beliefs stacked on
top of each other**. If a belief low in the chain is wrong, everything built
on top of it is wrong too, no matter how well-reasoned it looks. The job here
isn't to list assumptions — it's to find the ones that, if wrong, take the
rest of the model down with them, and get each one recorded honestly.

## Walk the chain in fill order

Step 1 of `bet-idea` recorded the order in which the human actively engaged
with the first three canvas boxes — that's the natural order to walk the
chain now, because it reflects what they reasoned about first (and likely
what everything else was built on top of). Don't re-derive a "logical" order
from the canvas template; use the order the human actually thought in.

## Categorize every belief

For each load-bearing belief in the chain, decide its `belief_type`:
- **`leap_of_faith`** — asserted with no evidence at all yet. The riskiest
  category by definition.
- **`anecdote`** — one or a few data points (a conversation, a single
  customer's story) — better than nothing, not yet a pattern.
- **`fact`** — actually established, ideally with a source the human can
  point to.

Being honest about the category matters more than the count — a canvas with
five `leap_of_faith` beliefs correctly labeled is in better shape than one
with five beliefs all optimistically called `anecdote`.

## Cover all three risk types

Every load-bearing belief also gets a `risk_type`: **customer** (will anyone
want this), **market** (is the market real/big/reachable), or **technical**
(can we actually build/deliver it). Before finishing this step, check
coverage: **if any of the three risk types has zero recorded assumptions,
flag it out loud.** A bet with only customer-risk assumptions recorded may
simply not have had its market or technical risk examined yet — that's a
blind spot, not evidence the risk doesn't exist.

## Priority = domino order, owner-confirmed

For each assumption, ask the domino question: *"if this is wrong, what else
in the model collapses?"* The assumption whose failure would invalidate the
most of the rest of the canvas gets `priority: 1`; work outward from there.
This ranking is **proposed by the interrogation, confirmed by the owner** —
you can surface the domino logic, but the human who owns the bet makes the
final call on what's actually most load-bearing for their idea.

## One call per assumption

Each load-bearing assumption maps to exactly one `upsert_assumption` call:

```
upsert_assumption(bet_id, statement, source_field_key, belief_type,
                   risk_type, chain_position, priority)
```

`source_field_key` ties the assumption back to the canvas or thesis field it
came from (e.g. `canvas.segments`, `thesis.why_now`) — this is what lets a
later invalidated assumption point straight back at the section it undermines.

## The cheap kill signal

The entire point of doing this now, before any money or research time is
spent, is that **an invalidated load-bearing assumption discovered later is
the cheapest possible kill signal** — cheaper than a failed pilot, cheaper
than a build that shipped to nobody. If a `leap_of_faith`/`priority: 1`
assumption comes back false during research, that's not a setback to route
around; it's the chain doing its job. Don't let a bet quietly carry an
invalidated top-priority assumption forward into planning.
