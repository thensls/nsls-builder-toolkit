---
name: dsr
description: >-
  Use when working on the Digital Sales Room — the thensls/digital-sales-room
  repo, its portal prototype, its Jira project, its decks in the System of
  Record, or its HubSpot chapter data. Trigger phrases: DSR, digital sales room,
  dsr-portal, DSR-<number>, dsr session, chapter model, chapter consult room,
  prototype portal, Coastal Carolina demo, dsr-portal-mockup-deploy, Epic 1
  prototype, Epic 2 build, Macroscope review, room creation on deal creation,
  institution room, grant-derived access, ice box ticket, society-sales-deck,
  deck rebuild.
---

# /dsr — Digital Sales Room

## SAFETY

**Tier 1 — read freely.** Reading the repos, docs, Jira issues, HubSpot records, the Slack channel, prototype source, test output.

**Tier 2 — ask first.** Committing, pushing, opening PRs, creating or transitioning Jira issues, posting Jira comments, writing to `docs/`. Standing rule: *never commit or push without asking, even when changes look ready.*

**Tier 3 — never without explicit instruction, and confirm the specific action.** Merging PRs. Manual Vercel deploys. Writing to HubSpot. Posting to Slack.

**Hard prohibitions. Violating the letter of these is violating the spirit of them.**

- **Never deploy manually.** No `vercel --prod`, no copying a build anywhere. Deploys are automatic on push to `main`. Not even when the pipeline looks stuck: it dropped push events for a day once, recovered on its own, and the manual workaround that time overwrote a local backup that had to be restored by hand.
- **Never ingest the Chapter object's assessment, health, sentiment or segmentation fields** into any DSR surface, store, mock or fixture. Not behind a display filter, not "just for the prototype," not commented out. The decision was explicitly *not to ingest* rather than to filter, because filtering leaves the values reachable by a bug, an export, or a future feature. CI enforces this (`never-ingest.yml`).
- **Never push to `main`.** Not for a one-line docs fix, not for a typo, not when the branch feels like ceremony. The whole point is that Macroscope sees every change.

## Purpose

The DSR is a room per institution holding everything prepared for a school — decks, dashboards, proposals, contracts — with access granted per object rather than per room. The production build lives in the System of Record (SoR) portal; `digital-sales-room` holds the prototype, the specs and the decisions. This skill carries the parts you cannot read off the code: which decisions are settled and which only look settled, the CRM data defects that silently produce wrong numbers, the Jira API behaviors that fail quietly, and the prototype internals that punish reasonable assumptions.

## Red Flags — STOP

If any of these is running through your head, stop and re-read the rule:

- "It's only a docs change, a branch is overkill"
- "The deploy looks stuck, I'll just push the build manually"
- "The field is useful and it's only the prototype"
- "The test says it passes, so the behavior is right"
- "The transcript says who said it, so that's who said it"
- "The doc probably still describes this correctly"
- "I'll create a second Google Doc rather than ask"
- "I already know what this ticket says"
- "Macroscope said skipping, so there's nothing to fix"

**Each of these was an actual failure on this project, not a hypothetical.**

## Rationalizations, and what is actually true

| Rationalization | Reality |
|---|---|
| "Macroscope shows *skipping*, so it's clean" | `skipping` can render a `neutral` conclusion, which means **issues were found**. Read `output.title` and the PR review comments. |
| "The tests pass, so the change is correct" | Nine of these scripts used to print observations and exit 0 regardless. Passing meant *didn't crash*. Check the script asserts before trusting it. |
| "The assertion matches, so the behavior is right" | An author list matched between staff and client while the *counts* differed — the privacy rule held, but an assertion on names would have locked in the wrong reading. Assert the property, not a proxy for it. |
| "Fathom labeled the speaker, so that's the attribution" | Segments carry two speakers under one name. Two attributions were published wrong from one recording. Sense-check every one. |
| "The docs were updated when the feature shipped" | They were not. Four documents described removed behavior until an audit caught them. Grep the docs for the thing you changed. |
| "I'm on the right branch" | An edit landed on `main`'s working tree mid-session. `git branch --show-current` before editing, not after. |
| "The ticket description is current" | DSR-54's member count was stale and its company id was wrong. Re-verify record data against HubSpot before building on it. |
| "The connector can update that doc" | The Drive MCP has no update tool. Creating a second doc silently forks the source of truth — ask first. |
| "Averaging the chapter rates is close enough" | 22.1% versus 36.5% on the same school. It flips the story against the goal. |
| "This decision was settled in the meeting" | Demo narration is not a decision. Check `docs/future/10` and `12` and `docs/advisory-concerns.md` before treating anything as settled. |
| "Saved in the SoR, so the school sees it" | A saved deck edit only queues a rebuild. The school sees it once the deck rebuild runner publishes it. |

