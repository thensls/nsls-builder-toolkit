---
name: help-center-article
description: Use when someone on Member Experience wants to write a new member-facing help article, update or fix the wording of an existing one, or check an article's copy and formatting for the NSLS Help Center knowledge base in HubSpot (info.nsls.org/help). Trigger phrases include write a help article, new help center article, update a help article, member FAQ article, fix this help article, check this help article, publish to the help center.
---

# Help Center Article

## Safety

This skill writes copy that members and prospective members read on a public website, so every step that changes the live site has a person in front of it.

1. **Read-only, no permission needed:** reading live Help Center pages, searching for existing articles, running `scripts/check_article.py`, building a local preview with `scripts/preview.py`, drafting copy in local files.
2. **Local files, say what you're creating:** the article package folder under `~/Documents/Help Center Drafts/<slug>/`.
3. **HubSpot, people only:** this skill never creates, edits, publishes or deletes anything in HubSpot. The writer pastes the article into a HubSpot **draft** and clicks **Save**. Only the MEX lead clicks **Publish** or **Update**. If a browser tool or an API token is available, still do not use it to change a Help Center article; hand the writer the paste steps instead.
4. **Out of bounds for this skill:** the Help Center design (header and footer code, theme, header, categories, home page door cards). Those belong to RevOps. Route requests with the message in `references/categories-and-home-page.md`.

## Purpose

Members land on the Help Center when they're stuck, usually on a phone, often stressed about a charge, a deadline or a missing kit. This skill turns a Member Experience teammate's knowledge into an article that answers the question in the first sentence, sounds like the NSLS, and drops into the October 2026 design without the spacing glitches, typed-out lists, double spaces and dashes the original articles were full of. It then walks the article through a short, reviewable path to publish so nothing goes live unchecked and nothing gets stuck waiting.

## Quick Start

1. Ask what the article answers and who asks it, then work through **Questions to ask the writer** below. Get the facts from the writer, not from memory.
2. Search for an existing article: `python3 scripts/find_articles.py "<keywords>"`, then again with `--deep` and two or three synonyms ("address" / "shipping" / "mail"). Read the top three results whatever their score. If one answers the same question, update it instead (`--get <slug>`).
3. New article: `python3 scripts/new_article.py <slug>` creates `~/Documents/Help Center Drafts/<slug>/` with the templates. Fill in `article.json` and `body.html` following `references/design-rules.md` and `references/style-and-facts.md`.
4. Run `python3 scripts/check_article.py "<folder>" --fix --links`. Repeat until it reports **0 errors**.
5. Run `python3 scripts/preview.py "<folder>"`. Look at it on desktop and with the window narrowed to phone width.
6. Hand the writer the paste steps and the review message from `references/publishing-in-hubspot.md`.
7. After the MEX lead publishes, run `python3 scripts/check_article.py --live <slug>`.

## Who's who

| Role | Person | Does |
|---|---|---|
| Writer | Any Member Experience teammate | Drafts with this skill, pastes into a HubSpot draft, clicks **Save**, sends for review |
| Approver | MEX lead: **Kimberly Campbell** (kcampbell@nsls.org, Director of Member Experience), **Kara Klimuszko** (kklimuszko@nsls.org) or **Atrayu Polhemus** (apolhemus@nsls.org, Member Experience Specialist) | Reviews the draft in HubSpot, clicks **Publish** (new) or **Update** (edit) |
| Help Center owner | Royce Rowan, RevOps (rrowan@nsls.org) | Categories, home page door cards, header, footer, theme, anything that looks broken across many articles |

The writer and the approver are never the same person for the same article. Send the review message to whichever approver is available; if more approvers are added later, update this table.

## The Help Center at a glance

- **Site:** https://info.nsls.org/help, branded **NSLS Help Center**. Public, no login.
- **HubSpot:** portal 5345251, knowledge base "NSLS Help Center". In HubSpot, the Knowledge base dropdown at the top of the article list must say **NSLS Help Center**; the other knowledge base is the staff-only internal one.
- **Layout:** home page with three "doors" (Thinking about joining / Already a member / I'm an advisor) that link to specific articles, then ten topic cards. Article pages show a date, the title, an optional subtitle, then the body, with a category sidebar on the left.
- **This is the member-facing Help Center.** Since October 21, 2026, info.nsls.org/help itself carries the design members see, so articles are written, published and read here. They are **not** pushed to the marketing site or the help.nsls.org portal any more, and the `/help-center` skill (portal curation) is not part of this process.
- **Ten categories** (exact names): Joining the NSLS; Membership, benefits & programs; Account & login; Orders & shipping; Payments, receipts & charges; Society by the NSLS; About the NSLS; Induction steps; Events; Bring the NSLS to your campus. Society by the NSLS has subcategories, listed in `references/categories-and-home-page.md`.

## Questions to ask the writer

Ask only what the writer hasn't already told you, and leave out anything they can't answer rather than guessing.

- What exactly does the member need to do, in order? Where (Members Area, email, chat, a form)?
- What do they need to have ready (account email, order number, chapter)?
- Is there a deadline, a cost, or a waiting time? Where does that number come from?
- What happens after they do it? Will they hear back, and how fast?
- What can't we do (no refunds after X, can't redirect once shipped)?
- Who is this for: prospective members, members, inducted members, advisors?
- Does any live article say something different? (The search in step 2 usually shows this.)

