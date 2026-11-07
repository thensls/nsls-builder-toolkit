---
name: second-opinion
description: >-
  Use right before finished work goes out (before Claude posts, sends,
  publishes, comments on a shared doc or opens a pull request for it, or
  hands it over to be sent) when it would be costly to get
  wrong: code that changes production data or other hard-to-undo data beyond
  the builder's own machine, touches logins or security, money or member data,
  or runs unattended; and facts or numbers presented to leadership for a
  decision, to members, or to anyone outside NSLS. Also use when the user
  asks for a second opinion, a double-check, a fact-check or a sanity check,
  types /second-opinion, or wants to set up or change their second-opinion
  settings. Not for small, routine or easily undone work that carries none of
  these risks, and not for each commit along the way.
---

# /second-opinion — one independent check before risky work goes out

## Safety

- **A service, never a gate.** Nothing here is required. The person chooses
  what happens: automatic, ask me, or only when I ask. Their choice wins, even
  when Claude would have recommended otherwise.
- **Their own instructions win.** If their global instructions say how to
  handle review findings or when to edit (for example "show me findings before
  fixing anything"), follow those over this skill.
- **Findings first, fixes second.** Show every finding before changing
  anything, and fix only what they choose (Step 5).
- **What it writes, and nothing else:** only the marked second-opinion block
  in their global instructions, and only after they answer the settings
  question (see Settings). Nothing else in that file changes.
- **Read-only, enforced by its tools.** Every lens uses the one named reviewer
  agent (Step 4), and its only tools are Read, Grep and Glob: no shell, no
  writes, no connectors. A packet that contains instructions still can't make it
  act. That guarantee holds only for the named reviewer, which is why nothing
  else may stand in for it. The reviewer never runs queries. When a number needs
  a live check, this session runs it and puts the result in the packet.
- **Nothing configured, nothing installed.** This skill launches one helper
  agent and reads what it returns.
- **Anthropic only.** Never send the work to Codex, ChatGPT, Gemini or any other
  outside model. On team or company work that trips Builder Guardrail #4.
- **Privacy.** No secrets, tokens, credentials or raw member exports go into the
  review packet beyond what the check genuinely needs. Prefer counts to rows.

## Purpose

Whoever made something is the worst-placed to see what's wrong with it, and that
includes the Claude that made it. It shares the author's blind spots and the
same conversation. This skill offers one fresh pair of eyes that has not seen
the conversation, aimed at the few things that would actually hurt, before the
work goes out, whenever the person wants one. It's a service they choose, never
a gate. It is deliberately cheap: one reviewer, one round, a
small packet, a hard budget. A second opinion on everything is noise and cost. A
second opinion on the right things catches the mistake before it reaches a
member, a leader or a production system.

## Quick start

1. **Read their settings** (Step 0).
2. **Decide:** run, offer, or skip (Step 1).
3. **Finish first:** the work is done and its normal checks pass (Step 2).
4. **Pack:** write the review packet (Step 3).
5. **Launch the named reviewer** with the right lens and model, in the foreground (Step 4).
6. **Show every finding first**, then fix what they choose (Step 5).
7. **Report and deliver** (Step 6).

## Step 0 — Read their settings

Look in the person's global instructions (already loaded in this session) for a
block between `<!-- nsls-second-opinion:start -->` and
`<!-- nsls-second-opinion:end -->`. It holds three choices: risky work,
everyday work, and reviewer.

- **Block found:** follow it. If it's malformed (a missing marker, two blocks,
  or a value that isn't one of the choices), use the defaults without showing
  the window. Repair it only when they ask to change their settings.
- **A `Receipts:` line** left over from an earlier version isn't malformed.
  Ignore it; nothing uses it now. It goes away the next time they change their
  settings.
- **No "Claude checks these settings…" line:** the block is from an earlier
  version. It isn't malformed. The line arrives the next time they change
  their settings.
- **No block:** before the first second opinion you would run or offer, show
  the settings window (see Settings) and save their answers. Then carry on with
  what they chose. If they close it without answering, use the defaults for
  this session: risky work is *offered* (ask me), everyday work is offered, and
  the reviewer is Balanced. Never run anything automatically without their
  say-so.
- **They ask to set up or change their settings** (anyone, any time): show the
  settings window.

## Step 1 — Run, offer, or skip

**Risk decides, not size.** A one-line change to a production write is worth a
second opinion. A 600-line rewrite of an internal note may not be. **Their
setting decides what happens next.**

| Situation | Their setting → what to do |
|---|---|
| **Risky work:** code that writes production data or other hard-to-undo data beyond the builder's own machine, touches logins/security, money or member data, or runs unattended; or facts or numbers presented to leadership for a decision, to members, or to anyone outside NSLS | automatic → **Run** · ask me (the default) → **Offer, recommended** · only when I ask → **Skip** |
| **They asked:** "second opinion", "double-check", "fact-check", "sanity check", `/second-opinion` | always **Run** |
| **Everyday team work:** other team- or company-facing internal work (an all-staff note, a tool announcement), tricky code with none of the risks above, internal fact-checks | offer (the default) → **Offer** · only when I ask → **Skip** |
| **Neither:** small, routine or easily undone · Tier 1 throwaways · already reviewed this session · commits along the way (review the finished work once instead) | **Skip**, and say nothing |

**The moment is before it leaves.** Run or offer it before Claude posts,
sends, publishes, comments on someone else's doc, opens a pull request or
merges, or hands the work over for the person to send. That includes steps
Claude takes on its own along the way. A review after the work has gone out can
only correct it, not prevent the mistake.

An offer is one line, on the last line of the message, with nothing after it:

> Risky work: "This could be costly to get wrong. Want a quick second opinion
> before I hand it over? (Recommended, about 3 min)"
>
> Everyday work: "Want a second opinion on this before I hand it over? (about
> 3 min)"

