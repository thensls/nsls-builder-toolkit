# hex-access

Handling Hex credit top-ups and license requests at NSLS.

**Who this is for:** whoever is fielding "I'm out of Hex credits" or "can my
team get Editor" in the BI Squad channel. Currently Rumzy, and whoever is on the
BI Squad on-call rotation.

**What it does:** works out whether a request is a credit problem or a license
problem, checks it against the training gate and the $1,000/month pool, picks a
number, and hands over the exact clicks. It does not execute anything. Hex has
no API for credit allocations, so a human does the change in Settings.

**The three things people get wrong:**
1. Topping up credits for someone on Viewer, who cannot use the agent at any
   credit level.
2. Not realizing "add-on credits per cycle" renews every month rather than
   being a one-time top-up.
3. Confusing Hex credits with Snowflake credits, which are a different bill
   entirely.

Source: the Hex operations walkthrough on the BI Team sync, 2026-08-13
(https://fathom.video/calls/782386521?timestamp=1167), plus Hex's own admin
documentation at https://learn.hex.tech/docs/administration/credits.

See `SKILL.md` for the runbook and `reference/monthly-audit.md` for the
cycle-start audit.
