# Installation guide — ready-to-apply change set (NOT applied)

Target: `INSTALLATION-GUIDE-DRAFT.md` (Draft v2 · 2026-07-27, in *BK and Training
Buff*) — the source the rendered artifact is generated from. **Per Davo's
instruction these are drafted only; nothing below has been applied.** After
applying: bump the draft to v3, regenerate the rendered artifact
(`build/installation-guide.html` → deploy), and note the old pre-master-prompt
Google Doc (`1o3V2n2oyrdDI4SSp0YDdEOx7mqRzvhhh_zc7nfT8NdM`) is superseded.
Line anchors reference Draft v2.

---

## G-1 (I-4) — Honest time estimate — line 3

**Replace** the intro italic line with:

> *A clean run takes about 15–20 minutes, most of it waiting on installs — but
> budget up to an hour the first time in case your machine needs one of the
> fixes in Troubleshooting (Windows especially). You do a few simple things by
> hand, then paste **one prompt**, and Claude walks you through the rest. Fine
> to split across two sittings — nothing is lost between sessions.*

Why: this run blew through 20 minutes once real friction hit; a builder who
budgets 20 and spends 60 concludes the toolkit is broken. The wider range also
reconciles the guide's own contradictions (troubleshooting №10 advises two
sessions; Advanced personal-setup alone is 15–20).

## G-2 (I-3) — One numbering scheme — lines 52–58

