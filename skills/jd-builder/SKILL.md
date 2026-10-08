---
name: jd-builder
description: >-
  Use when someone wants to create, draft, write, revise, or update an NSLS job
  description: "write a JD for [role]", "draft a job description", "we need a JD
  before we post this", "update the [role] job description", "turn this scorecard
  into a JD", "JD for a new role", "job posting for [role]", "rickety bones for
  these roles". Fills the official "Job Description Template 2025+" and produces
  a Google Doc; when a manager runs it, the Doc is auto-shared with HR. Revises an
  existing JD in place of rewriting it whenever one exists. Not for scorecards
  (use scorecard-builder) and never posts a job anywhere.
version: 0.1.0
---

# JD Builder

> **If `gws` fails (403 naming a project other than `nsls-gdocs-skill`, or exit 2):**
> run the doctor. It repairs the toolkit's own gws profile:
> `python3 <plugin>/skills/gws/scripts/gws_doctor.py --services docs,drive`
> (Windows: use the real Python at `%LOCALAPPDATA%\Programs\Python\Python312\python.exe`.)
> Then run this skill's `gws` commands against that profile, chained in the SAME shell call.
> Details: `../gws/references/multi-secret-profiles.md`.

Turn what a manager knows about a role into an **NSLS job description Google Doc** built from the
official template: same logo, same opener, same EEO line, every time. **The Doc is the deliverable.**

Three disciplines make this skill work, and all three are easy to skip:

1. **A JD is the public face of a scorecard.** The template says the purpose must be "in-sync with your
   Scorecard role Mission", and responsibilities should map to the scorecard's accountabilities. Get the
   scorecard first when one exists.
2. **If a JD already exists, revise it. Don't rewrite it.** Same reasoning as scorecards: approved
   language is the starting point.
3. **Every JD a manager builds is shared with HR (Jenna Fontanez) the moment it's rendered.** A JD that
   lives only in a manager's Drive never reaches recruiting, the comp benchmark, or the next posting.

## SAFETY: three-tier permissions

1. **Read-only (free):** the template (bundled at `references/jd-template-2025.docx`; Drive source of record
   `1X6P_dt6HKUFOSipAZSV4NQYE5XxMA5kH`); an existing JD or scorecard Doc (read, never edit in place); a role
   brief such as a "JD Bones" sheet; the Competency Bank (people-ops Airtable `appnXPTu01esWWbrK`, read-only,
   only if the runner has access).
2. **New-content write (OK; say what and where first):** render a `.docx` locally, upload it as a **new**
   Google Doc owned by the runner, and **share it with `jfontanez@nsls.org` as commenter** when the runner
   isn't Jenna.
3. **NEVER:**
   - **Never post, publish, or send a JD** to a job board, Rippling, Slack, or a candidate. Posting is HR's step.
   - **No pay figures, ranges, bonus, or commission numbers** in the Doc. Comp structure isn't JD content.
   - **No names of incumbents or candidates** in the Doc or its title. JDs are role-based; naming someone
     pre-announces a placement.
   - **No edits to the prior JD** in revise mode. Render a new version.
   - **No writes to Airtable or any HR system.**

## Quick Start

1. **Ask: does a JD or scorecard already exist for this role?** If yes, get it (paste or Drive URL) and read it
   before drafting. Existing JD → **Revise mode** (below). Scorecard only → its Mission and Side A are your
   main inputs.
2. **Gather inputs.** Use what exists: a scorecard, a role brief, notes from the meeting where the role was
   designed. If nothing exists, run the **manager interview** (below). Don't invent duties.
3. **Draft the spec** (the JSON fields in `references/build_jd.py`), applying the writing rules below.
   Bracket anything uncertain: `[years of experience]`, `[travel %]`.
4. **Show the draft to the runner** as a short outline (purpose, then responsibilities) before rendering
   anything in batch. For one-off JDs, rendering the DRAFT and reviewing in the Doc is fine.
