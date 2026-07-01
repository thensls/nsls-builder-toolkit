# Writing the Studio Backlog row

track-brief's last build step creates one **Tracks** row in the Track Studio base
so the idea appears in the Studio's **Backlog** column. This is a **Tier-3
write** (see the SKILL safety block). Order of operations: **verify the slug is
unique first** (list existing `Tracks` slugs), *then* show the user the final
field values and get explicit confirmation, *then* write.

## Target

- **Base:** `appzDWu6GowvnACtv` (Track Studio — "Track Previews")
- **Table:** `Tracks` (id `tblqDpGOYlgYnDZ66`)
- **Auth:** an Airtable PAT with `data.records:write` + `schema.bases:read` on
  this base. Kevin's toolkit PAT works; the Studio app's own key
  (`AIRTABLE_API_KEY` in the track-studio repo's `.env.local` / Doppler) also
  works. If no token is available, run `/connect` or fall back to printing the
  field values for the user to paste. See the `/airtable` skill for token setup.

## Fields to write

| Field | Type | Value |
|---|---|---|
| `slug` | text | kebab-case, unique (e.g. `peer-mentoring-circles`). Verify it isn't already used — list existing slugs first. |
| `title` | text | Working title. |
| `stage` | singleSelect | **`"backlog"`** — the option exists as of 2026-07-01. |
| `audience` | long text | Who it's for (one line). |
| `member_levels` | multiSelect | any of `Honor` / `Associate` / `Impact`. |
| `owner` | text | NSLS email of the owner, if one has claimed it. Optional — backlog ideas can be ownerless. |
| `benefit` | long text | One-line felt payoff — shown on the backlog card. |
| `brief_doc_url` | url | The Google Doc URL from gdoc-build (the combined Creative Content + Track Template brief). |

Leave `is_live`, `current_version`, score/metric fields empty — a backlog idea
has none yet, and the Studio board tolerates their absence.

## The write

Use `typecast: true`. This matters twice: it lets `member_levels` and `stage` be
plain strings, and — a hard-won gotcha — it is the ONLY way a scoped token can
create a new select option. (The Metadata API field-PATCH to add a choice returns
`422 INVALID_REQUEST_UNKNOWN` with a scoped token.) The `backlog` option already
exists, so typecast is just belt-and-suspenders here, but keep it.

```bash
curl -s -X POST "https://api.airtable.com/v0/appzDWu6GowvnACtv/Tracks" \
  -H "Authorization: Bearer $AIRTABLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "typecast": true,
    "fields": {
      "slug": "peer-mentoring-circles",
      "title": "Peer Mentoring Circles",
      "stage": "backlog",
      "audience": "First-year Honor members in their first 60 days",
      "member_levels": ["Honor"],
      "benefit": "Leave your first month with three peers who know your name and your goal.",
      "brief_doc_url": "https://docs.google.com/document/d/…/edit"
    }
  }'
```

A `200` returns the created record with its `id`. Report the record id + the
Studio URL (`https://studio.nsls.org`) so the user can see the card.

## Diagnostic loop

- **`422 INVALID_REQUEST_UNKNOWN` on a select field** → you sent `{"id": "sel…"}`
  or dropped `typecast`. Send the plain option-name string with `typecast: true`.
- **`403 / NOT_AUTHORIZED`** → the token lacks write scope on this base. Use a
  token that does, or print the fields for manual entry.
- **Card shows but has no "View brief" link** → `brief_doc_url` was empty. Patch
  the record with the gdoc URL.
- **Duplicate slug** → list `Tracks` slugs first and pick a unique one; the board
  drops slug-less rows and can confuse two rows sharing a slug.
- **`filterByFormula` returns 0 rows** → it uses field NAMES not IDs; `{stage}`
  works, the field id does not. (See `/airtable` gotchas.)
