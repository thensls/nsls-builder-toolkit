---
name: kb-article
description: >-
  Create or update articles in the NSLS internal HubSpot Knowledge Base at
  info.nsls.org/internal by building a HubSpot import CSV from the latest live
  KB export. Use when the user says "create a kb article", "new knowledge base
  article", "draft a kb article", "update a kb article", "add to the internal
  kb", "publish to info.nsls.org", or wants to capture a process / SOP / how-to
  into the internal KB.
---

# KB Article

Create or update articles in the NSLS internal Knowledge Base (HubSpot Service
Hub, public-facing at `https://info.nsls.org/internal`). The registry is a
persistent **master Google Sheet** that holds every internal article in
HubSpot-import-ready form. Every new or edited article is written into that
sheet, so at any point the sheet can be downloaded and re-imported to bring
HubSpot fully in sync. There is no write API, no exporter app, and no
paste-driven tool — publishing is always: update the master sheet, download it,
import it.

The master sheet is the **authoring source of truth**. A HubSpot **export** is
still used to reconcile (confirm what exists, current slugs) but is never the
thing you edit.

## How publishing works (no write API)

HubSpot exposes **no API** for creating, updating, or deleting KB articles
(verified: `cms/v3/knowledge-base/articles` rejects Private App tokens by
design). So do not promise API publish. The two supported paths are the
built-in **CSV importer** (primary) and manual **in-editor paste** (one-offs).

**CSV importer:** In HubSpot go to **Content → Knowledge Base → Current view
dropdown → Import knowledge base**, upload the CSV, and map columns.
- **Create new articles:** leave "Overwrite existing content" unchecked.
- **Update existing articles in place:** check **"Overwrite any existing content
  with imported content"**. Matching is by the **Article URL** column, so the
  URL must exactly equal the live article URL (`https://info.nsls.org/internal/<slug>`).
- Limits: 400 articles per import; the importer **rejects `<table>`**.

## The master Google Sheet (registry)

- **Title:** `NSLS Internal KB — Master (HubSpot Import)`
- **ID:** `1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8`
- **URL:** https://docs.google.com/spreadsheets/d/1vJ70z_fx_SQWPrJRBUyyptOoowJ1hbpm6iTEFLNEoF8/edit
- **Tabs:**
  - `Articles` (sheetId `1111298109`) — every internal article whose body fits
    Google Sheets' 50,000-char/cell limit. This tab is downloaded and imported.
  - `Oversized (import separately)` (sheetId `977468579`) — articles whose body
    exceeds 50,000 chars. The body cell holds a pointer, not the HTML; the real
    import-ready row lives in a companion CSV in `~/Downloads`
    (`nsls_kb_import_<slug>.csv`). These are imported one file at a time.
- **Columns (both tabs), in HubSpot mapping order:**
  `Article URL, Article title, Category, Subcategory, Keywords, Meta description, Article body, Article subtitle`

**Read/write it with `gws` (Sheets scope is authed via keyring).** Strip the
leading `Using keyring backend` stdout line before parsing JSON. Pass request
bodies via `--json "$(cat file.json)"` (payloads are well under the 1 MB
ARG_MAX). Always write with `valueInputOption: RAW` so HTML bodies are stored
literally, never parsed as formulas.

Adding/updating one article:
1. Read the URL column: `gws sheets +read --spreadsheet <ID> --range "Articles!A:A"`.
2. If the article's **Article URL already exists**, overwrite that row in place:
   `values update` at `Articles!A<rownum>` with the 8-column row.
3. If it's **new**, append it: `values append` at `Articles!A1`
   (`{"insertDataOption":"INSERT_ROWS"}`).
4. **Body over 50,000 chars:** put the row on the `Oversized` tab instead (body
   cell = a `[Body exceeds ...]` pointer), and write the full row to a companion
   `nsls_kb_import_<slug>.csv`.

## Critical gotchas of the importer

