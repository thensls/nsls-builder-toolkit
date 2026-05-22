---
name: feature-branch-protocol-template
description: A template for building your own work-discipline skill — a repeatable shape for starting any meaningful piece of NSLS work, checking in as you go, and handing off cleanly. Not a ready-to-use protocol. Copy this file into your own personal skills folder (`~/.claude/skills/<your-protocol-name>/SKILL.md`), then fill in each section with your own version. Red's developer-flavored version is included as a seed example so you can see the shape before you make it yours.
---

# Feature Branch Protocol — Template (with seed)

## What this is

This is a template, not a skill you should invoke directly. The point is to copy it into your own skills folder, rename it, and fill it in with your discipline — whatever kind of work you do at NSLS.

Red wrote the original for software development, where the "atomic unit of work" is a git commit on a feature branch. But the *shape* of the protocol generalizes: anyone doing meaningful work benefits from a repeatable rhythm of setup → checkpoints → handoff. The shape is what's valuable; the specifics belong to you.

Some examples of what "the work" might look like for different builders:

- A developer: changes to a code repository, committed on a feature branch
- A campaign builder: a Customer.io campaign being assembled and tested
- An analyst: a complex Airtable view, sync rule, or formula refactor
- A content lead: a new landing page being drafted and reviewed
- An ops lead: a multi-step n8n workflow being wired up
- A designer: a new visual system being prototyped in Figma

For each of these, the same questions apply: what's the setup, what's the checkpoint, what's the irreversible step, what's the final-handoff check. This template walks you through each one.

## How to use this template

1. Copy this file to your own personal skills folder: `~/.claude/skills/<your-protocol-name>/SKILL.md`. Pick a name that fits your work — `campaign-protocol`, `analytics-protocol`, `content-protocol`, whatever maps to what you actually do.
2. Rewrite the `name:` and `description:` fields at the top to match.
3. Walk through each section below. In each one, the template prompt asks you what the shape is for you. The seed example is Red's filled-in version — read it for shape, not for content. The make this your own line is what you write.
4. Delete the template prompts and the seed examples from your copy once you've written your own version. Keep your filled-in answers and the section structure.
5. Use the resulting skill on every piece of meaningful work — Claude Code will auto-load it when the description matches what you're about to do.

The protocol works only if you actually follow it. The shape is the discipline; the words are how the shape stays alive across sessions.

---

## Section 1 — Plain English with the person you're working with

**Template prompt:** How does the person you're working with want to hear updates, audits, and disclosures? What's their tolerance for the technical or domain-specific vocabulary you use? Do they want to learn the vocabulary (define it inline, keep using it), or do they want translations only?

This section is about your communication discipline during the work — not the work itself. It applies to status updates, disclosure of unauthorized changes, drafts of important messages, audit summaries, error reports, recommendations — every message you send while the work is in motion.

