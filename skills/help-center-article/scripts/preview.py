#!/usr/bin/env python3
"""Render a draft article inside a real Help Center page and open it in the browser.

Usage: python3 preview.py <article-folder> [--no-open]

Downloads a live article page (for the real header, footer, sidebar and CSS), swaps in
the draft's title, subtitle, category and body, and writes preview.html into the folder.
Nothing is sent anywhere.
"""
import html
import os
import re
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hc_lib as hc  # noqa: E402

TEMPLATE_ARTICLE = "how-can-i-track-my-order"


def replace_inner(page, el_id, new_inner):
    s = hc.element_span(page, el_id)
    if not s:
        raise SystemExit("Couldn't find %s in the template page; the Help Center layout may have changed. Tell RevOps." % el_id)
    return page[:s[1]] + new_inner + page[s[2]:]


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    folder, meta, body = hc.load_folder(args[0])
    try:
        _, page = hc.fetch("%s/%s" % (hc.BASE, TEMPLATE_ARTICLE))
    except Exception as e:  # noqa: BLE001
        sys.exit("Couldn't load the Help Center (%s). Check your internet connection and that info.nsls.org/help opens in a browser." % e)

    page = replace_inner(page, hc.TITLE_ID, html.escape(meta.get("title", "")))
    page = replace_inner(page, hc.SUBTITLE_ID, html.escape(meta.get("subtitle", "")))
    page = replace_inner(page, hc.BODY_ID, body)
    cat = meta.get("category", "")
    esc = html.escape(cat, quote=False)
    # breadcrumb: the template article's category becomes the draft's
    page = re.sub(r'(data-anchor="orders-shipping">)\s*Orders &amp; shipping\s*(</a>)',
                  lambda m: m.group(1) + esc + m.group(2), page, count=1)
    # sidebar: move the highlighted category
    page = re.sub(r'(class="hs-kb-category_accordion_nav_list_item)\s+hs-kb-category-accordion_link--active"', r'\1 "', page, count=1)
    page = re.sub(r'(<li role="presentation" class="hs-kb-category_accordion_nav_list_item\s*)("\s*>\s*<a role="menuitem" class="hs-kb-category-accordion_link"[^>]*>%s</a>)' % re.escape(esc),
                  r"\1 hs-kb-category-accordion_link--active\2", page, count=1)
    page = re.sub(r"<title>.*?</title>", "<title>PREVIEW: %s</title>" % html.escape(meta.get("title", "")), page, count=1, flags=re.S)
    banner = ('<div style="position:sticky;top:0;z-index:9999;background:#C0181B;color:#fff;font:600 14px/1.4 sans-serif;'
              'padding:8px 16px;text-align:center">DRAFT PREVIEW, not live. Category: %s. Slug: /help/%s</div>'
              % (html.escape(cat), html.escape(meta.get("slug", ""))))
    page = re.sub(r"(<body[^>]*>)", r"\1" + banner, page, count=1)
    page = page.replace("<head>", '<head><base href="https://info.nsls.org/help/">', 1)

    # confirm the draft landed in the right slots (useful when nobody can look at it yet)
    got = hc.parse_article_page(page)
    checks = [
        ("title", got["title"] == meta.get("title", "").strip()),
        ("subtitle", got["subtitle"] == meta.get("subtitle", "").strip()),
        ("body", got["body"].strip() == body.strip()),
        ("breadcrumb category", (got["category_breadcrumb"] or [""])[0] == cat),
    ]
    for name, ok in checks:
        print("  %s %s" % ("ok  " if ok else "FAIL", name))
    if not all(ok for _, ok in checks):
        print("The preview didn't assemble cleanly. Re-run; if it keeps failing, tell RevOps the Help Center layout may have changed.")

    out = os.path.join(folder, "preview.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("Preview written to %s" % out)
    print("Check it at full width, then narrow the window to phone width.")
    if "--no-open" not in argv:
        webbrowser.open("file://" + out)


if __name__ == "__main__":
    main(sys.argv[1:])
