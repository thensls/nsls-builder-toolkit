#!/usr/bin/env python3
"""Screenshot a mock-up after scripted clicks, using headless Chrome.

Clicks are written as plain JS steps with a delay, so you can walk a flow end to end:

  python3 shoot.py page.html out.png \
      --step 3200 "q('#bookBtn').click()" \
      --step 5600 "document.querySelectorAll('.slot')[2].click()" \
      --wait 16000

Helpers available inside steps: q(sel) = document.querySelector(sel), qa(sel) = querySelectorAll.
Any JS error is painted in red at the top of the screenshot, so a broken step is visible.
--measure paints "viewport / scrollWidth" at the top; equal numbers mean no sideways scroll.

Headless Chrome never lays out narrower than 500px, so a 420px shot is cropped,
not overflowing. Use --measure at --size 500x1200 to check phone width honestly.
"""
import argparse, os, subprocess, sys, tempfile

import shutil
CHROME = os.environ.get("CHROME_PATH") or next((c for c in [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    shutil.which("google-chrome") or "", shutil.which("chromium") or "",
] if c and os.path.exists(c)), "google-chrome")  # set CHROME_PATH to override

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--step", nargs=2, action="append", metavar=("MS", "JS"), default=[])
    ap.add_argument("--wait", type=int, default=4000, help="virtual time budget in ms; set past your last step")
    ap.add_argument("--size", default="1440x1000")
    ap.add_argument("--measure", action="store_true")
    a = ap.parse_args()

    src = open(a.html, encoding="utf-8").read()
    js = ["window.onerror=function(m){document.body.insertAdjacentHTML('afterbegin',"
          "'<h1 style=\"color:#c00;background:#fff;position:relative;z-index:99\">ERR '+m+'</h1>')};",
          "function q(s){return document.querySelector(s)} function qa(s){return document.querySelectorAll(s)}"]
    for ms, step in a.step:
        js.append("setTimeout(function(){try{%s}catch(e){window.onerror(e.message)}},%d);" % (step, int(ms)))
    if a.measure:
        js.append("setTimeout(function(){document.body.insertAdjacentHTML('afterbegin','<h1 style=\"background:#ff0\">'"
                  "+innerWidth+' / '+document.documentElement.scrollWidth+'</h1>')},300);")
    fd, tmp = tempfile.mkstemp(suffix=".html", dir=os.path.dirname(os.path.abspath(a.html)))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(src + "<script>" + "".join(js) + "</script>")
    w, h = a.size.split("x")
    try:
        subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
                        "--virtual-time-budget=%d" % a.wait, "--window-size=%s,%s" % (w, h),
                        "--screenshot=%s" % os.path.abspath(a.out), "file://" + tmp],
                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=120, check=False)
    finally:
        os.remove(tmp)
    if not os.path.exists(a.out):
        sys.exit("no screenshot written")
    print(a.out)

if __name__ == "__main__":
    main()
