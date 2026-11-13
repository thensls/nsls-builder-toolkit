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
import argparse, html, json, os, re, subprocess, sys, unicodedata

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

# --suggestions choice -> the Docs API suggestionsViewMode value.
#
# DANGER: the two PREVIEW modes return text with suggestions resolved, so every
# character index shifts relative to the live document. An edit computed against
# previewed text would land in the wrong place. Only `read` may pass a mode;
# every editing action calls get_doc() with the default and gets the live doc.
SUGGESTION_VIEWS = {
    "inline": "SUGGESTIONS_INLINE",
    "accepted": "PREVIEW_SUGGESTIONS_ACCEPTED",
    "rejected": "PREVIEW_WITHOUT_SUGGESTIONS",
}


def get_doc(doc, suggestions="inline"):
    params = {"documentId": doc}
    view = SUGGESTION_VIEWS.get(suggestions)
    # Send the parameter only for a non-default view: an unknown-but-harmless
    # param is still a behaviour change to every caller, and every editing
    # action goes through here.
    if view and suggestions != "inline":
        params["suggestionsViewMode"] = view
    return gws(["docs", "documents", "get"], params=params)


def count_suggestions(docjson):
    """(insertions, deletions) — text runs carrying pending suggestion ids.

    Counts RUNS, not suggestions: one person's edit can be split across several
    runs, so the number is "at least this much is pending", which is all the
    warning needs to claim. Walks table cells too, because a redline inside a
    table is exactly as misleading as one in a paragraph.

    Only meaningful under SUGGESTIONS_INLINE. The preview modes resolve
    suggestions away and strip the ids, so both counts come back zero there --
    which is correct, not a miss: nothing in that output is ambiguous.
    """
    ins = dele = 0

    def walk(content):
        nonlocal ins, dele
        for el in content:
            if "paragraph" in el:
                for e in el["paragraph"].get("elements", []):
                    run = e.get("textRun")
                    if not run:
                        continue
                    if run.get("suggestedInsertionIds"):
                        ins += 1
                    if run.get("suggestedDeletionIds"):
                        dele += 1
            elif "table" in el:
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(docjson.get("body", {}).get("content", []))
    return ins, dele


def pending_warning(docjson, editing=False):
    """The one-line PENDING SUGGESTIONS warning, or None when nothing is pending.

    `read` and the editing actions share the count; only the advice differs.
    An edit is worse than a misread: the API only makes direct edits, so a
    replace, remove or anchor edit on a line holding a colleague's suggestion
    replaces their suggestion instead of leaving it for them to accept.
    """
    ins, dele = count_suggestions(docjson)
    if not (ins or dele):
        return None
    if editing:
        return (f"\u26a0\ufe0f  PENDING SUGGESTIONS: this document has {ins} inserted and "
                f"{dele} deleted text run(s) nobody has accepted yet. This is a direct edit, "
                f"not a suggestion: where it touches a line holding one, it replaces that "
                f"suggestion. Run read to check what changed.")
    return (f"\u26a0\ufe0f  PENDING SUGGESTIONS: {ins} inserted and {dele} deleted "
            f"text run(s) below are UNACCEPTED edits, shown inline. What follows "
            f"is a redline, not the live document. Re-run with "
            f"--suggestions accepted (or rejected) to see one resolved version.")


def warn_before_edit(doc):
    """Fetch the live doc, print the warning first if anything is pending, return it.

    Printed before the edit runs, so a gws failure mid-edit can't swallow it.
    """
    d = get_doc(doc)
    w = pending_warning(d, editing=True)
    if w:
        print(w)
    return d


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


def do_replace_regex(doc, pattern, replace, d=None):
    """Client-side regex replace: the Docs API has no regex, so we resolve ranges
    from the live text and delete+insert from end->start so indices stay valid.
    `d` is the doc as just fetched; leave it out once an earlier edit has moved it."""
    d = d or get_doc(doc)
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


def do_insert_after(doc, anchor, title, text, level=3, d=None):
    d = d or get_doc(doc)
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


def do_remove(doc, anchors, d=None):
    d = d or get_doc(doc)
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


# ---------- anchored comments (Docs API insertComment) ----------
#
# Until 2026-09-30 an anchored comment could only be made by driving the Docs
# editor: Drive's comments.create accepts an `anchor` but the editors ignore it,
# and a Drive comment sent with one renders as an orphan reading "Original
# content deleted". Never use that route. The Docs API's insertComment request
# (generally available 2026-09-30) takes a text range and has Google's own
# server mint the kix anchor the editor uses, so the comment sits in the margin
# against its words like any comment a person made.

EXIT_ANCHOR = 3
OBJECT_MARK = "\ufffc"  # stands in for a non-text element in the character map
COMMENT_MAX = 2048  # insertComment's limit, in UTF-8 BYTES: an em dash costs three


def _paragraph_map(docjson):
    """Every paragraph, table cells included, as (text, [document index of each char])."""
    out = []

    def walk(content):
        for el in content:
            if "paragraph" in el:
                txt, idx = [], []
                for e in el["paragraph"].get("elements", []):
                    pos = e.get("startIndex")
                    if pos is None:
                        continue
                    if "textRun" not in e:
                        # A footnote marker, inline image, smart chip or similar: it
                        # occupies document positions but carries no text. Leaving it
                        # out let "about rubrics" match across a footnote between the
                        # words, with a range that silently took the footnote along.
                        # A visible placeholder per position keeps the map honest: the
                        # preview shows the object, and a plain phrase can't jump it.
                        for q in range(pos, e.get("endIndex", pos + 1)):
                            txt.append(OBJECT_MARK)
                            idx.append(q)
                        continue
                    for ch in e["textRun"].get("content", ""):
                        txt.append(ch)
                        idx.append(pos)
                        pos += _u16len(ch)
                out.append(("".join(txt), idx))
            elif "table" in el:
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(docjson.get("body", {}).get("content", []))
    return out