5. **Render:** `~/.local/bin/nsls-python references/build_jd.py spec.json --out-dir <working dir>`
   (Windows: `nsls-python …`, prefixed with `PYTHONUTF8=1`). If the import fails, re-run the toolkit installer;
   never pip-install into `~/.local/lib/nsls-pydeps` with another Python. It fails loudly if template guidance text survives, a list is over its cap, or a FINAL
   still has brackets.
6. **Upload as a new Google Doc** (see *Upload and share*), into the folder the runner names.
7. **Share with HR** if the runner isn't Jenna. Verify the share actually landed.
8. **Hand back** the URL and say what's still theirs (see *Output*).

## Writing rules (from the template's own guidance, plus HR law)

| Section | Rule |
|---|---|
| **Title** | Market-standard title a candidate would search for. No internal nicknames. |
| **Purpose** ("will be responsible for…") | 1–2 sentences. Must match the scorecard **Mission**. Lowercase start; it finishes a sentence. |
| **Team** ("This role forms part of the…") | About 4 sentences: the team, what it does for NSLS, and where this role sits in it. Starts lowercase, e.g. "Client Services team, which…" |
| **Responsibilities** | **≤ 10**, high level, mapped to scorecard accountabilities, without metric numbers. **One verb form throughout:** "Lead, manage, run", never "Lead, managing, responsible for". |
| **Qualifications** | **≤ 10**, objective hard requirements only: education, years, certifications, tools. Only list a degree if the job truly needs it; otherwise write "or equivalent experience". |
| **Nice To Haves** | Real differentiators that aren't required. |
| **Who You Are** | 4–6 traits drawn from the role's scorecard competencies (Competency Bank vocabulary), in candidate-friendly language. |
| **How We Work** | Standard copy from `references/how-we-work.md`. Don't tailor it per role; change the file instead. |

**Language checks (do these before rendering):**
- No age-coded or gendered words: "digital native", "young", "recent grad energy", "rockstar", "ninja", "he/she".
- **Physical and travel requirements must be real and stated:** travel %, lifting, hours. Essential-function
  clarity protects ADA accommodation decisions. Bracket the % if unknown.
- **Pay transparency:** CA, CO, NY, WA (and others) require a pay range on public postings. The skill never
  writes it. Say in the hand-back that HR adds the range at posting time.
- **"What this role is NOT"** belongs in the scorecard, not the JD. But when two new roles share a boundary
  (e.g., Sales Exec vs. Account Manager), make sure the responsibilities don't overlap.

## The manager interview (no scorecard, no brief)

1. Why does this role exist? (→ purpose)
2. What team is it on, and what does that team do for NSLS? (→ team paragraph)
3. What are the 5–8 things this person is accountable for? Get outcomes, not tasks. (→ responsibilities)
4. What must they already know or have on day one? (→ qualifications; push back on degree requirements)
5. What would make a candidate stand out? (→ nice to haves)
6. Which 4–6 behaviors separate great from fine in this seat? (→ who you are)
7. Location, travel, schedule realities? (→ title line + qualifications)

## Revise mode

