---
name: scorecard-builder
description: >-
  Use when a manager wants to create, draft, build, or significantly edit an
  employee performance ScoreCard — "create a scorecard", "build a scorecard for
  [name]", "draft [name]'s scorecard", "update/revise [name]'s scorecard",
  "reweight the accountabilities", "scorecard for my report", "make a scorecard
  doc", "help me set [name]'s accountabilities" — including for a brand-new hire
  with no history yet. Produces a founder-template Google Doc, never an Airtable row.
version: 2.1.0
---

# ScoreCard Builder

Turn a manager's real knowledge of a report into a clean **founder-template ScoreCard Google Doc** — weighted outcome accountabilities (Side A), core competencies (Side B), and a binary Core Values gate — that aligns manager and employee on what the role is *for* and how "meets" is judged. **The Doc is the deliverable.** The manager hands it to HR, who loads it into the system of record.

## SAFETY: THREE-TIER PERMISSION MODEL

This skill is deliberately **standalone and read-only against every shared system.** NSLS runs a live scorecard → scoring → bonus system (an HR-owned bot + a shared people-ops Airtable). This skill must never touch that machinery — it is not part of HR's process and is not the thing that loads scorecards into the system of record.

1. **Read-only (free to do):** read the founder SOP + research `references/`; *optionally* read the data sources below (LOP/KPIs, Signal Quick Notes, the Knowledge Base) as drafting inputs — **only if the manager running this has access.** All optional; degrade gracefully when absent.
2. **New-content write (OK — explain what and where first):** build a `.docx` locally and upload it as a **new, private Google Doc** owned by the manager running the skill.
3. **NEVER — hard boundary, not negotiable:**
   - **No writes to any people-ops Airtable / ScoreCards / scoring system.** Loading the card is HR's job. This skill hands over a Doc.
   - **No Slack/DM to the employee.** The manager shares the Doc themselves.
   - **No comp math, bonus numbers, or payout bands** anywhere in the output.
   - **No pay figures at all** — keep compensation out of the Doc entirely.

## Purpose

A good scorecard is hard because the manager knows the person but not the *frame* — they write tasks instead of outcomes, list ten things instead of the vital few, reward the number instead of the judgment, and quietly forget the work that just keeps the lights on. This skill carries the frame so any NSLS manager doesn't have to: the founder's Topgrading structure, the research on why outcome-goals beat task-lists, the 2×2 portfolio lens (growth / efficiency / hygiene / reliability), and the reality-check discipline that grounds accountabilities in what the person *actually does* without letting activity masquerade as an accountability. It produces a Doc a manager and report can sit down over, every draft value bracketed for the two of them to confirm.

## Two modes

| Mode | Trigger | Input |
|---|---|---|
| **Create** | New scorecard — existing role *or* brand-new hire | Role + whatever data exists (or a manager interview if none) |
| **Significant edit** | Reweight, add/remove accountabilities, swap competencies, change mission/growth focus | The current scorecard Doc (paste text, or give the Drive URL to read read-only) |

Both modes end the same way: a rendered Google Doc + a handoff reminder. Edit mode also emits a **change summary** so HR sees exactly what moved.

## Quick Start

1. **Mode + who + role + manager.** Creating or editing? Whose card? What is the role's one-sentence reason to exist? Who manages them?
2. **Gather inputs** — pull whatever of the data sources below exists (all optional). If it's a **brand-new hire with no history, run the manager interview** (below) instead.
3. **Draft the card** section by section (Mission → Side A → Core Values → Side B → Growth Focus → open questions), applying the guardrails. Leave every uncertain value as a `[bracket]` for the alignment conversation.
4. **Render the Doc.** Copy `references/build_doc_template.py` → `~/build_<name>_scorecard.py`, fill the BODY, run with python-docx; it derives the filename and prints the exact `gws` upload command. (Mechanics: `/gdoc-build`.)
5. **Hand off.** Give the manager the URL. Remind them: share with the report → align → send the finalized Doc to HR to load. **This skill stops at the Doc.**

## Data sources (all optional — use what exists, degrade gracefully)

The card gets stronger with grounding data, but the skill must work for a manager who has none. Pull what's available; never block on a missing source.

| Source | What it gives | How to read (read-only) | Status |
|---|---|---|---|
| **Company strategy / KPIs** | The bonus-grade outcome menu + targets to anchor Side A | LOP base `appAcnl4o8AQVZR1j` → `L1 Goals` + `KPIs` tables | Live |
| **Signal Quick Notes** | Reality-check: where the person's time *actually* went (spot missing accountabilities / low-value work to cut) | `/signal` · `/person-intelligence` (`signal_person_history`, `signal_person_goals`) | Live (if manager has access) |
| **Knowledge Base — KPI nodes** | Canonical **KPI definitions** + their **mapping to outcomes** — the shared vocabulary to phrase measures consistently across cards | `kb.nsls.org` `/mcp` (read-only search) | **Growing** — use a KPI node when it exists; skip cleanly otherwise |
| **Manager interview** | The fallback when nothing exists (new hire) | Structured questions (below) | Always available |