def find_anchor(paras, anchor):
    """Every occurrence of `anchor` as (paragraph, char offset, start index, end index).

    Searches whole paragraphs rather than single text runs: a phrase with a bold
    word or a link inside it is split across runs and a run-by-run search misses
    it. Indices come from the per-character map, so an emoji earlier in the
    paragraph (two UTF-16 units, one Python char) does not shift the range.
    """
    hits = []
    for p, (txt, idx) in enumerate(paras):
        k = txt.find(anchor)
        while k >= 0:
            last = k + len(anchor) - 1
            # Backstop: a match is only real if its characters are adjacent in the
            # document. Any gap means something the map didn't see sits inside it.
            if all(idx[j + 1] == idx[j] + _u16len(txt[j]) for j in range(k, last)):
                hits.append((p, k, idx[k], idx[last] + _u16len(txt[last])))
            k = txt.find(anchor, k + 1)
    return hits


def _anchor_context(paras, p, k, anchor):
    """The anchor's paragraph with the phrase underlined, between its nearest non-blank neighbours."""
    def neighbour(step):
        q = p + step
        while 0 <= q < len(paras) and not paras[q][0].strip():
            q += step
        return paras[q][0].rstrip("\n") if 0 <= q < len(paras) else None

    lines = []
    before, after = neighbour(-1), neighbour(1)
    if before is not None:
        lines.append("     " + before)
    lines.append("  >  " + paras[p][0].rstrip("\n"))
    def cols(t):  # terminal width: wide glyphs such as ✅ take two columns
        return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in t)
    lines.append("     " + " " * cols(paras[p][0][:k]) + "^" * cols(anchor))
    if after is not None:
        lines.append("     " + after)
    return "\n".join(lines)


def do_comment(doc, anchor, body, occurrence=None, recommend=None, why=None, preview=False):
    """Preview, or post, one comment anchored to `anchor`. Exits EXIT_ANCHOR rather than guess.

    One comment per call on purpose: on a colleague's document every comment
    needs its own yes, and a batch would make one approval cover several.
    """
    if not anchor.strip():
        print("ANCHOR_EMPTY: an empty phrase matches everywhere. Give the exact words to attach the comment to.")
        sys.exit(EXIT_ANCHOR)
    if "\n" in anchor:
        print("ANCHOR_MULTILINE: the anchor spans a paragraph break. Pick a phrase inside one paragraph.")
        sys.exit(EXIT_ANCHOR)
    if not preview and not body.strip():
        sys.exit("comment needs --text or --text-file")
    size = len(body.encode("utf-8"))
    if size > COMMENT_MAX:
        sys.exit(f"comment text is {size} bytes; Google's limit is {COMMENT_MAX} UTF-8 bytes")

    d = warn_before_edit(doc)
    paras = _paragraph_map(d)
    hits = find_anchor(paras, anchor)
    n = len(hits)

    if n == 0:
        print(f"TEXT_NOT_FOUND: {anchor!r} is not in the document. Nothing was posted.")
        print("Re-read it -- the text may have changed since the comment was drafted.")
        sys.exit(EXIT_ANCHOR)

    # --recommend only ever displays. Without this, a unique phrase skipped the
    # branch and `--recommend 1` posted straight away.
    if occurrence is None and (n > 1 or recommend is not None):
        # Ambiguous. Without --recommend: list every candidate and refuse, so nothing
        # ever lands on a coin-flip. With --recommend: the model has judged, so show
        # its pick first with its reason and keep the rest on screen as alternatives
        # -- a recommendation nobody can check is a guess. Either way nothing posts:
        # posting needs --occurrence, after the person has seen the choice.
        if recommend is not None and not 1 <= recommend <= n:
            sys.exit(f"--recommend {recommend} is out of range: {n} matches")
        order = list(range(1, n + 1))
        if recommend:
            order.remove(recommend)
            order.insert(0, recommend)
            print(f"{anchor!r} appears {n} time{'s' if n != 1 else ''} -- recommended one first.\n")
        else:
            print(f"AMBIGUOUS: {anchor!r} appears {n} times. Nothing was posted.")
            print("Decide which one the comment belongs on, then re-run with --recommend N --why \"...\".\n")
        for i in order:
            p, k, _, _ = hits[i - 1]
            if i == recommend:
                print(f"★ RECOMMENDED -- occurrence {i} of {n}")
                if why:
                    print(f"  why: {why}")
            else:
                print(f"--- {'alternative' if recommend else 'occurrence'} {i} of {n} ---")
            print(_anchor_context(paras, p, k, anchor) + "\n")
        if recommend and preview and body.strip():
            print("Comment:\n" + "\n".join("    " + ln for ln in body.splitlines()))
        if recommend:
            print(f"\n[to post, confirm the choice: --occurrence {recommend}]")
            sys.exit(0 if preview else EXIT_ANCHOR)
        sys.exit(EXIT_ANCHOR)

    if occurrence is None:
        occurrence = 1
    if not 1 <= occurrence <= n:
        sys.exit(f"--occurrence {occurrence} is out of range: {n} match(es)")
    p, k, start, end = hits[occurrence - 1]

    if preview:
        print(_anchor_context(paras, p, k, anchor))
        print(f"\n[anchor: occurrence {occurrence} of {n}]")
        if body.strip():
            print("\nComment:\n" + "\n".join("    " + ln for ln in body.splitlines()))
        return

    r = batch_update(doc, [{"insertComment": {
        "range": {"startIndex": start, "endIndex": end}, "content": body}}])
    thread = (r.get("replies") or [{}])[0].get("insertComment", {}).get("commentThread", {})
    state = r.get("commentUpdateState")
    # plainTextQuote comes back HTML-escaped ("Builder &#183; heavy builder"), so
    # compare after unescaping or a correct anchor reads as a mismatch.
    quote = html.unescape(thread.get("plainTextQuote") or "")
    if state != "ALL_SAVED" or quote != anchor or not thread.get("anchorId"):
        print(f"NOT CONFIRMED: save state {state!r}, anchored on {quote!r}, "
              f"anchor id {thread.get('anchorId')!r}. Check the document before trying again "
              f"-- a retry can post the same comment twice.")
        sys.exit(1)
    print(f"posted ✓  anchored on {quote!r}  (anchor {thread['anchorId']}, "
          f"comment {thread.get('commentId')})")


