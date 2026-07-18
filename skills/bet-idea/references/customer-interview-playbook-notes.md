# "How to Talk to Customers" (Ash Maurya / LEANSTACK) — reference for the customer-vetting skills

> Copied from thensls/market-exploration docs/plans, 2026-07-18.

Playbook: "The AI-Native Playbooks № 3", LEANSTACK / Ash Maurya
(leanspark.ai). 18 pages.

## The method (chapter by chapter)

**1. Why you can't trust what customers say.** Say ≠ do; past behavior is
the only honest predictor. *The interviewer's first rule:* never ask "would
you use this?" — ask "tell me about the last time you dealt with this" and
let the story do the talking. The question that matters before building: is
this a problem real people already struggle with, badly enough to do
something about it?

**2. Who to talk to.** The best interviewee is a **recent switcher** —
someone who hit the problem, went looking, and changed what they were doing
recently enough to remember the details. Interested people give opinions;
recent switchers give evidence. Cast wide then narrow: broad-match first to
find where pain clusters, then narrow-match on the sharpest segment; stop
when you stop being surprised. "A precise target beats a long contact list"
— 'Founders' is not a segment; 'solo founders who launched in the last 90
days and are below their conversion targets' is.

**3. What to ask.** Three acts: set the scene → walk the struggle
(step by step, including workarounds) → surface the switch. Map the **four
forces** under every switch:
1. **Push** — what was broken/frustrating about the old way
2. **Pull** — the outcome they wanted and couldn't get
3. **Friction** — effort/worry of changing ("will this even work for me?")
4. **Inertia** — habit and comfort of the status quo
*The switch equation:* people switch only when push + pull outweighs
friction + inertia — inertia is heavy, so a merely attractive pull rarely
beats it. *The switching trigger* is the single most predictive thing in
the interview — the specific moment the old way failed badly enough to make
them act. No trigger → you're hearing a nice-to-have, not a switch.
Three ways to ruin an interview: **leading** ("don't you hate it when…"),
**hypothetical** ("would you use…" — stay in the past), **pitching** (the
moment you describe your idea, they stop telling truth and start protecting
your feelings). Look for **workarounds, not "problems"** — when someone
goes out of their way, that effort IS the problem worth solving.

**4. Making sense.** One **Customer Forces Story** per interview — a short
synthesis in your own words of push/pull/friction/inertia + trigger. Not a
transcript; a book report. Force the **disconfirming evidence** into the
light side-by-side with supporting evidence and ask which list the data
backs. Most markets have 3–5 recurring stories — when new interviews stop
changing the stories, you've heard enough (saturation rule).

**5. From conversation to commitment.** A great interview proves the
problem is real; it doesn't prove anyone will pay. Talk is cheap — the
strong signal is when a customer gives up something they value. **The
commitment ladder:** time (a follow-up, a referral) → reputation (an intro
to their boss, a public yes) → money (a pre-order, a deposit, signed LOI).
Each rung costs more and is worth proportionally more as evidence. "A
fifty-dollar pre-order is worth more than fifty people saying 'I'd totally
use this.'"

**6. Love the problem.** Interviews are a habit, not a phase — keep a
standing slot (one or two a month, forever). Fall in love with the problem,
not the solution: solution-lovers interview to confirm and hear only yeses;
problem-lovers interview to understand and hear truth even when it says
pivot. AI does transcription/synthesis; sitting with a human and noticing
the workaround they didn't mention is still your job.

## Mapping onto Strategy Studio

- **Commitment ladder ↔ `signal_strength`**: interest ("that's really
  interesting" — costs nothing, means nothing) → exploration → commitment
  (time/reputation/money asks: intro, calendar, LOI, deposit) → payment.
  Our gates already count exploration+ only, with a source link required —
  this playbook is the training material for grading honestly.
- **Four forces + switching trigger → interview guide structure** for
  `bet-research`: three-act, past-tense only, leading/hypothetical/pitching
  questions flagged and rewritten. Warm-channel twist (our design): NSLS
  partners are extra-polite, so trigger-hunting and workaround-hunting
  matter even more than in cold interviews.
- **Customer Forces Story → `strategy_evidence` notes_md template** for
  kind=interview/roadshow rows: push/pull/friction/inertia/trigger +
  supporting-vs-disconfirming columns; `data.problem_confirmed` = a real
  trigger + workarounds heard unprompted, NOT enthusiasm.
- **Recent switchers → target shortlist**: for warm B2B bets, "recent
  switchers" ≈ schools that recently changed relationship_state or replaced
  a tool — a shortlist criterion the market DB can actually query.
- **Saturation rule (3–5 stories)** complements the ≥5-conversation gate:
  the gate is the floor, saturation is the ceiling — bet-research should
  say "stop interviewing when stories stop changing."
