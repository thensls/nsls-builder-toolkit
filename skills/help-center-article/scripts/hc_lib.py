"""Shared helpers for the help-center-article skill. Standard library only."""
import html
import json
import os
import re
import urllib.request

BASE = "https://info.nsls.org/help"
UA = {"User-Agent": "Mozilla/5.0 (help-center-article skill)"}
DRAFTS_DIR = os.path.expanduser(os.environ.get("HC_DRAFTS_DIR", "~/Documents/Help Center Drafts"))

CATEGORIES = [
    "Joining the NSLS",
    "Membership, benefits & programs",
    "Account & login",
    "Orders & shipping",
    "Payments, receipts & charges",
    "Society by the NSLS",
    "About the NSLS",
    "Induction steps",
    "Events",
    "Bring the NSLS to your campus",
]
SOCIETY_SUBCATEGORIES = [
    "Overview", "Member Benefits", "Institution Benefits", "Features - Available Now",
    "Features - Coming Soon", "Getting Started", "Transition", "AI Coaching", "Troubleshooting",
]

TITLE_ID = "hs_cos_wrapper_kb-article-module-3_"
SUBTITLE_ID = "hs_cos_wrapper_kb-article-module-4_"
BODY_ID = "hs_cos_wrapper_kb-article-module-5_"


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def element_span(page, el_id):
    """Return (start_of_open_tag, end_of_open_tag, start_of_close_tag, end_of_close_tag) for the element with this id."""
    m = re.search(r'<(\w+)[^>]*\bid="%s"[^>]*>' % re.escape(el_id), page)
    if not m:
        return None
    tag = m.group(1)
    depth, pos = 1, m.end()
    pat = re.compile(r"<(/?)%s\b[^>]*?(/?)>" % tag, re.I)
    while depth:
        n = pat.search(page, pos)
        if not n:
            return None
        if n.group(1):
            depth -= 1
        elif not n.group(2):
            depth += 1
        pos = n.end()
    return m.start(), m.end(), n.start(), n.end()


def inner(page, el_id):
    s = element_span(page, el_id)
    return page[s[1]:s[2]] if s else None


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment or "")).strip()


def parse_article_page(page):
    """Pull title, subtitle, body HTML, category and meta description from a live article page."""
    crumbs = re.findall(r'class="hs-kb-breadcrumb_item[^"]*"[^>]*>(.*?)</', page, re.S)
    crumbs = [text(c) for c in crumbs if text(c)]
    meta = re.search(r'<meta name="description" content="([^"]*)"', page)
    return {
        "title": text(inner(page, TITLE_ID)),
        "subtitle": text(inner(page, SUBTITLE_ID)),
        "body": (inner(page, BODY_ID) or "").strip(),
        "category_breadcrumb": crumbs[1:] if len(crumbs) > 1 else [],
        "meta_description": html.unescape(meta.group(1)) if meta else "",
    }


def load_folder(folder):
    folder = os.path.expanduser(folder)
    with open(os.path.join(folder, "article.json"), encoding="utf-8") as f:
        meta = json.load(f)
    with open(os.path.join(folder, "body.html"), encoding="utf-8") as f:
        body = f.read()
    return folder, meta, body
