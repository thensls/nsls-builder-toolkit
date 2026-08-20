---
name: hex-access
description: >-
  Use when someone asks for Hex credits or a credit top-up, says they have run
  out of credits or are getting blocked in a Hex thread, asks for Hex access or
  a Hex login, or when a manager asks to upgrade their team from Explorer to
  Editor. Also use when auditing Hex spend against the monthly budget or
  stripping inactive Hex users. Trigger phrases: hex credits, top off credits,
  top up credits, add-on credits, out of credits, credit allocation, hex access,
  hex license, hex seat, upgrade to editor, explorer license, hex user request,
  hex billing, hex audit.
---

# hex-access: Hex Credits and Licenses at NSLS

## Guardrails (read first)

**Tier 1 (read-only, no friction):** reading the credits table, the usage log,
the users list, the current-cycle spend, and a user's current tier. Working out
what a request should cost. Drafting the reply to the requester.

**Tier 2 (human executes, Claude prepares):** every credit and license change.
**There is no API for credits.** Hex exposes an Admin REST API for users and
groups, but credit allocations are Settings-only. Claude's job is to decide the
right number and the right tier, then hand the operator the exact clicks.
Confirm the person and the number out loud before the operator commits.

**Tier 3 (never without an explicit decision from Jordan Tannenbaum):**
- Changing the **workspace default** credit limit. That moves everyone at once.
- Any single allocation at or above **1,000 credits/month** ($500/month for one
  person, half the entire monthly pool).
- Setting a limit to **Unlimited**.
- Granting a paid seat to anyone who has not completed the Hex training.
- Granting a seat on a non-`@nsls.org` address.

## Purpose

Turns a one-line Slack ask ("I'm out of Hex credits") into a correct, costed,
policy-checked decision in about two minutes, without the operator having to
remember what a credit is worth, whether the request fits the monthly budget, or
whether the person is even on a tier that can spend credits in the first place.
The most common failure this prevents is treating a **license** problem as a
**credit** problem and topping up an allocation for someone who was never able
to use the agent to begin with.

## What this is not

This is not automation. Claude cannot add credits, cannot change a seat, and
should not claim it did. The deliverable is a decision plus a reply, and the
operator (currently Rumzy Khalil, or whoever is on the BI Squad on-call
rotation) clicks it through in the Hex UI.

## The money model

| Thing | Cost | Notes |
|-------|------|-------|
| Guest, Viewer | free | Can interact with published apps. Cannot use the agent. An account by itself costs nothing. |
| Explorer | $40/user/month | The tier that unlocks AI credits. Default for new invites. Right for most staff. |
| Editor | $75/user/month | Everything Explorer has, plus creating projects and building dashboards. |
| 1 credit | $0.50 | |
| Editor seat allotment | 40 credits/month | Included with the seat. Roughly $20 of agent usage. |
| Explorer seat allotment | 10 credits/month | Included with the seat. Runs out fast. |
| Monthly top-up pool | $1,000/month | Set by Jordan. Auto top-up refills the pool below 25 credits and stops at the $1,000 limit. Read the live figure, never a remembered one. |
| Typical power user | ~500 credits/month | Confirmed sufficient by Jordan under aggressive daily use. |

Licensing and credits are separate bills. A tier grants a monthly credit
allotment; add-on credits are what a user gets **on top** when they burn through
it.

**The included allotments are small on purpose.** Hex began metering AI credits
at 40/Editor and 10/Explorer per month (announced by Jordan in #bi-squad on
2026-07-31). At 10 credits a month, an Explorer who actually uses the agent is
out within days. Treat a top-up request as the normal course of business rather
than as a red flag, and expect the gap between 10 and a 500-credit power user to
be covered entirely by add-on credits.

Requests arrive in **#bi-squad** (`C091LF62BSB`), which is where Jordan pointed
everyone. They come in freeform ("Top up please!!"), often as thread replies
rather than new messages, and frequently mix a license ask and a credit ask in
one sentence. Kimberly's 2026-08-13 request is the canonical example: four
people, project-creation rights, and "very limited credits," all in one line.

## Step 0: Work out what is actually being asked

Three different requests arrive worded the same way. Sort it before touching
anything:

1. **"I'm out of credits" / "the agent stopped responding."** Usually a credit
   cap. Go to Step 1.
2. **"I need Hex access" / "I can't build anything."** A license question, not a
   credit one. Go to the Licenses section.
