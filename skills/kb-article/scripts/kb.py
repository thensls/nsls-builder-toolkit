#!/usr/bin/env python3
"""NSLS internal Knowledge Base client for staff. Talks to the kb-submit service, which holds the
HubSpot key and asks for approval in Slack. Standard library only.

  kb.py login --email YOU@nsls.org            one-time sign-in: approve it in Slack (KB Publisher DM)
  kb.py login                                 finish a sign-in after clicking Allow
  kb.py search WORDS...                       find existing articles and their Owner
  kb.py categories                            sections and subsections with ids
  kb.py get ID|SLUG [--out DIR]               save body.html + meta.json to edit
  kb.py check BODY.html --type sop|resource   house-style check (same rules the service enforces)
  kb.py submit --type sop|resource --body BODY.html
               [--article ID|SLUG]            edit an existing article, or for a new one:
               [--title T --meta M --category ID|NAME --slug SLUG [--subtitle S]]
               [--note "why this change"]
  kb.py status SUBMISSION                     where a submission stands

Nothing goes live from here. After submit, Slack takes over: the author gets a DM with Publish (their
own article, KB admins, small fixes), or the Owner / a KB admin gets an Approve button.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

URL = os.environ.get("KB_SUBMIT_URL", "https://kb-submit-production.up.railway.app").rstrip("/")
if not URL.startswith("https://"):  # the bearer token must never travel over plain http
    sys.exit(f"KB_SUBMIT_URL must start with https:// (got {URL}).")
DIR = os.path.expanduser(os.environ.get("KB_CONFIG_DIR", "~/.config/nsls"))
TOKEN_FILE, PENDING_FILE = os.path.join(DIR, "kb-token"), os.path.join(DIR, "kb-login-pending.json")


def _headers():
    h = {"Content-Type": "application/json"}
    if os.environ.get("KB_SUBMIT_KEY"):  # KB admin scripts only
        h["X-KB-Key"] = os.environ["KB_SUBMIT_KEY"]
    elif os.path.exists(TOKEN_FILE):
        h["Authorization"] = "Bearer " + open(TOKEN_FILE).read().strip()
    return h


def _signed_in():
    """True when requests go out with a personal token. The service then takes the author from the token."""
    return not os.environ.get("KB_SUBMIT_KEY") and os.path.exists(TOKEN_FILE)


def _folder_name(art):
    """Local folder name for `get`. The server's path is untrusted: keep only its last segment, allow only
    safe characters, and fall back to the article id. Never absolute, never '..'."""
    for raw in (art.get("path"), art.get("id")):
        name = re.sub(r"[^A-Za-z0-9._-]", "-", os.path.basename(str(raw or "").strip().rstrip("/"))).strip(".-")
        if name and ".." not in name:
            return name
    sys.exit("KB service returned an article with no usable path or id.")


def _save(path, text):
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(text)


def call(method, path, body=None):
    req = urllib.request.Request(URL + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers=_headers())
    try:
        raw = urllib.request.urlopen(req, timeout=120).read()
        try:
            return json.loads(raw)
        except ValueError:
            sys.exit(f"The KB service at {URL} sent back something that isn't JSON. Try again in a minute.")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            sys.exit(f"KB service error {e.code}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach the KB service at {URL} ({e.reason}). If you are on claude.ai, the sandbox may "
                 "block it: use Claude Code, or send the draft to a KB admin.")


def done(d):
    if not d.get("ok"):
        print("NOT DONE: " + d.get("error", "unknown error"))
        for p in d.get("problems", []):
            print("- " + p)
        sys.exit(1)
    return d


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("login"); x.add_argument("--email")
    x = s.add_parser("search"); x.add_argument("words", nargs="+")
    s.add_parser("categories")
    x = s.add_parser("get"); x.add_argument("ref"); x.add_argument("--out")
    x.add_argument("--force", action="store_true", help="replace body.html/meta.json already in the folder")
    x = s.add_parser("check"); x.add_argument("body"); x.add_argument("--type", choices=["sop", "resource"], required=True)
    x = s.add_parser("submit")
    x.add_argument("--author", help="KB admin scripts only (KB_SUBMIT_KEY); signed-in people are always the author")
    x.add_argument("--type", choices=["sop", "resource"], required=True)
    x.add_argument("--body", required=True)
    for k in ("--article", "--title", "--meta", "--category", "--slug", "--subtitle", "--note"):
        x.add_argument(k)
    x = s.add_parser("status"); x.add_argument("sid")
    a = p.parse_args()

    if a.cmd == "login":
        if a.email:
            d = done(call("POST", "/auth/start", {"email": a.email}))
            _save(PENDING_FILE, json.dumps({"login": d["login"], "secret": d["secret"], "code": d["code"]}))
            # Return right away so Claude can show the code; waiting here hides it until the wait ends.
            print(f"Sign-in code: {d['code']}\nCheck Slack: a DM from KB Publisher shows the same code. "
                  "Click Allow there only if it matches, then run: kb.py login")
            return
        if not os.path.exists(PENDING_FILE):
            if os.path.exists(TOKEN_FILE) and call("GET", "/api/categories").get("ok"):
                print("Already signed in on this computer. Nothing to do.")
                return
            sys.exit("Not signed in yet. Run: kb.py login --email you@nsls.org")
        pend = json.load(open(PENDING_FILE))
        for _ in range(20):  # about 60 seconds; run `kb.py login` again to keep waiting
            d = call("POST", "/auth/poll", {"login": pend["login"], "secret": pend["secret"]})
            if d.get("token"):
                _save(TOKEN_FILE, d["token"]); os.remove(PENDING_FILE)
                print(f"Signed in as {d['email']}. You won't need to do this again on this computer.")
                return
            if d.get("status") != "pending":
                os.remove(PENDING_FILE)
                sys.exit(f"Sign-in {d.get('status') or 'failed'}. Start again with: kb.py login --email you@nsls.org")
            time.sleep(3)
        print(f"Still waiting for Allow in Slack (code {pend['code']}). After clicking it, run: kb.py login")
        return
    if a.cmd == "search":
        for r in done(call("GET", "/api/search?q=" + urllib.parse.quote(" ".join(a.words))))["results"] or []:
            print(f"{r['id']}\t{r['state']}\t{r['url']}\t{r['title']}\tOwner: {r['owner'] or '(none)'}"
                  + ("\t[HANDBOOK: do not edit]" if r["handbook"] else ""))
    elif a.cmd == "categories":
        for c in done(call("GET", "/api/categories"))["categories"]:
            print(f"{c['id']}\t{c['name']}" + (f"\t(subsection of {c['parent']})" if c["parent"] else ""))
    elif a.cmd == "get":
        d = done(call("GET", "/api/article/" + urllib.parse.quote(a.ref)))
        art = d["article"]
        out = a.out or os.path.join(os.getcwd(), _folder_name(art))
        body_path, meta_path = os.path.join(out, "body.html"), os.path.join(out, "meta.json")
        if not a.force and (os.path.exists(body_path) or os.path.exists(meta_path)):
            sys.exit(f"{out}/ already has body.html or meta.json, maybe unsaved edits. Use --out NEWDIR, or --force to replace.")
        os.makedirs(out, exist_ok=True)
        open(body_path, "w").write(art.pop("body") or "")
        json.dump({**art, "owner": d["owner"], "handbook": d["handbook"]}, open(meta_path, "w"), indent=1)
        print(f"Saved to {out}/ (body.html, meta.json). Owner: {d['owner'] or '(none)'}.")
        if d["handbook"]:
            print("This is an Employee Handbook article. It cannot be edited; send changes to hr@nsls.org.")
        if d["pending_submission"]:
            print(f"Note: a change to this article is already waiting for approval ({d['pending_submission']}).")
    elif a.cmd == "check":
        d = call("POST", "/api/lint", {"body": open(a.body).read(), "type": a.type})
        if d.get("ok"):
            print("OK: passes house-style checks.")
        else:
            print("NOT OK" + (f": {d['error']}" if d.get("error") else ""))
            print("\n".join("- " + x for x in d.get("problems", [])))
        sys.exit(0 if d.get("ok") else 1)
    elif a.cmd == "submit":
        # Signed in: the service takes the author from the token, so never send a typed email.
        body = {"author_email": None if _signed_in() else a.author, "type": a.type, "body": open(a.body).read(), "article": a.article,
                "title": a.title, "meta": a.meta, "category": a.category, "slug": a.slug, "subtitle": a.subtitle,
                "note": a.note}
        d = done(call("POST", "/api/submit", {k: v for k, v in body.items() if v}))
        print(f"{d['message']}\nSubmission {d['submission']} (article {d['article_id']}).")
    elif a.cmd == "status":
        d = done(call("GET", "/api/status/" + a.sid))
        print(f"{d['status']}: {d['title']}" + (f"\n{d['result']}" if d.get("result") else ""))


if __name__ == "__main__":
    main()