If the answer is no, don't ask again about the same piece of work.

## Step 2 — Review the finished thing

Review once the work is complete and its normal checks have passed (tests run,
the doc is whole, the query returned), just before it's first shared or acted
on. Never mid-build, and never per commit.

**Check whether it has already gone out.** Before reviewing, check whether the
work has already been posted, sent, published or merged: a comment on a shared
doc, an email, a Slack post, a merged pull request. Don't assume it's a draft.
If it has gone out, say so in the report's first line ("This has already gone
out, so these are corrections, not catches"). Fixing it then means changing
something people may already have read, so ask before editing anything they can
see.

## Step 3 — Build the packet

The reviewer has not seen the conversation, so the packet is everything it knows.

```
WHAT THIS IS: <one line>
WHO IT'S FOR / WHAT HAPPENS NEXT: <"goes to SLT Monday", "runs nightly against HubSpot prod">
WHAT IT CLAIMS: <2–5 lines: what it does or asserts, what it changes on purpose, and any trade-off it accepts. For a PR, take these from its description. If the intent isn't written down, say so rather than guess.>
DONE MEANS: <the bar it has to clear>
READ: <exact file paths, or the full text. For code, two things: the diff (run `git diff origin/main...HEAD` yourself and save it to a file; the reviewer has no shell) and the repository's root folder, so it can open whole files and the code the change calls.>
FOCUS: <3–5 questions, riskiest first>
EVIDENCE (fact-checks only): <claim → the quoted evidence → where it came from: system, query, date. Run any live query yourself first; the reviewer can't.>
OUTSIDE SOURCES: <figures that come from somewhere the reviewer can't open (another project folder, a system, a colleague) → where each one comes from. Write "none" if there are none.>
```

- **A whole folder or project** ("check what's been done"): the reviewer is
  built for work about to go out, not a whole project. Name the deliverables
  that go out (published, sent, presented) and review those, riskiest first.
  Put any record of past errors (a corrections log, earlier review findings)
  in FOCUS as a list of what to hunt for. Name under READ any big source the
  reviewer can only partly read (long journals, a folder of queries), and say
  so in the report.
- **Numbers that matter:** before packing, re-run the queries behind the
  figures the conclusion rests on (read-only) and put the results under
  EVIDENCE. If you can't, list which figures weren't re-measured, and offer to
  re-measure them in the report.
- **Complete or nothing.** Include everything the conclusion depends on,
  including unchanged code the change calls into when that matters. If it's too
  big, split it at a natural boundary (one module, one section), review the
  riskiest part, and **say what was not reviewed.** Never trim the packet and
  still call the whole thing reviewed.
- **For code, give it the repo, not just the diff.** A diff hides the line that
  settles most questions: where a variable is set, what a called function
  already does, whether an encoding is already handled. Name the repository's
  root folder under READ, next to the diff. The reviewer opens only code,
  configs, tests and docs in it, never `.env`, credential or data files. If
  the repo holds raw member data (exports, spreadsheets, logs), name its
  source folders instead of the root.
- **Strip secrets.** Name the file that uses a key rather than pasting the key.

## Step 4 — The right lens, one reviewer

