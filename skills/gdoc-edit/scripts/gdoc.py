#!/usr/bin/env python3
"""gdoc-edit helper — read, edit, and create Google Docs via the `gws` CLI.

This replaces the old personal Apps Script webhook. It talks to the real Google
Docs + Drive APIs through `gws` (the Google Workspace CLI), so it works for ANY
builder who has authenticated `gws` once (`gws auth login`) — there is no shared
secret and no per-user deploy. Each call runs as the builder's own identity.

Auth: this helper shells out to `gws`. If `gws` isn't authenticated you'll get
exit code 2 and a hint to run `gws auth login`. See references/setup.md.

Actions (CLI surface preserved from the webhook era so existing docs still apply):
  read         --doc ID                                        # plain text
  comments     --doc ID                                        # reviewer comments (Drive API)
  create       --title STR [--text STR | --text-file PATH]     # NEW: make a doc, print URL
  replace      --doc ID --find STR --replace STR [--regex]     # literal by default
  insert-top   --doc ID --title STR (--text STR | --text-file PATH)
  insert-after --doc ID --anchor STR [--title STR] (--text STR | --text-file PATH)
  append       --doc ID (--text STR | --text-file PATH)
  append-rich  --doc ID --md PATH [--verify STR ...]           # headings, bullets, bold, links,
                                                               #   tables, callouts — at the end
  remove       --doc ID --anchor STR [--anchor STR ...]        # delete whole paragraphs
  batch        --doc ID --file edits.json                      # apply a list of edits + verify

batch edits.json shape (unchanged from before):
  {
    "regex": false,
    "edits": [
      {"label":"...", "anchor":"unique substring", "replace":"...", "marker":"phrase from replace"},
      {"label":"...", "find":"exact text to swap", "replace":"...", "marker":"..."}
    ],
    "remove": ["stale section anchor", "..."],
    "changelog": {"title":"...", "lines":["• ...","• ..."]}
  }
  - "anchor": read the doc, find the UNIQUE line containing the substring, replace
    that whole line. Robust against smart-quote / punctuation drift.
  - "find":  exact text to replace (escaped to a literal unless top-level "regex": true).
  - "marker": a phrase that should appear AFTER the edit; used to verify it landed.

Index model: the Docs API works on character indices. This helper reads the doc's
structure to map paragraph text -> indices, so anchor/insert/remove all resolve
against live text. Deletes within a batch are ordered high->low so indices don't shift.
Anchor/insert/remove target TOP-LEVEL paragraphs (not text inside tables).
append-rich can ADD a new section with tables, hyperlinks, real bullets and shaded
callouts at the end of a doc; editing an EXISTING table still needs /gdoc-build.
"""
import argparse, json, os, re, subprocess, sys

# The gdoc family ALWAYS runs gws from the toolkit's own profile — forced per
# spawned process, so neither the default config dir nor an ambient
# GOOGLE_WORKSPACE_CLI_CONFIG_DIR (which may point at another tool's profile)
# can leak in. See skills/gws/references/multi-secret-profiles.md.
GWS_PROFILE = os.path.expanduser(
    os.path.join("~", ".config", "gws-profiles", "nsls-gdocs-skill")
)


def _parse_gws_json(out):
    """Parse gws stdout, tolerating a leading keyring/log line. None if unparseable."""
    try:
        return json.loads(out)
    except Exception:
        lines = out.splitlines()
        for i, ln in enumerate(lines):
            s = ln.lstrip()
            if s.startswith("{") or s.startswith("["):
                try:
                    return json.loads("\n".join(lines[i:]))
                except Exception:
                    return None
    return None