- **Import resets audience access to Public.** There is no audience-access
  column, so it cannot be set or preserved via CSV. After each import, bulk-select
  the affected articles and use **More → Control audience access → Private,
  single sign-on (SSO) required**. Tell the user this every time.
- **Never re-import an export file.** Files named `hubspot-knowledge-base-export-*`
  are the raw pull FROM HubSpot and still contain the original messy markup
  (checkboxes, tables, cruft). Only import files you built, named
  `nsls_kb_import_*`.
- **Category descriptions are not importable.** They live on the category and
  are set manually (Content → Knowledge Base → edit category → Description). The
  Category column only assigns an article to a category.
- **Drafts:** keep drafts in a separate CSV and import them with "Import as
  draft" so an overwrite pass on published articles cannot flip a draft live.

## The workflow

1. **Open the master sheet** (above) — read the `Articles` tab. It is the
   running registry of what exists and every article's real live slug. Ask for a
   fresh HubSpot export only when you need to reconcile the sheet against
   HubSpot-side edits (see the reconcile gotcha).
2. **Gather inputs** (for a new article) or **identify the target** (for an
   edit). For a new article: topic, audience, owning team, category, slug.
3. **Check for duplicates** against the master sheet's Article URL and title
   column before creating.
4. **Draft or edit** the body in the house style (below). Show the user the
   draft (new) or a change summary (edit) before writing anything.
5. **Write the row into the master sheet** — overwrite in place if the Article
   URL already exists, append if new, route to the Oversized tab if the body is
   over 50,000 chars. This is the step that keeps the registry complete.
6. **Deliver the sync instructions** (see "Delivering and publishing"): download
   the Articles tab, import with overwrite, and the audience-access reminder.
   Emit a standalone CSV only for an oversized article.

## House style for article bodies

Allowed HTML only: `h2`, `h3`, `h4`, `p`, `ul`, `ol`, `li`, `strong`, `em`,
`code`, `a`, `pre`. Never `<h1>` (HubSpot reserves it for the title). No
`<table>` (importer rejects it; use lists). No inline `style`/`class`/`div`/
`span`.

Heading hierarchy: `<h2>` top sections, `<h3>` subsections, `<h4>` deepest
detail. Every article should start at `<h2>`. Do not skip levels.

Structure most good NSLS articles share:
1. Why this matters / what this is (one short paragraph).
2. Source-of-truth pointer if there is a canonical doc, dashboard, or Figma.
3. The process / how-to: `<h2>` per major section, `<ol>` for steps, `<ul>` for
   properties or options.
4. What is automatic vs. manual, called out explicitly for any mixed process.
5. Related items / known gotchas at the bottom, brief.

Voice: direct, declarative, operator-readable. The reader is an internal NSLS
team member who needs to do the thing, not a customer. Keep it tight (most
articles are 200-600 words).

## Slugs and cross-links

- The slug is the article URL (`https://info.nsls.org/internal/<slug>`). For an
  **existing** article, use its **real live slug from the export URL column**,
  never a guess, or an overwrite import will not match and you create a duplicate.
- For a **new** article, follow the live **descriptive-slug convention**: spell
  the topic out, do not abbreviate. Examples of the live pattern:
  `associating-contacts-to-companies` (not `associations`), `tickets-overview`
  (not `mex-tickets`), `objects-and-records`, `email-bounce-procedure`,
  `nco-new-joins-process`.
- Cross-reference other articles with their real live slug:
  `<a href="https://info.nsls.org/internal/SLUG">Article Title</a>`. Look the
  slug up in the export by the target's title. Do NOT use the `/article/` or
  doubled `/internal/internal/` path forms.

## Categories (Category column must match one of these strings exactly)

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

If the topic fits none, ask whether to add a new category or file under the
closest one. A mismatched Category string creates a new (usually unwanted)
category on import.

## Preparing the article row

