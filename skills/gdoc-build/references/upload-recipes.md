# Upload Recipes

Copy-paste shell snippets for the upload flow. Tested 2026-05-01 on the builder-toolkit onboarding doc rebuild.

## Upload `.docx` as a new Google Doc

The `.docx` MUST be in `~` (or the cwd you're running `gws` from). `gws` rejects paths outside cwd.

```bash
cd ~ && gws drive files create \
  --json '{"name":"YOUR DOC TITLE","mimeType":"application/vnd.google-apps.document"}' \
  --upload your_doc_name.docx \
  --upload-content-type "application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  --format json | tail -10
```

Output looks like:

```json
{
  "id": "1abc...",
  "kind": "drive#file",
  "mimeType": "application/vnd.google-apps.document",
  "name": "YOUR DOC TITLE"
}
```

The file URL is `https://docs.google.com/document/d/<id>/edit`.

## Why `| tail -10`?

`gws` writes a `Using keyring backend: keyring` line to stderr that gets interleaved with stdout. Parsing the full output as JSON fails. `tail -10` skips past the keyring line cleanly. Alternative: `grep -v "keyring backend"`.

## Trash an old draft (when iterating)

```bash
gws drive files update \
  --params '{"fileId":"<old_draft_id>"}' \
  --json '{"trashed":true}' 2>&1 | tail -5
```

This moves the file to Drive's trash (recoverable for 30 days). Don't use a hard-delete API call — soft-trash is the safer default.

## Verify the doc owner / link

```bash
gws drive files get \
  --params '{"fileId":"<id>","fields":"id,name,owners,webViewLink"}' \
  --format json 2>&1 | tail -20
```

Confirms the owner is the authed `gws` user (should be your `kprentiss@nsls.org`) and gives the share link.

## When the upload fails

| Error | Fix |
|---|---|
| `--upload '...' resolves to '/private/tmp/...' which is outside the current directory` | `cp /tmp/foo.docx ~/foo.docx && cd ~` and retry |
| `Bad Request` on the create call | Check `--upload-content-type` is exactly `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (not `application/msword` and not `application/docx`) |
| 401 / 403 | `gws` auth lapsed — re-auth via the gws login flow. This is `/gws`'s domain. |
| Doc uploads but tables have no borders | The `.docx` source didn't set `table.style` — fix the python-docx script, re-build, re-upload, trash the broken draft. |

## Don't replace canonical docs programmatically

There's a tempting recipe — use `gws docs documents batchUpdate` to replace an existing canonical doc's body content. **Don't.** The canonical doc's URL is shared broadly; the human controls what lives there. The right pattern:

1. Build the new draft as a separate Google Doc.
2. Give the user the URL.
3. Let them copy section-by-section into the canonical doc.

This preserves the canonical's existing fonts, comments, and revision history.
