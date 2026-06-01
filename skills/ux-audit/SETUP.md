# /ux-audit Setup

This skill audits UX / accessibility / brand for NSLS pages and validates proposed designs before they ship. It has external dependencies that need to be in place before the skill can run end-to-end.

Read this file once per new builder. After that the skill works without rechecking.

---

## Dependencies

### 1. MCP connections (required for full functionality)

| MCP | Why the skill needs it | What breaks without it |
|---|---|---|
| **HubSpot** | Persona retrieval (Step 6.4 — member-fit panel) pulls real ticket text filtered by `hs_ticket_category` × persona-segment filters | Persona reactions fall back to synthetic-only (no quoted member voice); confidence prediction downweights |
| **Atlassian (Confluence)** | Step 6.3 reads the canonical enrollment learnings doc at page `3602579458` for the past-test cross-reference | Enrollment-surface validations lose their primary past-test source; skill falls back to PostHog experiment enumeration alone |
| **PostHog** | Step 5 behavioral data layer (funnel, sessions, errors) + Step 6.3 in-flight experiment check | Skill still runs heuristic + brand + a11y; loses behavioral validation and in-flight-collision detection |
| **Slack** (optional) | Cross-reference test discussions / decisions for past-test layer | Skill still runs; misses Slack-only context |

To wire these up: run `/connect` and follow the prompts.

### 2. Fonts (required for high-fidelity mockup renders)

The skill references the NSLS-brand and Society-brand fonts by name. **Two paths — pick one:**

#### Path A — Install real licensed fonts (production fidelity)

If you have access to the licensed font files (ask the design team or check the shared Drive font folder), install them:

```bash
# macOS — install into ~/Library/Fonts/
# Drop the .otf files into Font Book, or:
cp <path-to>/Brandon\ Grotesque\ Regular.otf ~/Library/Fonts/
cp <path-to>/Brandon_med.otf ~/Library/Fonts/
cp <path-to>/Brandon_bld.otf ~/Library/Fonts/
cp <path-to>/AvenirLTStd-Book.otf ~/Library/Fonts/
cp <path-to>/AvenirLTStd-Roman.otf ~/Library/Fonts/
cp <path-to>/AvenirLTStd-Black.otf ~/Library/Fonts/
cp <path-to>/HW\ Cigars\ Trial\ Medium.otf ~/Library/Fonts/
cp <path-to>/HW\ Cigars\ Trial\ SemiBold.otf ~/Library/Fonts/
cp <path-to>/HW\ Cigars\ Trial\ Bold.otf ~/Library/Fonts/
```

Then, when the skill produces a mockup HTML, reference them via `@font-face` with a relative path to a project-local `fonts/` folder:

```css
@font-face { font-family: 'Brandon Grotesque'; src: url('fonts/Brandon_bld.otf') format('opentype'); font-weight: 700; }
@font-face { font-family: 'HW Cigars'; src: url('fonts/HW Cigars Trial Medium.otf') format('opentype'); font-weight: 500; }
```

#### Path B — Use documented Google Font proxies (works for everyone)

If you don't have the licensed fonts, use the NSLS-brand-book-approved proxies. **The NSLS brand book itself names Montserrat as the approved Brandon fallback** (per `references/brand-nsls.md`).

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;700&family=Fraunces:wght@500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

CSS family aliases:

```css
/* NSLS brand */
.font-display { font-family: 'Montserrat', sans-serif; font-weight: 700; }  /* Brandon Grotesque Bold proxy */
.font-body    { font-family: 'Inter', system-ui, sans-serif; font-weight: 400; }  /* Avenir Book proxy */

/* Society brand */
.font-serif   { font-family: 'Fraunces', Georgia, serif; font-weight: 500; }  /* HW Cigars Medium proxy */
.font-ui      { font-family: 'Inter', system-ui, sans-serif; font-weight: 400; }  /* Inter is open-source — used identically in real brand */
```

Lower fidelity than the real fonts, but renders work for any builder on any machine, and Montserrat is brand-approved per the NSLS brand book.

### 3. Brand asset files (optional but recommended)

For mockups that render accreditation badges or other NSLS image assets, copy the asset files into a project-local `assets/` folder and reference them by relative path. Source files for: Cognia, NCCRS, ACE, Newsweek live in the shared Drive (ask design team). The skill references them as `<img src="assets/badges/cognia.jpg" alt="Cognia Accredited">` etc.

The skill itself does NOT bundle the asset files — they're brand assets, not skill artifacts.

---

## First-run checklist

1. ☐ Run `/connect` and verify HubSpot + Atlassian + PostHog are connected
2. ☐ Decide: real fonts (Path A) or proxies (Path B). Either works; proxies are a fine starting point.
3. ☐ Skim `references/design-validate-failure-modes.md` — this is the calibrated catalog of past-failure patterns the skill is trained against. Knowing what's there before your first audit means you'll recognize the patterns when the skill flags them.
4. ☐ Skim `references/nsls-context.md` for NSLS-specific audit calibration (Prestige-Polish Paradox, nomination code architecture, etc.)
5. ☐ Run a small calibration test: pick any NSLS page and run `/ux-audit` on it. The pre-output gate should fire — confirm you see the gate's verification quoted in the output.

---

## When to update this file

- A new MCP becomes required (e.g., Customer.io for email-touchpoint persona retrieval)
- A new font is added to the brand reference docs
- A new failure mode (F20+) is cataloged that needs a setup step

---

## Calibration history

| Date | Version | Catalog state | What changed |
|---|---|---|---|
| 2026-05-08 | v1.0 | F1–F0 (skeletal) | Initial skill: SUS + Laws of UX + WCAG + Brand layers |
| 2026-05-11 | v2.0 | F1–F10 | Added Step 6 Design Validation Layer with surface taxonomy, personas, confidence framework, HubSpot retrieval, encoded principles from Confluence 3602579458 |
| 2026-05-12 morning | v2.1 | F1–F13 | Hardened with iteration discipline gate (10 items), failure-modes catalog calibrated against real session misses, chained to verification-before-completion |
| 2026-05-12 afternoon | v2.2 | F1–F19 | Comprehensive QA pass added gates 11–14 (responsive breakpoints, error states, semantic landmarks, code-readiness) and failure modes F14–F19 |

The catalog grows with use. When you find a new failure mode (F20+), add it to `references/design-validate-failure-modes.md` with the same structure: pattern, what to check, verification, red flag thought, dated example.
