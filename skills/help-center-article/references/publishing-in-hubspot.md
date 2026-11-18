# Publishing in HubSpot

Two people, two jobs. The **writer** builds the article and saves it as a draft. The **MEX lead** reviews it and publishes. The writer never clicks **Publish** or **Update**.

Before starting, the article folder must pass `python3 scripts/check_article.py "<folder>"` with **0 errors**, and the preview must look right.

## Part 1: Writer creates the draft (new article)

1. In HubSpot, search "Knowledge base" in the top search bar and open it. (Or Service > Knowledge base.)
2. At the top, check the **Knowledge base** dropdown says **NSLS Help Center**. If it says anything else, switch it. The other knowledge base is staff-only.
3. Click **Create article** (orange button, top right). The editor opens with the real Help Center page around it.
4. **Title:** click the large heading ("What question is your article answering?") and replace it with the `title` from `article.json`.
5. **Subtitle:** click the line under the title and paste the `subtitle`. If there's no subtitle, leave the placeholder empty.
6. **Body:**
   1. Click inside the body area so the editing toolbar appears at the top.
   2. Click **More**, then the **`</>`** (source code) button.
   3. In the source code window, select everything (Cmd+A on Mac, Ctrl+A on Windows) and delete it.
   4. Open `body.html` from the article folder in a text editor, copy all of it, and paste it into the source code window.
   5. Click the button at the bottom of the window to apply it (**Save changes**).
   6. Never paste the body straight into the editor from Word, Google Docs or an email. It brings in hidden styles that break the spacing.
7. **Settings** (button near the top right of the editor):
   1. **General:** next to **Article URL**, click the pencil and replace the end of the URL with the `slug`. Check the full URL reads `info.nsls.org/help/<slug>`.
   2. **Categories:** pick the **Category** (and **Subcategory** for Society articles) exactly as in `article.json`.
   3. **Tags & metadata:** paste the `meta_description` into **Meta description**. Add `tags` if listed (they help search).
   4. **Control audience access:** **Public**.
   5. Close Settings with the X.
8. Click **Save** (top right). **Do not click Publish.**
9. Copy the editor's URL from the browser address bar. This is the draft link for the reviewer.

## Part 1b: Writer edits an existing article

1. Get the current version first: `python3 scripts/find_articles.py --get <slug>` saves the live title, subtitle and body into a new folder under `~/Documents/Help Center Drafts/<slug>/`.
2. Make the change in that folder's `body.html` / `article.json`, run the check and preview.
3. In HubSpot, open the knowledge base (NSLS Help Center), search for the article, and click its title to open the editor.
4. Replace the body through **More > `</>`** as in step 6 above. Update the title, subtitle or Settings only if they changed.
5. Click **Save**. **Do not click Update.** Saved changes stay in the draft; the live article doesn't change until the MEX lead clicks **Update**. (To be sure, open the live URL in a private window after saving: it should still show the old version.)
6. Copy the editor URL for the reviewer.

Never change a published article's slug without telling RevOps first.

## Part 2: Writer sends it for review

Send the MEX lead this message (Slack DM or email). The skill fills it in:

> **Help Center article ready for review**
> - Article: <title>
> - New or edit: <new / edit to info.nsls.org/help/<slug>>
> - HubSpot draft: <editor URL>
> - Category: <category>
> - What it answers / what changed: <one or two sentences>
> - Facts to double-check: <any numbers, dates, policies, or "none">
> - Conflicts with live articles: <"none", or the article URL and what differs>
> - Checks: 0 errors in the article check, preview reviewed on desktop and phone width
> - Home page: <"no door card needed" or "suggest a door card under ...">

## Part 3: MEX lead reviews and publishes

1. Open the draft link. Click **Preview** (top right) and look at it at full width and on a phone (or a narrowed window).
2. Review checklist:
   - [ ] The title is a question a member would ask, and the first paragraph answers it.
   - [ ] Every fact (prices, dates, windows, policies) is right today, and any conflict with another live article is resolved (fix the other article too, or ask the writer to).
   - [ ] Nothing promises something the team doesn't do (a reply, a call back, an exception).
   - [ ] The subtitle adds something and doesn't repeat the first paragraph.
   - [ ] Steps are a numbered list; spacing matches other Help Center articles.
   - [ ] No dashes, no double spaces, no odd fonts or colors.
   - [ ] Links work and go to the right place.
   - [ ] The contact block is at the bottom, unchanged.
   - [ ] Settings: correct category, URL slug, meta description filled in, audience Public.
   - [ ] For an edit: nothing else in the article changed by accident.
3. If something needs fixing, reply to the writer with what to change. The writer fixes it in the folder, re-runs the check, re-pastes, and saves.
4. When it's right: click **Publish** (new article) or **Update** (edit). Confirm in the pop-up if one appears.
5. Reply to the writer that it's live.

## Part 4: After publishing

1. Run `python3 scripts/check_article.py --live <slug>`. It checks the live page loads, the body passes the rules, and the contact block is there.
2. Open the live URL and the category page in a normal browser window. The home page and category pages can take about 2 minutes to update; article pages occasionally longer.
3. If it should be on the home page doors, or it replaced or removed an article that has a door card, send RevOps the request in `categories-and-home-page.md`.
4. Delete nothing from the drafts folder: it's the record of what was published and when.

## Unpublishing or retiring an article

Don't delete articles. Ask the MEX lead to unpublish it (Actions > Unpublish in the article list) and tell RevOps the slug so door cards and links can be updated. If another article replaces it, ask RevOps for a redirect from the old URL.

## Troubleshooting

| Problem | Fix |
|---|---|
| **Publish** is greyed out or errors | Meta description is empty (Settings > Tags & metadata). |
| Body spacing in HubSpot looks off but the preview was fine | The paste went into the editor instead of the source code window. Redo step 6 through **More > `</>`**. |
| Category isn't in the dropdown | Check the spelling against the ten names. If it's truly missing, ask RevOps. Don't create one. |
| URL ends in `-1` or `-2` | That slug is already taken by another article (maybe an old draft). Search for it in the article list and tell the MEX lead. |
| The editor shows "suggestions from the knowledge base agent" | Ignore them unless they fix a real error. Accepting them can rewrite copy. |
| Article published but not on its category page | Wait 2 minutes and refresh. If still missing, check Settings > Categories and that it's Published. |
| Live article still shows old text after Update | Wait a few minutes; article pages are cached. Open it in a private window. |
| You clicked Publish/Update by mistake | Tell the MEX lead right away. They can review it live and fix it with another Update, or unpublish it. |