# ---------- the approval card (draft comments shown for a person's go) ----------
#
# `comment` posts one comment. `comment-card` is what a person approves before any
# are posted: every draft shown as the passage reads in the document, the anchored
# words in brackets with a highlighter behind them, the comment underneath, a
# one-click Skip and an Edit per comment, and one button that sends the go. The
# output is an HTML fragment for the chat's visual widget, printed verbatim.
#
# Built after Davo tried the multiple-choice question box on 2026-11-08: it shows
# plain text only, so nothing could be highlighted, and skipping took two clicks.

CARD_CONTEXT = 230  # characters of the document shown either side of the anchor


def _suggestion_kinds(docjson):
    """Document index -> "del" or "ins" for every character inside a pending suggestion.

    The card shows passages as they read in the editor with suggestions inline. Without
    this, a pending deletion and its replacement printed as one settled sentence -- the
    same trap `read` warns about -- and a person could approve a comment against text
    that isn't current.
    """
    kinds = {}

    def walk(content):
        for el in content:
            if "paragraph" in el:
                for e in el["paragraph"].get("elements", []):
                    tr, pos = e.get("textRun"), e.get("startIndex")
                    if not tr or pos is None:
                        continue
                    kind = ("del" if tr.get("suggestedDeletionIds") else
                            "ins" if tr.get("suggestedInsertionIds") else None)
                    if kind:
                        for q in range(pos, e.get("endIndex", pos)):
                            kinds[q] = kind
            elif "table" in el:
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(docjson.get("body", {}).get("content", []))
    return kinds


def _card_window(paras, p, k, anchor, kinds):
    """The text before, of, and after an anchor as (character, suggestion kind) pairs:
    about CARD_CONTEXT characters each side, cut at a word, runs of blank lines
    collapsed. Kept as pairs so trimming can never misalign the suggestion marks."""
    chars, starts = [], []
    for txt, idx in paras:
        starts.append(len(chars))
        chars.extend((ch, kinds.get(i, "")) for ch, i in zip(txt, idx))
    pos = starts[p] + k
    lo = max(0, pos - CARD_CONTEXT)
    hi = min(len(chars), pos + len(anchor) + CARD_CONTEXT)
    before, mid, after = chars[lo:pos], chars[pos:pos + len(anchor)], chars[pos + len(anchor):hi]
    if lo > 0:
        cut = next((j for j, (ch, _) in enumerate(before) if ch == " "), None)
        before = [("…", "")] + (before[cut + 1:] if cut is not None else before)
    if hi < len(chars):
        cut = next((j for j in range(len(after) - 1, 0, -1) if after[j][0] == " "), None)
        after = (after[:cut] if cut else after) + [("…", "")]

    def tidy(seq):
        out = []
        for ch, kd in seq:
            if ch == "\n" and out and out[-1][0] == "\n":
                continue
            out.append((ch, kd))
        return out

    before, after = tidy(before), tidy(after)
    while before and before[0][0] == "\n":
        before.pop(0)
    while after and after[-1][0] == "\n":
        after.pop()
    return before, mid, after


def _marked(pairs):
    """Escaped HTML for (character, kind) pairs, suggestions wrapped as Docs shows them."""
    out, i = [], 0
    while i < len(pairs):
        kind, j = pairs[i][1], i
        while j < len(pairs) and pairs[j][1] == kind:
            j += 1
        seg = html.escape("".join(ch for ch, _ in pairs[i:j]))
        out.append(f"<{kind}>{seg}</{kind}>" if kind else seg)
        i = j
    return "".join(out)


_CARD_STYLE = """<style>
.gc{background:var(--surface-2);border:0.5px solid var(--border);border-radius:12px;padding:1rem 1.25rem;margin:0 0 12px}
.gc [hidden]{display:none}
.gc-ctx{font-size:15px;line-height:1.7;color:var(--text-secondary);white-space:pre-wrap;margin:0}
.gc-ctx mark{background:var(--bg-highlight,var(--bg-warning));color:var(--text-primary);font-weight:500;padding:1px 3px;border-radius:3px}
.gc-cm{display:flex;gap:10px;margin:12px 0 0;padding:10px 12px;background:var(--surface-1);border-radius:var(--radius);font-size:15px;line-height:1.6;color:var(--text-primary)}
.gc-cm i{font-size:18px;color:var(--text-secondary);margin-top:2px}
.gc-txt{white-space:pre-wrap}
.gc-ta{flex:1;min-height:6em;font:inherit;line-height:1.6;resize:vertical}
.gc-row{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:10px}
.gc-n{font-size:13px;color:var(--text-muted)}
.gc-tag{display:none;margin-left:8px;font-size:12px;padding:2px 8px;border-radius:var(--radius);background:var(--bg-accent);color:var(--text-accent)}
.edited .gc-tag{display:inline}
.gc-err{font-size:13px;color:var(--text-danger);margin:6px 0 0}
.gc-err:empty{display:none}
.off{background:var(--surface-1)}
.off .gc-ctx,.off .gc-cm{color:var(--text-muted)}
.off .gc-ctx mark{background:transparent;color:var(--text-muted)}
.off .gc-txt{text-decoration:line-through}
.ok{box-shadow:inset 3px 0 0 var(--text-success)}
.gc button[aria-pressed="true"]{font-weight:500}
.gc-ctx del{color:var(--text-danger)}
.gc-ctx ins{color:var(--text-success);text-decoration:underline}
.gc-warn{font-size:14px;line-height:1.5;color:var(--text-warning);background:var(--bg-warning);border-radius:var(--radius);padding:8px 12px;margin:0 0 12px}
</style>"""