Read the existing JD and reflect it back. Ask what changed: the role, the team, the reporting line, the
requirements. **Patch only those sections, and carry everything else over verbatim.** Render a NEW Doc and
keep the prior URL. Write a one-line change summary ("Responsibilities: added procurement handoff; Quals:
dropped degree requirement") and put it in the HR share note.

## Upload and share

Use the toolkit gws profile, chained in ONE shell call. On Windows, use the Bash tool.

```bash
set -o pipefail
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/gws-profiles/nsls-gdocs-skill"
cd "<dir containing the docx>"   # gws --upload rejects paths outside cwd
gws drive files create \
  --json '{"name":"JD — <Title> (DRAFT)","mimeType":"application/vnd.google-apps.document","parents":["<FOLDER_ID>"]}' \
  --upload "JD - <Title> (DRAFT).docx" \
  --upload-content-type "application/vnd.openxmlformats-officedocument.wordprocessingml.document" \
  --params '{"fields":"id,name,webViewLink"}' | grep -v -i keyring
```

**Who's running it?** `gws auth status` → `user`.
- **Runner is `jfontanez@nsls.org`:** no share. She's the owner. **Do not share with anyone else unless she says so.**
- **Anyone else:** share with HR as commenter, then verify with `gws drive permissions list`:

```bash
set -o pipefail
gws drive permissions create \
  --params '{"fileId":"<DOC_ID>","sendNotificationEmail":true,"emailMessage":"<SHARE NOTE>"}' \
  --json '{"role":"commenter","type":"user","emailAddress":"jfontanez@nsls.org"}' | grep -v -i keyring
```

The share note says: role title, who built it, DRAFT or FINAL, and in revise mode the change summary + prior URL.
**If the share fails, stop and lead with it.** Give the manual fallback: open the URL → Share →
`jfontanez@nsls.org` → Commenter.

**FINAL:** when brackets are resolved, set `"status": "FINAL"` and re-render (the renderer refuses if brackets
remain). Upload as a new Doc, or retitle `(DRAFT)` → `(FINAL)` with `gws drive files update`. Confirm the new
name by re-reading it before telling HR.

## Diagnostics

| Symptom | Cause | Fix |
|---|---|---|
| `build_jd: template changed: …` | The Drive template was edited and the bundled copy no longer matches the renderer | Re-download `1X6P_dt6HKUFOSipAZSV4NQYE5XxMA5kH` (`alt: media`) over `references/jd-template-2025.docx`, then update the placeholder anchors in `build_jd.py` |
| Curly quotes print as `�` | Windows cp1252 console | Prefix with `PYTHONUTF8=1`. The Doc itself is fine |
| gws exit 2 / 401 | Default gws dir has no credentials | Use the toolkit profile export above. If still failing: `gws_doctor.py --services docs,drive` |
| Upload "outside the current directory" | gws only uploads from cwd | `cd` into the folder first |
| Command exits 0 but nothing changed | the pipe hides gws's exit status | `set -o pipefail`, then re-read the resource |
| Logo missing after upload | Google import dropped the image | Rare. Re-upload; if it persists, tell HR (template issue, not content) |

## Output

- **Return the Doc URL(s)** plus one line per JD (title + DRAFT/FINAL). Don't paste the JD into chat.
- State the HR share as **done** (or "not needed, you own it" when Jenna runs it).
- Name what's still open: the `[brackets]`, scorecard alignment if no scorecard exists yet, and **"HR adds
  the pay range before posting."**

## Rationalizations you will have

| Excuse | Reality |
|---|---|
| "No scorecard exists, so I'll make up the responsibilities." | Run the manager interview, or bracket the purpose and flag that a scorecard is needed. |
| "Twelve responsibilities is more complete." | The template caps it at 10, and the renderer refuses more. |
| "I'll add the salary range so it's posting-ready." | No pay in the Doc. HR adds it at posting. |
| "Naming the likely incumbent makes it clearer." | JDs are role-based. A name pre-announces a placement. |
| "I'll tweak the opener so it fits this role better." | The opener, guiding question and EEO line are fixed template text. |
| "A Bachelor's is standard, I'll require it." | Only if the job truly needs it. Otherwise write "or equivalent experience". |
| "It's just a draft, no need to share with HR." | Draft-and-shared beats finished-and-orphaned. Share it. |
| "Jenna ran it, I'll share with Heather too so she can see it." | Never share a Doc Jenna owns without her say-so. |

## Red Flags — STOP

- About to put a dollar figure, range, or commission rate in the Doc → **STOP.**
- About to put a person's name in the Doc or its title → **STOP.**
- About to post or send the JD anywhere → **STOP.** Doc only.
- About to overwrite an existing JD → **STOP.** New version.
- About to hand back a manager-built JD URL without confirming the HR share → **STOP.**
- About to render FINAL with brackets still open → **STOP.** (The renderer also refuses.)

## Related

- `scorecard-builder` (NSLS toolkit): the scorecard this JD must stay in sync with.
- `references/build_jd.py`: the fill-the-template renderer.
- `references/how-we-work.md`: standard How We Work copy (approved by Jenna 2026-10-08).
