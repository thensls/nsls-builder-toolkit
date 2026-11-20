---
name: kb-article
description: >-
  Claude Code only.
  Create or edit articles in the NSLS internal Knowledge Base at info.nsls.org/internal.
  Use when someone says "create a kb article", "new knowledge base article", "write an
  SOP", "document this process for the team", "update a kb article", "edit the kb",
  "add to the internal kb", or wants to capture a process or how-to for staff. Also use it
  to look things up in the KB while working ("check the kb", "what's our process for",
  "who owns", "who's the expert on").
---

<!-- claude-code-only:start (same words in every skill that has this note; change them in _shared/references/skill-surfaces.json) -->
> **Claude Code only.** This skill needs the person's own computer, so check
> where you are first, going by what your own instructions say you are running in.
> In **Claude Code** (a terminal, or the Code tab in the Claude app), skip this
> note. In **an ordinary Claude chat or a Cowork task** (its files live in a
> sandbox such as `/sessions/...`, not on their computer), stop and follow
> nothing else in this skill. If the person asked for this skill, or what they
> want can't be done here without it, reply with only this sentence:
> "This skill only works in Claude Code on your computer, so switch to Claude Code (the Code tab in the Claude app) and run it there."
> Otherwise don't mention this skill; help the way you would without it.
> Unsure which? Run `echo "$CLAUDE_CODE_ENTRYPOINT"` (PowerShell:
> `$env:CLAUDE_CODE_ENTRYPOINT`): `local-agent` is Cowork, and any other
> answer, blank included, is Claude Code. No way to run a command means chat.
<!-- claude-code-only:end -->

# KB Article

Write and update articles on the internal Knowledge Base (`https://info.nsls.org/internal`).
`scripts/kb.py` sends everything to the KB service. **Nothing goes live from here.** After a
submit, Slack takes over and the right person clicks Publish or Approve.

- Content rules (sections, voice, HTML): **`references/style.md`**. Read it before drafting.
  Danielle Mariani owns it.
- Member-facing articles for info.nsls.org/help use the `help-center-article` skill instead.
  If a member could read it, it belongs there.

Run the script from this skill's folder, for example
`python3 <skill folder>/scripts/kb.py search hubspot user`.

**First time on a computer: sign in.** It takes two commands. First run `kb.py login --email
THEIR@nsls.org`. It prints a code right away and sends them a Slack DM from **KB Publisher** with
the same code and an **Allow** button. Show them the code and ask them to click Allow only if it
matches. Once they say they clicked it, run `kb.py login` (no email) to finish. It saves a personal
key on their computer, so they never do it again there. If it says it is still waiting, ask whether
they clicked Allow, then run `kb.py login` again. Never start a new `--email` sign-in while one is
waiting: that sends a new code and the old Allow no longer counts. If `kb.py login` says "Already
signed in", they are done. Any command that says "not signed in" means: run login first.

## Looking things up

The KB is also a reference while you work. Before guessing how an NSLS process works, run
`kb.py search` with the key words and `kb.py get` the best match, then answer from the article and
link it. To find **who owns or knows a topic**, search it and report the Owner of the closest
articles. If nothing matches, say so plainly; don't invent an owner.

## Commands

| Command | What it does |
|---|---|
| `kb.py login --email EMAIL` | One-time sign-in, approved in Slack. |
| `kb.py search WORDS...` | Finds existing articles by title and text, with their Owner. |
| `kb.py categories` | Lists sections and subsections with their IDs. |
| `kb.py get ID\|SLUG` | Saves an article's `body.html` and `meta.json` to edit. Won't overwrite an existing copy unless you add `--force`. |
| `kb.py check BODY.html --type sop\|resource` | House-style check. Fix everything it reports. |
| `kb.py submit ...` | Sends the article. See step 7. |
| `kb.py status SUBMISSION` | Shows whether it was published, rejected or is still waiting. |

## Workflow

1. **Signed in?** The person signed in is the author: Slack messages go to them, and only they
   can click Publish on their own change. If they are not signed in, run `kb.py login` first.
2. **New or edit?** For an edit, find it with `kb.py search` and pull it with `kb.py get`. Use
   its real ID or slug; never guess. If `get` says it is an Employee Handbook article, stop:
   those cannot be edited here, and changes go to People Ops (hr@nsls.org).
3. **Duplicate check (new articles).** Search the topic's key words, not just the title. If
   something close exists, ask: is this the same process, an update to that article, or
   genuinely separate?
4. **Ask the type:** "Is this an SOP for a specific process, or a general resource?" Then apply
   that frame from `references/style.md`.
5. **Fill the gaps by asking.** Map what the author gave you against the required sections. For
   each one their material does not cover, ask in one message, one question per gap, with a
   suggested starting point. Never write filler.
6. **Check the people, then draft.** If you can search Slack, confirm everyone named (Owner,
   contacts) still works at NSLS; if someone seems to have left, ask who has the role now. Draft
   the body as HTML in a file, show the author the draft (new) or a short summary of the change
   (edit), then run `kb.py check` and fix what it reports. On an edit, older articles may already
   miss newer sections; the service only blocks problems your edit adds, but fix what is easy.
7. **Submit once the author says it's right.**
   - Edit: `kb.py submit --type sop|resource --article ID --body body.html --note "why"`
     (add `--title` or `--meta` only if they change).
   - New: `kb.py submit --type sop|resource --body body.html --title "..." --meta "one
     sentence on what the reader can do" --category ID --slug spelled-out-topic --note "why"`. To
     file under a subsection, pass the subsection's own ID.
8. **Tell the author what happens next**, using the message `submit` prints:
   - Their own article, a small fix, or a KB admin: a Slack DM with a **Publish** button.
   - Someone else's article: the Owner gets an **Approve** button in Slack. If the Owner hasn't
     decided after 3 business days, it also goes to #kb-submissions so a KB admin can decide (for
     when the Owner is away). If the Owner has left NSLS, it goes straight to the KB admins.
   - A new article: a KB admin approves it in #kb-submissions.
   They get a Slack DM when it's decided. Waiting approvals get a reminder after 3 business days
   and close after 6.

If `submit` says **NOT DONE**, read the reason to the author and fix it: style problems, a slug
that already exists, or a change already waiting on that article.

## Things this cannot do

- **Delete or archive** an article, **create sections**, or **upload images**: ask a KB admin
  (Royce Rowan, Danielle Mariani, Isaia Cirillo). Images must already be at a public URL, ideally
  HubSpot's file manager; see style.md.
- **Can't reach the service?** The claude.ai sandbox may block it. Save the body as an `.html`
  file and send it with the title, category and slug to a KB admin.
