#!/usr/bin/env python3
"""Start a new Help Center article folder from the templates.

Usage: python3 new_article.py <slug>

Creates ~/Documents/Help Center Drafts/<slug>/ (or $HC_DRAFTS_DIR/<slug>/) with article.json and body.html.
Refuses to overwrite an existing folder.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hc_lib as hc  # noqa: E402

TEMPLATES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")


def main(argv):
    if not argv:
        sys.exit(__doc__)
    slug = argv[0].strip().lower()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        sys.exit('Slug "%s" must be lowercase words joined by hyphens.' % slug)
    folder = os.path.join(hc.DRAFTS_DIR, slug)
    if os.path.exists(folder):
        sys.exit("%s already exists. Edit it there, or pick another slug." % folder)
    os.makedirs(folder)
    shutil.copy(os.path.join(TEMPLATES, "body.html"), folder)
    with open(os.path.join(TEMPLATES, "article.json"), encoding="utf-8") as f:
        meta = json.load(f)
    meta["slug"] = slug
    with open(os.path.join(folder, "article.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("Created %s" % folder)


if __name__ == "__main__":
    main(sys.argv[1:])