The guide's hand-steps are 1–3, then "Claude will walk you through these" is a
*second* list numbered 1–4, and the master prompt announces "Step 3 of 7" —
three schemes for one flow, colliding exactly when the builder finishes guide
Step 3. **Replace the section header + list** with (numbering continues to 7,
titles match the prompt's announcements):

> ## Claude takes it from here — Steps 3 to 7
>
> The prompt you pasted announces each of these as it goes ("Step 3 of 7" …
> "Step 7 of 7") — the numbers pick up right where you left off:
>
> 3. **Run the installer** — Claude installs 50+ NSLS skills and most of what
>    they run on.
> 4. **Restart Claude Code** — loads the toolkit's live machinery.
> 5. **`/setup` — identity, tools, and Google Docs access** — your work starts
>    counting here; connect Slack, Google Drive, Calendar, Gmail, Asana, and
>    Fathom one at a time.
> 6. **Your first build** — a real, branded NSLS Google Doc, then a second
>    skill edits it on the fly. This is the moment it clicks.
> 7. **Plan your day** — open your day in the morning, close it at night, and
>    track it in your own private command center.

(Also renames guide Step 3's title to "Step 3 — Paste your master prompt" →
keep, but add one line under "From here, Claude takes over": *"Claude will call
this 'Step 3 of 7' — same numbering, it's continuing your count."*)

Why: PC round 2 — the builder lost their place at the seam. M-8 note: Asana is
now in the connector list (line 55) to match the v4 prompts and `/setup`.

## G-3 (I-1) — Elevated-shell disclosure — new troubleshooting entry + one line up front

**Add to "Before you set off"** (or directly under the Step 3 intro): *"Two
Windows pieces need an **administrator** PowerShell and can't be done for you:
the VC++ runtime and Node.js. Claude will tell you if and when — the fix is in
Troubleshooting №12."*

**Add troubleshooting entry №12** (and cross-link from №9):

> #### 12 · Claude says Node.js needs an admin install *(Windows)*
>
> Some installs need permissions Claude doesn't have. Open an administrator
> PowerShell: click **Start**, type `powershell`, **right-click Windows
> PowerShell → Run as administrator**, click **Yes**. Then paste:
> `winget install --id OpenJS.NodeJS.LTS -e --source winget`
> When it finishes, quit and reopen Claude (tray icon → Exit), and tell Claude
> "Node's installed." Skipping this locks the day-planner dashboard
> (`/signal-setup` runs on Node).

Why: this is precisely where an unattended install stalls today, reported only
as a `[warn]` (installer side now fixed in PR A/T-3 — guide and prompt should
describe the same reality).

## G-4 (I-2) — Tell the truth about both hooks — troubleshooting №6, line 102

**Replace** the entry body with:

> That's normal — Claude asks before doing things on your machine. Read it and
> **approve it.** Two small toolkit scripts phone home, both so your work gets
> credited: a once-per-launch **session sync** (your builder email + GitHub
> username + platform — it records your daily session point and also updates
> the toolkit from GitHub each launch, so you always have the latest skills),
> and a per-skill **skill-event** ping (your email + the skill name). That's
> the full list — nothing about what you were doing.

Why: the current claim ("all it sends is your builder email and the name of
the skill") is true of one hook of two; a builder who reviews the script finds
undisclosed behavior and loses trust in the whole doc. Wording matches master
prompt v4 and `/setup`'s new disclosure — keep all three in sync.

## G-5 (I-5) — A real fix for "Python was not found" — troubleshooting №7, line 106

**Replace** with:

> A common Windows gotcha: the `python` command on stock Windows is a fake
> Microsoft Store shortcut, so things that need real Python can't find it even
> after the installer set it up. Say to Claude: *"Python was not found — use
> the full path."* (For the record, the real one lives at
> `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`; the toolkit's skills
> know to use it.) If Claude says Python truly isn't installed, approve its
> offer to install it — no admin needed for this one.

Why: every other entry gives a concrete remedy; this one delegated. Verified
against install.ps1 (it installs Python 3.12 per-user to that path and the
skills document the full-path rule).

## G-6 (I-6) — Dashboard's Node dependency — troubleshooting №8, line 110

**Replace** with:

> The dashboard belongs in your real web browser, not Claude's built-in
> preview panel. If Claude opens it in the side panel, say **"open it in my
> browser."** If it won't load at all, two likely causes: **Node.js isn't
> installed** (see №12 — the dashboard runs on it), or the signal server needs
> a restart — tell Claude *"the signal server failed"* and it'll sort out
> which.

Why: the current entry treats a missing dependency as a transient server
blip; the guide sells the dashboard as Step 7's payoff, so its one hard
dependency deserves a name.

## G-7 (I-7) — How to create the Projects folder — Step 3, line 41

**Replace** item 1 with:

> 1. **Open a new Code session.** Click **New session** (top-left), then
>    **Select Folder** near the bottom. In the picker, go to Documents, click
>    **New Folder**, name it `Projects`, click **Create**, then **Select
>    Folder** / **Open**. Set permissions to **Manual** so you see and approve
>    each step while you're learning.

⚠️ Verify the picker's button labels against the current desktop build before
applying (macOS and Windows pickers differ slightly).

## G-8 (A1, Mac round 2) — New troubleshooting entry: the sign-in page that never opened

**Add** (place right before №11, which covers the *wrong-account* failure):

> #### 11a · Claude said a sign-in page opened, but nothing happened
>
> The browser launch fails silently on some machines. Say *"start the Google
> sign-in again and paste the link here"* — then click the link yourself. Ask
> for a **fresh** link rather than reusing an old one: these links expire
> within a couple of minutes, and an expired one shows a scary-looking "can't
> reach localhost" error that just means the link went stale.

## G-9 (B4 support) — Add the "Ten skills worth trying next" section

The v4 master prompts end by pointing here ("the guide's *ten skills worth
trying next* has your next moves") — the section doesn't exist yet. **Add
after the Steps 3–7 preview** (starter list for Davo to curate):

> ## Ten skills worth trying next
> `/brainstorm` — think through anything messy · `/nsls-slides` — branded
> decks · `/receipts` — clear your Ramp queue · `/web-research` — cited
> research · `/slack` — search team knowledge · `/data-intel` — questions
> across every system · `/close-week` — Friday roll-up · `/person-intelligence`
> — prep for any 1:1 · `/register-automation` — put your builds on the org
> tracker · `/deployment-guide` — ship something real.

## G-10 (I-8) — Version housekeeping — line 5

Bump to *Draft v3* with a one-line changelog, and add: *"Master prompts:
v4 · 2026-08-03"* so guide↔prompt drift is visible at a glance. Regenerate the
rendered artifact after edits (it's a downstream copy), and mark the old
Google-Doc guide superseded wherever it's still linked.

---

**Already covered by Draft v2 (no action):** Git-at-Step-2 with say-YES framing
(PC-R1 1.2) · connector FAQ incl. per-account binding (1.5/T3) ·
restart-after-connectors (№4) · /setup-before-skills (flow order) · token
budget (№10) · @nsls.org-only sign-in (№11) · tray-exit restart (№1/2) ·
master-prompt links for both platforms (1.9).