_CARD_JS = r"""const st={},edits={},all=Object.keys(D.items).map(Number),go=document.getElementById('gc-go'),goErr=document.getElementById('gc-goerr'),tally=document.getElementById('gc-tally');
all.forEach(n=>st[n]='');
const card=n=>document.getElementById('gc'+n),btn=(n,k)=>card(n).querySelector('[data-'+k+']'),open=n=>!card(n).querySelector('.gc-ta').hidden;
function count(){const a=all.filter(n=>st[n]==='ok'),s=all.filter(n=>st[n]==='off'),u=all.filter(n=>!st[n]);
tally.textContent=a.length+' accepted · '+s.length+' skipped'+(u.length?' · '+u.length+' to decide':'');
go.textContent=a.length?'Post '+a.length+' comment'+(a.length>1?'s':'')+' ↗':u.length?'Post accepted comments ↗':'Post nothing ↗';goErr.textContent=''}
function set(n,v){st[n]=v;const c=card(n),A=btn(n,'accept'),S=btn(n,'skip');c.classList.toggle('ok',v==='ok');c.classList.toggle('off',v==='off');
A.textContent=v==='ok'?'Accepted ✓':'Accept';A.setAttribute('aria-pressed',v==='ok');S.textContent=v==='off'?'Undo skip':'Skip';S.setAttribute('aria-pressed',v==='off');count()}
function lock(n,on){btn(n,'accept').disabled=on;btn(n,'skip').disabled=on}
document.querySelectorAll('[data-accept]').forEach(b=>b.addEventListener('click',()=>{const n=+b.dataset.accept;if(!open(n))set(n,st[n]==='ok'?'':'ok')}));
document.querySelectorAll('[data-skip]').forEach(b=>b.addEventListener('click',()=>{const n=+b.dataset.skip;if(!open(n))set(n,st[n]==='off'?'':'off')}));
document.querySelectorAll('[data-edit]').forEach(b=>b.addEventListener('click',()=>{const n=+b.dataset.edit,c=card(n),sp=c.querySelector('.gc-txt'),ta=c.querySelector('.gc-ta'),er=c.querySelector('.gc-err');
if(ta.hidden){ta.value=edits[n]??D.items[n];sp.hidden=true;ta.hidden=false;ta.style.height=Math.max(ta.scrollHeight,96)+'px';ta.focus();b.textContent='Done';lock(n,true);return}
const v=ta.value.trim();
if(!v){er.textContent='A comment can’t be empty.';return}
if(new TextEncoder().encode(v).length>2048){er.textContent='Too long for Google Docs: keep it under 2,048 bytes.';return}
er.textContent='';if(v!==D.items[n].trim()){edits[n]=v;c.classList.add('edited')}else{delete edits[n];c.classList.remove('edited')}
sp.textContent=v;ta.hidden=true;sp.hidden=false;b.textContent='Edit';lock(n,false);set(n,'ok')}));
document.querySelectorAll('.gc-ta').forEach(t=>t.addEventListener('input',()=>{t.closest('.gc').querySelector('.gc-err').textContent=''}));
go.addEventListener('click',()=>{if(all.some(open)){goErr.textContent='Finish editing first: press Done on the open comment.';return}
const u=all.filter(n=>!st[n]);if(u.length){goErr.textContent='Accept or skip every comment first. Still to decide: '+u.join(', ')+'.';return}
const k=all.filter(n=>st[n]==='ok');let m;
if(!k.length)m='Post none of the comments on “'+D.title+'”.';
else{m='Go: post comments '+k.join(', ')+' on “'+D.title+'”.';k.forEach(n=>{if(edits[n])m+='\n\nComment '+n+', edited:\n'+edits[n]})}
go.disabled=true;go.textContent='Sent ✓';document.querySelectorAll('.gc button').forEach(x=>x.disabled=true);SEND(k,edits,m)});
count();"""


_SEND_CHAT = "const SEND=(k,e,m)=>sendPrompt(m);"