*This list is meant to grow.* As the KB accumulates KPI definitions + mappings, it becomes the preferred source for phrasing Side A measures — and, downstream, the mapping HR pushes into ScoreCards. Add new sources here as the same kind of **optional, read-only, degrade-gracefully** input — never a hard dependency.

## The manager interview (brand-new hire / no data)

When there is no strategy linkage, no Quick Notes, no history, **don't invent** — interview the manager:

1. **Why does this role exist?** → the one-sentence Mission.
2. **What are the 3–6 outcomes you'll hold them to?** Walk the 2×2 to prompt: *What growth number do they move? What operating system do they make better? What must not break on their watch (hygiene)? What existing thing must not rot (reliability)?* Capture outcomes, not tasks.
3. **How will each be measured?** Get a binary "meets" bar where the manager has one; **bracket it** where they don't — it's set with the report later.
4. **Weights** — force the vital few (3–6), ≥ 10% each, summing to 100%.
5. **Which 5–8 competencies** from the bank matter most for this seat? Set a MAR each.
6. **One growth focus** — the development bet for the period + a specific observable action.

## The founder-template structure

One double-sided page. Four blocks, in order:

| Block | What it is | Rating |
|---|---|---|
| **Mission** | One sentence: why this role exists. | — |
| **Side A — Accountabilities** | 3–6 durable **outcomes**, weighted (≥ 10%, sum = 100%), each with a binary **Pass/Fail "Meets" measure**. | A = clearly beat the bar · B = met it · C = missed |
| **Core Values** | The 5 NSLS values, each with a Minimum Acceptable Rating (MAR). | **Binary Pass / Flag gate** (see below) |
| **Side B — Competencies** | 5–8 behaviors from the Topgrading Competency Bank, each with a MAR. | 4 Excellent · 3 Very Good · 2 Good · 1 Weak |

Plus a **Growth Focus** and an **Open Questions** + **Alignment Notes** section. Full template + render mechanics: `references/founder-sop-framework.md`, `references/build_doc_template.py`.

## Side A — the 2×2 portfolio frame

Accountabilities are **outcomes**; for operating/coordination roles the top accountability is often "run the right portfolio." Sort candidate work with the 2×2 (full explanation + how to align a report on it: `references/portfolio-2x2-framework.md`):

|  | **Output** — value produced | **Machine** — system that produces it |
|---|---|---|
| **Advance** | **① Growth driver** — move a number up | **② Operating efficiency** — make the machine leaner |
| **Protect** | **③ Hygiene** — sudden external harm (legal, security, FERPA) | **④ Reliability** — gradual internal decay of what works |

Rows = offense (①②) vs. defense (③④). The two floors (③④) are **cleared, not ranked** against upside. **Bottlenecks** — work that halts other priorities if undone — jump the queue regardless of quadrant.

## Drafting guardrails (from the research — `references/research-grounding.md`)

- **Outcomes, not tasks.** "Ship the automation model" not "work on automation." Specific hard goals beat "do your best" (Locke & Latham). Rewrite every activity into the outcome it serves.
- **The vital few.** 3–6 accountabilities, not 10. Metric sprawl is the #1 scorecard failure mode.
- **Controllability check.** Flag accountabilities largely outside the person's control. For a coordinator role a broad outcome is defensible (tag `[contributor]`), but name the tradeoff.
- **Quality counterweight.** Pair any quantity metric with a countervailing quality one, or the number gets gamed (Goodhart, Kerr).
- **Learning goal for novel work.** For genuinely new/complex work, a capability accountability beats a hard number (which causes tunnel vision).
- **Reality-check, never reality-source.** Quick Notes tell you where time *went* — the manager decides what becomes an outcome. Signal is a **drift detector, NEVER a source of accountabilities.**
- **Bracket everything uncertain.** Dates, thresholds, names → `[brackets]`, set *with the report* in the alignment conversation.

## Core Values — binary gate, NOT a modifier

Score the 5 NSLS values as a **binary Pass / Flag gate** against each MAR. **Do not implement a ±15% modifier** — it was retired as unworkable (Kevin, 2026-07-11), matching HR's production scoring convention (values are binary). This is a decided divergence from the founder SOP, documented in `references/sop-reconciliation-memo.md`. No comp multiplier, ever.

## Side B — competencies from the bank

