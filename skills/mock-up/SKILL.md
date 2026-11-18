---
name: mock-up
description: Build clickable concept mock-ups as private claude.ai artifacts. Covers Society coach conversations, member flows, school and Career Services dashboards, partner and event pages, and "what the other side receives" views, for the product team, SLT or partners to click through. Use whenever the builder asks to mock up, prototype, "show what this would look like", "play it out", make something interactive, add a scenario, or extend or change an existing mock-up artifact, even if they never say "mock-up". Not for docs or proposals (Claude Docs), slide decks, real nsls.org pages (nsls-web-brand) or PDFs.
---

# Mock-up

Mock-ups make an idea real enough that the product team, SLT or a partner can react to it. The idea might be a coach conversation, a school dashboard or a speaker event page. A good one is clickable end to end. It shows both sides of every interaction and is clearly labeled as a concept. It gets built fast, with the house defaults below applied the first time so nobody has to correct them.

## Start from what already works

Copy an example rather than starting from a blank page. Both have been through many rounds of review:

- `assets/example-coach-flow.html`: the Society member app with the coach panel. It has a full booking flow and an email flow, both inbox views, the Product notes toggle, Start over and the scenario switcher. The flow engine is plain JS: `say()`, `reply()`, `note()`, `toast()`, `openMail()`, `reset()`. Reuse it.
- `assets/example-school-dashboard.html`: the school-facing side. It has summary tiles, a filterable student table with a side drawer, aggregate bars, a funnel, and an event composer with a Preview button that shows what the student sees.
- `references/brands.md`: which brand to use (Society, NSLS slide or NSLS web) and their tokens. Read it before choosing colors.

When the builder points at an existing artifact, find its source in the scratchpad if it was built this session; otherwise `Artifact read` it. Copy it to `name.v1-backup.html` before editing, then edit and publish to the same path so the URL stays the same.

## Settle the scenario in one breath

Work out three things from what the builder said, and only ask if one is truly missing:

1. **Who is the member, and what is the one moment?** For example, a sophomore asks the coach about tech careers.
2. **What does the member do next?** Each choice becomes a button, and each button leads somewhere.
3. **Who is on the other side?** Career Services, a partner, a speaker or a chapter. Their view is half the point.

Give the member a believable name, school, year and situation. Make up the people on the other side too (like Jordan Ellis at Lakeview University in the examples). Use a real school, partner or staff member only when the builder names them, and then add a "shown for this concept only" note under them.

## The interaction pattern

This is what made the Society coach mock-ups land with the product team:

- **Every visible button works.** Clicking it posts the member's choice as their chat bubble. Then the coach "types" (three dots, about 1.3 s) and responds with a working card: a slot picker, a pre-filled note, an RSVP form or an email draft.
- **Chain to a real ending.** Each path ends in a confirmation card. Then comes a coach follow-up: prep ideas, a reminder promise, and an Achievements chip marked "(in progress)". Offer a way back or a way across too, like "Book time instead" or "Go back to the event".
- **Show the other side.** End each path with "See what [the advisor / the partner / the speaker] receives". It opens a modal styled as that person's inbox, built from what the member actually entered or ticked. If a box was unchecked, that data is missing from their view.
- **Product notes toggle** (in the coach header): dashed purple callouts after each step. They explain what has to exist for this to work in real life: integrations, consent, data flows, partner value and follow-through. The product team reads these. Keep each to one or two sentences.
- **Start over** resets the whole flow, including any open modal.
- **Simulated actions** ("Add to calendar", "Send", "Invite") change the button to the done state and show a toast that ends in "(simulated)". Nothing is ever sent.
- **For staff-facing tools,** add a **Preview** wherever staff create something students will see. It should show it the way the student will.

## House defaults

Each of these came from a correction on an earlier mock-up. Getting them right first time is the point of this skill.