def _card_html(doc, title, cards, total, has_suggestions=False, send_js=_SEND_CHAT, nonce=None):
    """The card's HTML. In the chat (the default) the go button sends a chat message; served by
    `comment-serve`, `send_js` posts the decision straight to the helper instead."""
    e = html.escape
    out = ['<h2 class="sr-only">Draft comments for ' + e(title) + ', each shown in its surrounding '
           'text with the anchored words highlighted, with accept, edit and skip for each and one '
           'button to post the accepted ones.</h2>', _CARD_STYLE, '<div style="padding:0.5rem 0 0">']
    if has_suggestions:
        out.append('<p class="gc-warn">This document has unaccepted suggested edits. The passages '
                   'show them as Docs does: <del>struck through</del> is a pending deletion, '
                   '<ins>underlined</ins> a pending insertion. Neither is settled text yet.</p>')
    for c in cards:
        where = f"{c['n']} of {total}"
        if c["total"] > 1:
            where += f" · match {c['occurrence']} of {c['total']} for this phrase"
        out.append(
            f'<div class="gc" id="gc{c["n"]}">'
            f'<p class="gc-ctx">{_marked(c["before"])}<mark>[{_marked(c["mid"])}]</mark>{_marked(c["after"])}</p>'
            f'<div class="gc-cm"><i class="ti ti-message" aria-hidden="true"></i>'
            f'<span class="gc-txt">{e(c["text"])}</span>'
            f'<textarea class="gc-ta" hidden aria-label="Edit comment {c["n"]}"></textarea></div>'
            f'<p class="gc-err" role="alert"></p>'
            f'<div class="gc-row"><span class="gc-n">{e(where)}<span class="gc-tag">Edited</span></span>'
            f'<span><button data-accept="{c["n"]}" aria-pressed="false">Accept</button> '
            f'<button data-edit="{c["n"]}">Edit</button> '
            f'<button data-skip="{c["n"]}" aria-pressed="false">Skip</button></span></div></div>')
    out.append(f'<p class="gc-err" id="gc-goerr" role="alert"></p>'
               f'<div class="gc-row" style="margin:16px 0 0.5rem">'
               f'<a href="https://docs.google.com/document/d/{e(doc)}/edit" style="font-size:14px">'
               f'Open the document <i class="ti ti-external-link" aria-hidden="true"></i></a>'
               f'<span><span class="gc-n" id="gc-tally"></span> '
               f'<button id="gc-go" style="font-weight:500">Post accepted comments ↗</button></span>'
               f'</div>' + ('<p class="gc-done" id="gc-done" role="status"></p>' if nonce else '') + '</div>')
    # json.dumps leaves "</script>" intact inside a string, which would end the
    # script block early; escaping the slash keeps any comment text inert.
    data = json.dumps({"title": title, "items": {c["n"]: c["text"] for c in cards}},
                      ensure_ascii=False).replace("</", "<\\/")
    attr = f' nonce="{e(nonce)}"' if nonce else ""
    out.append(f"<script{attr}>(()=>{{const D=" + data + ";" + send_js + _CARD_JS + "})();</script>")
    return "\n".join(out)


def _resolve_cards(doc, items):
    """(title, cards, total, has_suggestions) for a batch of draft comments.

    Every anchor is resolved before anything is drawn. One that is empty,
    multi-line, missing, or ambiguous without an "occurrence" stops the whole
    card (exit 3): a card must never ask a person to approve a guess.
    """
    if not isinstance(items, list) or not items:
        sys.exit('comment-card needs --file: a JSON list of {"anchor": ..., "text": ...}')
    d = get_doc(doc)
    paras = _paragraph_map(d)
    kinds = _suggestion_kinds(d)
    cards, problems = [], []
    for n, it in enumerate(items, 1):
        if not isinstance(it, dict):
            problems.append(f'{n}: not an object -- each item needs "anchor" and "text"')
            continue
        anchor, text, occ = it.get("anchor"), it.get("text"), it.get("occurrence")
        if not isinstance(anchor, str) or not isinstance(text, str):
            problems.append(f'{n}: "anchor" and "text" must both be text')
        elif not anchor.strip():
            problems.append(f"{n}: ANCHOR_EMPTY")
        elif "\n" in anchor:
            problems.append(f"{n}: ANCHOR_MULTILINE {anchor!r}")
        elif not text.strip():
            problems.append(f"{n}: no comment text")
        elif len(text.encode("utf-8")) > COMMENT_MAX:
            problems.append(f"{n}: comment is over Google's {COMMENT_MAX}-byte limit")
        else:
            hits = find_anchor(paras, anchor)
            if not hits:
                problems.append(f"{n}: TEXT_NOT_FOUND {anchor!r}")
            elif len(hits) > 1 and occ is None:
                problems.append(f"{n}: AMBIGUOUS {anchor!r} appears {len(hits)} times -- settle it "
                                f"with `comment --recommend`, then give the item an \"occurrence\"")
            elif occ is not None and (isinstance(occ, bool) or not isinstance(occ, int)
                                      or not 1 <= occ <= len(hits)):
                problems.append(f"{n}: occurrence {occ!r} is out of range ({len(hits)} matches)")
            else:
                occ = 1 if occ is None else occ
                p, k, _, _ = hits[occ - 1]
                before, mid, after = _card_window(paras, p, k, anchor, kinds)
                cards.append({"n": n, "before": before, "mid": mid, "after": after, "anchor": anchor,
                              "text": text, "occurrence": occ, "total": len(hits)})
    if problems:
        print("Card not built. Fix these first:")
        for pr in problems:
            print("  " + pr)
        sys.exit(EXIT_ANCHOR)
    return d.get("title", "this document"), cards, len(items), bool(kinds)


def do_comment_card(doc, items):
    """Print the approval card for the chat's visual widget. Its go button sends a
    message listing the comments to post, plus the new wording of any that were
    edited. That message is the approval; post each listed comment with `comment`,
    one call each. `comment-serve` is the same card without the chat message."""
    title, cards, total, has_suggestions = _resolve_cards(doc, items)
    print(_card_html(doc, title, cards, total, has_suggestions))


# ---------- comment-serve: the card posts by itself, no chat message ----------
#
# A card inside the chat can reach nothing but the chat: tested 2026-11-13, its
# requests to a helper on the same machine never arrived. Davo asked for a post
# button that works in the background, so `comment-serve` serves the same card as
# a page from a short-lived helper on this machine. The person opens it in the
# app's browser panel (or any browser), decides, and presses the button; the
# helper posts each accepted comment through `do_comment` -- every check it makes,
# including the read-back -- and shows the result on the page. Nothing goes
# through the chat. Claude hears about it when the helper exits.
#
# The helper is deliberately small and short-lived. It listens on 127.0.0.1 only,
# answers only requests carrying a random key from the page's address and the
# right Host, sends no CORS headers, posts only the drafts it started with (edited
# wording allowed), takes one decision, and stops after it or after the timeout.

SERVE_TIMEOUT = 900  # seconds the card stays open before the helper gives up


def _span(sec):
    return f"{sec // 60} minutes" if sec >= 120 else "1 minute" if sec >= 60 else f"{sec} seconds"