Select **5–8** from the Topgrading Competency Bank (the org's canonical behavioral taxonomy, HR-owned). Set a MAR per competency by role. Don't invent competencies; consume the bank. Menu + groupings + the caveat that the offline list is partial: `references/competency-bank.md`.

## Significant-edit mode

1. **Get the current card.** Ask for the existing scorecard Doc — paste its text, or give the Drive URL and read it read-only via `gws`.
2. **Show current state** back to the manager (accountabilities + weights, competencies, mission, growth focus).
3. **Apply the changes** they want: add/remove/reweight accountabilities (re-validate weights = 100%), swap competencies + MARs, revise the mission or growth focus. Same guardrails apply.
4. **Render a NEW Doc version** — never overwrite the old one; a new file preserves history.
5. **Emit a change summary** — a short "what changed vs. the prior card" list (e.g., *"Accountability #3 reweighted 15% → 20%; added Reliability line at 10%; dropped Vendor Management"*) so HR can update the system of record precisely, not re-key the whole card.

## The HR handoff (the seam)

The Doc is a **contract** to HR: its structure maps 1:1 to the fields HR loads into the system of record. Keep the render structurally consistent (stable headings, fixed table columns) so the handoff is a parse, not a re-type. The section-to-field mapping lives in `references/handoff-mapping.md` — **confirm it with HR before treating any card as loadable.** This skill produces the Doc; a separate HR-only skill loads it.

## Diagnostic loop — rendering the Doc

**TRY** build → upload → open the Doc. **OBSERVE / DIAGNOSE / ADAPT:**

| Symptom | Cause | Fix |
|---|---|---|
| `ImportError: cannot import name 'Document' from 'docx'` | Corrupt/partial python-docx in `/tmp/pptx_deps` | `python3.12 -m pip install --upgrade --force-reinstall python-docx --target /tmp/pptx_deps -q` |
| Tables render borderless | `table.style` unset | `table.style = 'Light Grid Accent 1'` |
| `**bold**` shows literally in a cell | cell text added as a raw string | use the template's `add_runs()` parser (handles `**bold**`, `*italic*`, `` `code` ``, `\n`) |
| `gws --upload` rejects the path | file outside cwd | build in `~`, run `gws` from `~` |
| `gws` JSON parse fails | keyring line on stdout | pipe through `grep -v -i keyring \| tail` |
| Brand font missing after upload | Google Docs strips custom fonts | Calibri body; brand = navy `#1A2B4A` colors |

Full render mechanics: `/gdoc-build`.

## Service awareness

- **`/gdoc-build`** — the underlying Google-Doc renderer; this skill is a scorecard-shaped wrapper.
- **`/signal` · `/person-intelligence`** — read-only Quick Notes for the reality-check (optional).
- **LOP base** `appAcnl4o8AQVZR1j` — read-only strategy/KPI cascade.
- **Knowledge Base** (`kb.nsls.org` `/mcp`) — read-only KPI definitions/mappings, growing.
- **HR's scorecard system** (people-ops Airtable + scoring bot) — the live system of record. **This skill never touches it.** Loading the Doc is a separate, HR-only step.

## Output guidelines

- **Deliverable = the Doc URL** + a one-line section list. Don't dump the whole card into chat.
- **It's a discussion instrument** — brackets are a feature; say so.
- **Edit mode also returns the change summary.**
- **Remind the handoff:** manager → share with report → align → send finalized Doc to HR to load. **Keep pay out.**

## Rationalizations you will have

| Excuse | Reality |
|---|---|
| "I'll just write the Airtable record too, to save HR a step." | No. Doc only. Writing HR's system is the one thing this skill must never do. |
| "The Quick Notes clearly show this is her job — I'll make it an accountability." | Signal is a reality-*check*, not a source. The manager decides. |
| "The SOP says ±15% values modifier, so I'll add the math." | Binary Pass/Flag. No comp multiplier. |
| "Ten accountabilities is more thorough." | #1 failure mode. Vital few: 3–6. |
| "I'll fill in the Sep 30 dates so the card looks finished." | Brackets are the point. Dates get set *with the report*. |
| "It's a new hire and I have no data, so I'll draft generic accountabilities." | Run the manager interview. Generic ≠ grounded. |
| "This role is unusual — I'll invent a competency." | Consume the bank; flag gaps to HR. |
| "I'll paste the whole card into chat." | Return the URL. |

## Red Flags — STOP

- About to call the Airtable API / write the people-ops base → **STOP.** Doc only.
- About to DM the employee → **STOP.** The manager shares it.
- About to put a bonus %, band, or salary in the Doc → **STOP.** No comp.
- About to promote a Signal Quick Note straight into an accountability → **STOP.** Reality-check, not source.
- About to implement ±15% values math → **STOP.** Binary gate.
- About to overwrite the prior Doc in edit mode → **STOP.** Render a new version.
- About to hand back 7+ accountabilities or task-shaped lines → **STOP.** Vital few (3–6), outcomes.

## References

- `references/founder-sop-framework.md` — the founder's methodology and full template.
- `references/portfolio-2x2-framework.md` — the growth/efficiency/hygiene/reliability 2×2 + how to align a report.
- `references/research-grounding.md` — the evidence base (Locke & Latham, Kerr, Goodhart, controllability).
- `references/sop-reconciliation-memo.md` — where NSLS diverges from the SOP, incl. the decided binary-values gate.
- `references/competency-bank.md` — the Topgrading competency menu + groupings (partial offline list).
- `references/handoff-mapping.md` — Doc section → Airtable field mapping for the HR handoff (confirm with HR).
- `references/build_doc_template.py` — copy-and-fill python-docx renderer (derives filename, prints the upload command).