## Quick Start

```bash
cd <your clone of thensls/digital-sales-room>
git log --oneline -5 && git status --short && gh pr list --state open
```

Then read `docs/README.md` (the index), `docs/future/12-chapter-model-design.md` (the settled model), and check the active sprint in Jira. Verify live state before trusting any doc — they go stale within days on this project.

## Where things live

| Thing | Location |
|---|---|
| Specs, decisions, prototype | GitHub `thensls/digital-sales-room` |
| Deck engine (Part 1, Part 2, Chapter Consult decks) | GitHub `thensls/society-sales-deck` |
| SoR portal (admin UI, institution rooms, built documents) | GitHub `thensls/invitation-dashboard` — David Adams reviews and merges |
| SoR backend, template registry, deck rebuild runner | GitHub `thensls/system-of-record` — David Adams reviews and merges. Runner: `scripts/deck-rebuild-runner/README.md` |
| SoR staging | `staging.invitations.nsls.org` — admin routes are `/institutions/<id>`, the school view is `/institution/<id>/...` |
| Prototype | `prototypes/01-dsr-portal/` — `index.html`, `portal.js`, `dashboard.js`, `crm-data.js`, `styles.css`, `real-deck-assets.js` |
| Prototype live site | `dsr-portal-mockup-deploy.vercel.app` (Vercel team `nsls`) |
| Tech specs | `docs/techspec/` (00 demo consolidation, 01 portal, 02 chapter consult, 03 institutional dashboard, 04 chapter leader dashboard, 05 sales decks, 06 application-to-proposal conversion, 07 document authoring pipeline, 08 HubSpot relationship sync, 09 sales deck template and instances) |
| Decisions | `docs/future/`. **12 is the chapter model. 10 is the HubSpot decision log (D1–D13). 11 is the CRM evidence. 19 is the MVP definition.** Canonical decision log: `docs/advisory-concerns.md` |
| QA scripts | `tests/` in `digital-sales-room` (moving there under DSR-192) |
| Jira | project `DSR`, board 778, `societyleadership.atlassian.net` |
| Sprint summaries | Confluence, one page per sprint |
| Slack | `#digital-sales-room`, id `C0BQ3R1NCG0` (private) |

## The workflow, which is not optional

**Branch → PR → wait for Macroscope → fix → merge.** Never push to `main`. Macroscope reviews every PR and has caught real bugs here that tests did not.

**Keep PRs small and single-purpose.** Macroscope prices off *diff size*, not file size. Split unrelated changes — a prototype change and a docs change are two PRs.

**Squash-merge with `--delete-branch`.** Matches the existing history (`DSR-38: … (#32)`). With stacked PRs, retarget the dependent PR to `main` *before* merging its base, or `--delete-branch` closes it.

**Reading Macroscope correctly:** the check is `Macroscope - Correctness Check`. A conclusion of `neutral` renders as **"skipping"** in `gh pr checks` but means *issues were found* — read `output.title` from the check run, then fetch findings from **PR review comments** (`gh api repos/thensls/<repo>/pulls/N/comments`), not issue comments.

```bash
gh api repos/thensls/digital-sales-room/commits/$(git rev-parse HEAD)/check-runs \
  --jq '.check_runs[] | select(.name|test("Macroscope")) | "\(.status) \(.conclusion) \(.output.title)"'
```

**Deploys:** GitHub Actions → Vercel on push to `main`, but the workflow watches `prototypes/`. **A docs-only merge fires no deploy — that is correct, not a failure.** After a prototype merge, verify the live site actually serves the change rather than assuming. Vercel keeps serving the last good deployment indefinitely, so the site staying up proves nothing about the pipeline; use the workflow's `workflow_dispatch` trigger after any credential change.

**Deck changes reach the SoR in two steps:** merge in `society-sales-deck`, then the decks are rebuilt where they're consumed (the prototype in `digital-sales-room`, and the SoR via the deck rebuild runner). A merge alone changes nothing a school sees.

## Jira — behaviors that fail silently

