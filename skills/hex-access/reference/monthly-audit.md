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

The 2026-08 cycle is the worked example: $475 on 8/13 and $775 on 8/20 in a
Jul 24 – Aug 24 cycle. Only the mid-cycle pass can see that while there is
still time to act on it.

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
Jul 24 to Aug 24. If that pace holds, the pool binds before the cycle closes,
which is the scenario this audit exists to catch early.

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

Add up the per-user limits on the credits page and compare to $1,000 (2 credits
per dollar). On 2026-08-20 the caps totalled about 3,400 credits/cycle, roughly
$1,700 of caps against a $1,000 pool.

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

- No credit spend **and** no sign-in / project activity for a full cycle: drop
  to Viewer (free). They keep app access.
- Viewing dashboards but never using the agent: Viewer is the right tier.
- Building nothing but running agent threads: Editor should be Explorer,
  saves $35/month per person.
- Real project activity, no agent use: leave the seat alone. This is the case
  the credit column cannot see.

Downgrade is not a punishment and does not delete anything. Say that in the
message, or people will resist it.

## 5. Pulling the data instead of reading the page

Thread-level metadata (thread details, user, credit consumption) can be pulled
via the Hex CLI or API rather than clicking through the UI. Credit *allocation*
is UI-only, but credit *consumption* is queryable, which is what the audit
actually needs. Hex's Admin REST API also covers users and groups on Team and
Enterprise plans, so the seat side of this audit can be scripted.

No workspace API token is configured on Royce's machine as of 2026-08-20. If
this audit becomes recurring, that token is the first thing to set up, and it
can be configured to never expire.

## 6. Report

To Jordan, monthly:
- current-cycle spend against $1,000, with the month-over-month delta
- allocation changes since last audit and who approved each
- seats recommended for downgrade, with the monthly saving
- anything that hit a cap twice in one cycle, which usually means the person
  needs agent-usage coaching rather than more credits
