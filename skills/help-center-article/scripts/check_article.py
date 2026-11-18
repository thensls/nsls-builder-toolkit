#!/usr/bin/env python3
"""Check a Help Center article against the design and style rules.

Usage:
  python3 check_article.py <article-folder>          report only
  python3 check_article.py <article-folder> --fix    also fix mechanical problems in body.html / article.json
  python3 check_article.py --live <slug>             check a published article on info.nsls.org/help
  add --links to also confirm every info.nsls.org/help link loads

Exit code 0 = no errors (warnings allowed), 1 = errors.
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hc_lib as hc  # noqa: E402

BLOCK = {"p", "ol", "ul", "h3", "h4", "table", "figure", "iframe", "img", "blockquote", "pre", "hr", "video"}
INLINE = {"a", "strong", "b", "em", "i", "u", "code", "br", "sup", "sub", "small"}
MEDIA = {"img", "iframe", "video", "source", "figure", "figcaption", "table", "thead", "tbody", "tr", "td", "th"}
DASHES = re.compile(r"[—–]|&mdash;|&ndash;")

GLOSSARY = [  # (pattern, suggestion)
    (r"\bNational Office\b", 'use "Member Experience team"'),
    (r"\bDISC\b", 'use "DiSC"'),
    (r"\bregistration fee\b", 'use "one-time membership fee"'),
    (r"\bmembership cost\b", 'use "one-time membership fee"'),
    (r"\bfive Steps to Induction\b", 'there are four Steps to Induction'),
    (r"\bCredit Pathway\b|\bcredit recommended pathway\b", 'use "Credit-Recommended Pathway"'),
    (r"\bshipping warranty\b", 'use "shipping protection"'),
    (r"(?<!National )\b[Oo]nline [Cc]hapter\b", 'use "National Online Chapter"'),
    (r"\bNSLS Knowledge Base\b", 'use "NSLS Help Center"'),
    (r"\bclick here\b", "use link text that says where the link goes"),
    (r"\bplease note\b", "cut it; say the thing"),
    (r"\bin order to\b", 'use "to"'),
    (r"\$400,000(?! in scholarships and awards annually)", 'standard wording: "over $400,000 in scholarships and awards annually"'),
]


class Scan(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack, self.issues, self.tags = [], [], []
        self.top_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a, len(self.stack)))
        if not self.stack and tag not in BLOCK and tag != "div":
            self.top_text.append("<%s>" % tag)
        if tag not in ("br", "img", "hr", "source"):
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs), len(self.stack)))

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data):
        if not self.stack and data.strip():
            self.top_text.append(data.strip()[:60])


def fix_body(body):
    b = body.replace(" ", " ").replace("&nbsp;", " ")
    # strip style/class/id attributes except on media elements
    def strip_attrs(m):
        tag = m.group(1).lower()
        if tag in MEDIA or tag == "div" and "iframe" in m.group(0):
            return m.group(0)
        return re.sub(r'\s(?:style|class|id|dir|data-[\w-]+)="[^"]*"', "", m.group(0))
    b = re.sub(r"<(\w+)(?:\s[^>]*)?>", strip_attrs, b)
    # unwrap span/font always, div unless it holds an embed
    b = re.sub(r"</?(?:span|font)\b[^>]*>", "", b, flags=re.I)
    if "<iframe" not in b and "<video" not in b:
        b = re.sub(r"</?div\b[^>]*>", "", b, flags=re.I)
    # <br><br>+ inside a paragraph becomes a paragraph break
    b = re.sub(r"(?:\s*<br\s*/?>\s*){2,}", "</p><p>", b, flags=re.I)
    # br right after an opening or before a closing block tag
    b = re.sub(r"(<(?:p|li|h3|h4)[^>]*>)\s*(?:<br\s*/?>\s*)+", r"\1", b, flags=re.I)
    b = re.sub(r"(?:\s*<br\s*/?>)+\s*(</(?:p|li|h3|h4)>)", r"\1", b, flags=re.I)
    # text-only fixes, never inside tags
    parts = re.split(r"(<[^>]+>)", b)
    for i, p in enumerate(parts):
        if p.startswith("<"):
            continue
        p = re.sub(r"[ \t]{2,}", " ", p)
        p = re.sub(r"(?<=[a-z]),(?=[A-Za-z])", ", ", p)
        p = re.sub(r" +([,.;:!?])(?=\s|$)", r"\1", p)
        parts[i] = p
    b = "".join(parts)
    b = re.sub(r"(<(?:p|li|h3|h4)[^>]*>)\s+", r"\1", b)
    b = re.sub(r"\s+(</(?:p|li|h3|h4)>)", r"\1", b)
    b = re.sub(r"<p[^>]*>\s*</p>", "", b)
    b = re.sub(r"\n{3,}", "\n\n", b)
    return b.strip() + "\n"


def fix_field(v):
    return re.sub(r"\s{2,}", " ", (v or "").replace(" ", " ")).strip()


def check(meta, body, live=False, check_links=False):
    errors, warns = [], []
    E, W = errors.append, warns.append
    title, sub, md = meta.get("title", ""), meta.get("subtitle", ""), meta.get("meta_description", "")

    # ---- fields
    for name, v in (("title", title), ("subtitle", sub), ("meta description", md)):
        if DASHES.search(v):
            E("%s has an em or en dash: reword it" % name)
        if re.search(r"\S {2,}\S", v) or " " in v:
            E("%s has a double or non-breaking space" % name)
        if v != v.strip():
            E("%s starts or ends with a space" % name)
    if not title:
        E("title is empty")
    else:
        if not title.endswith("?"):
            W("title isn't a question; Help Center titles are the question a member would ask")
        words = [w for w in re.findall(r"[A-Za-z][\w']*", title)[1:] if len(w) > 3]
        if words and sum(w[0].isupper() for w in words) / len(words) > 0.6:
            W("title looks like Title Case; use sentence case")
        if len(title) > 90:
            W("title is %d characters; aim for under 90" % len(title))
    if len(sub) > 150:
        W("subtitle is %d characters; keep it to one sentence under 150" % len(sub))
    if not md:
        E("meta description is empty (HubSpot won't publish without it)")
    elif len(md) > 155:
        W("meta description is %d characters; Google cuts it after about 155" % len(md))

    if not live:
        slug = meta.get("slug", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or ""):
            E('slug "%s" must be lowercase words joined by hyphens (no periods, slashes, spaces or capitals)' % slug)
        elif len(slug) > 70:
            W("slug is %d characters; shorter is easier to share" % len(slug))
        cat = meta.get("category", "")
        if cat not in hc.CATEGORIES:
            E('category "%s" is not one of the ten Help Center categories (exact spelling)' % cat)
        subc = meta.get("subcategory", "")
        if cat == "Society by the NSLS":
            if not subc:
                W("Society articles should have a subcategory")
            elif subc not in hc.SOCIETY_SUBCATEGORIES:
                E('subcategory "%s" is not a Society subcategory' % subc)
        elif subc:
            E("only Society by the NSLS has subcategories; clear subcategory")

    # ---- body structure
    s = Scan()
    s.feed(body)
    if s.top_text:
        E("text outside a paragraph or list at the top level (wrap it in <p>): %s" % ", ".join(s.top_text[:3]))
    for tag, attrs, depth in s.tags:
        if tag in ("h1", "h2"):
            E("<%s> in the body: use <h3>" % tag)
        if tag in ("span", "font"):
            E("<%s> found (pasted formatting): run --fix" % tag)
        embed = "<iframe" in body or "<video" in body
        if tag == "div" and not embed:
            E("<div> found (pasted formatting): run --fix")
        if tag == "div" and embed:
            continue
        if "style" in attrs and tag not in MEDIA:
            if "list-style-type: none" in attrs["style"]:
                E("an invisible nested list (list-style-type: none) pushes text right; use a plain list")
            else:
                E("inline style on <%s> (%s): run --fix" % (tag, attrs["style"][:40]))
        if "class" in attrs and tag not in MEDIA:
            E("class attribute on <%s>: run --fix" % tag)
        if tag == "img" and not attrs.get("alt"):
            E("image without alt text")
        if tag == "a":
            href = attrs.get("href", "")
            if href.startswith("http://"):
                W("link uses http:// (%s); use https://" % href[:60])
            if not href:
                E("link with no href")
    if re.search(r"<br\s*/?>\s*<br", body, re.I):
        E("two line breaks in a row: use separate paragraphs (--fix does this)")
    if re.search(r"<p[^>]*>\s*</p>", body):
        E("empty paragraph (--fix removes it)")
    if "&nbsp;" in body or " " in body:
        E("non-breaking spaces (--fix removes them)")
    plain = re.sub(r"<[^>]+>", " ", body)
    if DASHES.search(body):
        for m in list(DASHES.finditer(plain))[:3]:
            E('em or en dash: "...%s..." reword with a comma, colon, period or parentheses' % plain[max(0, m.start() - 30):m.end() + 30].strip())
    if re.search(r"\S {2,}\S", re.sub(r"<[^>]+>", "", body)):
        E("double space in the text (--fix collapses it)")
    if re.search(r"(?:<p[^>]*>|<br\s*/?>)\s*\(?\d{1,2}[.)]\s", body):
        E('steps typed as "1." "2.": use <ol><li>')
    if re.search(r"(?:<p[^>]*>|<br\s*/?>)\s*[•·\-\*]\s", body):
        E('bullets typed as "•" or "-": use <ul><li>')
    for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", body, re.S):
        h = hc.text(m.group(1))
        if "<strong" in m.group(1):
            W('heading "%s" has <strong> inside; headings are already bold' % h)
        if h.endswith(":"):
            W('heading "%s" ends with a colon' % h)
        ws = [w for w in h.split()[1:] if len(w) > 3]
        if ws and sum(w[0].isupper() for w in ws) / len(ws) > 0.6 and h not in ("Related articles",):
            W('heading "%s" looks like Title Case; use sentence case' % h)

    # ---- contact block
    need = ["support@nsls.org", "201-222-6544", "800-601-6248", "hs-chat-open"]
    missing = [n for n in need if n not in body]
    if missing:
        E("standard contact block missing or changed (missing: %s); copy it from templates/body.html" % ", ".join(missing))
    else:
        tail = body.strip()[-700:]
        if "800-601-6248" not in tail:
            W("the contact block should be the last thing in the article")

    # ---- glossary and voice
    alltext = " ".join([title, sub, md, hc.text(body)])
    for pat, tip in GLOSSARY:
        m = re.search(pat, alltext)
        if m:
            W('"%s": %s' % (m.group(0), tip))
    first_p = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    if first_p and len(hc.text(first_p.group(1))) > 400:
        W("first paragraph is long; answer the question in one to three sentences, then add detail")

    # ---- links
    if check_links:
        for href in sorted(set(re.findall(r'href="(https://info\.nsls\.org/help/[^"#?]+)', body))):
            try:
                code, _ = hc.fetch(href, timeout=20)
                if code != 200:
                    E("link returns %s: %s" % (code, href))
            except Exception as e:  # noqa: BLE001
                E("link doesn't load: %s (%s)" % (href, e))
    return errors, warns


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    links = "--links" in flags
    if "--live" in flags:
        if not args:
            sys.exit("usage: check_article.py --live <slug>")
        slug = args[0].strip("/").split("/help/")[-1]
        url = "%s/%s" % (hc.BASE, slug)
        try:
            code, page = hc.fetch(url)
        except Exception as e:  # noqa: BLE001
            sys.exit("Could not load %s: %s" % (url, e))
        a = hc.parse_article_page(page)
        print("Live article: %s (HTTP %s)" % (url, code))
        print("Category: %s" % " > ".join(a["category_breadcrumb"]))
        errors, warns = check(a, a["body"], live=True, check_links=links)
    else:
        if not args:
            sys.exit(__doc__)
        folder, meta, body = hc.load_folder(args[0])
        if "--fix" in flags:
            nb = fix_body(body)
            changed = nb != body
            for k in ("title", "subtitle", "meta_description"):
                if meta.get(k) is not None and fix_field(meta[k]) != meta[k]:
                    meta[k] = fix_field(meta[k]); changed = True
            if changed:
                with open(os.path.join(folder, "body.html"), "w", encoding="utf-8") as f:
                    f.write(nb)
                with open(os.path.join(folder, "article.json"), "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                print("Applied mechanical fixes to body.html / article.json")
            else:
                print("No mechanical fixes needed")
            body = nb
        errors, warns = check(meta, body, check_links=links)
        print("Article: %s" % meta.get("title", "(no title)"))
    for e in errors:
        print("  ERROR  " + e)
    for w in warns:
        print("  warn   " + w)
    print("%d error%s, %d warning%s" % (len(errors), "" if len(errors) == 1 else "s", len(warns), "" if len(warns) == 1 else "s"))
    if not errors:
        print("Passes the Help Center checks.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
