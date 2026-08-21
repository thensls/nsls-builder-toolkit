---
name: kb-article
description: >-
  Create or update articles in the NSLS internal HubSpot Knowledge Base at
  info.nsls.org/internal by writing the article into the master Google Sheet
  registry and handing back the import steps. Use when the user says "create a
  kb article", "new knowledge base article", "draft a kb article", "update a kb
  article", "add to the internal kb", "publish to info.nsls.org", or wants to
  capture a process / SOP / how-to into the internal KB.
---

# KB Article

Create or update articles in the NSLS internal Knowledge Base (HubSpot Service
Hub, at `https://info.nsls.org/internal`). The registry is a persistent **master
Google Sheet** holding every internal article in HubSpot-import-ready form. Every
new or edited article is written into that sheet, so at any point the sheet can be
downloaded and re-imported to bring HubSpot fully in sync. There is no write API
and no exporter app: publishing is always update the master sheet, download it,
import it.

The master sheet is the **authoring source of truth**. A HubSpot **export** is
used only to reconcile (confirm what exists, get real slugs), never edited.

The process this skill automates is itself documented as an article at
`https://info.nsls.org/internal/creating-a-knowledge-base-article`. Keep the two
in sync: if you change the workflow here, update that article's row too.

## Internal vs external KB (decide first)

- **Internal**, `info.nsls.org/internal`, staff-only, ~70 articles. Internal
  process, system mechanics, anything naming a HubSpot field / workflow ID /
  pipeline stage. **This skill covers internal.**
- **External**, `info.nsls.org/help`, member and prospect facing, ~87 articles
  across 8 categories. Different voice and review bar. Route external copy
  through the `nsls-copywriter-skill` and treat publishing as a separate,
  higher-care task.

If a member could read it, it is external. If it only makes sense with a HubSpot
login, it is internal.

## How publishing works (no write API)

HubSpot exposes **no API** for creating, updating, or deleting KB articles
(verified: `cms/v3/knowledge-base/articles` rejects Private App tokens by design,
on every tier and scope set). Never promise API publish. The supported paths are
the built-in **CSV importer** (primary) and manual **in-editor paste** (one-offs).

**CSV importer:** **Content → Knowledge Base → Current view dropdown → Import
knowledge base**, upload the CSV, map columns.
- **Create new articles:** leave "Overwrite existing content" unchecked.
- **Update existing in place:** check **"Overwrite any existing content with
  imported content"**. Matching is by the **Article URL** column, so the URL must
  exactly equal the live article URL (`https://info.nsls.org/internal/<slug>`).
- Limits: 400 articles per import; the importer **rejects `<table>`**.

## The master Google Sheet (registry)