def gws(args, params=None, body=None):
    """Run a gws command, return parsed JSON. Any failure exits — never returns an error object.

    gws signals failure BOTH ways and you must check both: a non-zero exit code AND
    a JSON error object on *stdout*. e.g. a bad documentId gives exit 1 with
    `{"error": {"code": 404, ...}}` on stdout. Parsing stdout without checking either
    one returns that error dict to the caller as though the call succeeded — so a
    failed batchUpdate reads as a successful edit. Check the exit code first, then
    check for an `error` key even on exit 0.
    """
    cmd = ["gws"] + args
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    # Profile forced into the child (never setdefault, never a separate export:
    # an ambient/foreign GOOGLE_WORKSPACE_CLI_CONFIG_DIR would leak in, and an
    # export doesn't survive between an agent's Bash calls).
    env = dict(os.environ, GOOGLE_WORKSPACE_CLI_CONFIG_DIR=GWS_PROFILE)
    # encoding pinned: text=True alone decodes with the locale codec (cp1252 on
    # Windows), which crashes on the em dashes present in essentially every
    # NSLS doc. gws emits UTF-8 everywhere.
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if r.returncode == 2:
        sys.exit(
            "gws auth error (exit 2): no credentials in the toolkit profile.\n"
            "Fix:  python3 <plugin>/skills/gws/scripts/gws_doctor.py\n"
            "(It sets the profile itself and logs in with `granted ∪ requested`. Do NOT"
            " run a bare `gws auth login` — that authenticates the WRONG directory — nor a"
            " raw `gws auth login --services docs,drive`, which overwrites this shared"
            " profile's scopes and breaks squad-dashboard/receipts. Details:"
            " references/setup.md.)"
        )

    out = (r.stdout or "").strip()
    parsed = _parse_gws_json(out)

    def _fail(prefix):
        detail = ""
        if isinstance(parsed, dict) and isinstance(parsed.get("error"), dict):
            e = parsed["error"]
            detail = f" [{e.get('code')}] {e.get('message')}"
        sys.exit(f"{prefix} `gws {' '.join(args)}`{detail}\n"
                 + (out or r.stderr or "no output")[:400])

    if r.returncode != 0:
        _fail(f"gws call failed (exit {r.returncode}):")
    # Exit 0 with an error payload is possible; treat it as a failure, not a result.
    if isinstance(parsed, dict) and "error" in parsed:
        _fail("gws returned an error payload:")
    if parsed is None:
        _fail("gws returned unparseable output:")
    return parsed


# ---------- document structure helpers ----------

def get_doc(doc):
    return gws(["docs", "documents", "get"], params={"documentId": doc})


def _para_text(paragraph):
    return "".join(e.get("textRun", {}).get("content", "")
                   for e in paragraph.get("elements", []))


def paragraphs(docjson):
    """Top-level paragraphs as {raw, text, start, end}. `raw` keeps the trailing \\n."""
    out = []
    for el in docjson.get("body", {}).get("content", []):
        if "paragraph" in el:
            raw = _para_text(el["paragraph"])
            out.append({"raw": raw, "text": raw.rstrip("\n"),
                        "start": el.get("startIndex"), "end": el.get("endIndex")})
    return out


def full_text(docjson):
    """Plain text incl. table cell text (for read/verify). Mirrors getBody().getText()."""
    parts = []

    def walk(content):
        for el in content:
            if "paragraph" in el:
                parts.append(_para_text(el["paragraph"]))
            elif "table" in el:
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))
    walk(docjson.get("body", {}).get("content", []))
    return "".join(parts)


def body_end_index(docjson):
    content = docjson.get("body", {}).get("content", [])
    return content[-1].get("endIndex", 1) if content else 1


def batch_update(doc, requests):
    if not requests:
        return {"ok": True}
    return gws(["docs", "documents", "batchUpdate"],
               params={"documentId": doc}, body={"requests": requests})


# ---------- edit primitives ----------

def do_replace_literal(doc, find, replace):
    return batch_update(doc, [{
        "replaceAllText": {
            "containsText": {"text": find, "matchCase": True},
            "replaceText": replace if replace is not None else "",
        }
    }])


