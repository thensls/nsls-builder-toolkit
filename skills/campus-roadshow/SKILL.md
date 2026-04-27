---
name: campus-roadshow
description: >-
  Use when working on the Campus Roadshow stakeholder report site — adding a
  new school, generating a meeting report from a Fathom recording, building a
  survey results page from Airtable, injecting Fathom timestamp links, or
  updating the cross-school ideas grid. Trigger phrases: campus roadshow,
  roadshow report, add school to roadshow, generate meeting report, Fathom
  transcript report, Airtable survey page, add timestamps to report, ideas grid,
  product insights grid, roadshow deploy, roadshow site
---

# Campus Roadshow Pipeline

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (Fathom transcripts, Airtable records, reading existing HTML) — runs without asking.
2. **Configuration** (generating new HTML files, updating `index.html`, writing to `report/schools/`) — explain what will be written and where, confirm before writing.
3. **Deployment** (`vercel --prod`) — always confirm explicitly. There is no rollback button.

## Purpose

The Campus Roadshow pipeline turns Fathom recordings and Airtable survey responses into a navigable stakeholder report site — not just a document dump, but a structured intelligence layer where every school's meeting notes are timestamped to the actual recording, survey data is rendered per-respondent, and product insights are cross-attributed across all discovery meetings. The site deploys statically to Vercel and is accessible to any stakeholder with the URL. This skill exists so any CS rep can run the pipeline without reverse-engineering three Python scripts from scratch.

## Quick Start — Full Pipeline for a New School

```bash
source ~/.zshrc   # ensure API keys are loaded

# 1. Generate meeting report + add to index nav (timestamps injected automatically)
python3 Scripts/generate_school.py --slug mott-community-college --update-index

# 2. Generate survey page (use respondent record ID — see Stage 3 below)
python3 Scripts/generate_survey.py \
  --airtable-id rec...respondent_id... \
  --slug mott-community-college \
  --school "Mott Community College"

# 3. Deploy
cd report && npx vercel --prod
```

**Note:** `generate_school.py` now automatically runs `add_timestamps.py` on the new meeting report immediately after writing it. Stage 2 (manual timestamp injection) is no longer a separate step. Run `add_timestamps.py --slug` manually only if re-annotating an existing report.

Read the stage sections below for gotchas — especially Stage 3 (Airtable record type) and Stage 2 (excerpt size).

---

## Pipeline Overview

Five stages, always in this order:

| Stage | Script | What it produces |
|-------|--------|-----------------|
| 1. Generate report | `generate_school.py` | Fathom → Claude → meeting HTML + timestamps (auto) |
| 2. Generate survey | `generate_survey.py` | Airtable respondent record → `survey.html` |
| 3. Update ideas grid | Manual edit of `index.html` | Cross-school product insight cards with attribution |
| 4. Deploy | `cd report && npx vercel --prod` | Push all changes to production |

All scripts live in `Scripts/`. All output lands in `report/schools/{slug}/`.

**Before running any script:** `source ~/.zshrc` to ensure `ANTHROPIC_API_KEY`, `AIRTABLE_API_KEY`, and `FATHOM_API_KEY` are in the environment. Scripts exit immediately with a clear error if a key is missing.

---

## Stage 0 — Onboard a New School

If the school directory doesn't exist yet, run `generate_school.py` with both `--slug` and `--update-index`:

```bash
python3 Scripts/generate_school.py --slug mott-community-college --update-index
```

Without `--update-index`, the script creates the directory and writes `hub.html` but does **not** add the school to `index.html`'s navigation. The script prints a reminder: "Re-run with --update-index to add this school to the index."

After Stage 0, complete these three checks before moving to Stage 1:

**Check 1 — Fix school card ordering.** `--update-index` always appends the new card at the end of the grid. The grid is ordered newest-first by meeting date. Move the card to its correct position manually in `index.html`. Find the first existing card with an older date and insert the new card immediately before it.