- **Make the sharing default explicit.** Consent and sharing boxes start checked unless the builder says otherwise, and a product note states the default plainly ("on by default; the member can uncheck it") so reviewers can push back. Real consent defaults are a product and governance decision; a mock-up only shows one option.
- **Members are professionals and members first.** Don't stamp the member's own screens with badges like "Alumni · Class of 2022" or "Alumni coaching". Their status can show where it does a job, such as the advisor's view needing to route an alumni appointment.
- **Suggest, don't prescribe.** For example: "Here are a few ideas for questions:", not "Three questions to ask Jordan:".
- **Estimates read as estimates.** For example: "An estimated 420 students will hear about it…", and the same wording everywhere that number appears (preview footer, toast).
- **Selected states use Society yellow** (#f3d94e) with dark text.
- **Keep system copy pronoun-neutral.** A real product can't know a member's pronouns, so use their name or "their" in notifications and inbox views.
- **Society brand rules** (from `references/brands.md`):
  - Society product screens never use the NSLS slide palette, and slides never use Society's.
- **Apply a cross-cutting change everywhere.** When the builder changes a shared element (the scenario switcher, a default, a phrase), apply it to every sibling mock-up in the set, not just the one in front of you. Say that you did.

## Label it honestly

- **Concept banner.** Put a thin red banner at the very top, for example: "Concept mock-up · internal only · student is fictional · booking and email are simulated, nothing is sent." Add specifics when they apply, like "[partner] is a target partner, not confirmed".
- **Made-up data.** Every number, name and price is illustrative. Say so in the banner or a footnote, and never present it as real NSLS data.
- **No contact details.** Don't use real email addresses, phone numbers or street addresses. Use "personal email", "Career Services office" or "near the University of Houston campus".
- **Contested ideas.** If a mock-up shows something governance hasn't approved, add a product note and flag it in your reply. For example, individual student data shown to schools: AI governance currently allows schools aggregate data only.

## Test before you publish

Run both checks, then look at the screenshots yourself. They need Claude Code on the builder's computer. In a chat or Cowork session, skip them, reread every JS string for stray apostrophes, and say in your reply that the clicks weren't tested.

1. `python3 scripts/check_js.py page.html`: catches the classic failure. An apostrophe inside a JS string (`'Society's'`) kills every button while the page still looks fine. Use `&rsquo;` or rephrase. Run this after every copy edit, too.
2. `python3 scripts/shoot.py page.html out.png --step 3200 "q('#bookBtn').click()" --step 5600 "qa('.slot')[1].click()" … --wait 16000`
   - Shoot one screenshot per path: each button, each other-side modal, and the Product notes on.
   - Time the steps past the coach's typing delay.
   - Errors paint in red at the top.
   - For phone width, run `--measure --size 500x1200`. The script finds Chrome on macOS, Windows and Linux; set `CHROME_PATH` if it can't. Matching numbers mean no sideways scroll. Headless Chrome can't go narrower than 500 px, so a narrower shot is cropped, not broken.

Fix what you see, then publish. Delete the test files afterward.

## Publish and hand off

- Publish with the Artifact tool.
  - **New page:** include an `icon` and a one-sentence `description`.
  - **Edit:** publish the same file path, with no icon.
  - It's private by default. Don't share it, send it or post the link anywhere. The builder decides who sees it.
- Reply in this order:
  1. The link.
  2. What each button now does, as a short numbered walk-through per path.
  3. What the Product notes cover.
  4. What's illustrative.
  5. One line on what you tested.
  6. The sharing state: private, or shared only with specific people. Tell the builder who they'd need to add in the Share menu.

## Putting mock-ups in other work

- **In a Claude Doc:** upload a screenshot as a blob and embed it as a linked image, so clicking it opens the live artifact.
- **In a scrolling deck:** use the iframe pattern in `references/brands.md`.
- **Mock-ups in a set:** link them to each other through the scenario switcher, with the current one highlighted.