- **Title:** `NSLS Internal KB — Master (HubSpot Import)`
- **ID:** `1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8`
- **URL:** https://docs.google.com/spreadsheets/d/1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8/edit
- **Tabs:**
  - `Articles` (sheetId `1111298109`) — every article whose body fits Google
    Sheets' 50,000-char/cell limit. This tab is the **published set**: it is
    downloaded whole only for a deliberate, reconciled mass sync. Routine
    publishes import a changed-row CSV instead (see "Delivering and
    publishing").
  - `Oversized (import separately)` (sheetId `977468579`) — bodies over 50,000
    chars. The body cell holds a pointer, not HTML; the real import-ready row
    lives in `~/Downloads/nsls_kb_import_<slug>.csv`, imported one file at a time.

**Columns (both tabs) are A:J — 8 import columns in HubSpot mapping order, then 2
attribution columns:**

| Col | Field | Notes |
|---|---|---|
| A | Article URL | Full live URL, single `/internal`. The import match key. |
| B | Article title | What someone would search for; lead with the noun. |
| C | Category | Must match an existing category string exactly (list below). |
| D | Subcategory | Usually blank. |
| E | Keywords | Comma-separated search terms, including acronyms and owner. |
| F | Meta description | One sentence on what the reader can do after reading. |
| G | Article body | Source HTML, single line, no newlines. |
| H | Article subtitle | One line under the title; often same as F. |
| I | User Name | Who created / last edited the row. **Not** a KB field. |
| J | User Email | Same. |

Columns I and J are sheet-only attribution. On HubSpot import, leave them
**unmapped** (the importer ignores unmapped columns) so they never reach HubSpot.
Every row must have them filled, or the registry loses authorship. Detect the
current user from `git config user.name` / `git config user.email`, falling back
to the toolkit `.env` files, or ask.

## Working the sheet with `gws`

Sheets access is authed via keyring. Strip the leading `Using keyring backend`
stdout line before parsing JSON. Always write with `valueInputOption: RAW` so
HTML bodies are stored literally and never parsed as formulas.

Read:

```bash
gws sheets +read --spreadsheet 1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8 --range "Articles!A1:C200" --format json
```

Write a row (note: the request options go in `--params`, the body in `--json`;
both `range` values must agree):

```bash
gws sheets spreadsheets values update \
  --params '{"spreadsheetId":"1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8","range":"Articles!A72:J72","valueInputOption":"RAW"}' \
  --json "$(cat row.json)"
```

Build `row.json` with Python (`{"range":..., "majorDimension":"ROWS","values":[[...10 cells...]]}`),
never by hand-quoting HTML in the shell. Payloads are well under ARG_MAX.

Gotchas learned the hard way:
- `gws sheets read` is not a subcommand. It is `gws sheets +read` (helper) or
  `gws sheets spreadsheets values get` (raw API).
- **Collapse the body to a single line before writing.** Author the HTML in a
  scratchpad file for readability, then join the lines with no separator (block
  tags need no whitespace between them). Every existing row is single-line HTML;
  matching that keeps CSV downloads clean.
- **Verify after writing.** Read the row back and print each cell's length. A
  silently truncated or column-shifted body is the failure mode you cannot see
  from the write response, which reports success either way.

Adding or updating one article:
1. Detect the current user for columns I and J.
2. **Read the URL column on both tabs.** An article lives on exactly one of
   them, and which one is a function of its body size, not its identity:
   ```bash
   gws sheets +read --spreadsheet <ID> --range "Articles!A:A"
   gws sheets +read --spreadsheet <ID> --range "'Oversized (import separately)'!A:A"
   ```
   Searching only `Articles!A:A` is how you get a duplicate: an existing
   oversized article is not found, so you append a second row for a slug that
   already has one, and the next import ships two conflicting versions of it.
   Count rows to find the next empty row too.
3. **Existing Article URL:** overwrite that row in place, on whichever tab holds
   it — `Articles!A<n>:J<n>` or `'Oversized (import separately)'!A<n>:J<n>`.
4. **New:** write the next empty row at `Articles!A<n>:J<n>` (or `values append`
   at `Articles!A1:J1` with `{"insertDataOption":"INSERT_ROWS"}`).
5. **Body over 50,000 chars:** put the row on the `Oversized` tab (body cell = a
   `[Body exceeds ...]` pointer) and write the full row to the companion CSV.
6. **Crossing the threshold means MOVING the row, not writing a second one.** An
   edit that pushes a body past 50,000 chars, or back under it, changes which tab
   the article belongs on. Write the row to the new tab and **delete the row from
   the old one** (`batchUpdate` → `deleteDimension` on that row; clearing the
   cells leaves a blank row that downloads as an empty CSV record). Leaving the
   stale row behind puts the same slug on both tabs, and since both get imported,
   whichever lands last wins — silently, and differently depending on import
   order. Say out loud that you moved it.
7. Read the row back and confirm all 10 cells landed in the right columns.

## Critical gotchas of the importer

- **Import resets audience access to Public.** There is no audience column, so it
  cannot be set or preserved via CSV. After every import, bulk-select the affected
  articles and use **More → Control audience access → Private, single sign-on
  (SSO) required**. Tell the user this every time. This is the easiest step to
  forget and the one that quietly exposes internal process publicly.
- **Never re-import an export file.** Files named
  `hubspot-knowledge-base-export-*` are the raw pull FROM HubSpot and still carry
  the original messy markup (checkboxes, tables, cruft). Only import files you
  built: the sheet download or a `nsls_kb_import_*` companion.
- **Reconcile before a full re-import.** The sheet holds the body as *we* last
  authored it. If someone edited an article directly in HubSpot, a wholesale
  re-import overwrites their change with the sheet's older body. Before a big
  sync, pull a fresh export, fold live changes into the sheet, then import. For a
  single new article this does not apply.
- **Category descriptions are not importable.** They live on the category and are
  set manually (Content → Knowledge Base → edit category → Description). The
  Category column only assigns an article to a category.
- **Drafts:** keep drafts in a separate CSV (`nsls_kb_draft_<slug>.csv`) and
  import them with "Import as draft" so an overwrite pass on published articles
  cannot flip a draft live. **This means a draft row never goes on the `Articles`
  tab.** That tab IS the publish set, so a draft parked there ships the next time
  anyone imports, including a colleague syncing something unrelated.

## The workflow

1. **Read the `Articles` tab** — it is the running registry and the source of
   every article's real live slug. Ask for a fresh HubSpot export only when
   reconciling against HubSpot-side edits.
2. **Confirm internal vs external**, then gather inputs (new: topic, audience,
   owning team, category, slug) or identify the target row (edit).
3. **Check for duplicates** against the Article URL and title columns.
4. **Draft or edit the body** in the house style below. Show the user the draft
   (new) or a change summary (edit) before writing anything.
5. **Establish whether this is a draft or a publish, before writing anything.**
   The two take different paths and the choice is not recoverable after an
   import. If the user said "draft", "write it up for review", "not live yet", or
   anything short of publish, it is a draft. Ask if it is genuinely unclear.
   - **Publish** → write the row into the master sheet, all 10 columns:
     overwrite in place if the Article URL already exists, append if new, route to
     the `Oversized (import separately)` tab if the body is over 50,000 chars.
     Read it back. This is the step that keeps the registry complete.
   - **Draft** → **keep the row OFF the `Articles` tab.** Write the draft to a
     standalone `nsls_kb_draft_<slug>.csv` instead (same 8 import columns) and
     hand it over with the draft import instructions below. The registry records
     it only when it publishes.
6. **Write the companion vault note** (see below).
7. **Deliver the import instructions** verbatim, including the audience reset.

## House style for article bodies

Allowed HTML only: `h2`, `h3`, `h4`, `p`, `ul`, `ol`, `li`, `strong`, `em`,
`code`, `a`, `pre`. Never `<h1>` (HubSpot reserves it for the title). No
`<table>` (importer rejects it; convert to a `<ul>`, one bullet per row, label
bolded, meaning after). No inline `style` / `class` / `div` / `span`. Escape
literal angle brackets as `&lt;` / `&gt;` so example markup renders.

Heading hierarchy: `<h2>` top sections, `<h3>` subsections, `<h4>` deepest
detail. Every article starts at `<h2>`. Do not skip levels.

Structure most good NSLS internal articles share:
1. **What it is** — one short paragraph, so the reader knows in two sentences
   whether they are in the right place.
2. **Where things live** — systems, sheets, IDs, workflow numbers, owners.
3. **The process** — `<h2>` per major section, `<ol>` for steps (what to click,
   what you should see), `<ul>` for properties or options.
4. **What is automatic vs manual**, called out explicitly for any mixed process.
5. **Gotchas** — the part people come back for.
6. **Who to ask.**

Voice: direct, declarative, operator-readable. The reader is an internal NSLS
team member who needs to do the thing, not a customer. Name real things: field
names, workflow IDs, pipeline stages, sheet names, owners. Vague articles do not
get read twice. Internal how-tos are detailed rather than phone-scannable.

Length: most articles are 200-600 words. Detailed runbooks run longer; do not pad
and do not compress out the specifics.

**Em dashes:** the global no-em-dash rule applies to internal KB prose. Em dashes
are permitted only in copy produced through the `nsls-copywriter-skill` (mostly
external/member-facing). Keep dash style consistent within an article. Literal
proper nouns that contain one (the master sheet's own title) stay accurate.

## Slugs and cross-links

- The slug is the article URL, `https://info.nsls.org/internal/<slug>`, single
  `/internal`.
- For an **existing** article use its **real live slug** from the sheet or export,
  never a guess, or an overwrite import will not match and you create a duplicate.
- For a **new** article follow the live **descriptive-slug convention**: spell the
  topic out, do not abbreviate. Live pattern:
  `associating-contacts-to-companies` (not `associations`), `tickets-overview`
  (not `mex-tickets`), `objects-and-records`, `email-bounce-procedure`,
  `nco-new-joins-process`.
- Cross-reference with the real slug:
  `<a href="https://info.nsls.org/internal/SLUG">Article Title</a>`. Do NOT use
  the `/article/` or doubled `/internal/internal/` path forms.

## Categories (column C must match one of these strings exactly)

| Category | Icon |
|---|---|
| Getting Started | 🚀 |
| HubSpot Core | ⚙️ |
| Program Development (PD) | 🏫 |
| Chapter Success (CS) | 🤝 |
| SPD & Intern Recruitment | 🎓 |
| Member Experience (MEX) | 💬 |
| Revenue Operations | ⚙️ |
| Marketing | 📣 |

A mismatched Category string silently **auto-creates** a new, usually unwanted
category on import. If the topic fits none, ask whether to add a category or file
under the closest one.

Rough sense of the distribution (read the sheet for current counts): Chapter
Success and Revenue Operations are the big buckets; Marketing, MEX, and SPD are
small. Onboarding-style and cross-team references go in Getting Started.

## Normalizing a pasted body

Bodies are often pasted from Google Docs or a HubSpot export. Normalize with a
script (Python + BeautifulSoup), not by hand:
- Convert `<table>` to `<ul>` lists.
- Strip editor cruft: remove `style` / `class` / `id` attributes, unwrap `<div>`
  and `<span>`, replace `&nbsp;` with a space, convert `<br>` runs to paragraph
  breaks (do not just delete them, or lines merge into run-ons), collapse
  whitespace (skip inside `<pre>`).
- Strip leading Markdown task-list checkboxes (`[ ]`, `[x]`) from list items only.
  **Keep** genuine bracket content such as `[First Name]`, `[DATE]`, or
  `[Custom language]` template placeholders.
- Fix cross-links to `https://info.nsls.org/internal/<real-slug>`.
- Normalize headings to h2/h3/h4; no `<h1>`; start at `<h2>`.
- Fill the subtitle (craft a one-sentence summary in the article's voice if the
  export has none). Default Meta description to the subtitle.
- Remove a leading heading that just repeats the article title, or an "Owner:"
  line (those belong to the title / owner fields).

Any CSV you write is RFC-4180 quoted, UTF-8 with BOM (`utf-8-sig`) so accented
characters survive.

## Which file to emit

Every publish produces a CSV, because the sheet is the registry and not something
HubSpot reads. Which file depends on the case:

| Case | File to emit |
|---|---|
| Publish, any size | `nsls_kb_import_<slug>.csv` — header + the changed row(s) |
| Publish, body >50,000 chars | same filename; it carries the full body the `Oversized (import separately)` tab cannot hold |
| Draft | `nsls_kb_draft_<slug>.csv`, and NO row on `Articles` (see workflow step 5) |
| Deliberate mass sync | none — download the whole `Articles` tab, after reconciling |

## Companion vault note

Alongside the sheet row, write a draft note in the Obsidian vault root named
`KB - <Title> (draft YYYY-MM-DD).md`. This is the established pattern and the
record of what was staged. It holds:
- **Status** line naming the tab and **row number** staged, and the date.
- Audience, Category, URL/slug, master sheet ID, and where the HTML body source
  file lives.
- **Meta** block: subtitle, meta description, keywords.
- **To publish**: the numbered import steps (below).
- **What the article covers**: a section-by-section summary, so the note is
  reviewable without opening the sheet.
- **Facts verified while drafting**, with the date, for anything counted or
  looked up (row counts, category distribution, IDs).

If the article was drafted from a project doc in the vault, offer to add a stub
link from that doc to the live article URL.

## Delivering and publishing

The article is already in the master sheet. **Default to shipping only the rows
you changed.** An overwrite import matches on Article URL and rewrites the body
of *every* row in the file, so a whole-sheet import to publish one new article
also pushes the sheet's stored body over every other article, reverting anything
edited in HubSpot since the sheet last saw it. That damage is silent, unrelated to
the change being made, and invisible until someone notices their edit is gone.

**Default path — one article (or the few you touched):**

> 1. Build a CSV with the header row plus **only the changed article's row(s)**,
>    named `nsls_kb_import_<slug>.csv`. Same 8 import columns in the same order.
> 2. In HubSpot: **Content → Knowledge Base → Current view dropdown → Import
>    knowledge base**, upload that CSV, map the columns. Leave **User Name** and
>    **User Email** unmapped.
>    - Check **"Overwrite any existing content with imported content"** — it
>      matches by the Article URL column, so it updates the article if the slug
>      exists and creates it if not. Rows absent from the file are untouched.
> 3. After importing, the articles reset to **Public**. Re-select them and set
>    **Control audience access → Private, SSO required**.

**Whole-sheet path — only after reconciling.** A full `Articles`-tab import is the
right tool for a deliberate mass sync, and it is the only way to guarantee HubSpot
matches the registry. It is not a routine publish step. Before running it, do the
reconcile pass (see the reconcile gotcha): pull a fresh
`hubspot-knowledge-base-export-*`, diff it against the sheet, and fold any
HubSpot-side edits into the sheet first. Then download the `Articles` tab as CSV
and import it with overwrite, plus each `Oversized (import separately)` article's
companion CSV separately.

If the user asks for "the usual import" and has not reconciled, say what a
whole-sheet overwrite would do and offer the single-row path instead. Do not
present the two as equivalent.

**Draft path — never touches `Articles`:**

> 1. Take the `nsls_kb_draft_<slug>.csv` produced for this draft (it is not on the
>    master sheet — that is deliberate).
> 2. In HubSpot: **Content → Knowledge Base → Current view dropdown → Import
>    knowledge base**, upload it, map the columns, and choose **Import as draft**.
>    - Leave **"Overwrite any existing content"** UNCHECKED. Overwrite plus a slug
>      that already exists live would replace the live article with the draft body.
> 3. Review in HubSpot and publish there when it is ready.

Once a draft is published, write its row into the master sheet (the publish path
above) so the registry stops being incomplete. An article live in HubSpot with no
sheet row is invisible to every future reconcile.

## When a build project ships

For RevOps / BI build projects, a KB article is a **standard deliverable**, not
optional. When wrapping such a project, add a KB-article task to the epic and
draft the article rep-facing, alongside the vault docs and the Jira epic.

## Gotchas recap

- The master sheet is the registry and authoring source of truth. Anything
  authored only in HubSpot gets clobbered by the next full re-import.
- **Publish the changed rows, not the whole sheet.** A whole-sheet overwrite is a
  mass sync gated behind a reconcile pass, never the routine path.
- **A draft never goes on the `Articles` tab.** That tab is the publish set.
- Check both tabs before adding a row, and move (not copy) a row that crosses the
  50,000-char threshold.
- Rows are 10 columns (A:J). Fill User Name / User Email; leave them unmapped on
  import.
- Body cell: single line, under 50,000 chars, no `<table>`, no div/span/style.
- Verify the row after writing by reading back cell lengths.
- No KB write API. Publish is CSV import or in-editor paste.
- Import always resets audience to Public. Fix it after every import.
- Overwrite matches by Article URL, so slugs must equal live slugs.
- Never import a raw `hubspot-knowledge-base-export-*` file.
- Keep `[Placeholder]` tokens; only strip empty `[ ]` / `[x]` checkboxes.
- Category strings must match exactly; category descriptions are manual.
- Slug changes, category creation, and audience settings are manual in HubSpot by
  a CMS admin. `app.hubspot.com` is blocked to the browser tools, so hand those
  steps to the user rather than attempting them.