def do_replace_regex(doc, pattern, replace):
    """Client-side regex replace: the Docs API has no regex, so we resolve ranges
    from the live text and delete+insert from end->start so indices stay valid."""
    d = get_doc(doc)
    # Build an absolute-index map of the concatenated top-level paragraph text.
    segs, text = [], []
    pos = 0
    for el in d.get("body", {}).get("content", []):
        if "paragraph" in el:
            for e in el["paragraph"].get("elements", []):
                tr = e.get("textRun")
                if tr and "content" in tr and e.get("startIndex") is not None:
                    c = tr["content"]
                    segs.append((pos, pos + len(c), e["startIndex"]))
                    text.append(c)
                    pos += len(c)
    joined = "".join(text)

    def to_doc_index(off):
        for s, en, docstart in segs:
            if s <= off < en:
                return docstart + (off - s)
        return None

    matches = [(m.start(), m.end()) for m in re.finditer(pattern, joined)]
    reqs = []
    for s, e in reversed(matches):  # end -> start
        ds, de = to_doc_index(s), to_doc_index(e - 1)
        if ds is None or de is None:
            continue
        reqs.append({"deleteContentRange": {"range": {"startIndex": ds, "endIndex": de + 1}}})
        if replace:
            reqs.append({"insertText": {"location": {"index": ds}, "text": replace}})
    if reqs:
        batch_update(doc, reqs)
    return len(matches)


def _u16len(s):
    """Length in UTF-16 code units — the unit the Docs API indexes by.

    len() counts code points; the two differ on astral chars (emoji), which
    would shift every styled range that follows one.
    """
    return len(s.encode("utf-16-le")) // 2


def _insert_block(index, title, text, title_heading):
    """Return batchUpdate requests to insert `title` (styled) + `text` lines at `index`."""
    chunk = ""
    if title:
        chunk += title + "\n"
    if text:
        chunk += text + ("\n" if not text.endswith("\n") else "")
    reqs = [{"insertText": {"location": {"index": index}, "text": chunk}}]
    if title:
        reqs.append({"updateParagraphStyle": {
            "range": {"startIndex": index, "endIndex": index + _u16len(title) + 1},
            "paragraphStyle": {"namedStyleType": title_heading},
            "fields": "namedStyleType",
        }})
    # Pin the body lines to NORMAL_TEXT explicitly. Inserted text otherwise
    # inherits the paragraph style at the insertion point — inserting above a
    # heading once turned five body lines into HEADING_1 giants.
    body_start = index + (_u16len(title) + 1 if title else 0)
    body_end = index + _u16len(chunk)
    if body_end > body_start:
        reqs.append({"updateParagraphStyle": {
            "range": {"startIndex": body_start, "endIndex": body_end},
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
            "fields": "namedStyleType",
        }})
    return reqs


def do_insert_top(doc, title, text, level=2):
    # index 1 == start of body content
    return batch_update(doc, _insert_block(1, title, text, "HEADING_%d" % level))


def do_insert_after(doc, anchor, title, text, level=3):
    d = get_doc(doc)
    hit = [p for p in paragraphs(d) if anchor in p["text"]]
    if not hit:
        return {"ok": False, "error": "anchor not found: " + anchor}
    if len(hit) > 1:
        return {"ok": False, "error": "anchor matched %d paragraphs (not unique)" % len(hit)}
    return {"ok": True, "res": batch_update(doc, _insert_block(hit[0]["end"], title, text, "HEADING_%d" % level))}


def do_append(doc, text):
    d = get_doc(doc)
    idx = max(1, body_end_index(d) - 1)  # before the final newline of the body
    return batch_update(doc, [{"insertText": {"location": {"index": idx}, "text": "\n" + text}}])


def do_remove(doc, anchors):
    d = get_doc(doc)
    hits = [p for p in paragraphs(d)
            if any(a and a in p["text"] for a in anchors) and p["start"] is not None]
    # delete high -> low so earlier deletions don't shift later indices
    hits.sort(key=lambda p: p["start"], reverse=True)
    reqs = [{"deleteContentRange": {"range": {"startIndex": p["start"], "endIndex": p["end"]}}}
            for p in hits]
    batch_update(doc, reqs)
    return len(hits)