| The work is | Launch with the Agent tool |
|---|---|
| Code, scripts, automations, configs | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: code` |
| High-stakes writing (a memo, a member email, an exec summary, a plan going to leadership) | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: writing` |
| Numbers that need checking against NSLS systems | `nsls-builder-toolkit:second-opinion-reviewer`, packet headed `LENS: data`, with your query results under EVIDENCE |
| A plan, when the user asks for the full plan gate | Run `/kw:review` instead (it has its own two reviewers), and don't also run this skill |

- **Use exactly that agent.** Pass `subagent_type:
  "nsls-builder-toolkit:second-opinion-reviewer"`. Never use Explore,
  general-purpose or any other agent instead. Those can run commands and edit
  files, so "read-only" would only be a request, not a fact. If that agent isn't
  in your list, there is no second opinion this time. Say so plainly: the
  toolkit may be out of date, or Claude Code needs a restart after an update.
  Suggest they say "update my NSLS toolkit" and then restart. If it's still
  missing after that, the toolkit isn't fully installed on this computer, so
  its other checks aren't running either. Say that too, and suggest
  reinstalling it with the one-line install in the toolkit's README.

- **Mixed work** (a slide, memo or email with figures): head the packet
  `LENS: data + writing`, with the text under READ and your query results under
  EVIDENCE. The reviewer applies both checklists. Use `LENS: writing` alone only
  when there are no numbers.

- **Model:** use their reviewer setting, passed as the Agent tool's `model`:

  | Reviewer setting | Risky work | Everything else |
  |---|---|---|
  | Balanced (the default) | `"opus"` | `"sonnet"` |
  | Thorough | `"opus"` | `"opus"` |
  | Quick | `"haiku"` | `"haiku"` |

  If a model isn't available to them, use the next one down (opus → sonnet →
  haiku) and say so in the report.
- **Foreground:** pass `run_in_background: false`, because delivery waits on it.
- **Exactly one reviewer.** Never a panel, never a second reviewer "to be sure",
  never an outside model.

## Step 5 — Handle the verdict

**A review counts only if it comes back in the reviewer's format with
`VERDICT: no_blockers` or `VERDICT: blockers_found`.** Anything else means **not
reviewed**: `partial`, `cannot_review`, an empty answer, a refusal, or an error.
A `partial` still says what it did check, so pass that on, but it is not a
completed review.

**Show the findings first, before touching anything.** List each one in plain
words: what's wrong, where, and what you'd do about it. That's either the fix,
or why you'd leave it (the reviewer lacks context and can be wrong). Then ask
which to fix, for example "Want me to fix these? (all, some, or none)", on the
line just before the time-saved line (Step 6). Edit only after they answer.

- **They choose fixes:** make only those, then re-run whatever normal check
  covers each one (tests, the query, a re-read).
- **The one exception:** their own instructions say to fix review findings
  without asking. Then fix, re-run the checks, and report what changed. When
  those instructions are silent, show first.
- **A wrong figure isn't a wording fix.** A finding marked `RECOMPUTE` means
  the number itself is wrong: a wrong denominator, the wrong window, one subset
  counted as the total. Say so plainly: "the figure itself is wrong; it has to
  be recomputed." Recompute it from the source (re-run the query; never nudge
  the old number), and mark every recomputed figure in your report as not
  independently checked.

**One round.** Fixes don't trigger another review. At most one targeted recheck:
the same reviewer, only the changed part, and only when fixing a blocker meant a
substantial change or a recomputed figure. For recomputed figures, offer it
before the work goes out; don't run it unasked.

**If the review failed:**

