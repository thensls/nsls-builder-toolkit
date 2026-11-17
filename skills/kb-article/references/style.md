# Internal KB writing rules

These are the content rules for every article on info.nsls.org/internal. Danielle
Mariani (dmariani@nsls.org) owns this file and can edit it directly. Royce Rowan
owns the mechanics in SKILL.md and scripts/kb.py.

## Two kinds of article (ask first)

Before drafting, ask: **"Is this an SOP for a specific process, or a general
resource?"**

### SOP (standard operating procedure)
Required `<h2>` sections, in this order:
1. **What This Is**: one short paragraph. The reader knows in two sentences whether
   they are in the right place.
2. **Who It's For**: the role or situation. "CSMs handling a chapter that has gone
   quiet", not "everyone".
3. **Steps**: an `<ol>`, one numbered step per action: what to click and what you
   should see. Use `<h3>` subsections for long procedures. Say what is automatic
   and what is manual.
4. **Troubleshooting**: what goes wrong and what to do about it. This is the part
   people come back for.

The author may add more sections (for example **Where Things Live**, for systems,
sheets, IDs and owners, placed between Who It's For and Steps). If any required
section is missing from what the author gave you, **ask them for it before
submitting**. One question per gap, with a suggested starting point.

### General resource
Free-form: overviews, references, glossaries, department pages. Use whatever
`<h2>` sections the content needs.

### Every article ends with
- **Related Articles**: a `<ul>` of real links to other KB articles. At least one.
- **Owner**: a named person and their email, not a team alias alone.
- **Last Updated**: a spelled-out date, for example `November 17, 2026`. Change it
  on every edit.

## Never fill a gap with filler
Do not write "No known issues", "TBD" or "Not documented in the source". It reads
like a real answer and nobody comes back to fix it. Ask the author, or ask who
would know.

## Voice
- Direct and plain. The reader is an NSLS staff member who needs to do the thing.
- Name real things: field names, sheet names, workflow numbers, people.
- Most articles run 200 to 600 words. Detailed SOPs can run longer. Do not pad.
- **No em dashes or en dashes.** Use commas, colons or periods.

## HTML
- Allowed: `h2`, `h3`, `h4`, `p`, `ul`, `ol`, `li`, `strong`, `em`, `code`, `a`,
  `pre`, `table`, `img`.
- Never `h1` (HubSpot uses it for the title). No `style`, `class`, `div` or `span`.
- Start at `h2` and do not skip levels.
- Tables are fine for genuinely tabular content (rates, schedules).
- Escape literal angle brackets as `&lt;` and `&gt;`.

## Links and slugs
- An article's URL is `https://info.nsls.org/internal/<slug>`.
- New slugs spell the topic out: `associating-contacts-to-companies`, not
  `associations`.
- Link to other articles with their real slug. Look it up; never guess.

## Images
Images must already live at a public URL, ideally HubSpot's file manager
(`info.nsls.org/hubfs/...`). Google Drive image links do not render. Always add
`alt` text, and keep personal information out of screenshots: the image files are
public even though the article is not.

## Employee Handbook articles
The 32 handbook policy articles in the Human Resources section are word-for-word
copies of the legal-approved handbook. **Never edit, summarize or restyle them by
hand.** Handbook changes go to People Ops (hr@nsls.org). The articles are
regenerated from the handbook when it changes.

## New department sections
A new section needs at least one article (a `<department>-overview` stub saying
what belongs there and who owns it). Sections themselves are created by a KB admin
in HubSpot.