def do_comments(doc):
    fields = ("comments(id,author/displayName,content,quotedFileContent/value,"
              "resolved,replies(author/displayName,content))")
    r = gws(["drive", "comments", "list"],
            params={"fileId": doc, "fields": fields, "pageSize": 100})
    return r.get("comments", r)


def do_create(title, text):
    r = gws(["docs", "documents", "create"], body={"title": title})
    doc = r.get("documentId")
    if not doc:
        sys.exit("create failed: " + json.dumps(r)[:300])
    if text:
        batch_update(doc, [{"insertText": {"location": {"index": 1}, "text": text}}])
    return doc


def read_text(a):
    if a.text is not None:
        return a.text
    if a.text_file:
        return open(a.text_file, encoding="utf-8-sig").read()  # -sig: tolerate a PS 5.1 BOM
    return ""


# ---------- rich append (markdown subset, appended at the end of the doc) ----------

RICH_BULLET_PRESET = "BULLET_DISC_CIRCLE_SQUARE"
_RICH_INLINE = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)|\*\*(.+?)\*\*')


def rich_parse_inline(s):
    """'[text](url)' -> link run, '**text**' -> bold run.

    Returns (plain, spans); each span is (start, end, textStyle, fields) with
    offsets in UTF-16 units relative to the start of `plain`, which is the unit
    the Docs API indexes by."""
    out, spans, pos = "", [], 0
    for m in _RICH_INLINE.finditer(s):
        out += s[pos:m.start()]
        if m.group(1) is not None:
            a = _u16len(out); out += m.group(1)
            spans.append((a, _u16len(out), {"link": {"url": m.group(2)}}, "link"))
        else:
            a = _u16len(out); out += m.group(3)
            spans.append((a, _u16len(out), {"bold": True}, "bold"))
        pos = m.end()
    out += s[pos:]
    return out, spans


def rich_parse_blocks(md):
    """Markdown subset -> ordered blocks.

    Line grammar:  '# '..'#### ' heading (HEADING_1..4) | '- ' bullet | '> ' callout
    (one shaded table cell) | '| a | b |' table row (first row is the header;
    '|---|' separator rows are ignored) | anything else a normal paragraph.
    Blank lines are skipped. Consecutive non-table lines form one text block so
    they go to the API as a single insertText.

    Inline markup is deliberately small: '**bold**' and '[text](url)', NOT nested
    (bold inside a link or a link inside bold renders as literal markup), and a
    link URL may not contain whitespace or ')'. Anything else is plain text."""
    blocks, chunk, table = [], [], []

    def flush_chunk():
        nonlocal chunk
        if chunk:
            blocks.append(("text", chunk)); chunk = []

    def flush_table():
        nonlocal table
        if table:
            blocks.append(("table", table)); table = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("|"):
            flush_chunk()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r"[-:\s]*", c) for c in cells):
                continue
            table.append(cells); continue
        flush_table()
        if line.startswith("> "):
            flush_chunk(); blocks.append(("callout", [[line[2:].strip()]])); continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            chunk.append({"kind": "HEADING_%d" % len(m.group(1)), "src": m.group(2)}); continue
        if line.startswith("- "):
            # createParagraphBullets strips leading tabs (it reads them as nesting), which
            # would leave every later offset stale — strip them before measuring anything.
            chunk.append({"kind": "bullet", "src": line[2:].lstrip("\t")}); continue
        chunk.append({"kind": "NORMAL_TEXT", "src": line})
    flush_chunk(); flush_table()
    return blocks


def _rich_style_reqs(base, spans):
    return [{"updateTextStyle": {"range": {"startIndex": base + a, "endIndex": base + b},
                                 "textStyle": st, "fields": fields}}
            for a, b, st, fields in spans]