- **Sprint ids are global across the site, not per board. Never guess one.** Guessing once put a DSR ticket into another team's sprint on another board; the write succeeded silently. Read the sprint field off an issue already in the sprint, or list board 778's sprints.
- **Field ids:** story points are `customfield_11921` ("Story point estimate"). `customfield_10016` does not exist here — reads silently return nothing, so a sum comes back 0 and looks real. Sprint is `customfield_10007`.
- **The sprint field rejects closed sprints.** Assign before a sprint completes.
- **Rank (`customfield_10100`) writes are silently ignored.** Board order must be dragged by hand. Never promise a rerank.
- **`priority` is rejected on create** — "The priority selected is invalid." Omit it and set it after, or leave it.
- **Do not put HTML entities in a summary.** `&quot;` renders literally. Use plain quotes.
- **Done issues do not appear in the Backlog view** and no filter brings them back. Use search or the API.
- **A broad JQL blows the token limit.** Request explicit `fields`.
- **The project is team-managed and has no Icebox state.** Statuses are To Do / In Progress / In Review / Done (transition ids 11 / 21 / 31 / 41). **Ice box = the `ice-box` label plus no sprint.**
- Sprints are weekly. Epics: **DSR-1** = finish the prototype (Epic 1). **DSR-2** = build production (Epic 2). **DSR-158** = MVP; MVP tickets carry the `dsr-mvp` label. Set `parent` on create.
- When closing a ticket, post a comment saying what shipped, what was verified, and what is next — then transition. People read the ticket later, not the chat.

## The prototype — traps worth knowing before editing

- **"Chapter" means two different things in `portal.js`, and one of them is not a chapter.** `openChapter()`, `#screen-chapter`, `#chapter-main-wrap` and `#tb-lockup-chapter` all mean **the school room** — names that predate NSLS chapters entering the model. The actual chapter filter added by DSR-56 is deliberately namespaced `chapterFilter*` (`chapterFilterId`, `chapterFilterChoices`, `setChapterFilter`) to keep the two apart. Never add a `currentChapter*` name.
- **`recomputeCurrentDocs()` is the single derivation of `currentDocs`** — viewer-filtered first, then chapter-filtered. Both `openChapter` and `addLibraryDoc` route through it. Filtering documents anywhere else puts the two filters out of step.
- **The chapter switcher renders at two or more reachable chapters, and not below** (`chapterFilterChoices`), so Coastal is the only school that shows it. Reach comes from `chapterIdsReachableBy`, shared with Manage Team's Scope column — change one and check the other.
- **`SCHOOLS` is derived**, not declared: `crm-data.js` (HubSpot-shaped companies, deals, owners, contacts, chapters) joined with `SCHOOL_CONTENT` in `portal.js`. Change data in `crm-data.js`; change content in `SCHOOL_CONTENT`.
- **`dashboard.js` holds ONE hardcoded University of Phoenix dataset** — its narrative copy, real Facebook posts, real named scholarship winners. Setting `hasDashboard: true` on another school renders UoP's numbers and stories under that school's name. Only UoP has a dashboard; everyone else gets a placeholder that names their school.
- **Login personas are hardcoded in `index.html`.** Adding to `PEOPLE` in `portal.js` does *not* create a persona. Use inline `{name, email}` shares for people who never log in.
- **`extraTeamMembers: ["Name"]`** is how a school appears in someone's "Your schools" grid. Without it a school owned by a non-persona sits below the "not on your accounts" divider.
- **`#back-btn` is a "Switch Schools ›" dropdown**, not back-to-grid, and the row for your current school is disabled. To return to a school, switch away and back.
- **Manage Team shared assets are two levels deep:** row button (`[data-action="accounts"]`, labeled "Accounts (N)") → click an account name → modal with the assets.
- **Title/org is edited only in Manage Team** (`#access-member-title-input`), never in a share drawer. A title belongs to the person, not to one share.
- **The owner's row in any Shared With drawer short-circuits** to "Created this document." — no permission control. Selecting `.first()` gets the owner, which is why assertions about permission selects fail there.
- **`previewKind` values that render:** `call-recording`, `chapter-consult` (needs `fields`), `sales-deck` (needs `deck`), `esign-contract`, `invite-flyer` (needs `fields`). Anything else falls through to "Nothing to preview yet."
- **Demo edits are stored in the browser**, per persona. They don't move between machines or reps, and clearing browser data wipes them.
- **`doc.editable` is read nowhere.** Vestigial — do not propagate it.
- **`real-deck-assets.js` is vendored** third-party content, excluded from Macroscope via `.macroscope/ignore.md`. Do not hand-edit.
- Use **local-date arithmetic**, never `toISOString()`, for anything date-aligned — the latter crosses the UTC boundary and lands a day early west of Greenwich, which on a date control is a quiet wrong answer rather than a visible bug.
- **QA the prototype over http, not `file://`.** Present-mode sync between windows fails under `file://`; all decks failing to sync at once means the protocol, not the decks.

