# Monthly Hex audit

Jordan committed to this on 2026-08-13 as the counterweight to the
grant-Editor-freely policy. Without it, "grant on manager request" has no brake.
Nobody owns it yet. Run it at the start of each billing cycle.

## 1. Spend against the pool

Hex → Settings → Plan and billing → Credits. Read the current-cycle total.

Baseline: **$475 of $1,000** as of 2026-08-13. Report the delta, not just the
number. A month-over-month climb with no new users is the signal that
per-cycle allocations have been ratcheting (see Step 5 in SKILL.md).

## 2. Allocations that were meant to be temporary

Any allocation raised "just for this month" renews forever unless someone
lowers it. Marissa's 500 to 600 on 2026-08-13 is the known case. Check every
allocation above the 500 baseline and ask whether the crunch that justified it
is over.

## 3. Paid seats with no usage

Explorer is $40/month and Editor is $75/month whether or not the person logs in.
Pull the users list and cross-reference against the Usage log. Anyone with a
paid tier and no activity for a full cycle is a downgrade candidate:

- No activity at all: drop to Viewer (free). They keep app access.
- Viewing dashboards but never using the agent: Viewer is the right tier.
- Building nothing but running agent threads: Editor should be Explorer,
  saves $35/month per person.

Downgrade is not a punishment and does not delete anything. Say that in the
message, or people will resist it.

## 4. Pulling the data instead of reading the page

Thread-level metadata (thread details, user, credit consumption) can be pulled
via the Hex CLI or API rather than clicking through the UI. Credit *allocation*
is UI-only, but credit *consumption* is queryable, which is what the audit
actually needs. Hex's Admin REST API also covers users and groups on Team and
Enterprise plans, so the seat side of this audit can be scripted.

No workspace API token is configured on Royce's machine as of 2026-08-20. If
this audit becomes recurring, that token is the first thing to set up, and it
can be configured to never expire.

## 5. Report

To Jordan, monthly:
- current-cycle spend against $1,000, with the month-over-month delta
- allocation changes since last audit and who approved each
- seats recommended for downgrade, with the monthly saving
- anything that hit a cap twice in one cycle, which usually means the person
  needs agent-usage coaching rather than more credits