def _rich_append_text(doc, paras):
    """Append heading/bullet/normal paragraphs in ONE insertText, then pin each
    paragraph's named style and bullet state explicitly (inserted text otherwise
    inherits whatever the last paragraph had)."""
    d = get_doc(doc)
    idx = body_end_index(d) - 1
    plist = paragraphs(d)
    prefix = "\n" if (plist and plist[-1]["text"].strip()) else ""
    parsed = [(p["kind"],) + rich_parse_inline(p["src"]) for p in paras]
    chunk = prefix + "\n".join(plain for _, plain, _ in parsed)
    reqs = [{"insertText": {"location": {"index": idx}, "text": chunk}}]
    # Inserted text inherits the style of the character before it: a doc that ends in a
    # bold link would make the whole appendix bold and linked. Reset to baseline first;
    # listing "link" in fields without a link value clears any inherited link.
    # Listing a field with no value clears the explicit override, so the paragraph's named
    # style (a heading's bold, its size) shows through instead of being forced off.
    reqs.append({"updateTextStyle": {
        "range": {"startIndex": idx, "endIndex": idx + _u16len(chunk)},
        "textStyle": {},
        "fields": "bold,italic,underline,strikethrough,link,foregroundColor,backgroundColor,"
                  "fontSize,weightedFontFamily,smallCaps,baselineOffset"}})
    cur = idx + _u16len(prefix)
    for kind, plain, spans in parsed:
        n = _u16len(plain)
        rng = {"startIndex": cur, "endIndex": cur + n + 1}
        reqs.append({"updateParagraphStyle": {
            "range": rng, "fields": "namedStyleType",
            "paragraphStyle": {"namedStyleType": "NORMAL_TEXT" if kind == "bullet" else kind}}})
        if kind == "bullet":
            reqs.append({"createParagraphBullets": {"range": rng, "bulletPreset": RICH_BULLET_PRESET}})
        else:
            reqs.append({"deleteParagraphBullets": {"range": rng}})
        reqs += _rich_style_reqs(cur, spans)
        cur += n + 1
    batch_update(doc, reqs)