**Check 2 — Verify no unclosed div in the quotes section.** The editorial update (Key Findings, Heatmap, Quotes) can drop a closing `</div>` when inserting a new quote card, causing the entire site to go blank. After generation, run:
```bash
python3 -c "
html = open('report/index.html').read()
depth = sum(l.count('<div') - l.count('</div>') for l in html.split('\n'))
print('Div depth (should be 0):', depth)
"
```
If depth is not 0, find the unclosed div in the `tab-intel` quotes section (search for `<div class="quote-card">` blocks where the closing `</div>` is missing) and add it.

**Check 4 — Verify "NSLS Society Roadshow" badge links home with hover animation.** Every page should have the badge as a link (not a plain span) with a smooth color transition on hover. All three scripts generate this correctly. If patching an older page manually:
- Hub pages (`schools/{slug}/index.html`): `<a href="../../index.html" class="badge" style="text-decoration:none;">NSLS Society Roadshow</a>` — CSS must include `transition:color .2s;` on `.badge` and `a.badge:hover{color:#C96058;}`
- Meeting pages (`schools/{slug}/meetings/*.html`): `<a href="../../../index.html" class="header-pill" style="text-decoration:none;">NSLS Society Roadshow</a>` — CSS must include `transition:color .2s;` on `.page-header .header-pill` and `a.header-pill:hover{color:#C96058;}` as a **separate rule** (the `.page-header .header-pill` two-class selector has higher specificity than `a:hover`, so the hover rule must be `a.header-pill:hover` to win)
- Survey pages (`schools/{slug}/survey.html`): `<a href="../../index.html" class="pill" style="text-decoration:none;">NSLS Society Roadshow</a>` — CSS must include `transition:color .2s;` on `.pill` and `a.pill:hover{color:#C96058;}`

**Check 3 — Create survey placeholder if no Airtable ID.** If no survey respondent record exists yet, create a minimal placeholder so the hub link doesn't 404:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Survey — School Name | NSLS Roadshow</title>
</head>
<body style="font-family:sans-serif;padding:2rem;">
  <p><a href="index.html">&larr; School Name Hub</a></p>
  <h1>School Name &mdash; Pre-Meeting Survey</h1>
  <p>No survey responses on file yet.</p>
</body>
</html>
```
Save to `report/schools/{slug}/survey.html`. Replace with the real page via `generate_survey.py` when the submission arrives.

If the school directory already exists (hub built by hand), confirm it's at `report/schools/{slug}/` before running `generate_survey.py` — the script exits if the directory is missing.

---

## Stage 1 — Generate Meeting Report

```bash
cd "/path/to/Campus Roadshow"
python3 Scripts/generate_school.py --slug mott-community-college
```

Creates `report/schools/{slug}/meetings/meeting-N-YYYY-MM-DD.html` from the Fathom recording linked to the school.

**Gotcha — code fence artifacts.** Claude sometimes wraps generated HTML in ` ```html ` / ` ``` ` fences. `generate_school.py` strips these, but if ` ```html ` appears as visible text at the top of a report's content div, strip it manually with Edit:
- Remove the ` ```html ` line immediately after `<div class="content">`
- Remove the closing ` ``` ` line before `</div></main>`