3. **"Am I burning credits by querying?"** If the query is against Snowflake
   from outside Hex, this is **Snowflake** credits, a completely different bill
   (roughly $3/hour of warehouse runtime, owner Brandon Evans). One person's
   usage does not move that number. Do not open the Hex credits page for this.

## Step 1: Gate checks before any spend

- **Training first.** Nobody gets credits or a paid seat before completing the
  Hex training. This is a standing gate, not a formality.
- **`@nsls.org` only.**
- **Who is asking?** A manager asking on behalf of their own team is
  pre-approved for Editor (see Licenses). An individual asking for a large
  allocation is not.
- **Is the person even on Explorer or above?** A Viewer cannot spend credits at
  all. Raising their allocation changes nothing and they will be back tomorrow.

## Step 2: Read the current state

**Go straight there:**
https://app.hex.tech/019847ea-73c2-7002-9a3a-cff99736a83d/settings/credits

(Or navigate: Hex → **Settings**, bottom left → **Plan and billing** →
**Credits**.)

Read four numbers off that page before deciding anything:

| Field | What it tells you |
|-------|-------------------|
| **Top-ups** ($ spent / $1,000 spend limit) | The binding constraint. When this hits $1,000, auto top-ups stop and everyone past their seat grant is blocked. |
| **Add-on credits left** | The workspace pool balance right now. Auto top-up refills it when it drops below 25 credits, up to the monthly spend limit. |
| **Users past monthly credit grant** | How many people are already living on add-on credits. |
| **Add-on credits used** | Consumption this cycle. |

Do not trust a spend figure written down anywhere, including in this skill. It
moves fast. On 2026-08-13 the workspace was at $475 of $1,000. Seven days later
it was at **$775 with 47.5 credits left in the pool** and four days remaining in
the cycle. Open the page.

**Usage log** on the same page is where per-user consumption detail lives, and
it is what the monthly audit runs on. See `reference/monthly-audit.md`.

## Step 3: Pick the number

- Start at the **low end** and raise again if they come back. Do not front-load
  a large allocation because the person sounds frustrated.
- **+100 credits ($50/month)** is the routine bump. Rumzy raised Marissa from
  500 to 600 this way.
- **500/month** is the established power-user baseline. Landing there needs no
  discussion.
- **1,000/month or more** for one person is a conversation with Jordan, not an
  approval. That is half the pool for one seat.
- Remember a limit is a **cap, not a spend**. Raising a cap costs nothing by
  itself; only usage bills. The real budget control is the $1,000 pool, not the
  individual number. This is why routine bumps are low-risk and why the pool is
  the thing to watch.

## Step 3.5: Caps oversubscribe the pool, and that is the thing to watch

Per-user caps are allowed to add up to far more than the pool can fund. As of
2026-08-20 the allocations on the page totalled roughly 3,400 credits/cycle,
which is about $1,700 of caps drawing on a $1,000 pool.

That is not a misconfiguration, it is how the controls are meant to work. Caps
stop any one person running away with the budget; the pool is what actually
limits spend. The consequence is the part that catches people out: **the pool
can run dry while everybody is still under their individual cap.** When it does,
the block lands on whoever happens to submit the next prompt, not on the heaviest
user.

So when a request arrives late in a cycle, the question is not "does this person
deserve more" but "is there anything left in the pool." Check the top-ups figure
first, and if the pool is close to the limit, say so in the reply instead of
quietly raising a cap that cannot be funded.

The workspace default is **No access**, so a new user with no explicit
allocation gets only their seat grant (40 Editor, 10 Explorer) and then stops.

## Step 4: The two UI paths

**If the user has no allocation yet:** click the user in the credits table, then
**Add allocation**.

**If "Add allocation" is greyed out:** that means they already have a monthly
allocation. This is the single most confusing moment on the page. Use the
**three-dot menu → Edit → add-on credits per cycle**. Options are Unlimited,
Custom amount, or No access. Use Custom amount.

## Step 5: The recurrence trap (say this out loud every time)

**"Add-on credits per cycle" is recurring, not a one-time top-up.**

Raising someone from 500 to 600 "just to get them through the month" sets their
new monthly baseline at 600, auto-renewing every cycle until somebody changes it
back. That is exactly what happened with Marissa on 2026-08-13.

If the bump is genuinely for one crunch period, say so in the reply and set a
reminder to revisit at the start of the next cycle. Otherwise the pool quietly
ratchets upward and the $1,000 ceiling arrives without anyone deciding to spend
it.

