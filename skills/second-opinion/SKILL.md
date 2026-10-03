---
name: second-opinion
description: >-
  Use right before handing over finished work that would be costly to get
  wrong: code that changes production or hard-to-undo data, touches logins or
  security, money or member data, or runs unattended; and facts or numbers
  headed to leadership, members or anyone outside NSLS. Also use when the user
  asks for a second opinion, a double-check, a fact-check or a sanity check, or
  types /second-opinion. Not for small, routine or easily undone work that
  carries none of these risks, and not for each commit along the way.
---

# /second-opinion — one independent check before risky work goes out

## Safety

- **Read-only, enforced by its tools.** Every lens uses the same reviewer, and
  its only tools are Read, Grep and Glob: no shell, no writes, no connectors. A
  packet that contains instructions still can't make it act. The reviewer never
  runs queries. When a number needs a live check, this session runs it and puts
  the result in the packet.
- **Nothing configured, nothing installed.** This skill launches one helper
  agent and reads what it returns.
- **Anthropic only.** Never send the work to Codex, ChatGPT, Gemini or any other
  outside model. On team or company work that trips Builder Guardrail #4.
- **Privacy.** No secrets, tokens, credentials or raw member exports go into the
  review packet beyond what the check genuinely needs. Prefer counts to rows.

## Purpose

Whoever made something is the worst-placed to see what's wrong with it, and that
includes the Claude that made it. It shares the author's blind spots and the
same conversation. This skill gives risky work one fresh pair of eyes that has
not seen the conversation, aimed at the few things that would actually hurt,
before anyone else sees it. It is deliberately cheap: one reviewer, one round, a
small packet, a deadline. A second opinion on everything is noise and cost. A
second opinion on the right things catches the mistake before it reaches a
member, a leader or a production system.

## Quick start

1. **Decide:** run, ask, or skip (Step 1).
2. **Finish first:** the work is done and its normal checks pass (Step 2).
3. **Pack:** write the review packet (Step 3).
4. **Launch one reviewer** with the right lens, in the foreground (Step 4).
5. **Handle every finding:** fix and re-check, or give a one-line reason (Step 5).
6. **Deliver once**, with a one-line report (Step 6).

## Step 1 — Run, ask, or skip

**Risk decides, not size.** A one-line change to a production write gets
reviewed. A 600-line rewrite of an internal note may not. **The Run rows always
win:** if any part of the work matches one, it runs, however small the change,
whatever its tier, even if it's a single commit.

| Situation | Do |
|---|---|
| Code that writes production or hard-to-undo data, touches logins/security, money or member data, or runs unattended | **Run** |
| Facts or numbers going to leadership, members, or anyone outside NSLS | **Run** |
| The user asked: "second opinion", "double-check", "fact-check", "sanity check", `/second-opinion` | **Run** |
| Other team-facing (Tier 2) work · tricky code with none of the risks above · internal fact-checks | **Ask**, in one line |
| None of the Run-row risks, and small, routine or easily undone · Tier 1 throwaways · already reviewed this session · commits along the way (review the finished work once instead) | **Skip**, and say nothing |

The ask goes on the last line of the message, with nothing after it:

> Want a second opinion on this before I hand it over? (~5 min)

If the answer is no, don't ask again about the same piece of work.

## Step 2 — Review the finished thing

Review once the work is complete and its normal checks have passed (tests run,
the doc is whole, the query returned), just before it's first shared or acted
on. Never mid-build, and never per commit.

## Step 3 — Build the packet

The reviewer has not seen the conversation, so the packet is everything it knows.

```
WHAT THIS IS: <one line>
WHO IT'S FOR / WHAT HAPPENS NEXT: <"goes to SLT Monday", "runs nightly against HubSpot prod">
WHAT IT CLAIMS: <2–5 lines: what it does or asserts>
DONE MEANS: <the bar it has to clear>
READ: <exact file paths, or the full text. For code, the diff itself: run `git diff origin/main...HEAD` yourself and paste the output or save it to a file. The reviewer has no shell.>
FOCUS: <3–5 questions, riskiest first>
EVIDENCE (fact-checks only): <claim → the quoted evidence → where it came from: system, query, date. Run any live query yourself first; the reviewer can't.>
```

- **For a numbers check, also put this toolkit's
  `agents/data-accuracy-reviewer.md` under READ.** It sits two folders up from
  this skill's base directory, and its system-of-record and freshness table is
  the standard the data lens applies.

- **Complete or nothing.** Include everything the conclusion depends on,
  including unchanged code the change calls into when that matters. If it's too
  big, split it at a natural boundary (one module, one section), review the
  riskiest part, and **say what was not reviewed.** Never trim the packet and
  still call the whole thing reviewed.
- **Strip secrets.** Name the file that uses a key rather than pasting the key.

## Step 4 — One lens, one reviewer