The fence-strip regex lives at line ~1307 in `generate_school.py`:
```python
sections_html = re.sub(r"^```(?:html)?\s*", "", sections_html.strip())
sections_html = re.sub(r"\s*```$", "", sections_html.strip())
```

**Gotcha — schools with no Fathom recording.** Do not include a `recording-link` button for schools where no call was recorded (WGU is the known case). Remove the `<a class="recording-link" href="...">` anchor from the report header entirely.

---

## Stage 2 — Annotate Timestamps

```bash
python3 Scripts/add_timestamps.py --slug mott-community-college
# or: --file path/to/meeting.html
# or: --dry-run      (plan without writing)
```

Fetches the Fathom transcript, calls Claude to suggest `(fragment, keywords)` pairs, scores each against the actual transcript via keyword matching, injects only those with `score >= MIN_SCORE` (default: 3).

**Gotcha — timestamps only appear in Section 1.** `extract_content_html()` sends a character excerpt to Claude. If the report is long, a small excerpt means only the first section gets annotated. The current default is 12,000 chars (sufficient for most reports). If a long report still shows gaps, increase the limit at line ~106 in `add_timestamps.py`:
```python
report_excerpt = content_html[:16000]   # bump further for very long reports
```

**Gotcha — Fathom has two separate IDs.** The API returns `recording_id` (internal integer, used only for transcript fetch) and `url` (the `/calls/{id}` public URL, used for `?t=` timestamp links). These are different numbers for the same recording. `find_recording_id()` uses `recording_id` for transcript fetching and `calls_url` (from `m["url"]`) for timestamp link generation. Never use `recording_id` in `?t=` links — it will produce an access-denied page for recordings not owned by the API key holder.

**Gotcha — Fathom share URL ≠ recordings API ID.** The share URL in the report (`fathom.video/share/xyz`) is not the API recording ID. `find_recording_id()` resolves it via the meetings list API. Never pass the share URL directly to the transcript endpoint.

**Gotcha — all annotations skipped silently.** If `MIN_SCORE` rejects everything, Claude's keywords are likely paraphrases instead of verbatim transcript words. Run `--dry-run` to inspect the suggested fragments and keywords. Keywords must match the literal transcript text.

**Re-annotating a report that already has timestamps:** strip existing `?t=` links from the HTML first (the script's `already_annotated()` check will skip the file otherwise), then re-run.

---

## Stage 3 — Generate Survey Page

```bash
python3 Scripts/generate_survey.py \
  --airtable-id rec...        \
  --slug mott-community-college \
  --school "Mott Community College"
```

Creates `report/schools/{slug}/survey.html` from a single Airtable respondent record.

**Critical gotcha — two Airtable record types.** The `Survey Responses` table contains two kinds of records:

| Type | Fields | Use for |
|------|--------|---------|
| School-level summary | ~9 fields (School Name, CS Rep, linked responses…) | **Not** for `generate_survey.py` |
| Individual respondent | 33 fields (all survey answers, selections, open text) | Pass this ID to `--airtable-id` |

School-level records look right at first glance — they surface in Airtable base links, hub pages, and user-provided IDs — but they produce an empty or near-empty survey page with no visible error. **Never assume an Airtable ID from an external source is the respondent record.** Always verify before running:

1. Fetch the school-level record.
2. Find the `Survey Responses` linked field — it contains the respondent record ID(s).
3. Fetch that respondent record and confirm it has 33 fields with actual survey data.
4. Use the respondent record ID in `--airtable-id`.

**No respondent record = no survey page.** If the advisor simply didn't submit a survey, there is no respondent record. Do not try to generate a page. Mark it as "no survey submitted" in any status tracking.

Airtable connection: base `app5rj9bOGQNFoIoD`, table `Survey%20Responses`. Env var: `AIRTABLE_API_KEY`.

---

## Stage 4 — Ideas Grid

The ideas grid in `report/index.html` (lines ~1222–1504) tracks product insights surfaced across discovery meetings. Each card:

```html
<div class="idea-card">
  <div class="idea-header">
    <span class="idea-number">#3</span>
    <h3 class="idea-title">FOL Micro-Learning &amp; Modular Content</h3>
    <span class="idea-schools">4 schools</span>
  </div>
  <div class="idea-body">
    <p>Description of the insight...</p>
    <div class="idea-attribution">
      <strong>First discussed:</strong> Kimberly Giorgio &middot; Drew University<br>
      <strong>Also discussed:</strong> Dawn Vanniman &middot; Mott CC, ...
    </div>
  </div>
