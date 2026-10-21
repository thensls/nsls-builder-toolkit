# Help Center design rules

These rules come from the October 21, 2026 restyle and cleanup of all 90 Help Center articles. Each one fixes something that was visibly wrong on the live site. `scripts/check_article.py` enforces them.

## How an article page is built

HubSpot assembles each article page from four pieces, in this order:

1. **Date** (automatic, the last time the article was published or updated).
2. **Title** (an `<h1>` the page creates from the article title).
3. **Subtitle** (an `<h2>` the page creates from the subtitle field; hidden when empty).
4. **Body** (the HTML you paste).

The site CSS spaces these consistently: 14px from title to subtitle, 28px from subtitle to body, about 28px from title to body when there is no subtitle. That only works if the body starts with a normal block element (`<p>`, `<ol>`, `<ul>`, `<h3>`) and contains no spacing hacks.

## Body HTML: allowed

| Element | Use for |
|---|---|
| `<p>` | Every paragraph. All text lives in a block element. |
| `<ol><li>` | Steps the member does in order. The page numbers them. |
| `<ul><li>` | Options, lists of items, related articles. |
| `<h3>` | Section headings inside the article, sentence case, no colon, no `<strong>` inside. |
| `<h4>` | A sub-section under an `<h3>`, rarely needed. |
| `<strong>` | A few words that must not be missed (a deadline, a button name). Not whole sentences. |
| `<em>` | Rare emphasis. |
| `<a href="...">` | Links with descriptive text ("track your order in the Members Area"), never "click here" or a bare URL. |
| `<br>` | Only inside the contact block or an address, where each line belongs together. Never two in a row. |
| `<img>`, `<iframe>` | Screenshots and videos, with `alt` text on images. Images must already be in HubSpot File Manager. |
| `<table>` | Only for genuinely tabular facts (rates, dates by tenure). Rare. |

## Body HTML: not allowed

| Don't | Why | Instead |
|---|---|---|
| `<h1>`, `<h2>` | The page already uses them for the title and subtitle; a second one breaks the visual order. | `<h3>` |
| Text outside a block element | Renders with no paragraph spacing, so the body hugs the subtitle. | Wrap in `<p>` |
| `<br><br>` or empty `<p>` for spacing | Creates random gaps that don't match other articles. | Separate `<p>` elements |
| "1." "2." typed at the start of lines | Uneven indent, no hanging alignment, looks broken on phones. | `<ol><li>` |
| "•" or "-" typed as bullets | Same problem. | `<ul><li>` |
| `style="..."`, `<span>`, `<div>`, `<font>`, `class=` | Overrides the site font, size and color, so one article looks different from the rest. | Nothing. The CSS handles it. |
| Lists nested inside invisible list items (`list-style-type: none`) | Pushes content far to the right. | A plain `<ul>` or `<ol>` |
| `&nbsp;` or non-breaking spaces | Creates double spaces and odd line breaks. | A normal space |

## Text rules

- **No em dashes (—) or en dashes (–)** in the title, subtitle, meta description or body. Reword:
  - "and more—all designed to..." becomes "and more, all designed to..."
  - "isn't a formality – it's what sets you apart" becomes "isn't a formality: it's what sets you apart"
  - "the carrier—UPS, FedEx, or USPS—takes over" becomes "the carrier (UPS, FedEx, or USPS) takes over"
  - A plain hyphen in a range ("Monday - Friday", "9 a.m. - 6 p.m.") or a name ("Features - Available Now") is fine.
- **One space** after every period, comma and colon. Never two.
- **A space after every comma** ("certificate, lapel pin", not "certificate,lapel pin").
- **Sentence case** for titles and headings: capitalize the first word and proper nouns only.
- **Titles are questions** a member would type, ending in "?".
- **Numbers:** numerals for counts with units ("3 Speaker Broadcasts", "30 days"), words for one through nine in plain prose ("one-time fee", "four Steps to Induction").
- **Times:** "9 a.m. - 6 p.m. ET".

## The standard contact block

Every article ends with this block, exactly. Copy it from `templates/body.html`.

```html
<p>📚 <a href="https://info.nsls.org/help">NSLS Help Center</a> available 24/7<br>💬 <a href="#hs-chat-open">Live Chat</a>, Phone, and Text are available Monday - Friday, 9 a.m. - 6 p.m. ET<br>📧 Email: <a href="mailto:support@nsls.org">support@nsls.org</a><br>📞 Phone: 201-222-6544<br>📞 Toll Free: 800-601-6248</p>
```

It is one paragraph with single line breaks so it sits as a tight block. The `#hs-chat-open` link opens the chat widget on whatever page the member is on.

If an article needs a lead-in before the block, use one short `<p>` such as "Still need help? Our Member Experience team is here for you."

Don't repeat the phone number or email elsewhere in the article, **unless contacting support is the answer** (for example, "email support@nsls.org with your new address before your kit ships"). Then name it, linked, in the first paragraph or the step where the member uses it, and still end with the standard block.

## Subtitle

- Optional. About a third of live articles have one.
- One sentence, 150 characters or fewer, that adds context or reassurance ("Changing schools doesn't mean starting over.").
- Don't restate the title or repeat the first paragraph.
- Plain text only. No links, no dashes.

## Meta description

- Required. HubSpot won't publish without it.
- One sentence, 155 characters or fewer, describing what the member will find ("How to track your NSLS Shop order and what to do if your shipping confirmation hasn't arrived.").
- Shows in Google results and link previews, so make it make sense on its own.

## Slug

- Lowercase letters, numbers and hyphens only: `how-do-i-track-my-graduation-regalia`.
- Built from the title, without filler words if it gets long (aim for under 60 characters).
- No periods, slashes, dates, or "copy".
- Once published, the slug doesn't change. Home page door cards and Google results link to it. If a slug must change, tell RevOps first so the door cards and a redirect can be updated.

## Images and video

- Upload images to HubSpot File Manager (folder `help-center/`) and insert them through the editor's image button, or use the File Manager URL in an `<img>` tag.
- Every image needs `alt` text that describes what it shows.
- Screenshots: crop to the relevant part, no member data, no internal tools.
- Video: use the editor's embed option; keep it under the first paragraph, never above the answer.
