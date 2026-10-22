#!/usr/bin/env python3
"""Find existing Help Center articles, or pull one down to edit.

Usage:
  python3 find_articles.py "<keywords>"     list articles whose title or slug matches, best first
  python3 find_articles.py --deep "<keywords>"   also search the text of every article (slower, about 20 seconds)
  python3 find_articles.py --all             list every published article by category
  python3 find_articles.py --get <slug>      save a live article into ~/Documents/Help Center Drafts/<slug>/ for editing

Reads the public site only.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hc_lib as hc  # noqa: E402

STOP = {"the", "a", "an", "to", "of", "and", "or", "my", "i", "do", "how", "is", "what", "can", "for", "in", "on", "nsls", "you", "your"}


def index():
    _, home = hc.fetch(hc.BASE)
    cats = {}
    for href, name in re.findall(r'class="hs-kb-home-list__category-link[^"]*"\s+href="https://info\.nsls\.org/help/([^"?#]+)[^"]*"[^>]*>.*?<h3[^>]*>(.*?)</h3>', home, re.S):
        cats[href] = hc.text(name)
    if not cats:  # fall back to any link on the home page that matches a category name
        for href, name in re.findall(r'href="https://info\.nsls\.org/help/([^"?#/]+)[^"]*"[^>]*>(.*?)</a>', home, re.S):
            if hc.text(name) in hc.CATEGORIES:
                cats[href] = hc.text(name)

    def crawl(item):
        slug, name = item
        try:
            _, page = hc.fetch("%s/%s" % (hc.BASE, slug))
        except Exception:  # noqa: BLE001
            return []
        found = []
        for href, t in re.findall(r'<a[^>]+href="https://info\.nsls\.org/help/([^"?#]+)[^"]*"[^>]*>(.*?)</a>', page, re.S):
            if href in cats or any(href.startswith(c + "/") for c in cats) or href == slug:
                continue
            found.append({"slug": href, "title": hc.text(t), "category": name})
        return found

    seen, arts = set(), []
    with ThreadPoolExecutor(8) as ex:
        for lst in ex.map(crawl, cats.items()):
            for a in lst:
                if a["slug"] not in seen and a["title"]:
                    seen.add(a["slug"]); arts.append(a)
    return arts


def words(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 1}


def main(argv):
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "--get":
        slug = argv[1].strip("/").split("/help/")[-1]
        _, page = hc.fetch("%s/%s" % (hc.BASE, slug))
        a = hc.parse_article_page(page)
        folder = os.path.join(hc.DRAFTS_DIR, slug.replace("/", "-"))
        os.makedirs(folder, exist_ok=True)
        crumbs = a["category_breadcrumb"]
        meta = {
            "title": a["title"], "subtitle": a["subtitle"], "slug": slug,
            "category": crumbs[0] if crumbs else "", "subcategory": crumbs[1] if len(crumbs) > 1 else "",
            "meta_description": a["meta_description"], "tags": [], "type": "edit",
            "existing_url": "%s/%s" % (hc.BASE, slug), "writer": "", "notes_for_reviewer": "",
        }
        with open(os.path.join(folder, "article.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False); f.write("\n")
        with open(os.path.join(folder, "body.html"), "w", encoding="utf-8") as f:
            f.write(a["body"] + "\n")
        with open(os.path.join(folder, "original-body.html"), "w", encoding="utf-8") as f:
            f.write(a["body"] + "\n")
        print("Saved the live version to %s" % folder)
        print("Edit body.html and article.json; original-body.html is kept for comparison.")
        if "/" in slug:
            print("Note: this article's URL contains a slash. Keep the URL as it is in HubSpot; don't re-slug it without RevOps.")
        return
    arts = index()
    if argv[0] == "--all":
        for cat in hc.CATEGORIES:
            group = [a for a in arts if a["category"] == cat]
            print("\n%s (%d)" % (cat, len(group)))
            for a in group:
                print("  %s  ->  /help/%s" % (a["title"], a["slug"]))
        print("\n%d articles" % len(arts))
        return
    deep = "--deep" in argv
    q = words(" ".join(x for x in argv if not x.startswith("--")))
    if deep:
        def body(a):
            try:
                _, page = hc.fetch("%s/%s" % (hc.BASE, a["slug"]))
                return hc.text(hc.parse_article_page(page)["body"])
            except Exception:  # noqa: BLE001
                return ""
        with ThreadPoolExecutor(8) as ex:
            for a, b in zip(arts, ex.map(body, arts)):
                a["body_words"] = words(b)
    scored = []
    for a in arts:
        w = words(a["title"] + " " + a["slug"].replace("-", " "))
        hit = len(q & w)
        if deep:
            hit += 0.5 * len((q & a.get("body_words", set())) - w)
        if hit:
            scored.append((min(hit / max(len(q), 1), 1.0), a))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        print("No existing article matches. (Searched %d published articles.)" % len(arts))
        return
    print("Possible matches (searched %d published articles):" % len(arts))
    for score, a in scored[:10]:
        print("  %3d%%  %s  [%s]  https://info.nsls.org/help/%s" % (round(score * 100), a["title"], a["category"], a["slug"]))
    print("Read the top three, whatever their score: a low score can still be the same question in different words.")
    print("If one answers the same question, update it instead of writing a new article. Try --deep and a few synonyms before deciding.")


if __name__ == "__main__":
    main(sys.argv[1:])
