---
name: publish-public-page
description: >-
  Use when an authorized NSLS marketer wants to publish a public marketing page
  or microsite to docs.nsls.org/<slug> from an HTML file, using a person-bound
  publishing token (no AWS, no repo clone). Triggers: "publish a public page",
  "publish to docs.nsls.org", "push this microsite live", "put this page on
  docs.nsls.org", "publish this landing page", "go live with this HTML".
---

# publish-public-page

## Purpose

Publish one HTML file as a **public** page at `docs.nsls.org/<slug>`. Auth is a
publishing token tied to you personally; the script is plain HTTPS using Node's
built-in `fetch`. No AWS credentials, no shared internal key, no system-of-record
checkout. (For private, institution-specific Digital Sales Room documents this
is the wrong skill — this one is for public pages only.)

## Prerequisites

1. This plugin installed (the script ships with it; Node 18+).
2. A publishing token: generate one on the dashboard **Marketing Pages** page.
3. The page as a single HTML file. External `https:` resources (fonts, images,
   scripts) are allowed on public pages.

**Tokens are per environment.** A staging token does not work against production, and the single `~/.config/nsls/publish-token` file holds only one. Use the matching token for each `--stage` (pass `--token` or set `NSLS_PUBLISH_TOKEN` per run).

Token lookup order: `--token <t>`, then `NSLS_PUBLISH_TOKEN`, then the file
`~/.config/nsls/publish-token` (chmod 600). Prefer the env var or file; a flag
lands in shell history. **Never echo, print or paste the token** in chat.

## Usage

Run from the user's own directory (where the page lives), invoking the script by
its plugin path and giving `--file` as an absolute path:

```bash
# Staging first (the default)
node "${CLAUDE_PLUGIN_ROOT}/skills/publish-public-page/scripts/publish.mjs" \
  --file /abs/path/to/page.html --slug fall-2026-launch \
  --title "Fall 2026 Launch" --description "Optional summary"

# Production — requires BOTH flags, and the user's explicit go-ahead in chat
node "${CLAUDE_PLUGIN_ROOT}/skills/publish-public-page/scripts/publish.mjs" \
  --file /abs/path/to/page.html --slug fall-2026-launch \
  --title "Fall 2026 Launch" --stage production --allow-production
```

Add `--help` for usage.

**Always publish to staging first and show the user the URL**, then publish to
production only after they say so. Say which stage you are targeting before
running. Never add `--allow-production` on your own initiative.

## Rules (checked locally before any network call)

- **Slug:** lowercase letters, digits, single hyphens (`^[a-z0-9]+(?:-[a-z0-9]+)*$`),
  max 80 characters, and `ph` is reserved.
- **Title:** required, max 200. **Description:** optional, max 2000.
- **HTML:** non-empty, under 25 MB, starts with `<!doctype html>` or `<html>`.

## Errors

| Result | Meaning | Do |
|---|---|---|
| 200 | Published | Give the user the printed `publicUrl`. |
| 401 | Token invalid, expired or revoked | Have them generate a new token on Marketing Pages. |
| 400 | Bad slug or body | Fix the input named in the message. |
| 413 | Page too large | Shrink it; host heavy media elsewhere. |
| 409 | Slug already taken | First open `docs.nsls.org/<slug>` — it may be their own earlier publish. Otherwise pick a new slug. |
| 502 / network error | Upstream or ambiguous | **Do not retry yet.** The page may already be live: check `docs.nsls.org/<slug>` first. Retrying a page that did publish just produces a confusing 409. |

If the script exits with "No publishing token found", stop and send the user to
the dashboard Marketing Pages page; do not ask them to paste the token into chat.

## Tests

`node --test "${CLAUDE_PLUGIN_ROOT}/skills/publish-public-page/scripts/"` (logic lives in `scripts/lib.mjs`).