def _rich_append_table(doc, rows, callout=False):
    """Insert an empty table at the end, re-read to learn the cell indices, then
    fill cells from the LAST cell backwards so earlier indices never shift.
    Header row (row 0) is bolded; a callout is a single shaded cell."""
    cols = max(len(r) for r in rows)
    rows = [r + [""] * (cols - len(r)) for r in rows]
    # Anchor to where we insert: a collaborator's concurrent table elsewhere must never be
    # mistaken for ours, so pick the first table at or after the end index we inserted at.
    at = body_end_index(get_doc(doc)) - 1
    batch_update(doc, [{"insertTable": {"rows": len(rows), "columns": cols,
                                        "endOfSegmentLocation": {"segmentId": ""}}}])
    d = get_doc(doc)
    t = next(el for el in d["body"]["content"] if "table" in el and el["startIndex"] >= at)
    cells = [(r, c, cell["content"][0]["startIndex"])
             for r, row in enumerate(t["table"]["tableRows"])
             for c, cell in enumerate(row["tableCells"])]
    reqs = []
    for r, c, start in sorted(cells, key=lambda x: -x[2]):
        plain, spans = rich_parse_inline(rows[r][c])
        if not plain:
            continue
        reqs.append({"insertText": {"location": {"index": start}, "text": plain}})
        if r == 0 and not callout:
            reqs.append({"updateTextStyle": {"range": {"startIndex": start, "endIndex": start + _u16len(plain)},
                                              "textStyle": {"bold": True}, "fields": "bold"}})
        reqs += _rich_style_reqs(start, spans)
    if callout:
        reqs.append({"updateTableCellStyle": {
            "tableRange": {"tableCellLocation": {"tableStartLocation": {"index": t["startIndex"]},
                                                 "rowIndex": 0, "columnIndex": 0},
                           "rowSpan": 1, "columnSpan": 1},
            "tableCellStyle": {"backgroundColor": {"color": {"rgbColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}}},
            "fields": "backgroundColor"}})
    batch_update(doc, reqs)
    # Docs creates a paragraph after every table, and it inherits the bullet of
    # the paragraph above the table — clear it so the next block starts clean.
    d = get_doc(doc)
    t = next(el for el in d["body"]["content"] if "table" in el and el["startIndex"] >= at)
    after = next(p for p in paragraphs(d) if p["start"] is not None and p["start"] >= t["endIndex"])
    rng = {"startIndex": after["start"], "endIndex": after["end"]}
    # deleteParagraphBullets keeps the list's indent as indentStart; clear that too, or the
    # next heading or paragraph sits indented like the list above the table.
    batch_update(doc, [{"deleteParagraphBullets": {"range": rng}},
                       {"updateParagraphStyle": {"range": rng, "fields": "namedStyleType,indentStart,indentFirstLine",
                                                 "paragraphStyle": {"namedStyleType": "NORMAL_TEXT",
                                                                    "indentStart": {"magnitude": 0, "unit": "PT"},
                                                                    "indentFirstLine": {"magnitude": 0, "unit": "PT"}}}}])


def rich_missing_markers(before, after, verify):
    """A --verify phrase counts only if the append ADDED an occurrence: a phrase
    that was already in the doc must not make an accidental no-op look verified."""
    return [v for v in verify if after.count(v) <= before.count(v)]


def do_append_rich(doc, md, verify=()):
    """Append a markdown-subset section to the end of `doc`; returns (blocks, missing_markers).

    Exits if the markdown parses to zero blocks (an empty or whitespace-only file
    must fail loudly, not report "blocks applied: 0")."""
    blocks = rich_parse_blocks(md)
    if not blocks:
        sys.exit("append-rich: the --md file parsed to zero blocks (empty or whitespace-only?)")
    before = full_text(get_doc(doc))
    for kind, payload in blocks:
        if kind == "text":
            _rich_append_text(doc, payload)
        elif kind == "table":
            _rich_append_table(doc, payload)
        else:
            _rich_append_table(doc, payload, callout=True)
    after = full_text(get_doc(doc))
    return len(blocks), rich_missing_markers(before, after, verify)


# ---------- CLI ----------

def main():
    # Windows consoles default to a legacy codepage; re-encode stdout so
    # printing doc text (em dashes, smart quotes) can't crash read/comments —
    # the output-side twin of the subprocess decode fix above.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Read, edit, and create Google Docs via gws.")
    ap.add_argument("action", choices=["read", "comments", "create", "replace", "insert-top",
                                       "insert-after", "append", "append-rich", "remove", "batch"])
    ap.add_argument("--doc", help="Google Doc ID (required for all actions except create)")
    ap.add_argument("--find")
    ap.add_argument("--replace")
    ap.add_argument("--regex", action="store_true", help="treat --find as a regex (default: literal)")
    ap.add_argument("--title")
    ap.add_argument("--anchor", action="append", help="repeatable; line/section anchor substring")
    ap.add_argument("--text")
    ap.add_argument("--text-file", dest="text_file")
    ap.add_argument("--file", help="batch edits JSON")
    ap.add_argument("--md", help="append-rich: markdown-subset file to append at the end")
    ap.add_argument("--verify", action="append", default=[],
                    help="append-rich: phrase that must be present after the append (repeatable)")
    ap.add_argument("--level", type=int, choices=[1, 2, 3, 4],
                    help="heading level for the inserted --title "
                         "(default: 2 for insert-top, 3 for insert-after)")
    a = ap.parse_args()

    if a.action != "create" and not a.doc:
        sys.exit(a.action + " needs --doc")

    if a.action == "read":
        sys.stdout.write(full_text(get_doc(a.doc)))

    elif a.action == "comments":
        print(json.dumps(do_comments(a.doc), indent=2, ensure_ascii=False))

    elif a.action == "create":
        if not a.title:
            sys.exit("create needs --title")
        doc = do_create(a.title, read_text(a))
        print("ok  https://docs.google.com/document/d/%s/edit  (id: %s)" % (doc, doc))

    elif a.action == "replace":
        if a.find is None or a.replace is None:
            sys.exit("replace needs --find and --replace")
        if a.regex:
            n = do_replace_regex(a.doc, a.find, a.replace)
            print("ok, matches=%d" % n)
        else:
            r = do_replace_literal(a.doc, a.find, a.replace)
            print("ok" if r.get("ok", "replies" in r or "documentId" in r) else "FAILED: " + str(r))

    elif a.action == "insert-top":
        if not a.title:
            sys.exit("insert-top needs --title")
        do_insert_top(a.doc, a.title, read_text(a), level=a.level or 2)
        print("ok")

    elif a.action == "insert-after":
        if not a.anchor:
            sys.exit("insert-after needs --anchor")
        r = do_insert_after(a.doc, a.anchor[0], a.title or "", read_text(a),
                            level=a.level or 3)
        print("ok" if r.get("ok") else "FAILED: " + str(r.get("error", r)))

    elif a.action == "append":
        do_append(a.doc, read_text(a))
        print("ok")

    elif a.action == "append-rich":
        if not a.md:
            sys.exit("append-rich needs --md")
        n, missing = do_append_rich(a.doc, open(a.md, encoding="utf-8-sig").read(), a.verify)
        print("blocks applied: %d" % n)
        print("verify: " + ("all newly present ✓" if not missing
                            else "MISSING or not newly added: " + "; ".join(missing)))
        if missing:
            sys.exit(1)

    elif a.action == "remove":
        if not a.anchor:
            sys.exit("remove needs at least one --anchor")
        print("ok, removed=%d" % do_remove(a.doc, a.anchor))

    elif a.action == "batch":
        if not a.file:
            sys.exit("batch needs --file")
        cfg = json.load(open(a.file, encoding="utf-8-sig"))  # -sig: tolerate a PS 5.1 BOM
        use_regex = cfg.get("regex", False)
        lines = full_text(get_doc(a.doc)).split("\n")
        results = []
        for e in cfg.get("edits", []):
            if "anchor" in e:
                m = [ln for ln in lines if e["anchor"] in ln]
                if len(m) != 1:
                    results.append((e.get("label", "?"), "ANCHOR matched x%d (skipped)" % len(m)))
                    continue
                find, is_re = m[0], False
            else:
                find, is_re = e["find"], use_regex
            if is_re:
                do_replace_regex(a.doc, find, e["replace"])
                results.append((e.get("label", "?"), "ok(regex)"))
            else:
                do_replace_literal(a.doc, find, e["replace"])
                results.append((e.get("label", "?"), "ok"))
        if cfg.get("remove"):
            n = do_remove(a.doc, cfg["remove"])
            results.append(("remove", "removed=%d" % n))
        cl = cfg.get("changelog")
        if cl:
            do_insert_top(a.doc, cl["title"], "\n".join(cl.get("lines", [])))
            results.append(("changelog", "ok"))
        new = full_text(get_doc(a.doc))
        print("== applied ==")
        for lbl, st in results:
            print("  %s: %s" % (lbl, st))
        miss = [e.get("label", "?") for e in cfg.get("edits", [])
                if e.get("marker") and e["marker"] not in new]
        gone = [a2 for a2 in cfg.get("remove", []) if a2 in new]
        print("== verify ==")
        print("  markers: " + ("all present ✓" if not miss else "MISSING: " + ", ".join(miss)))
        if cfg.get("remove"):
            print("  removed: " + ("all gone ✓" if not gone else "STILL PRESENT: " + ", ".join(gone)))


if __name__ == "__main__":
    main()