**No invented promises.** Don't write that the team will reply, confirm, call back, waive a fee or "talk through options" unless the writer said so. If a step or outcome is unknown, leave it out and put the question in `notes_for_reviewer`.

**Conflicts with live articles.** If the writer's facts differ from a live article (a different timeframe, fee or process), don't silently pick one. Write what the writer gave, record the conflict and the other article's URL in `notes_for_reviewer`, and include it under "Facts to double-check" in the review message.

## Writing the article

Read `references/design-rules.md` before writing anything. It is short and every rule in it came from a real problem fixed on the live site. The essentials:

**Shape**
1. **Title:** the question a member would type, in sentence case, ending in a question mark. "How do I track my order?" not "Order Tracking Information".
2. **Subtitle (optional):** one sentence of context that doesn't repeat the first paragraph. Leave it empty rather than padding it.
3. **First paragraph answers the question.** One to three sentences. A member who reads only this paragraph should know what to do.
4. **Steps go in a real numbered list** (`<ol>`), one action per item, starting with a verb.
5. **Extra detail** goes under `<h3>` headings in sentence case. Never `<h1>` or `<h2>`; the page uses those for the title and subtitle.
6. **Related articles (optional):** `<h3>Related articles</h3>` and a `<ul>` of up to three links to real live articles.
7. **The standard contact block, always last,** copied exactly from `templates/body.html`.

**Text**
- No em dashes or en dashes anywhere (title, subtitle, meta description, body). Reword with a comma, colon, period or parentheses.
- No double spaces, no non-breaking spaces, no stray spaces before punctuation.
- Every piece of body text sits inside `<p>`, `<li>`, `<h3>` or `<h4>`. No loose text, no `<br><br>` for spacing, no empty paragraphs.
- No inline styles, `<span>`, `<div>` or `<font>`. The site's CSS does the styling; inline styles are what made the old articles uneven.

**Voice** (full list in `references/style-and-facts.md`)
- Talk to the member as "you". Use "we" only for the NSLS explaining itself.
- Lead with what the member gets or needs to do. Active voice. Short sentences.
- Warm, confident, never defensive. Assume success: "When you complete Orientation, you'll unlock..."
- "the NSLS" on second reference, not "NSLS" alone in a sentence.
- Use the standard terms and facts in the glossary (four Steps to Induction, DiSC, one-time membership fee, Member Experience team, over $400,000 in scholarships annually). Anything marked **confirm** in the glossary needs the MEX lead to confirm before it goes in an article.

**Metadata** (in `article.json`)
- `slug`: lowercase words joined by hyphens, from the title, no periods, no slashes, no dates.
- `category` (and `subcategory` for Society articles): one of the exact names above.
- `meta_description`: required by HubSpot. One plain sentence, 155 characters or fewer, that says what the member will learn. No dashes.

## Checking

`scripts/check_article.py` is the gate. **An article with any error does not go to HubSpot.**

```bash
python3 scripts/check_article.py "~/Documents/Help Center Drafts/<slug>"          # report only
python3 scripts/check_article.py "~/Documents/Help Center Drafts/<slug>" --fix    # also fix the mechanical problems
python3 scripts/check_article.py "~/Documents/Help Center Drafts/<slug>" --links  # also confirm every Help Center link loads
python3 scripts/check_article.py --live <slug>                                    # check a published article
```

`--fix` handles non-breaking spaces, double spaces, empty paragraphs, `<br><br>` runs, inline styles, spans and divs, and missing spaces after commas. It never rewrites wording. Dashes, typed lists, loose text, headings, voice and facts are reported as errors for you to fix in the copy.

The checker can't judge meaning. Before calling the article done, also confirm by reading it: the subtitle doesn't repeat the first paragraph, every fact traces to the writer or the glossary, and nothing promises an action the writer didn't describe.

## Previewing

`scripts/preview.py` downloads a real Help Center article page, swaps in the draft's title, subtitle, category and body, and opens the result in the browser. It uses the live site's CSS, so what you see is what members will see. It needs internet access and nothing else.

The red bar at the top marks it as a draft. The cookie banner and chat bubble come from the live site; dismiss them. The date shown is today's; HubSpot sets the real one when the article is published.

The script also prints `ok` or `FAIL` for the title, subtitle, body and category, confirming the draft landed in the right places even before anyone looks at it.

