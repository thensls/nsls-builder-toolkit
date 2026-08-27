# Monthly Hex audit

Jordan committed to this on 2026-08-13 as the counterweight to the
grant-Editor-freely policy. Without it, "grant on manager request" has no brake.
Nobody owns it yet.

**Run it twice per cycle, not once.** A start-of-cycle audit structurally
cannot catch the case section 1 exists to catch — a cycle that will exhaust its
pool before it closes — because by the next run the spend counter has already
reset and the overrun is invisible. Run it:

- **at the start of each billing cycle** (the retrospective pass: what
  ratcheted, what went unused), and
- **mid-cycle, or the moment top-ups cross ~60% of the $1,000 spend limit**,
  whichever comes first (the early-warning pass).

The 2026-08 cycle is the worked example, and the answer it gives is "fine":
$475 on 8/13 and $775 on 8/20 in a Jul 24 – Aug 24 cycle projects to about
$946 at close, roughly $54 of headroom. The point is not that it was heading
for trouble — it wasn't — but that a start-of-cycle-only audit could not have
told you either way, because by its next run the counter has reset. The
mid-cycle pass is what turns "that slope looks steep" into a number. Section 1
has the arithmetic.

## 1. Spend against the pool

https://app.hex.tech/019847ea-73c2-7002-9a3a-cff99736a83d/settings/credits

Read the top-ups figure against the $1,000 spend limit. Report the delta, not
just the number.

**Top-ups are not evidence that allocations ratcheted.** Top-ups measure what
the workspace actually *spent* refilling the pool; an allocation is a
non-billing *cap* on what one person may draw. The same month-over-month climb
is produced by unchanged allocations and heavier use — which is a usage story,
not a policy one, and has a different fix. So when top-ups climb with no new
users, compare the **allocation list itself** against last cycle's before
concluding anything ratcheted (section 2 does that), and say which of the two
you actually found.

Observed so far: **$475 on 2026-08-13, $775 on 2026-08-20**, in a cycle running
Jul 24 to Aug 24.

**Do the arithmetic; do not eyeball the shape of it.** $300 over 7 days is
~$43/day. Four days remain to the 8/24 close, so straight-line the run ends
near **$946 — under the $1,000 limit.** This cycle did *not* bind, and an
earlier draft of this file said it would. That is the error the forecast exists
to prevent, made in the document teaching the forecast: a steep climb read as
an overrun without anyone multiplying it out.

State the projected close figure and the margin every time — "$946, about $54
of headroom" — not a verdict. A number can be checked; "the pool binds" cannot.
Escalate on the projection crossing the limit, or on the pace changing, never
on the slope looking alarming.

## 2. Allocations that were meant to be temporary

Any allocation raised "just for this month" renews forever unless someone
lowers it. Marissa's 500 to 600 on 2026-08-13 is the known case.

**Check every allocation that was RAISED since the previous audit — not every
allocation above some absolute figure.** A 500-baseline filter only ever sees
the people who were already large. A recurring 100 → 200 bump is exactly the
same failure, costs the same renewing-forever money, and sits permanently below
the line: it would renew indefinitely without ever being looked at. The signal
is the *change*, not the size.

That means the audit has to keep last cycle's allocation list to diff against.
If there isn't one — first run, or nobody saved it — say so plainly, record
this cycle's list as the baseline, and note that the ratchet check is not
possible until the next run. An audit that silently compares against nothing
reports "no ratcheting" every time.

For each raise found, ask whether the crunch that justified it is over.

## 3. Total caps against the pool

Sum each person's **effective** limit and compare to $1,000 (2 credits per
dollar). Per-user limits alone undercount: a limit can be set at User, Group or
Workspace Default scope, so a 500-credit group limit covering ten people who
have no individual limit is 5,000 credits of potential draw that a per-user
sum reports as zero.

Effective limit resolves by the same precedence as Step 6 in SKILL.md —
**User > Group (highest wins) > Workspace Default**:

- explicit user limit → that figure, and the person's group limits are
  irrelevant to them (do **not** also add the group's; that double-counts)
- no user limit → the highest limit among the groups they belong to
- neither → the workspace default, which is currently **No access**, so zero

On 2026-08-20 the *per-user* caps alone totalled about 3,400 credits/cycle,
roughly $1,700 against a $1,000 pool. That figure is a floor, not the total —
it predates this correction and no group or default exposure was added to it.

Oversubscription is normal and intended. It is worth tracking anyway, because
the ratio tells you how much of a cushion is left before the pool, rather than
any individual cap, becomes what stops people working.

## 4. Paid seats with no usage

Explorer is $40/month and Editor is $75/month whether or not the person logs in.
Pull the users list and cross-reference against the Usage log.

**The Usage log measures credit CONSUMPTION, not activity.** It reports
add-on-credit spend per user — so an Editor who builds and ships projects all
cycle without touching the agent shows up in it as a flat zero, identical to
someone who never signed in. Recommending a downgrade off that column alone
means proposing to demote your most active builders, and you will only find out
when they lose the ability to work.

So before any downgrade recommendation, corroborate with a **second, non-credit
signal** of whether the person actually used Hex: last sign-in, projects
created or edited this cycle, or app runs. Zero credits plus real project
activity is not a downgrade candidate — it is an Editor who does not use the
agent, which is section 4's third bullet, not its first.

If no activity source is available to you, **say the check could not be
completed** and list the zero-credit users as *unverified* rather than as
downgrade candidates. Naming them as candidates on credit data alone is the
recommendation that gets someone demoted for doing their job.

With both signals in hand:

- No credit spend **and** no sign-in, no project activity **and no app runs**
  for a full cycle: drop to Viewer (free). They keep app access. All four have
  to be silent — an app run is real use, and it is the signal most likely to
  be the only one a light user leaves.
- Viewing published apps, **never drilling down**, and never using the agent:
  Viewer is the right tier.
- **Drilling down into charts, even with no agent use: leave Explorer alone.**
  Drill-down is an Editor/Explorer capability — Viewers cannot do it — so this
  downgrade silently removes something the person actively uses, and they will
  discover it the next time they try to work. ([Hex roles
  docs](https://learn.hex.tech/docs/collaborate/sharing-and-permissions/roles).)
- Building nothing but running agent threads: Editor should be Explorer,
  saves $35/month per person.
- Real project activity, no agent use: leave the seat alone. This is the case
  the credit column cannot see.

Downgrade is not a punishment and does not delete anything. Say that in the
message, or people will resist it.

## 5. Pulling the data instead of reading the page

Thread-level metadata (thread details, user, credit consumption) can be pulled
via the Hex CLI or API rather than clicking through the UI. Credit *allocation*
is UI-only. Hex's Admin REST API also covers users and groups on Team and
Enterprise plans, so the seat side of this audit can be scripted.

> **Do not make downgrade decisions from thread data.** Thread-level
> consumption is not billing-cycle data and does not reconcile with the
> credits page: deleted threads drop out of it entirely, and usage is
> attributed to the date the thread was *created* rather than when the
> messages that spent the credits were added. Both failures point the same
> way — they make a real user look quiet. Combined with section 4, that is how
> an active person gets nominated for a downgrade.
>
> Use it for what it is good at: which threads are expensive, which workflows
> to optimise, where the spend is concentrated. The **billing source of truth
> for any seat decision is the credits page's Usage log**, and even that only
> answers consumption — it still needs the separate activity signal section 4
> requires.

No workspace API token is configured on Royce's machine as of 2026-08-20. If
this audit becomes recurring, that token is the first thing to set up, and it
can be configured to never expire.

## 6. Report

**To Jordan after every pass, not once a month.** An early warning nobody sends
is not an early warning. The mid-cycle pass exists to catch an overrun while
there is still time, so its result goes out **immediately** when top-ups cross
~60% of the $1,000 limit — waiting for the monthly report means delivering it
after the cycle it was about has already closed, which is the exact failure
the twice-per-cycle schedule was added to fix.

Every pass reports:
- current-cycle spend against $1,000, with the month-over-month delta, **and
  the projected close figure with its margin** (see section 1 — the number and
  the headroom, not a verdict)
- allocation changes since last audit and who approved each
- seats recommended for downgrade, with the monthly saving
- anything that hit a cap twice in one cycle, which usually means the person
  needs agent-usage coaching rather than more credits