</div>
```

**Ranking rules:**
1. Primary: number of schools that surfaced the idea (descending)
2. Tiebreaker: signal strength — unprompted > prompted; specific feature request > vague frustration
3. When renumbering: update both the `<span class="idea-number">` and the card's DOM position

**Attribution rules:**
- "First discussed" = chronologically earliest school to raise this in a discovery meeting
- "Also discussed" = all subsequent schools, in chronological order
- Run cross-school research (grep all meeting HTML files) before finalizing attribution — a pattern surfacing in School N may have been raised first by School A two weeks earlier

**Meeting date order for attribution** (earliest first):
- Drew University: March 22
- Mott CC / St. John's University / UTRGV: March 23
- Western Governors University: March 24
- April 3 cohort: multiple schools
- Arapahoe CC / Coastal Carolina / FAMU / Gonzaga / UTK: April 10
- Muskingum University: April 16

**Society Connect sessions** (e.g., Mott's April 20 call) are not discovery meetings — exclude them from school counts and attribution.

---

## Stage 5 — Deploy

```bash
cd "/path/to/Campus Roadshow/report"
source ~/.zshrc
npx vercel --prod
```

Always confirm with the user before deploying. The deploy completes in ~10 seconds. There is no rollback — verify the site looks correct locally before running.

**Common failure — socket hang up.** Transient Vercel network error during file upload. Retry; it succeeds on the second attempt.

---

## Red Flags — Stop and Verify

These are the decisions where skipping the check silently produces wrong output:

| Situation | What goes wrong if skipped |
|-----------|----------------------------|
| Using an Airtable ID from a hub page or user message without fetching it first | School-level record → empty survey page, no error |
| Running `add_timestamps.py` without checking excerpt size on a long report | Timestamps only in first section, rest unannotated |
| Leaving a `recording-link` button for a school with no Fathom call | Broken link published to stakeholders |
| Fixing the ` ```html ` artifact in the HTML without checking `generate_school.py` | Next regeneration reintroduces the artifact |
| Deploying without sourcing `~/.zshrc` | Script exits or uses stale keys |

---

## Diagnostic Loop

**Entire site is blank after adding a new school:**
→ Unclosed `<div>` in the `tab-intel` quotes section. The editorial update dropped a `</div>` when inserting the new school's quote card. Run the div-depth check above, find the unmatched quote-card div, and add the missing `</div>`. Then redeploy.

**Survey page is blank or nearly empty:**
→ Wrong record type. Fetch the school-level Airtable record, read the linked `Survey Responses` field, fetch that respondent record to confirm 33 fields, then re-run `generate_survey.py` with the respondent ID.

**Timestamps appear only in the first section:**
→ `extract_content_html()` excerpt too short. Increase `report_excerpt = content_html[:N]` in `add_timestamps.py` (~line 104). 12,000 chars covers most reports.

**Code fence visible in rendered report:**
→ ` ```html ` artifact in content div. Strip it with Edit. Also confirm `generate_school.py` strips fences after `call_claude()` at line ~1307 — if not, add the regex there.

**Zero timestamps injected, all annotations skipped:**
→ Keywords are paraphrases. Run `add_timestamps.py --dry-run` to inspect suggested fragments and keywords. Keywords must match verbatim transcript words. Temporarily lower `MIN_SCORE` to debug.

**`find_recording_id()` errors or returns wrong result:**
→ The share URL in the report header does not match any recording in the Fathom account. Confirm the Fathom URL in the HTML matches an actual recording, and that `FATHOM_API_KEY` is set.

**`generate_survey.py` exits: school directory not found:**
→ Run `generate_school.py --slug` first to create the school's directory structure before generating the survey page.

**Vercel deploy fails with socket hang up:**
→ Transient network error. Retry `npx vercel --prod`.

---

## File Structure

```
Campus Roadshow/
  Scripts/
    generate_school.py       # Stage 1: meeting report generation
    add_timestamps.py        # Stage 2: Fathom timestamp injection
    generate_survey.py       # Stage 3: Airtable → survey.html
  report/
    index.html               # Main site — ideas grid at ~line 1222
    schools/
      {slug}/
        hub.html             # School hub page
        meetings/
          meeting-1-YYYY-MM-DD.html
        survey.html
```

## Environment Variables Required

| Variable | Used by |
|----------|---------|
| `ANTHROPIC_API_KEY` | `generate_school.py`, `add_timestamps.py` |
| `AIRTABLE_API_KEY` | `generate_survey.py` |
| `FATHOM_API_KEY` | `generate_school.py`, `add_timestamps.py` |

If any key is missing, the script exits with a clear error. Set them in `~/.zshrc` and `source ~/.zshrc` before running.

If connections aren't loading in Claude Code MCP tools, run `/connect` to configure them.