> **Seed example (Red's version):**
>
> The user does not speak code. This rule applies to EVERY message you send during this work — status updates, disclosure of unauthorized changes, commit message drafts, "what I'm about to do" sentences, audit summaries, error reports, recommendations, the lot.
>
> Two practical rules:
>
> 1. **The first time a technical term appears in a message, define it inline.** Example: "webhook (an HTTP request the video provider sends to our server when something happens in a room)." Once per message is enough — don't re-define on every reference.
> 2. **Replace the term with its explanation only when the plain-language version is genuinely clearer than the term-plus-inline-definition.** "Token expiration" → "how long the join-password is valid" if that flows better. Otherwise, leave the technical term in (with its inline definition the first time) — the user wants to learn the vocabulary, not have it scrubbed away.
>
> The "needs inline definition" category covers all field-specific acronyms and shorthand — examples include SDK, JWT, STT, egress, diarization, FSM, RPC, HMAC, JSONB, OAuth, gRPC, CORS, ICE, SFU, MFU. This list is illustrative, not exhaustive. If a term is the kind of thing a person outside that field would not recognize on sight, it belongs in this category — define it in the same sentence or rewrite to avoid it.
>
> Not jargon (use directly): proper-noun identifiers like file names (`UnifiedVideoRoom.tsx`), env var names (`LIVEKIT_API_KEY`), function names, branch names, route paths. These are names, not shorthand — they refer to one specific thing in the codebase. Examples are illustrative; the test is "is this the literal name of a thing, or a category of concept."

**Make this your own:** Write your own version. Who is the person you're working with? What vocabulary do they actively want to learn? What terms — from your specific domain (marketing, ops, design, data, automation) — would you naturally use and need to define or replace? Write the two practical rules in your own voice.

---

## Section 2 — Anchor your protocol in something durable

**Template prompt:** Where does your discipline need to be re-readable when the AI's working memory gets compacted or the session ends and a new one starts? What's your durable home — a plan file, a Notion page, a comment at the top of a Google Doc, a pinned message in a Slack thread, a record in Airtable? Whatever it is, name it — and write the rule that says the protocol's steps must be copied into that place before the work starts.

The point of this section: AI sessions get compacted. Skills can get unloaded. The discipline only survives if its steps are written somewhere that lives outside the conversation.

> **Seed example (Red's version):**
>
> The conversation context will get compacted. This protocol will NOT survive compaction unless you place its steps somewhere durable. The plan file IS that durable place — it stays on disk and is re-read on session resumption.
>
> Before you write any code, after the plan file has been created (or as part of creating it):
>
> 1. Open the active plan file (typically under `/Users/newor/.claude/plans/`).
> 2. Copy the actionable steps of this protocol verbatim into the plan file. At minimum: the Phase 1 branch setup checklist, the Phase 2 per-commit checkpoint (all four sub-steps a/b/c/d), the Phase 3 no-push rule, and the Phase 4 final-commit checks.
> 3. Do not paraphrase or summarize when copying. The wording is the point.
> 4. If the plan already exists from prior planning, append a "## Protocol (carried for compaction)" section at the end and paste the steps there.
>
> If you skip this, the protocol disappears the moment the session compacts and the discipline drifts. The skill file is just where the words first lived. The plan file is the source of truth across compactions.

**Make this your own:** Name your durable home. Write the steps that put this protocol into it. If you don't use plan files, what do you use? Where would future-you (or future-Claude) look first?

---

## Section 3 — Setup ritual (a.k.a. "before you do anything")

**Template prompt:** What's the setup ritual for a new piece of work? What needs to be true *before* you can start safely? What gets named, created, opened, cleaned up? Who names the work (you, your manager, a ticket), and where does that name come from?

For a developer, this is "create a branch off the latest integration branch." For a campaign builder, it might be "duplicate the template campaign, name it after the ticket, confirm the segment exists." For an analyst, it might be "open the base, confirm a backup exists, create a view with your initials."

> **Seed example (Red's version — "Phase 1: Branch setup"):**
>
> Before writing any code:
>
> 1. **Clean up the current branch.** If there are uncommitted changes, ask the user whether to stash, commit, or discard. Confirm `git status` is clean before moving on.
> 2. **Switch to the integration branch.** Typically `staging`. Never branch off `main`. If unsure which branch is the integration branch in this repo, ask.
> 3. **Pull the latest.** `git pull origin <integration-branch>`. Confirm the pull succeeded.
> 4. **Create the new branch.** The user will give you the branch name in the plan or in conversation. Do NOT invent one, do NOT default to a generic pattern. If you don't have a branch name, ask.
> 5. **Confirm to the user** in one line: the new branch is created off the latest integration branch and is ready for implementation.
> 6. **Anchor the protocol in the plan file** per Section 2 above, before moving on.

**Make this your own:** Walk through your setup ritual step by step. What's the equivalent of "clean the working tree" for you? What's the equivalent of "branch off the right thing"? Who names the work, and what do you do if no name has been given?

---

## Section 4 — Per-checkpoint discipline

**Template prompt:** What's your atomic unit of work — a commit, a campaign save, an Airtable record update, a Google Doc save, an n8n workflow activation? At each of those checkpoint moments, what does an audit look like? What needs to be disclosed to the person you're working with? What needs to be approved before the checkpoint locks in?

This is the most important section. The discipline is not about the setup or the handoff — it's about every single checkpoint along the way. Skipping a checkpoint is how silent, unauthorized work creeps in.

> **Seed example (Red's version — "Phase 2: Per-commit checkpoints"):**
>
> Pause at every commit and do ALL of the following before moving on. Do not batch checkpoints across multiple commits.
>
> ### a. Line-by-line audit
> Walk every file you just changed in this commit's scope. Every change. Don't summarize ("the changes look good"). Don't trust your memory of what you intended — read what you actually wrote. Compare each change to the plan or to the prior approval conversation.
>
> ### b. Disclose anything that wasn't explicitly authorized
> For every change in the commit, ask: was this in the plan / prior approval, or did I add it on my own? For each unauthorized item, surface it to the user:
> - What you did (specific, with file:line if relevant)
> - Why you did it (the reasoning, not an apology)
> - Whether you recommend keeping it or removing it
>
> This applies to small things too: a renamed variable, a tiny refactor, a comment, an unrequested guard clause. If it wasn't in scope, name it. The user has been burned by silently-added behavior in the past; disclosure is required even for changes that feel obvious or harmless.
>
> ### c. Show the commit message for approval
> Draft the commit message. Show it to the user. Wait for explicit approval ("yes", "approved", "go", or similar) before running `git commit`. Do not draft-and-commit in one step. Do not assume approval from silence or from a related "yes."
>
> When drafting, remember: no human names in the commit message. Describe technical concerns, not who flagged them. Reference tickets/issues by number, not by author.
>
> ### d. State the concrete next step
> End the checkpoint by naming the next specific action — the file to edit, the function to write, the command to run. Not "ready for the next step." Not "let me know when to continue." Name the move.

**Make this your own:** Define your atomic unit of work. Then write your four sub-steps for the audit, the disclosure, the approval, and the next-step naming. The shape stays — fill in your unit of work, your audit content, your approval phrasing.

---

## Section 5 — The irreversible step you don't take alone

**Template prompt:** What's the action that, once done, is hard or impossible to reverse? Pushing code to a shared remote? Publishing a campaign to subscribers? Activating an n8n workflow? Releasing a slide deck? Whatever it is, write the rule that says you don't take that step without explicit confirmation from the person you're working with.

> **Seed example (Red's version — "Phase 3: Never push"):**
>
> You do not run `git push`. The user pushes manually when she's ready. Do not suggest pushing as a "next step."

**Make this your own:** What's your equivalent of "push"? Name it explicitly. Write the one-paragraph rule that says you don't do it without explicit go-ahead. Be specific about who triggers the step (you? them? both, with a confirmation step?).

---

## Section 6 — The final-handoff check

**Template prompt:** When the work is *almost* done — the last checkpoint before handing it off — what additional checks need to be true? What's the environment, the audience, the destination that has to be ready before the work is shippable?

For Red, this is "the user is about to test the feature locally — the dev server and ngrok tunnel must both be live." For a campaign builder, it might be "the segment count looks reasonable, the test send went to the right people, the merge fields render correctly." For a deck author, it might be "the deck has been shared with the audience, the version in the link matches the version on disk."

> **Seed example (Red's version — "Phase 4: At the FINAL commit"):**
>
> In addition to the per-commit checkpoint above, on the LAST commit of the branch you must also:
>
> 1. Confirm the user's local dev server is running on port 3000 (typically `pnpm dev`). If it isn't, prompt her to start it. Never let Next.js auto-pick another port.
> 2. Confirm the user's specific ngrok tunnel — `society.ngrok.io` — is up and pointing at port 3000. Do NOT create a new tunnel. Do NOT use any other tool. Do NOT propose an "equivalent." If that exact URL is not live, you start it yourself: `ngrok http --domain=society.ngrok.io 3000`.
>
> If either isn't running, do not pass the final-commit checkpoint. She is about to test locally, and both must be live before that handoff makes sense.

**Make this your own:** What's the environment / staging / preview state that needs to be live before the work is handed off? Write the explicit, specific checks. Be specific about URLs, port numbers, accounts — vagueness here is how silent fallbacks creep in.

---

## Section 7 — When this protocol applies (and when it doesn't)

**Template prompt:** What kinds of work earn this protocol? What kinds don't? A protocol that applies to everything ends up being skipped on the things that matter; a protocol with a clear scope gets followed.

> **Seed example (Red's version — scope):**
>
> Anything that earns its own branch: features, bug fixes, refactors, chores, dependency updates, schema migrations.
>
> Does NOT apply to: one-off scripts run from the CLI, throwaway exploration agents do on a worktree, or work the user has explicitly told you to inline into an existing in-progress branch.

**Make this your own:** Write the list of things that do trigger this protocol and the list of things that don't. Be specific.

---

## Section 8 — If you forget

If you realize mid-checkpoint that you skipped a step, stop, do the missed step, then continue. Don't push through. The discipline is the point.