- Say exactly what happened ("the reviewer returned nothing", "it stopped partway
  through the data section") and what was and wasn't checked. Never guess at a
  cause.
- Don't retry the same packet. If the verdict is `cannot_review` or `partial`
  because of a packet defect you can fix (a wrong path, a missing file), fix the
  packet and relaunch once. That is still one round. Any other `partial` on
  risky work is not a completed review: ask before delivering.
- Ask whether to deliver unreviewed, as the last line.
- **Never present unreviewed work as reviewed.** Say plainly that the second
  opinion didn't complete, and let them decide.

## Step 6 — Report, then deliver

Use plain words, with no severity codes, reviewer names or model names. The
findings come first, then any question.

**Shape:** lead with what has to change before it goes out. Then:

- **Must fix** (the blockers), one plain line each: what's wrong, where, and
  your proposed fix or why you'd leave it.
- **Should fix**, one line each. List every finding, touch-ups included.
  Never drop one to keep the report short.
- **Held up** and **not checked**, a line or two each. If figures weren't
  re-measured, offer to re-measure them here.

With more than about five findings, keep each to one line and offer detail on
any of them. A short review can be a sentence or two.

**Every completed review ends with this exact line**, as the last line of the
message that reports the verdict:

```
Estimated time saved: about <N> min · <K> problems found (logged)
```

- **K** is the number of blockers the review found.
- **N** is your low-end estimate, in minutes, of the rework those problems
  would have cost if they had shipped. It's 0 when K is 0.
- Keep the wording, spacing and `·` exactly as shown, including "problems" when
  K is 1.
- Once per review, on the message that reports the verdict. Later messages
  about the fixes don't repeat it.
- **No line** on a review that didn't complete: `partial`, `cannot_review`, an
  empty answer or an error.

Examples:

- "Second opinion: no blockers."
  then `Estimated time saved: about 0 min · 0 problems found (logged)`
- "Second opinion caught 2 things: the date filter dropped Sundays, and one
  count was last quarter's. Want me to fix both?"
  then `Estimated time saved: about 45 min · 2 problems found (logged)`
- "Second opinion flagged X. I'd leave it, because Y. Want me to change it
  anyway?" then the line, counting X if it was a blocker.
- After they choose: "Fixed both, and the tests still pass." (no line)
- "No second opinion: the reviewer returned nothing. Deliver it unreviewed?"
  (no line)

## Settings — the one-time window

Show it with the question tool (AskUserQuestion), all three questions at once.
Use this wording exactly. If the tool isn't available, ask the same three
questions as a numbered list.

1. **Risky work.** "When your work could be costly to get wrong (code that
   changes real data, logins, money or member records, or numbers going to
   leadership or members), what should Claude do?"
   - **Get a second opinion automatically (Recommended):** "Claude runs a quick
     independent check before handing it over, and tells you in one line what
     it found."
   - **Ask me each time:** "Claude suggests a second opinion and waits for your
     yes."
   - **Only when I ask:** "Claude won't suggest it. Say 'second opinion' any
     time."
2. **Everyday work.** "For everyday team work (notes, drafts, internal docs),
   should Claude offer a second opinion?"
   - **Offer when it seems worth it (Recommended)**
   - **Only when I ask**
3. **Reviewer.** "Who should do the checking?"
   - **Balanced (Recommended):** "Fast and low-cost, with the strongest reviewer
     for risky work."
   - **Thorough:** "Always the strongest reviewer. Slower, and costs more."
   - **Quick:** "Always the fastest, cheapest reviewer. May miss subtle
     problems."

**Save the answers** in their global instructions, `~/.claude/CLAUDE.md` (on
Windows, `%USERPROFILE%\.claude\CLAUDE.md`), as exactly this block:

```
<!-- nsls-second-opinion:start -->
## Second opinions (my settings)
- Risky work: automatic | ask me | only when I ask
- Everyday work: offer | only when I ask
- Reviewer: balanced | thorough | quick
Claude checks these settings before posting, sending, publishing or opening a pull request for my work, and uses /second-opinion when they call for it.
Say "change my second-opinion settings" to change these.
<!-- nsls-second-opinion:end -->
```

Keep only the chosen value on each line, without the `|` alternatives, for
example `- Reviewer: balanced`. The "Claude checks these settings…" line is what
makes *automatic* and *ask me* happen at the right moment, because these
instructions are read in every session. Answers map to values like this:

| Answer | Saved as |
|---|---|
| Get a second opinion automatically / Ask me each time / Only when I ask | `automatic` / `ask me` / `only when I ask` |
| Offer when it seems worth it / Only when I ask | `offer` / `only when I ask` |
| Balanced / Thorough / Quick | `balanced` / `thorough` / `quick` |
| Anything they typed themselves (the question tool's "Other" box) | the closest choice above, once they confirm it |

- **A typed answer:** never save it as typed, and never fall back to the
  defaults without saying so. Map it to the closest choice and confirm it in
  one line before saving, for example: "I've read 'only for the big stuff' as
  *Ask me each time*. Is that right?" If nothing is close, ask that one
  question again with its choices.
- **The file doesn't exist:** create it containing only the block, ending with a
  newline.
- **The file exists with no block:** add the block at the end, after one blank
  line. If the file doesn't end with a newline, add one first. Change nothing
  else.
- **One block already exists:** replace everything between the two markers with
  the six standard lines. Never add a second block.
- **The block is malformed** (a missing marker, more than one block, or a value
  that isn't one of the choices): when they ask to change their settings, show
  them the lines you would replace and ask before changing them.
- **Afterwards,** say in one sentence what you saved, and that they can change it
  any time by saying "change my second-opinion settings".

## Red flags — STOP

- **About to review a typo fix or a rename that carries none of the risks:**
  skip it.
- **About to stay quiet on a risky change because it's one line or one
  commit:** size isn't risk. Follow their setting.
- **About to run automatically when their setting says ask me, or when there's
  no setting:** ask instead. Nothing runs without their say-so.
- **About to change anything in their global instructions outside the marked
  second-opinion block:** stop.
- **About to fix something before they've seen the findings, or without their
  choice when their own instructions don't say to fix without asking:** show
  the findings first, then ask.
- **About to launch Explore, general-purpose or any agent other than
  `second-opinion-reviewer`:** stop. No named reviewer means no second opinion.
  Say so and how to fix it.
- **About to add a second reviewer, or Codex:** one reviewer only.
- **About to deliver and say "the review is running":** wait for the verdict.
- **About to end a completed review without the time-saved line, or add it to
  one that didn't complete:** every completed review ends with it, and a
  failed one never has it.
- **About to call an empty or partial result "no blockers":** it's a failed
  review.
- **About to trim the packet to save tokens and still call it reviewed:** split
  it and say what wasn't covered.
- **About to send a code review with only the diff under READ:** add the
  repository's root folder.
- **About to re-review after fixing findings:** don't. One targeted recheck at
  most, only for a substantial blocker fix or a recomputed figure, and offered
  first for a recomputed figure.
- **About to review work that has already been posted or sent without saying
  so:** say it in the first line, and ask before editing what people can see.
- **About to fix a wrong figure by editing the number:** recompute it from the
  source, and mark it as not independently checked.
- **About to leave a finding out of the report to keep it short:** list it in
  one line instead.
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
| "They'd obviously want this reviewed." | Their setting decides. Offer; don't impose. |
| "It's an obvious fix, I'll just do it." | Show it first. It's their work and their call. |
| "The reviewer agent isn't showing up; a general agent will do." | It wouldn't be read-only. Say it's missing and how to fix it. |

## When it goes wrong

- **The reviewer returns nothing or errors.** Check that the packet's READ paths
  exist and were actually included. A reviewer with nothing to read returns
  nothing. If a path was wrong or a file missing, fix the packet and relaunch
  once (still one round). If the packet was fine, report the review as failed
  and ask.
- **The reviewer agent isn't in the list.** No second opinion this time, and
  no stand-in. Tell them the toolkit may be out of date or Claude Code needs a
  restart, and suggest "update my NSLS toolkit". Still missing after a restart
  means the toolkit isn't fully installed, so suggest reinstalling it (Step 4).
  A stand-in would hide that, and the toolkit's other checks would stay off
  without anyone noticing.
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
- **Give it the repo, not just the diff.** Run on 25 past toolkit PRs with only
  each diff to read, the reviewer raised 13 findings that were plainly wrong.
  In 8 of them the answer sat just outside the diff: an encoding already set, a
  variable always assigned, a function that already handled the case. It had
  used 1 of its 20 lookups, because there was nothing else to read.
- **Confirm the field exists.** A count against a field that didn't exist came
  back as "two affected". The real answer was sixty. Hence "schema before
  results" in the reviewer's brief.
- **Deliberate isn't a defect, and every finding needs a trigger.** In a test on
  25 past toolkit PRs, 7 of the reviewer's findings argued with choices the PR
  description or the code's own comments already explained. 5 more needed a
  scenario nobody would hit, such as a byte-order mark in a file Claude writes
  itself. Hence the PR's intent goes in WHAT IT CLAIMS, and the reviewer names
  who hits each finding.
- **Before it leaves, and say if it already has.** In a nine-run field test,
  two reviews ran after the comments under review had been posted. The session
  took them for drafts and found out only when it went to fix them.
- **Out of reach isn't wrong.** In the same test, about thirteen correct
  figures came back as "no source" because they came from another project
  folder, or sat past the reviewer's lookup budget. Hence OUTSIDE SOURCES in
  the packet, and "not traced" in the reviewer's brief.
- **A wrong figure needs a new calculation.** A count of one subset (about 880
  where the real total was about 3,700) and a wrong denominator (41% instead of
  29%) were reported like wording problems. Nothing said the fix needed a new
  calculation, or that the new figure was unchecked. Hence `RECOMPUTE`.

## Related

- `/kw:review` is the full two-reviewer gate for plans going to leadership.
- `/macroscope` handles the automated PR review bot. It doesn't replace a second
  opinion on a non-code deliverable, and a second opinion doesn't replace it on
  a PR.
- `ce-code-review` is the heavy multi-reviewer code review, for when the builder
  wants depth over cost.