_SEND_PAGE = r"""const SEND=(k,e,m)=>{const ed={};k.forEach(n=>{if(e[n])ed[n]=e[n]});go.textContent='Posting…';
const done=document.getElementById('gc-done');
fetch('/post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:KEY,post:k,edits:ed})})
.then(r=>r.json().then(j=>({ok:r.ok,j})))
.then(({ok,j})=>{if(!ok){goErr.textContent=j.error||'The helper refused the request.';go.textContent='Not posted';return}
let good=0;(j.results||[]).forEach(x=>{const p=document.createElement('p');p.className='gc-res '+(x.ok?'ok':'bad');p.textContent=x.ok?'Posted ✓':'Not posted: '+x.note;if(x.ok)good++;const c=card(x.n);if(c)c.appendChild(p)});
go.textContent=k.length?'Posted '+good+' of '+k.length+(good===k.length?' ✓':''):'Nothing posted';
done.textContent=(k.length&&good<k.length?'Some comments didn’t post; Claude has the details. ':'Done. ')+'You can close this tab.'})
.catch(()=>{goErr.textContent='Couldn’t reach the helper on this computer. It stops after one post or after its time limit; ask Claude for a fresh card.';go.textContent='Not posted'})};"""

_PAGE_STYLE = """<style>
:root{color-scheme:light dark;--surface-0:#f6f5f2;--surface-1:#fff;--surface-2:#f0eee9;--border:#d9d6cf;--radius:8px;--text-primary:#1f1e1c;--text-secondary:#4a4844;--text-muted:#76736b;--text-success:#1e7a3c;--text-danger:#b3261e;--text-warning:#7a5000;--bg-warning:#fff4d6;--bg-highlight:#ffe680;--bg-accent:#e6effc;--text-accent:#1f4f99}
@media (prefers-color-scheme:dark){:root{--surface-0:#1b1a18;--surface-1:#26241f;--surface-2:#2e2c27;--border:#45423b;--text-primary:#ecebe7;--text-secondary:#c9c6bf;--text-muted:#9a968d;--text-success:#6fcf8e;--text-danger:#ff8a80;--text-warning:#f2c14e;--bg-warning:#3a2f12;--bg-highlight:#6b5a12;--bg-accent:#1e2b40;--text-accent:#9cc1ff}}
body{margin:0;background:var(--surface-0);color:var(--text-primary);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:20px;line-height:1.3;margin:0 0 4px}
.lede{color:var(--text-secondary);margin:0 0 16px;font-size:14px}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.ti{display:none}
.gc-row{flex-wrap:wrap}
button{font:inherit;font-size:14px;padding:6px 12px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface-1);color:var(--text-primary);cursor:pointer}
button:disabled{opacity:.55;cursor:default}
#gc-go{background:var(--text-primary);color:var(--surface-1);border-color:var(--text-primary)}
a{color:var(--text-accent)}
.gc-res{font-size:13px;margin:8px 0 0;font-weight:500}.gc-res.ok{color:var(--text-success)}.gc-res.bad{color:var(--text-danger)}
.gc-done{font-size:14px;color:var(--text-secondary);text-align:right;margin:4px 0 0}.gc-done:empty{display:none}
</style>"""


def _card_page(doc, title, cards, total, has_suggestions, key, nonce):
    """The card as a whole page, its go button posting to the helper that served it."""
    send = "const KEY=" + json.dumps(key) + ";" + _SEND_PAGE
    body = _card_html(doc, title, cards, total, has_suggestions, send_js=send, nonce=nonce)
    t = html.escape(title)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Comment approval</title>' + _PAGE_STYLE + '</head><body><main>'
            f'<h1>Draft comments for {t}</h1>'
            '<p class="lede">Accept, edit or skip each one. When you press the button, the accepted '
            'comments go straight into the document from this computer; nothing goes through the chat.</p>'
            + body + '</main></body></html>')


def _check_decision(post, edits, by_n):
    """(problem, edits): why a decision from the page can't be used, or the edits cleaned."""
    if not isinstance(post, list) or any(isinstance(x, bool) or not isinstance(x, int) for x in post):
        return "post must be a list of comment numbers", None
    if len(set(post)) != len(post) or any(x not in by_n for x in post):
        return "post names a comment that isn't on this card", None
    if not isinstance(edits, dict):
        return "edits must be an object", None
    clean = {}
    for k, v in edits.items():
        if not (isinstance(k, str) and k.isdigit() and int(k) in post):
            return f"an edit for comment {k!r}, which isn't being posted", None
        if not isinstance(v, str) or not v.strip():
            return f"comment {k}: an edited comment can't be empty", None
        if len(v.strip().encode("utf-8")) > COMMENT_MAX:
            return f"comment {k}: over Google's {COMMENT_MAX}-byte limit", None
        clean[int(k)] = v.strip()
    return None, clean


def _post_quietly(doc, anchor, text, occurrence):
    """Post one comment through do_comment -- every check it makes, none of its printing.
    (ok, note): the posted line, or the reason nothing was posted."""
    import contextlib, io
    buf, code = io.StringIO(), 0
    with contextlib.redirect_stdout(buf):
        try:
            do_comment(doc, anchor, text, occurrence=occurrence)
        except SystemExit as ex:
            code = ex.code
        except Exception as ex:  # one failed comment must not stop the rest
            code = f"{type(ex).__name__}: {ex}"
    lines = [ln.strip() for ln in buf.getvalue().splitlines() if ln.strip()]
    if code in (0, None) and lines and lines[-1].startswith("posted ✓"):
        return True, lines[-1]
    if isinstance(code, str):
        return False, code[:300]
    flagged = [ln for ln in lines if ln.split(":")[0].replace("_", " ").isupper()]
    return False, (flagged[0] if flagged else (lines[-1] if lines else f"exit {code}"))[:300]


