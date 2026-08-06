---
name: page-qa
description: >-
  Use before shipping ANY web page or front-end PR — to decide, on evidence, whether it is
  ready to merge. Trigger when someone says "QA this page", "is this page ready", "run QA on
  this PR / branch / preview", "check this before merge", "gate this page", or when a build
  workflow (e.g. marketing-page) reaches its QA phase. Not for backend-only changes, and not
  a substitute for a human's own eyes on the deploy preview.
---

# page-qa — the evidence-based page quality gate

## Safety

- **Tier 1 — read/run (no friction):** read source + built output, run `build`/`typecheck`/`lint`/unit tests/`axe`/Lighthouse/Playwright, take screenshots, spawn a read-only review subagent, inspect git.
- **Tier 2 — configuration (say what you're doing):** add the page to `a11y.spec`/`lighthouserc`, write a per-page e2e spec, apply *fixes you found* to the page. These are commits on the page's own branch — never on `main`/`staging`.
- **Tier 3 — external writes (never from here):** page-qa does NOT merge, deploy, move Jira, or write Confluence/Figma. It produces a verdict; shipping is the caller's job (the human, or `/marketing-page`).

## Purpose

page-qa turns "looks done" into "proven ready." It runs every machine gate, an accessibility/UX/brand audit, and an adversarial reviewer that reads the *built output* and tries to refute readiness — then it re-derives every claim against git and real test runs, because a confident self-report is not evidence. The output is a single verdict a human can trust: what's a hard blocker, what's advisory, and exactly which command proved it. It exists because pages ship broken when QA is a vibe instead of a ladder of gates that each produce evidence.

## Quick Start

```
Input: a page route + its branch/worktree (or a PR / deploy-preview URL).
1. L1 machine gates      → build · typecheck(0) · lint(0) · unit · axe(0 serious/critical) · overflow sweep 320→1440 · Lighthouse
2. Audit                 → /ux-audit (SUS · Laws of UX · WCAG · brand)   [a11y = BLOCK, UX/brand = advisory]
2b. DS compensations     → if built from NSLS Design System output: the checks axe cannot catch [BLOCK]
3. Adversarial review    → fresh-context subagent refutes readiness vs BUILT output
3b. Multi-lens panel     → WHOLE SURFACES ONLY: 6-8 read-only agents, distinct specialty + seniority
4. Verify gate           → scripts/verify-task.sh <sha> ALL PASS + built-output assertions
5. Verdict               → SHIP / DO-NOT-SHIP, blockers first, each with the command that proved it + a "could not verify" list
```

Nothing is "passed" on a self-report. Every PASS names the command that produced it.

## The gate ladder

Run in order. A hard-blocker at any rung stops the ladder — fix, then re-run from that rung.

### Rung 1 — L1 machine gates
Run from the page's worktree/branch:
```bash
npm run verify         # lint + typecheck + format:check + test, in one gate
# or individually:
npm run build          # must complete
npm run typecheck      # 0 errors (pre-existing "Props declared but never used" hints are OK)
npm run lint           # clean
npm run format:check   # Prettier, on CHANGED LINES ONLY — see the no-burying rule below
npm run test           # vitest — all pass; print the real count
```

**Formatting: enforce it on the diff, never on the repo.** `nsls-marketing` had ~140 files before
Prettier was added, and none of them were formatted: quote style split roughly 29/24, and 37 lines in
`src/lib` alone over 120 chars. So:

- **Never** run `prettier --write .`. It buries the real change at repo scale and destroys `git blame`
  everywhere. A PR of 140 reformatted files plus 8 real changes does not get reviewed, it gets skimmed.
- **Never** run `prettier --write` on whole *modified* files either. That buries at FILE scale, which
  is less obvious and still bad. Measured: `prospective.astro` had a 3-line change and whole-file
  formatting rewrote 45 of its 46 lines, a 15:1 noise ratio. After the line-scoped gate the same
  change is 2 insertions.
- `npm run format` / `format:check` (`scripts/format-changed.mjs`) is the only formatting entry point:
  **NEW files whole** (no history to protect), **MODIFIED files only at the changed line ranges** via
  Prettier's `--range-start`/`--range-end`.
- **Range formatting can corrupt source, so it is validated per range.** It really happened: a range
  boundary landing mid-expression produced `};);` where `});` belonged, which then poisoned every
  later range in that file, and only eslint caught it after the write. Each candidate is re-parsed
  before being accepted; a range that fails is skipped and reported. If you build this kind of tool,
  the validation is not optional.
- `.astro` modified files are **could-not-verify**, not pass: the Astro plugin ignores ranges and
  reformats the whole document, which is the thing being prevented.
- Synced content (`src/content/help/`) and `package-lock.json` are `.prettierignore`d. Formatting the
  KB mirror would change bodies the sync compares by hash, so the next run would report ~95 phantom
  "changed" articles.
Then the browser gates (Playwright), per page:
- **axe** — 0 *serious/critical* violations (this is a hard blocker).
- **Overflow sweep 320→1440** — at each of `[320,360,390,414,560,768,1024,1185,1280,1440]`, assert `document.documentElement.scrollWidth === window.innerWidth`. Any overflow = hard blocker (this is Rule 9 of the marketing platform; h-overflow has shipped from wide CTAs and nav turning on too early).
- **Lighthouse** — via `lighthouserc.json`. **Accessibility ≥ 0.9 is the blocking assertion**; performance/SEO are `warn` (SEO dips to ~0.69 purely because staging is `noindex` — that is expected, not a defect, until cutover).

Add the page to `tests/e2e/a11y.spec.ts` and `lighthouserc.json`, and write a per-page `tests/e2e/<page>.spec.ts` (overflow sweep + render assertions + interactive checks) so these gates persist in CI.

### Rung 2 — Audit (`/ux-audit`)
Invoke `/ux-audit` on the built page (or Figma/screenshot). It produces Predicted SUS, Laws-of-UX findings, WCAG 2.1 A/AA checks, and brand-style findings.
- **WCAG/accessibility findings → BLOCK.** They join the axe results as must-fix.
- **UX (SUS, Laws of UX) + brand findings → advisory.** Surface them verbatim to the human gate; do not auto-block. The human weighs them.

### Rung 2b — Design-system compensation checks

Applies when the page was built from **NSLS Design System** output (Claude Design, its `components/` primitives, or either `ui_kits/` template). Those components ship the defects below, and the design system is Tatiana's and frozen — so the compensation happens **here, in the page**. axe cannot detect any of these: they are missing-*relationship* and missing-*role* defects, not invalid-markup defects, and every one of them is valid HTML.

| Check the page for | Why axe misses it | Compensation |
|---|---|---|
| error/hint text linked via `aria-describedby`, `aria-invalid` set when the field errors | axe checks a field *has a label*, not that its error text is associated | add both at the call site |
| current step / current page marked with `aria-current` | no axe rule; DS carries the state in colour alone | `aria-current="step"` / `"page"` |
| numbered sequence (Steps to Induction) is an `<ol>` | a div grid is valid markup | `<ol>`/`<li>`, number in the DOM |
| progress bar has `role="progressbar"` + `aria-valuenow/min/max` | an unroled div is invisible to axe | add role + values, or use `<progress>` |
| initials-only avatar has `role="img"` + `aria-label` | bare text is valid | add both; `aria-hidden` the initials |
| clickable card/tile is a `<button>` or `<a>` | `<div onClick>` is valid markup | use the real element |
| focus ring on navy / gradient backgrounds | axe has no focus-appearance rule | white ring on dark — the DS Foundation Blue ring measures **1.1:1** on the hero gradient and **1.3:1** on the navy footer |
| icon-only control has an accessible name | axe *does* catch this (`button-name`, critical) — but only if it is a real `<button>`; the DS kits use `<span>` | make it a `<button aria-label="…">` |

**Heading levels are a hole in Rung 1.** axe classes `heading-order` as *moderate* and `page-has-heading-one` as a *best-practice* rule — neither is serious/critical, so **both pass the Rung-1 threshold**. Assert them explicitly here. The design system's own kits ship `h1 → h2 → h4 → h6` with levels picked for font size, and a portal page with no `h1` at all, so anything derived from them starts broken.

**Expect an adherence-lint warning; do not revert the fix.** `_adherence.oxlintrc.json` declares a per-component prop allowlist, so adding `aria-describedby` or `aria-label` to a design-system component warns. The allowlist is incomplete — the code is correct. Record it as advisory and move on.

These carry the same weight as axe findings: **a11y blocks.**

### Rung 3 — Fresh-context adversarial review
Spawn a subagent (general-purpose) that has NOT seen the build, prompted to **refute** readiness by reading the **built output**, not any self-report. Give it the authoritative facts to check against (copy, links, headings, alt, SEO meta). Ask for findings ranked most-severe first with file/line or a built-HTML quote, and a SHIP/DO-NOT-SHIP verdict.

**Then re-derive every finding yourself against git + real runs. Never accept the subagent's verdict as truth** (a subagent once fabricated a commit SHA and test counts). Apply the real fixes; *reject false positives with evidence* — e.g. a reviewer that reads the live DOM via WebFetch will report headings as title-case and flag a "casing blocker," but WebFetch returns text *before* CSS `text-transform`; confirm the rendered truth (recording, or `curl | od -c` on the live bytes) before acting.

### Rung 3b — Multi-lens panel (whole surfaces, not single pages)

Rung 3 is one reviewer refuting one page. When the target is a **whole surface** — a portal, a
migration, a subsystem about to be handed to another team — one reviewer is not enough, because the
defects live in different disciplines and each lens is blind to the others'. Run a panel of
read-only subagents with **distinct specialties AND distinct seniorities**, in parallel, in one
message.

Proven lens set (2026-08-06, NSLS self-help portal, 8 agents). Each found defects no other lens
found, which is the whole argument for the panel:

| Lens | Seniority framing | What only it found |
|---|---|---|
| QA engineer | senior, release gates | success copy shown while the relay discarded the submission |
| QA analyst | mid, walks it as a real impatient user | the primary control rendering 358x24 on mobile |
| Data engineer | senior, pipelines + integrity | two base-prop builders disagreeing, so events could not join their own denominator |
| Product analyst | measurement design | the outcome metric is not captured and neither side of it is |
| Staff platform engineer | 15y, maintainability | the static-site model cannot hold the proposed feature at all |
| AppSec / privacy | 9y | the POST was a CORS *simple* request, so any third-party page could fire it |
| SRE | reliability, operability | the failure alert `exit 0`d when its webhook was unset, so a broken alarm reported success |
| Product designer | internal tools | four of five proposed panels would render zeros for months |

Scale the panel to the target: 3 lenses for a page, 6 to 8 for a surface. Prompt every one with:

- **Read-only, explicitly.** No edits, no commits, no tickets, no Slack. Say it in the prompt; agents
  will otherwise "helpfully" file things.
- **The CURRENT verified state, not the docs.** Repo docs go stale and agents quote them as fact.
  Three agents independently reported an env var as unset because `WHERE-WE-LEFT-OFF.md` said so;
  it had been set that morning. State what you have verified and tell them to verify the rest.
- **A demand for `file:line` or a real query + numbers**, and a required split of
  **CONFIRMED / SUSPECTED / could-not-check.** The could-not-check list is what makes the rest
  trustworthy.
- **An instruction to leave a reproducible probe** (a script, an exact query) for anything numeric.
  The UX agent's `probe.mjs` let every search claim be re-run in seconds.

Then synthesise. **The synthesis is your job and it is where the value is** — the panel produces
raw material, not a verdict.

### Verifying a panel: the failure modes that actually occurred

Re-derive before relaying, and expect all four of these:

1. **Stale premise ranked #1.** An agent's top-ranked finding was "the analytics key is unset,"
   which had been fixed hours earlier. It had built its entire framing on it. Check the headline
   claim of every report against live state before reading the rest.
2. **Overstated headline numbers.** Verify every quotable figure yourself: reported 4.9% of help
   visitors search, real number 2.5% (it used pageviews as the numerator against people); reported
   190 password resets/day, real 99 (it summed two events); reported 9 articles affected, real 10.
   The direction was right every time and the magnitude was wrong most times.
3. **Severity wrong in BOTH directions.** The same report understated one defect (contact-form
   messages irretrievably discarded, no sink at all) and overstated its neighbour (the feedback
   widget, which has a second sink and loses nothing). Do not assume the bias runs one way.
4. **A confidently reported "unreachable" that was reachable.** Articles called unbrowseable were
   surfaced by a different view the agent had not read. Check the claim's negative space: *where
   else* could this be reached from?

Two things that make a panel worth the tokens, and both are about the synthesis:

- **Look for the ordering rule across reports.** Three lenses independently found that several
  defects were harmless *only* because an env var was unset, and that the natural order of work
  (make the feature work) activates each one. That inversion — harden before you configure — was in
  no single report; it only appears when you read them together.
- **Credit what is right.** The panel will find good decisions too (keep-last-good on fetch failure,
  a deliberate Tier-0 identity stub that retro-fits a segment). Say so. A report that is all defects
  reads as noise and gets discounted wholesale.

### Rung 4 — Verify gate
```bash
scripts/verify-task.sh <sha> \
  "dist/<page>/index.html::<verbatim string that must be present>" ...
```
Must print `== ALL PASS ==`: commit exists in HEAD history, working tree clean, build/vitest/typecheck/lint pass, and every built-output assertion is found. If the tree is "dirty" only because of a `node_modules` symlink in a worktree, exclude it via the shared git dir's `info/exclude` (append `node_modules`) — do not commit it.

## Verdict format

```
page-qa: <route> @ <sha>  —  VERDICT: SHIP | DO-NOT-SHIP (N blockers)

BLOCKERS (fix before merge):
  - [a11y] <finding> — proof: <axe rule / command> — fix: <...>
ADVISORY (human weighs at the gate):
  - [ux]  Predicted SUS <n>; <Law of UX finding>
  - [brand] <finding>
COULD NOT VERIFY:
  - <thing you could not check and why>   ← mandatory; counters "everything passed"
EVIDENCE:
  - build ✓ · typecheck 0 · lint 0 · vitest <n> ✓ · axe 0 serious/critical · overflow 320→1440 ✓ · Lighthouse a11y <score>
  - verify-task ALL PASS @ <sha>
```

The **"could not verify" list is mandatory** on every run — a QA report with nothing it couldn't check is lying.

## Domain micro (hard-won)

- **`npm run typecheck` in `.astro`:** map/forEach callbacks in frontmatter need explicit param types (`(it: T, i: number)`) or they throw implicit-`any`; an unused `Props` interface is a benign hint, not an error.
- **Screens for the sweep are PNG (Playwright default).** For a full-page reference vs live, macOS screen-recording/screenshot filenames use a **narrow no-break space** (U+202F) before AM/PM — reference them by glob, not a typed literal path.
- **Reduced-motion for deterministic e2e:** `page.emulateMedia({ reducedMotion: "reduce" })` freezes marquees/scroll-reveals so interaction tests don't race.
- **Fidelity:** compare the built render to the live page visually (screenshot) AND on copy at the byte level for punctuation — curly vs straight quotes/apostrophes are a real Rule-2 defect and are invisible in a glance.
- **The adversarial reviewer is the highest-value rung and the most dangerous** — its findings feel authoritative. The rule is verify-don't-trust: re-derive against git and real runs every time.

## Diagnostic loop

TRY → OBSERVE → DIAGNOSE → ADAPT → re-run the failing rung.
- axe fails → read the node target → fix contrast/alt/label/role → re-run axe only.
- overflow at one width → binary-search the offending element (a wide fixed-width child, an image without `max-width`, transform pushing past the viewport) → fix → re-sweep.
- Lighthouse a11y < 0.9 → open the LHCI report's failing audits (usually names/labels/contrast) → fix → re-run.
- verify-task "working tree not clean" → `git status --porcelain`; if it's only the `node_modules` symlink, exclude it (above); else commit the real change.

## Hierarchy / references

- Tools not available (Playwright, PostHog, etc.) → run `/connect`.
- Audit dimensions (SUS, Laws of UX, WCAG, brand) → `/ux-audit` owns these; page-qa calls it, doesn't duplicate them.
- This skill is the QA phase of `/marketing-page`; it is also usable standalone on any page or PR.

## Red Flags — STOP if you catch yourself thinking:

| Thought | Reality |
|---|---|
| "Build passed, it's probably fine" | Fine = the whole ladder + the verdict, not one gate. |
| "The reviewer said SHIP, so ship" | Re-derive its findings vs git/tests. Its verdict is input, not truth. |
| "The reviewer flagged a blocker, I'll just fix it" | Re-derive it FIRST — reviewers hallucinate blockers (WebFetch casing). Reject false positives with byte/recording proof before touching code. |
| "This gate wouldn't run here, so I'll pass the rest" | A gate you couldn't run is a **could-not-verify**, never a pass. Missing evidence ≠ passing evidence. |
| "A11y is close enough" | axe serious/critical = 0 and Lighthouse a11y ≥ 0.9 are hard blockers, not targets. |
| "axe passed, so a11y is done" | axe cannot see missing relationships or roles — no rule for unassociated error text, `aria-current`, an unroled progress div, or focus-ring contrast. Run Rung 2b. |
| "Headings are fine, Rung 1 was green" | `heading-order` is *moderate* and `page-has-heading-one` is *best-practice* — both slip past 0-serious/critical. Assert them by hand. |
| "The design-system component handles that" | It does not, and it will not — the DS is frozen. The page compensates (Rung 2b). |
| "The adherence lint warned on my aria prop, I'll remove it" | The allowlist is incomplete; your fix is correct. Keep it, note it advisory. |
| "No overflow on my screen" | Sweep 320→1440 programmatically; assert scrollWidth == innerWidth. |
| "Nothing to put in could-not-verify" | Then you didn't look hard enough. It's mandatory. |
| "I'll merge since QA passed" — or someone asked me to | page-qa never merges/deploys/moves Jira, even when asked. It reports; redirect shipping to the human/caller. |
| "The copy looks right" | Check punctuation at the byte level against the live source (curly vs straight). |
| "One reviewer covered it" | For a whole surface, one lens is blind to seven others. Run Rung 3b — every lens in the proven set found defects no other lens found. |
| "The panel agreed, so it's true" | Agreement can be a shared stale premise. Three agents repeated the same wrong env-var state because they all read the same doc. |
| "I'll quote the agent's number" | Re-derive every figure. In one run the direction was right every time and the magnitude wrong most times (4.9% vs 2.5%, 190/day vs 99/day). |
| "Its top finding is the top finding" | Check the headline claim against live state FIRST. A #1-ranked finding was already fixed hours earlier, and the whole report was framed on it. |
| "It said this is unreachable" | Check the negative space: where ELSE could it be reached from? A "31 unbrowseable articles" finding missed a second view that surfaced them. |
| "More lenses is strictly better" | 3 for a page, 6-8 for a surface. Past that you are paying tokens to re-read the same files. |
| "I'll just run prettier to fix the format gate" | Repo-wide `--write` buries the change in a 140-file diff and destroys git blame. Whole-file `--write` on a modified file buries it too (measured 45 reformatted lines for a 3-line change). Use `npm run format` — changed lines only. |
| "The formatter can't break code" | It can. Range formatting emitted `};);` for `});` here and corrupted a test file. Re-parse every formatted result before accepting it. |
| "The format gate said could-not-verify, close enough" | Same rule as every other gate: a gate you couldn't run is a could-not-verify, never a pass. Modified `.astro` files always land here. |