Check: the title and subtitle spacing looks like other articles, lists are numbered by the page (not typed), headings are the small navy size, and the contact block sits tight at the bottom.

## Publishing

Follow `references/publishing-in-hubspot.md` step by step. In short:

1. **Writer:** HubSpot > Knowledge base (NSLS Help Center) > **Create article**. Paste the title and subtitle, paste the body through **More > `</>`** (source code), fill **Settings** (URL, category, meta description, audience Public), click **Save**. Never **Publish**.
2. **Writer:** send the MEX lead the review message the skill drafts (title, HubSpot draft link, check result, what changed and why).
3. **MEX lead:** review against the checklist, then **Publish** (new article) or **Update** (edit).
4. **Writer or lead:** run the live check. If the article should appear on the home page doors or needs a new category, send RevOps the request.

Editing an existing article works the same way: open it in HubSpot, make the change, click **Save** (not **Update**), and send it for review.

## Diagnostic loop

When something doesn't look right: check the live page or preview, find which rule it breaks in `references/design-rules.md`, fix the source HTML, re-run `check_article.py`, re-preview. Common cases:

| What you see | Likely cause | Fix |
|---|---|---|
| Big gap or no gap between paragraphs | `<br><br>` or empty `<p>` pasted from a doc | Run `--fix`, re-paste the body through `</>` |
| "1." "2." typed in the text, uneven indent | Steps typed as text | Rewrite as `<ol><li>` |
| Text in a different font size or color | Inline styles or `<span>` from copy-paste | Run `--fix`; paste through `</>`, never straight into the editor from Word or Google Docs |
| Heading looks huge | `<h2>` or `<h1>` in the body | Use `<h3>` |
| Preview script fails | No internet, or info.nsls.org is down | Check the site loads in a browser; try again; check `references/publishing-in-hubspot.md` troubleshooting |
| HubSpot won't let you publish | Meta description is empty | Settings > Tags & metadata > Meta description |
| Article missing from its category page | Category not set, or saved but not published | Settings > Categories; ask the MEX lead to publish |
| Whole site looks broken, not just one article | Design code or theme problem | Stop and message RevOps; don't try to fix it from an article |
| A door card on the home page goes to "page not found" | Slug changed or article unpublished | Message RevOps with the old and new slug |

## Rationalizations to refuse

| Thought | Answer |
|---|---|
| "It's a tiny edit, I'll just click Update." | Every change to a live article goes through Save, then the MEX lead. Tiny edits are how typos and broken links reach members. |
| "The dash reads better here." | No dashes on the Help Center. Reword it. |
| "Pasting straight from the Google Doc is faster." | That brings in the spans, styles and non-breaking spaces that broke the old articles. Paste through `</>` only. |
| "The checker's error is picky; it looks fine." | The checker is the bar. Fix the source or explain to the MEX lead why the rule doesn't apply. |
| "I'm fairly sure the price/date/policy is X." | Facts come from the writer, the glossary, or a confirmed source. Anything marked **confirm** waits for the MEX lead. |
| "There's an article on this, but writing a fresh one is easier." | Update the existing one. Two articles answering one question split search results and drift apart. |
| "I'll add a heading with `<h2>` so it stands out." | `<h3>` only. The page design depends on it. |
| "I can fix the header or the topic card text while I'm in there." | Design belongs to RevOps. Send the request instead. |
| "I have an API token / browser access, I'll publish it for them." | This skill never changes HubSpot. People save, the MEX lead publishes. |

## Red flags: stop and fix before going on

- `check_article.py` reports any error.
- The title isn't a question a member would ask.
- The first paragraph doesn't answer it.
- The contact block is missing or reworded.
- A fact you can't trace to the writer or the glossary, or a promise (reply, refund, exception) the writer didn't make.
- The writer's facts contradict a live article and the review message doesn't say so.
- The writer is about to click **Publish** or **Update**.
- The category isn't one of the ten exact names.
- A slug contains a period, slash, date or capital letter.

## Output

- **To the writer:** the folder path, the check result (0 errors), what the preview showed, then the numbered paste steps for this specific article with every value ready to copy.
- **The review message:** fill in every field of the template in `references/publishing-in-hubspot.md` yourself; the writer only adds the HubSpot draft link after saving.
- **To the MEX lead:** the review message from `references/publishing-in-hubspot.md`, filled in. Plain language, no HTML.
- **To RevOps (only when needed):** the request message from `references/categories-and-home-page.md`.
- Never put member names, emails or account details in an article or a draft folder. Use generic examples.

## Related

- Internal staff-only articles (process docs, HubSpot how-tos) use `/kb-article`, not this one.
- How the Help Center design is built and maintained: internal KB article "Maintaining the External Help Center Design" (info.nsls.org/internal/maintaining-the-external-help-center-design).
- For deeper brand voice work, `/nsls-copywriter-skill` if installed. Its em dash allowance does not apply here.