## Testing

Playwright is not a repo dependency. Install it somewhere disposable and point Node at it:

```bash
cd <scratch dir> && npm install playwright && npx playwright install chromium
cd <digital-sales-room>/tests
NODE_PATH=<scratch dir>/node_modules node test_split_files.js
```

**Every script hardcodes its own port, and the set grows every time a ticket adds a script — so derive it, never copy a list.** Some scripts write `localhost:<port>` inline and others declare `const PORT = <n>`, so a grep for one form silently misses the other:

```bash
cd <digital-sales-room>/prototypes/01-dsr-portal
PORTS=$(grep -hoE "localhost:[0-9]+|^const PORT = [0-9]+" ../../tests/test_*.js \
        | grep -oE "[0-9]{4}" | sort -un)
for p in $PORTS; do (python3 -m http.server $p >/dev/null 2>&1 &); done
sleep 2
```

macOS has no `timeout` command; don't wrap scripts in it. Tear the servers down with `pkill -f "http.server"` when done.

**A missing server looks exactly like a broken feature.** `ERR_CONNECTION_REFUSED` surfaces as `name: 'Error'` and a non-zero exit, indistinguishable at a glance from a real failure. A hardcoded list once named seven ports when the suite used fourteen, and restarting only the listed ones produced five spurious failures that read as a regression. **Before diagnosing any multi-script failure, confirm a server is actually listening on that script's port.**

**Adding a script: pick a port nothing else claims** (run the grep above first) and record it in the script's header comment.

**All scripts assert and exit non-zero.** They did not before 2026-08-12: they printed observations and exited 0 regardless, which hid six expectations that had drifted away from actual behavior, two of them contradicting each other. **A new script must compare against an expected value and exit non-zero.** A script that cannot fail is worse than no script.

**When output looks wrong, baseline before blaming yourself:** `git stash push prototypes/`, run, restore, run, diff. That distinguishes a real regression from pre-existing drift in seconds.

**Beware assertions that pass for the wrong reason.** In `test_dash_comments`, staff and client see *identical* comment-author lists — but staff see four comments and the client three, because the internal one is withheld and its author happens to appear twice. Assert the count and the withheld text, not the names.

## Data rules that change the answer

- **Recompute, never average.** Institution rates must be recomputed from raw counts. Coastal Carolina's three active chapters average to 22.1% and recompute to 36.5% — a 14.4-point error that flips the story against a 40% goal.
- **The institution→chapter join is broken in HubSpot.** No Chapter↔Company association exists, and `company_id` collides across schools for ≥55% of active chapters. Coastal's main chapter — 92% of its members — points at **Madonna University**. Chapter→company links in the prototype are *hand-declared*, never computed. Production resolution waits on a CRM cleanup owned by Royce Rowan and Angelica Evans.
- **Chapters are filters on one institution room** — not containers, not rooms of their own. One room per institution.
- **Institutional users get no standing access.** Every permission derives from a specific shared object, which also determines which chapters *and which nav sections* they see. There is no chapter membership.
- **Ownership is room-level and only room creation confers it.** A deal into an existing room makes its owner document owner of that contract only. Watch for requests that quietly add a second path to ownership.
- **Room creation fires at deal creation** (D1), explicitly *not* when a meeting completes or a deck is shared.
- **Dashboard metrics come from Brandon Evans's middleware (BI-422)**, never the Chapter object's own counts and never Snowflake directly.
- **The Grant App form is the source of truth** for proposal fields. Record form options as options and labels as labels; don't treat a label as a stored value.
- **Vocabulary rule:** the DSR keeps its own plain-language terms even when the source system differs — the signer is a **Signatory**, which maps to HubSpot's "Terms and Conditions contact". Document the mapping; never rename the DSR concept.

## Meeting notes and attribution