Related rollover behavior, which is easy to get backwards:
- **Per-seat monthly grants reset each billing cycle** and do not roll over.
- **Auto top-up credits do roll over** to the next cycle.
- Committed add-on credits from an annual contract expire at the end of the
  contract cycle.

## Step 6: Precedence, if the number does not take effect

Credit limits resolve **User > Group > Workspace default, and the highest limit
wins.** A generous group limit will silently override a tighter individual one.
If a change appears to do nothing, check the group before assuming the UI failed.

## Licenses

Hex → **Settings** → **Users** → invite a new user. Start everyone at
**Explorer**.

**Standing policy, set by Jordan on 2026-08-13:**
- A manager requesting Editor for their own team: **grant it, do not escalate.**
  First case was Kimberly Campbell's team (Kimberly, Kara, Alejandro, Eliana).
- A request for roughly 20 seats at once: have the conversation first.
- New CS hires get Hex by default.
- **Audit monthly** and strip users who are not really using it. That audit is
  the counterweight that makes the grant-freely policy safe. If it is not
  running, the policy is quietly just "grant freely."

Explorer is the tier most staff need (drill-downs and agent Q&A). Editor is for
people who build.

## Diagnostic loop

**"The agent stopped working for me."**

1. **Is the run blocked or did it just end?** A depleted user is blocked from
   submitting *new* prompts. A run already executing when credits run out
   finishes normally. If their last run completed and the next will not start,
   that is the credit cap.
2. **Check their tier before their allocation.** Viewer or Guest cannot use the
   agent at any credit level. This is the misdiagnosis to rule out first.
3. **Check group and workspace precedence** (Step 6) before concluding the
   allocation is wrong.
4. **Check the pool headroom** at the top of the Credits page before raising.
5. **Raise on the low end**, tell them it is recurring, note the revisit date.
6. **Still blocked?** Look at the Usage log for that user. A single expensive
   run pattern (heavy model on repeated first passes) burns a month of credits
   fast, and the fix is coaching on agent usage, not more credits. The training
   covers this: run heavy first passes on pricier models, then iterate cheap.

## Rationalizations to refuse

| The thought | The correction |
|-------------|----------------|
| "They're blocked and it's urgent, just give them 1,000." | Urgency is not authority. Low-end bump now, conversation with Jordan if they come back. |
| "It's only a cap, so the number doesn't matter." | The cap is what makes the pool predictable. An unmonitored cap becomes real spend. |
| "It's a one-time top-up, no need to mention renewal." | It is not one-time. Per-cycle means every cycle. Say it every time. |
| "I'll just set Unlimited to stop the back-and-forth." | Unlimited is a Jordan decision, not a convenience. |
| "They asked for credits so the answer is credits." | Half of these are license problems. Check the tier first. |
| "I can probably do this through the Hex API." | There is no credits API. Users and groups have one; credits do not. |
| "They haven't done the training but they're senior." | The gate is the gate. It exists because untrained users burn credits fastest. |

## Red flags (STOP)

- About to say Claude added, raised, or granted anything in Hex. Claude prepared
  it; a human clicked it.
- About to change the workspace default.
- About to grant a paid seat to a personal email address.
- About to quote a credit number without converting it to dollars.
- About to raise an allocation without checking the current-cycle headroom.
- About to top up someone whose tier you have not verified.

## Output

**To the requester** (Slack, plain and short): what they now have, that it
renews monthly, when it will be revisited, and one line on where to get help
(BI Squad Slack channel, or data team office hours Thursdays 1pm ET).

**To the log:** who, what tier, how many credits, the dollar delta, who
approved, and the date. Without this the monthly audit has nothing to work from.

**To Jordan, monthly:** current-cycle spend against the $1,000 pool, the change
list since last month, and any allocation that has been quietly ratcheting.

## Related

- Setup and connections: `/connect`
- Cross-system analysis: `/data-intel`
- The sibling flow for HubSpot seats: `hubspot-user-provisioning`
- Snowflake roles for skills that query the warehouse: ask Brandon Evans. The
  convention discussed on 2026-08-13 is to name a minimally-privileged role
  after the skill that needs it.
- A centralized BI access matrix (HubSpot, Snowflake, Hex, dbt) was ticketed by
  Jordan for the sprint following 2026-08-13. When it lands, it supersedes the
  tier defaults in this skill and this skill should point at it.