| The work is | Launch with the Agent tool |
|---|---|
| Code, scripts, automations, configs | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: code` |
| High-stakes writing (a memo, a member email, an exec summary, a plan going to leadership) | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: writing` |
| Numbers that need checking against NSLS systems | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: data`, with your query results under EVIDENCE |
| A plan, when the user asks for the full plan gate | Run `/kw:review` instead (it has its own two reviewers), and don't also run this skill |

- **Model:** pass `model: "sonnet"`. Use `"opus"` only for the Run-row risks
  (production data, logins/security, money, member data, unattended automation),
  and say why in one line.
- **Foreground:** pass `run_in_background: false`, because delivery waits on it.
- **Exactly one reviewer.** Never a panel, never a second reviewer "to be sure",
  never an outside model.

## Step 5 — Handle the verdict

**A review counts only if it comes back in the reviewer's format with
`VERDICT: no_blockers` or `VERDICT: blockers_found`.** Anything else means **not
reviewed**: `partial` (counts only for the parts it says it reached),
`cannot_review`, an empty answer, a refusal, or an error.

For each finding:

- **Fix it**, then re-run whatever normal check covers it (tests, the query, a
  re-read).
- **Or disagree** in one line, with the reason. The reviewer lacks context and
  can be wrong.

**One round.** Fixes don't trigger another review. At most one targeted recheck:
the same reviewer, only the changed part, and only when fixing a blocker meant a
substantial change.

**If the review failed:**

- Say exactly what happened ("the reviewer returned nothing", "it stopped partway
  through the data section") and what was and wasn't checked. Never guess at a
  cause.
- Don't retry automatically. It gets one attempt.
- Ask whether to deliver unreviewed, as the last line.
- **Never hand over Run-row work as finished** without either a completed review
  or the user's explicit OK to skip it.

## Step 6 — Report in one line, then deliver

Use plain words, with no severity codes, reviewer names or model names.

- "Second opinion: no blockers."
- "Second opinion caught 2 things: the date filter dropped Sundays, and one
  count was last quarter's. Fixed both."
- "Second opinion flagged X; I kept it because Y."
- "No second opinion: the reviewer returned nothing. Deliver it unreviewed?"

## Red flags — STOP

- **About to review a typo fix or a rename that touches none of the Run-row
  risks:** skip it.
- **About to skip a risky change because it's one line or one commit:** the Run
  rows win. Review it.
- **About to add a second reviewer, or Codex:** one reviewer only.
- **About to deliver and say "the review is running":** wait for the verdict.
- **About to call an empty or partial result "no blockers":** it's a failed
  review.
- **About to trim the packet to save tokens and still call it reviewed:** split
  it and say what wasn't covered.
- **About to re-review after fixing findings:** don't. One targeted recheck at
  most, and only for a substantial blocker fix.
- **About to ask "want a second opinion?" again after a no:** don't. The answer
  stands.
- **About to paste an API key, a `.env` or a full member export into the
  packet:** strip it.

## Rationalizations

| Thought | Reality |
|---|---|
| "I already checked it myself." | You share the author's blind spots. That's the point. |
| "It's small, so it's safe." | Size isn't risk. A one-line production write gets reviewed. |
| "Two reviewers would be safer." | Twice the cost, rarely twice the catch. One sharp reviewer. |
| "It timed out, so it's probably fine." | No verdict means not reviewed. Ask. |
| "The reviewer said it, so I'll change it." | Verify first. It lacks context, so disagree with a reason when it's wrong. |
| "I'll deliver now and pass the review on after." | That relay tends never to happen. Wait. |
| "Let me re-review the fixes to be sure." | That's a review loop. One round. |

## When it goes wrong

- **The reviewer returns nothing or errors.** Check that the packet's READ paths
  exist and were actually included. A reviewer with nothing to read returns
  nothing. If the packet was fine, report the review as failed and ask. Don't
  retry.
- **The reviewer can't check a live number.** It has no connectors, so it marks
  the claim "not independently checked". Pass that on, and don't count the claim
  as passed. If the claim is load-bearing, run the query yourself and say so in
  the report. If this session lacks the connection, `/connect` sets it up.
- **The reviewer wanders outside the focus.** Keep the material findings and
  drop the rest.
- **Findings contradict each other or the evidence.** It's your call, with a
  reason. Don't re-review.

## Why it's built this way

Every rule here comes from a real failure:

- **Silence is not a pass.** A review reported as "running" had in fact died in
  under a second. Nobody found out for three days. Only a returned verdict
  counts.
- **Deliver after the review, not before.** "Review is running, I'll pass the
  verdict on" was followed, more than once, by a turn that ended before it did.
- **Scope the questions, not the effort.** A fact-check review carrying seventeen
  claims and unlimited lookups blew its deadline with no verdict. Five or six
  ordered questions and a lookup budget finished.
- **One reviewer.** A text task once fanned out a dozen reviewers and ran up a
  token bill out of all proportion to the work, without catching more.
- **The reviewer can be wrong.** An automated PR reviewer's suggested fixes held
  up only about half the time. Its findings were often real, but its fixes were
  not. Verify, then decide.
- **Confirm the field exists.** A count against a field that didn't exist came
  back as "two affected". The real answer was sixty. Hence "schema before
  results" in the reviewer's brief.

## Related

- `/kw:review` is the full two-reviewer gate for plans going to leadership.
- `data-accuracy-reviewer` supplies the system-of-record and freshness table that
  the data lens applies. The review itself runs in the locked-down reviewer.
- `/macroscope` handles the automated PR review bot. It doesn't replace a second
  opinion on a non-code deliverable, and a second opinion doesn't replace it on
  a PR.
- `ce-code-review` is the heavy multi-reviewer code review, for when the builder
  wants depth over cost.