**Fathom's speaker labels on DSR recordings are unreliable** — single segments routinely carry two speakers under one name, and a presenter reading a page aloud gets labeled as whoever spoke last. **Sense-check every attribution against who would plausibly say it**, and say in the write-up that attributions are sense-checked rather than transcript-verified.

**A meeting doc must record disposition, not just discussion.** For each piece of feedback, name the ticket it became or the doc it landed in.

**Meeting docs live in `docs/future/` beside the real specs**, which is exactly where a loose paraphrase hardens into a requirement. When a demo narration contradicts a settled decision, record both in a table and state that the settled document wins.

**`docs/advisory-concerns.md` is the canonical decision log, and a decision recorded only in a meeting document has not been recorded.** Every decision produces a resolved item there, a new section in a techspec, or a commit message that explains the reasoning. The meeting doc records *what was said*, the log records *what was decided*. Both, or it will be re-litigated.

**When a feature ships, grep the docs for what it replaced.** The prototype README and `docs/README.md`'s index are the two most likely to go stale.

**US English** is enforced in CI on the DSR repos (`us-english.yml`). Extend its word list rather than sweeping by hand.

## Tooling notes

- **The Drive MCP connector can create files but cannot update them.** "Updating" a Google Doc means creating a new one and deleting the old — ask before forking a doc someone else is reading.
- **Drive's HTML→Docs conversion mangles inline `<strong>`/`<em>` inside table cells** into literal asterisks. Strip inline markup inside tables before uploading.
- **`pandoc`** is the reliable path from markdown to HTML or docx.
- If Jira tools appear unavailable through one Atlassian connector, try the other before reporting Jira as down.

## Diagnostic loop

**TRY → OBSERVE → DIAGNOSE → ADAPT → TRY AGAIN**

| Symptom | Likely cause | Next move |
|---|---|---|
| `gh pr checks` says "skipping" | Macroscope found issues (`conclusion: neutral`) — or reviewed nothing (`skipped`, "No code objects were reviewed") | Read `output.title`; if neutral, fetch PR review comments |
| Several scripts fail at once with `name: 'Error'` | No server on their ports — not a regression | Re-derive the port list with the grep above and restart |
| Test times out clicking a nav button | A document is open; nav is hidden — **or the viewport is under 1560px, where `.app-nav` is `display:none`** | Reload and re-navigate, use Switch Schools, or widen to 1700 |
| Test prints a number that contradicts its own label | Log-only drift, or a stale selector | Baseline with `git stash`, then diff |
| Jira write "succeeded" but nothing changed | Rank write, or a wrong-but-valid sprint id | Re-read the issue; never trust a silent success |
| Dashboard shows the wrong school's data | `hasDashboard: true` on a non-UoP school | Set it false |
| A school is missing from the grid | Owner is not a login persona | Add `extraTeamMembers` |
| Numbers look plausible but wrong | Averaged rates, or a `company_id` join | Recompute from raw counts; check the chapter link is hand-declared |
| An edit vanished | Wrong branch — changes were made on `main` | `git stash push <file>`, checkout branch, `git stash pop` |
| A school doesn't see a saved deck edit | The rebuild was queued but the runner hasn't published it | Check the queue and run the deck rebuild runner (`scripts/deck-rebuild-runner/README.md` in `system-of-record`) |
| Present windows don't sync | Prototype opened over `file://` | Serve over http |

## Output guidelines

**Lead with what changed and what it means.** Flag non-obvious technical tradeoffs briefly; the DSR's stakeholders are sales and CS leaders, not engineers.

**Say the risky thing first.** If something is wrong, will cost time later, or contradicts a settled decision, open with it rather than burying it under status.

**Report verification honestly.** "Tests pass" means they were run and the output was read. If a check was skipped, say which and why. Distinguish "verified live" from "should work."

**Slack** (`#digital-sales-room`): plain text only, no markdown asterisks. Line breaks and numbering for structure, caps sparingly. Put URLs at the end of a line. Draft before posting.

**Stakeholder docs are not build docs.** A meeting write-up shared with CS should carry disposition and decisions; it should not carry internal filenames, ticket-numbering trivia, or decisions still pending.

## Related skills

Setup and connections → `/connect`. Cross-system queries → `/data-intel`. HubSpot depth → `/hubspot`. Slack depth → `/slack`. SoR data model → `/system-of-record`. The chapter consult microsite is its own surface — see `docs/techspec/02-chapter-consultation.md`.