def do_comment_serve(doc, items, timeout=SERVE_TIMEOUT, port=0):
    """Serve the approval card from this machine and post what the person accepts.

    Prints `CARD_URL: <address>` straight away, then waits. After the person's one
    decision (or the timeout) it prints the outcome and exits: 0 when everything
    accepted was posted or nothing was, 1 when a comment failed to post, 4 when the
    card expired with no decision."""
    import hmac, http.server, secrets, threading
    from urllib.parse import parse_qs, urlsplit

    title, cards, total, has_suggestions = _resolve_cards(doc, items)
    by_n = {c["n"]: c for c in cards}
    key, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(16)
    page = _card_page(doc, title, cards, total, has_suggestions, key, nonce).encode("utf-8")
    state = {"used": False, "expired": False, "outcome": None}
    gate = threading.Lock()
    csp = (f"default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-{nonce}'; "
           "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")

    class Card(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            b = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            for h, v in (("Content-Type", ctype), ("Content-Length", str(len(b))),
                         ("Cache-Control", "no-store"), ("Referrer-Policy", "no-referrer"),
                         ("X-Content-Type-Options", "nosniff"), ("Content-Security-Policy", csp)):
                self.send_header(h, v)
            self.end_headers()
            self.wfile.write(b)

        def _refuse(self, code, msg):
            self._send(code, json.dumps({"error": msg}))

        def _host_ok(self):
            # A web page can't make a browser send a foreign Host here (DNS rebinding).
            return self.headers.get("Host") in hosts

        def do_GET(self):
            u = urlsplit(self.path)
            if not self._host_ok():
                return self._refuse(403, "wrong host")
            if u.path != "/card":
                return self._refuse(404, "not found")
            if not hmac.compare_digest((parse_qs(u.query).get("key") or [""])[0], key):
                return self._refuse(403, "wrong or missing key")
            self._send(200, page, "text/html; charset=utf-8")

        def do_POST(self):
            if not self._host_ok():
                return self._refuse(403, "wrong host")
            if urlsplit(self.path).path != "/post":
                return self._refuse(404, "not found")
            if self.headers.get("Origin") not in (None, *origins):
                return self._refuse(403, "wrong origin")
            if (self.headers.get("Content-Type") or "").split(";")[0].strip() != "application/json":
                return self._refuse(415, "JSON only")
            try:
                size = int(self.headers.get("Content-Length") or 0)
                if size > 200_000:
                    return self._refuse(413, "too large")
                req = json.loads(self.rfile.read(size).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return self._refuse(400, "unreadable request")
            if not isinstance(req, dict) or not hmac.compare_digest(str(req.get("key", "")), key):
                return self._refuse(403, "wrong or missing key")
            post, edits = req.get("post"), req.get("edits") or {}
            problem, edits = _check_decision(post, edits, by_n)
            if problem:
                return self._refuse(400, problem)
            with gate:
                if state["used"]:
                    return self._refuse(409, "This card has already been used. Ask Claude for a fresh one.")
                state["used"] = True
            results = []
            for num in post:
                c = by_n[num]
                ok, note = _post_quietly(doc, c["anchor"], edits.get(num, c["text"]),
                                         c["occurrence"] if c["total"] > 1 else None)
                results.append({"n": num, "ok": ok, "note": note, "text": edits.get(num)})
            state["outcome"] = (post, results)
            self._send(200, json.dumps({"results": [{"n": r["n"], "ok": r["ok"], "note": r["note"]}
                                                    for r in results]}))
            threading.Thread(target=srv.shutdown, daemon=True).start()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Card)
    bound = srv.server_address[1]
    hosts = (f"127.0.0.1:{bound}", f"localhost:{bound}")
    origins = tuple("http://" + h for h in hosts)

    def expire():
        with gate:
            if state["used"]:
                return
            state["used"] = state["expired"] = True
        srv.shutdown()

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    print(f"CARD_URL: http://127.0.0.1:{bound}/card?key={key}")
    print(f"Open that in the browser panel. The card takes one decision and stops; "
          f"it gives up after {_span(timeout)}.", flush=True)
    try:
        srv.serve_forever()
    finally:
        timer.cancel()
        srv.server_close()

    if state["expired"]:
        print(f"EXPIRED: no decision on the card for {title!r} within {_span(timeout)}. Nothing was posted.")
        sys.exit(4)
    post, results = state["outcome"]
    skipped = total - len(post)
    if not post:
        print(f"NOTHING POSTED: every comment on {title!r} was skipped.")
        return
    good = sum(r["ok"] for r in results)
    print(f"RESULT: posted {good} of {len(post)} accepted on {title!r}"
          + (f", {skipped} skipped" if skipped else "") + ".")
    for r in results:
        print(f"  {r['n']}: {'✓' if r['ok'] else '✗'} {r['note']}")
        if r["text"]:
            print("     edited to: " + r["text"].replace("\n", "\n     "))
    if good < len(post):
        sys.exit(1)


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
    that was already in the doc must not make an accidental no-op look verified.
    An empty phrase is reported as missing, never as verified: str.count("") is
    the text length plus one, so it would otherwise always look "added"."""
    return [v for v in verify if not v or after.count(v) <= before.count(v)]


def do_append_rich(doc, md, verify=()):
    """Append a markdown-subset section to the end of `doc`; returns (blocks, missing_markers).

    Exits if the markdown parses to zero blocks (an empty or whitespace-only file
    must fail loudly, not report "blocks applied: 0")."""
    blocks = rich_parse_blocks(md)
    if not blocks:
        sys.exit("append-rich: the --md file parsed to zero blocks (empty or whitespace-only?)")
    if any(not v for v in verify):
        sys.exit("append-rich: an empty --verify phrase cannot be checked; give a phrase or drop the flag")
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
    ap.add_argument("action", choices=["read", "comments", "comment", "comment-card", "comment-serve", "create", "replace",
                                       "insert-top", "insert-after", "append", "append-rich",
                                       "remove", "batch"])
    ap.add_argument("--doc", help="Google Doc ID (required for all actions except create)")
    ap.add_argument("--find")
    ap.add_argument("--replace")
    ap.add_argument("--regex", action="store_true", help="treat --find as a regex (default: literal)")
    ap.add_argument("--suggestions", choices=["inline", "accepted", "rejected"], default="inline",
                    help="read: how to render pending suggestions. inline (default) shows the "
                         "redline as it stands; accepted previews them applied; rejected previews "
                         "them discarded. Ignored by the editing actions, which always use the "
                         "live document.")
    ap.add_argument("--title")
    ap.add_argument("--anchor", action="append", help="repeatable; line/section anchor substring")
    ap.add_argument("--text")
    ap.add_argument("--text-file", dest="text_file")
    ap.add_argument("--file", help="batch edits JSON, or comment-card draft comments JSON")
    ap.add_argument("--md", help="append-rich: markdown-subset file to append at the end")
    ap.add_argument("--verify", action="append", default=[],
                    help="append-rich: phrase that must be present after the append (repeatable)")
    ap.add_argument("--level", type=int, choices=[1, 2, 3, 4],
                    help="heading level for the inserted --title "
                         "(default: 2 for insert-top, 3 for insert-after)")
    ap.add_argument("--occurrence", type=int,
                    help="comment: which match of --anchor to attach to (1-based), when it repeats")
    ap.add_argument("--recommend", type=int,
                    help="comment: the match the model judges right; shown first and flagged, never posted")
    ap.add_argument("--why", help="comment: one line explaining --recommend")
    ap.add_argument("--timeout", type=int, default=SERVE_TIMEOUT,
                    help="comment-serve: seconds the card stays open before the helper gives up")
    ap.add_argument("--port", type=int, default=0,
                    help="comment-serve: port on 127.0.0.1 (default: any free one)")
    ap.add_argument("--preview", action="store_true",
                    help="comment: show where it would anchor, with surrounding text; post nothing")
    a = ap.parse_args()

    if a.anchor and any(not x.strip() for x in a.anchor):
        sys.exit("--anchor can't be empty or blank: it would match every line of the document")
    if a.action != "create" and not a.doc:
        sys.exit(a.action + " needs --doc")

    if a.action == "read":
        d = get_doc(a.doc, a.suggestions)
        if a.suggestions == "inline":
            w = pending_warning(d)
            if w:
                # First line of stdout, deliberately -- not stderr. The failure
                # this prevents is a reader (human or agent) treating a redline
                # as settled text, and a warning that a pipe or a log can drop
                # does not prevent it. A doc with no suggestions prints exactly
                # what it printed before, byte for byte. The editing actions
                # print their own version first for the same reason.
                print(w)
        else:
            print(f"\u2139\ufe0f  Showing this document with suggestions {a.suggestions.upper()} "
                  f"-- a preview, not what the document says right now.")
        sys.stdout.write(full_text(d))

    elif a.action == "comments":
        print(json.dumps(do_comments(a.doc), indent=2, ensure_ascii=False))

    elif a.action == "comment-card":
        if not a.file:
            sys.exit('comment-card needs --file: a JSON list of {"anchor": ..., "text": ...}')
        do_comment_card(a.doc, json.load(open(a.file, encoding="utf-8-sig")))  # -sig: tolerate a PS 5.1 BOM

    elif a.action == "comment-serve":
        if not a.file:
            sys.exit('comment-serve needs --file: a JSON list of {"anchor": ..., "text": ...}')
        do_comment_serve(a.doc, json.load(open(a.file, encoding="utf-8-sig")), timeout=a.timeout, port=a.port)

    elif a.action == "comment":
        if not a.anchor or len(a.anchor) != 1:
            sys.exit("comment needs exactly one --anchor: the exact text to attach it to")
        do_comment(a.doc, a.anchor[0], read_text(a), occurrence=a.occurrence,
                   recommend=a.recommend, why=a.why, preview=a.preview)

    elif a.action == "create":
        if not a.title:
            sys.exit("create needs --title")
        doc = do_create(a.title, read_text(a))
        print("ok  https://docs.google.com/document/d/%s/edit  (id: %s)" % (doc, doc))

    elif a.action == "replace":
        if a.find is None or a.replace is None:
            sys.exit("replace needs --find and --replace")
        d = warn_before_edit(a.doc)
        if a.regex:
            n = do_replace_regex(a.doc, a.find, a.replace, d=d)
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
        text = read_text(a)
        r = do_insert_after(a.doc, a.anchor[0], a.title or "", text,
                            level=a.level or 3, d=warn_before_edit(a.doc))
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
        print("ok, removed=%d" % do_remove(a.doc, a.anchor, d=warn_before_edit(a.doc)))

    elif a.action == "batch":
        if not a.file:
            sys.exit("batch needs --file")
        cfg = json.load(open(a.file, encoding="utf-8-sig"))  # -sig: tolerate a PS 5.1 BOM
        use_regex = cfg.get("regex", False)
        lines = full_text(warn_before_edit(a.doc)).split("\n")
        results = []
        for e in cfg.get("edits", []):
            if not isinstance(e, dict):
                results.append(("?", "not an object (skipped)"))
                continue
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
                if isinstance(e, dict) and e.get("marker") and e["marker"] not in new]
        gone = [a2 for a2 in cfg.get("remove", []) if a2 in new]
        print("== verify ==")
        print("  markers: " + ("all present ✓" if not miss else "MISSING: " + ", ".join(miss)))
        if cfg.get("remove"):
            print("  removed: " + ("all gone ✓" if not gone else "STILL PRESENT: " + ", ".join(gone)))


if __name__ == "__main__":
    main()