The row's eight fields, in HubSpot's mapping-screen order (also the master
sheet's column order):

`Article URL, Article title, Category, Subcategory, Keywords, Meta description, Article body, Article subtitle`

Build the row as clean, normalized HTML, then write it into the master sheet
(overwrite-in-place or append). Only emit a `.csv` when the article is oversized
(companion file) — the normal deliverable is the updated sheet, not a file. Any
CSV you do write is quoted, UTF-8 with BOM (`utf-8-sig`) so accented characters
survive.

**Normalize every body to the house style** before writing it. Because bodies
are large and often pasted from Google Docs, do this with a script (Python +
BeautifulSoup), not by hand:
- Convert `<table>` to `<ul>` lists (importer rejects tables; house style has none).
- Strip editor cruft: remove `style`/`class`/`id` attributes, unwrap `<div>`
  and `<span>`, replace `&nbsp;` with a space, convert `<br>` runs to paragraph
  breaks (do not just delete them, or lines merge into run-ons), collapse
  whitespace (skip inside `<pre>`).
- Strip leading Markdown task-list checkboxes (`[ ]`, `[x]`) from list items
  only. Keep genuine bracket content such as `[First Name]`, `[DATE]`, or
  `[Custom language]` template placeholders.
- Fix cross-links to `https://info.nsls.org/internal/<real-slug>` (no `/article/`,
  no doubled `/internal/internal/`).
- Normalize headings to h2/h3/h4 (top/sub/detail); no `<h1>`; each article
  starts at `<h2>`.
- Fill the subtitle (a crafted one-sentence summary in the article's voice if
  the export has none). Default Meta description to the subtitle.
- Remove a leading heading that just repeats the article title or an "Owner:"
  line (that belongs to the title/owner fields).

Show the user the draft (for a new article) or a summary of changes (for a bulk
cleanup) before finalizing.

## Delivering and publishing

The article is already in the master sheet. To sync HubSpot, give the user these
instructions verbatim:

> 1. Open the master sheet, `Articles` tab: **File → Download →
>    Comma-separated values (.csv)**.
> 2. In HubSpot: **Content → Knowledge Base → Current view dropdown → Import
>    knowledge base**, upload that CSV, map the columns.
>    - Check **"Overwrite any existing content with imported content"** — it
>      matches by the Article URL column, so it updates existing articles and
>      creates any new ones in a single pass.
> 3. For any article on the **Oversized** tab, import its companion
>    `nsls_kb_import_<slug>.csv` separately the same way.
> 4. After importing, the articles reset to **Public**. Re-select them and set
>    **Control audience access → Private, SSO required**.

Because the whole sheet re-imports with overwrite, this is idempotent: run it
anytime to bring HubSpot fully up to date with the registry.

If the article was drafted from a project doc in the Obsidian vault, offer to
add a stub link from that doc to `https://info.nsls.org/internal/<slug>`.

## Gotchas recap

- The master Google Sheet is the registry and authoring source of truth; every
  new/edited article must be written into it, or it drifts out of sync.
- **Reconcile before a full re-import.** The sheet holds the body as *we* last
  authored it. If someone edits an article directly in HubSpot, a wholesale
  re-import will overwrite (clobber) their change with the sheet's older body.
  Before a big sync, pull a fresh export and update any rows edited in HubSpot,
  or import only the changed rows.
- Google Sheets caps a cell at 50,000 chars; bodies over that go on the
  `Oversized` tab + a companion CSV, never inline.
- No KB write API; publish is CSV import (download the sheet) or in-editor paste.
- Import always resets audience access to Public; fix with Control audience
  access after every import.
- Importer rejects `<table>`; 400 articles per import (the registry is ~50, so
  headroom is fine).
- Never import a raw `hubspot-knowledge-base-export-*` file; import the sheet
  download or a `nsls_kb_import_*` companion.
- Overwrite matches by Article URL, so slugs must equal the live slugs.
- Keep `[Placeholder]` tokens; only strip empty `[ ]`/`[x]` checkboxes.
- Category strings and category descriptions: match live strings exactly;
  descriptions are set manually on the category, not via CSV.
