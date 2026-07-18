# Office-hours diagnostic questions

Used by `bet-idea` step 3 to pressure-test the canvas's weakest boxes before
the causal-chain step builds assumptions on top of them. The point isn't to
collect answers — it's to refuse the first, polished one and make the human
say something truer.

## The anti-sycophancy rule (verbatim)

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

This is not tone advice — it's a structural rule. A drafted canvas box that
survives contact with these questions unchanged either genuinely is solid, or
was never actually challenged. If you find yourself agreeing quickly, you
skipped a push.

## The forcing questions

**Demand reality.** *"What's the strongest evidence someone would be
genuinely upset if this disappeared tomorrow?"* Not "would this be useful" —
upset. Enthusiasm for a hypothetical is cheap; only a real loss is evidence.
If the best answer is "they said it sounded cool," that's interest, not
demand — name it: "interest ≠ demand."

**Status quo.** *"What's the current workaround, and what does it cost — in
hours, dollars, or duct-tape?"* Every real problem has a workaround, even a
bad one; if there's no workaround at all, the problem may not be painful
enough to have forced one yet. **Red flag:** "nothing exists, that's the
opportunity" — flip it. The status quo is the real competitor. If nothing is
currently being done about this, ask why not before assuming it's whitespace.

**Desperate specificity.** *"Name the actual human. What's their title? What
gets them promoted, or fired, over this?"* "Colleges" is not a buyer. "The VP
of Career Services who has to report placement rates to the president every
semester" is. If the human drafting the bet can't name the actual person,
the segment box isn't done yet — go back to it.

**Narrowest wedge.** *"What's the smallest thing someone would pay for this
week?"* Not "eventually," not "once it's built out" — this week, as it
stands right now. An answer that requires the full roadmap to exist first is
a sign the bet is solving a future problem, not a present one.

**NSLS warm-channel twist.** Our channel is warm — campus partners, chapter
advisors, people who already like NSLS. They will say "oooh, interesting" to
almost anything out of politeness; treat that as noise, not signal. What
counts is behavior and commitment, never enthusiasm alone: did they make an
introduction, put something on a calendar, offer to pay, sign something? Cite
the **commitment ladder** from the Customer Forces material
(`references/customer-interview-playbook-notes.md`) — time (a follow-up, a
referral) → reputation (an intro to their boss, a public yes) → money (a
pre-order, a deposit, a signed LOI). A warm "that's interesting" sits below
all three rungs and proves nothing on its own.

## Using the answers

Once a sharper answer lands, update the relevant section
(`update_section(bet_id, field_key, content_md, evidence_tag)`) — the
sharpened content replaces the vague draft, still tagged `assumption` or
`opinion` unless the human is supplying their own first-hand knowledge (in
which case it can be `data`). Don't silently keep both versions — the point
of pushing twice is to arrive at one truer statement, not to log a debate.
