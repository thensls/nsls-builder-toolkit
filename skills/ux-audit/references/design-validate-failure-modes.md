# Design Validation — Failure Modes Reference

## Why this doc exists

This catalogs failure patterns observed while running this skill on real NSLS work. Each entry is calibrated against a specific real-world miss — not hypothetical risks. The skill's pre-output gate (in SKILL.md) requires explicit verification against this list before any design output ships.

The pattern this prevents: making a change in chat, claiming it's done, and only finding out later that the change broke an adjacent guardrail. Every entry below is a real instance of that failure mode from the session where this skill was being calibrated.

---

## How to use this doc

When the skill triggers (any design creation, mockup change, or validation request), this doc is read BEFORE output. For each failure mode below:

1. Identify whether the current task could plausibly trigger this failure
2. If yes, run the **What to check** + **Verification** steps
3. Quote the result of the verification in your response — do not paraphrase
4. Only after every applicable mode is checked, present the output

The honesty constraint: if a check wasn't run, the output is not done — state that explicitly rather than claim completion.

---

## F1 — Contrast violation slipped past visual review

**Pattern:** Light text on light background, or any text/bg pairing that "looks fine" but hasn't been measured.

**What to check:**
- Every text color + background color pairing in the new or changed content
- Including hover states, focus states, and overlays if defined
- Especially: text on tinted panels, text on photographs, accent colors used as text

**Verification:**
Calculate WCAG contrast ratio for each pairing using the relative-luminance formula. Required: ≥4.5:1 for body text, ≥3:1 for large text (≥18pt or ≥14pt bold), ≥3:1 for UI components per WCAG 1.4.11. **Quote the ratio, not "passes."**

**Red flag thought:** "The contrast looks fine visually." Visual estimation fails — light purple panels read as fine but commonly fail AA.

**Example failure (2026-05-11):** Society purple panel `#949AE2` with white text `#FFFDF8` shipped at 2.59:1. Fixed by switching to Society Black text at 6.85:1.

---

## F2 — Wrong proxy font instead of available real font

**Pattern:** Using a Google Font proxy (Oswald, Cormorant Garamond, etc.) when the licensed font is actually installed locally.

**What to check:**
- Before falling back to any proxy, run: `find ~/Downloads ~/Library/Fonts ~/Desktop /Users/$USER -maxdepth 4 \( -iname "*.otf" -o -iname "*.ttf" \) 2>/dev/null | grep -i <font-name>`
- For NSLS-related work: check for `Brandon`, `Avenir`, `Cigars`, `Lexend Deca`
- Local fonts wire up via `@font-face` from a relative path; copy into a mockup-adjacent folder

**Verification:**
Confirm the real font is being loaded, not the proxy. Inspect the `font-family` declaration AND the `@font-face src` path. **Quote the path.**

**Red flag thought:** "This proxy is close enough." Oswald is condensed; Brandon Grotesque is humanist — entirely different feel. Close-enough proxies break brand recognition.

**Example failure (2026-05-11):** Used Oswald as Brandon Grotesque proxy + Cormorant Garamond as Cigars proxy when both real fonts were in `~/Library/Fonts/`. Caught when user asked "are you using the real fonts?"

---

## F3 — Validated wins absent from new design

**Pattern:** Designing a mockup or proposing a change on a surface that has a canonical learnings doc, without integrating the validated patterns from that doc.

**What to check:**
- Is the target surface in `references/design-validate-surfaces.md` as having a canonical learnings doc?
- If yes (e.g., enrollment funnel → Confluence 3602579458):
  - Read the validated principles + the experiment outcomes table
  - For each Validated principle: does the design align? If absent, state why
  - For each Rejected pattern: does the design avoid it?
- Read `references/design-validate-encoded-principles.md` for the auto-flag list

**Verification:**
Output a "validated patterns integrated" table inline with the design. Every applicable CDP-### win must appear or have a stated reason for absence. **Quote the Jira key for each.**

**Red flag thought:** "I'll add the validated wins later as enhancements." No — the mockup IS the proof of design intent. Missing CDP-214 ($600K/yr win) from v1 is not v2 polish; it's a v1 failure.

**Example failure (2026-05-11):** Initial NSLS + Society mockups omitted CDP-214 (30-day refund copy), CDP-149 (SMS opt-in), CDP-301/339 (mobile floating CTA), EE-8 (accreditation badges). All had to be added in v2 after user pushed back.

---

## F4 — Adjacent components visually identical

**Pattern:** Building two or more visually-adjacent UI components from the same template, resulting in interface elements that can't be distinguished at a glance.

**What to check:**
- Identify component groups (payment method buttons, social sign-on, CTA pairs)
- For each pair/group, ask: "If a user glanced at this for one second, could they tell these apart?"
- Common adjacency failures: black-on-black with same icon size + same text length

**Verification:**
Open the rendered output. Look at the adjacent components side-by-side, not in isolation. Each component must have at least one of: distinct background color, distinct foreground color, distinct icon, distinct text-length pattern. **Quote which axis differentiates each pair.**

**Red flag thought:** "The buttons are clearly different — they have different labels." Different labels at the same visual weight read as identical to a fast-scanning user.

**Example failure (2026-05-11):** Apple Pay button (black bg + white  + "Pay") and Google Pay button (black bg + white G + "Pay") rendered visually identical. Fixed by: Apple Pay = black, Google Pay = white with multicolor G, PayPal = yellow with dark italic — three distinct visual treatments per each brand's actual style guide.

---

## F5 — Mock terminology mismatched product reality

**Pattern:** Using product-specific terms (induction, membership, dashboard, FOL) loosely without verifying they map to the actual moment in the funnel.

**What to check:**
- Read `references/nsls-context.md` for the canonical NSLS terminology + funnel stages
- For each piece of copy that uses domain terms, ask: "Is this term accurate at THIS step?"
- Confirm with the user when in doubt — never assume terminology

**Verification:**
Quote the specific phrase + the funnel moment it appears at. Confirm against the canonical glossary or ask the user. **Never invent timing of induction, certification, or post-purchase events without checking.**

**Red flag thought:** "Inducted sounds right for the post-payment confirmation." It's not — induction comes AFTER Foundations of Leadership completion, not at payment.

**Example failure (2026-05-11):** Initial confirmation page said "You're inducted, Jesse" at the moment of NSLS membership purchase. Induction actually happens later, after FOL completion. Fixed to "Welcome to NSLS, Jesse."

---

## F6 — Heading hierarchy inflated

**Pattern:** Multiple `<h1>` elements per page, OR skipped levels (h1 → h3 without h2).

**What to check:**
- Count h1/h2/h3/h4 occurrences:
  ```bash
  grep -oE "<h[1-6]" <file> | sort | uniq -c
  ```
- Verify exactly one h1 per page (or per landmark)
- Verify sequential nesting — no jumps

**Verification:**
Run the grep above. **Quote the output.** If h1 count > 1, fix before claiming done. WCAG 2.4.6 + 1.3.1 conformance depend on this.

**Red flag thought:** "Each section needs an h1 to look like its own page." No — semantic structure stays consistent regardless of mockup framing. Multiple h1s break screen reader nav.

**Example failure (2026-05-11):** Both NSLS and Society mockups had 11 h1 elements each (one per step desktop + one per step mobile + doc title). User flagged when a11y check was requested. Fixed via bulk replace to `<h2 class="...">` for all mockup-internal heroes.

---

## F7 — Mobile as truncated desktop

**Pattern:** Building a desktop view first, then producing a mobile version by removing/shortening content rather than designing for mobile-first.

**What to check:**
- Compare bullet counts: does desktop have 5 bullets where mobile has 4?
- Compare CTAs: does mobile drop a secondary action that desktop shows?
- Compare supporting text: does the desktop pricing card have a paragraph that the mobile version drops?
- Compare links: are "What is the X?" / fine-print links present on one platform but not the other?

**Verification:**
Each piece of content on the desktop view must exist on the mobile view in some accessible form (visible, expandable, or linked) — or have an explicit user-facing reason to differ. **Quote the parity check result.**

The one acceptable difference (per audit Top-10 #3): Grad Set upsell on enrollment Payment step — desktop shows, mobile removes. This is justified by the CDP-353 mobile-payment-screen-overload finding.

**Red flag thought:** "Mobile is just a smaller version of desktop." Modern mobile-first design requires designing the mobile experience as primary, with desktop as enhancement.

**Example failure (2026-05-11):** Initial Society mockup had 5 benefit bullets on desktop, 4 on mobile. Pricing card paragraph on desktop, dropped on mobile. "What is the NSLS?" link on desktop only. Fixed in v2 rebuild by enforcing parity.

---

## F8 — Placeholder assets shipped instead of real assets

**Pattern:** Using styled CSS divs or text labels in place of real logos, badges, or images, even when the real files exist locally.

**What to check:**
- Before falling back to styled placeholders, run:
  ```bash
  find ~/Downloads ~/Documents ~/Desktop -maxdepth 4 \( -iname "*<asset-name>*" \) \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.svg" \) 2>/dev/null
  ```
- For NSLS accreditation work: check for Cognia, NCCRS, ACE, Newsweek, NSLS seal
- For brand work: check for any image asset in `~/Downloads` matching the asset name

**Verification:**
If real asset files exist, copy them to a mockup-adjacent assets folder and reference via relative path with proper `alt` text. **Quote the file path used.**

**Red flag thought:** "The user can replace the placeholder later." If the asset exists now, use it now. Placeholders communicate "not ready" and force the user to do work the agent could have done.

**Example failure (2026-05-11):** Initial mockups rendered Cognia/NCCRS/ACE/Carnegie as styled cards with text labels and `◆` glyphs. Real PNGs for Cognia, NCCRS, ACE, plus Newsweek were sitting in `~/Downloads`. User had to ask "use the real badges" before the agent searched for them.

---

## F9 — Unvetted CTAs

**Pattern:** Picking CTA copy or hierarchy by intuition rather than against documented product behavior.

**What to check:**
- For post-purchase / post-action confirmation pages: what is THE primary next action per the product?
- For mid-flow steps: what is the canonical CTA copy used elsewhere in the product?
- For Society-on-NSLS or NSLS-on-Society contexts: does the brand context allow cross-product CTAs?

**Verification:**
Confirm CTA copy + hierarchy with the user before shipping. If you have to guess, ask. **Never default to vibes-based CTA hierarchy.**

**Red flag thought:** "Try Society's AI Coach" reads like a natural next step on confirmation. Maybe — but the actual NSLS primary CTA is "Continue to dashboard" and Society is a secondary member benefit, not a competing primary action.

**Example failure (2026-05-11):** Made "Open Society" the visually-primary CTA on the NSLS confirmation page. The actual primary is "Continue to dashboard"; Society is a member benefit. Also wrongly placed a Society panel on the NSLS-branded mockup, violating "no Society mention on NSLS brand" rule.

---

## F10 — Skill artifacts that contradict each other

**Pattern:** Skill output (annotation, rationale, design) contains references to elements that were removed in a later iteration but the references weren't cleaned up.

**What to check:**
- After any removal or large change, grep for orphan references:
  ```bash
  grep -n "<removed-element>" <file>
  ```
- Verify rationale blocks, legend sections, and TOCs are consistent with the current state

**Verification:**
Run the grep AFTER the edit, not just before. **Quote the result.** If orphans exist, fix them before claiming done.

**Red flag thought:** "I just removed the social sign-on. The rationale will be updated separately." No — rationale must stay consistent with the design in the same edit pass. Orphan references confuse readers and signal sloppy work.

**Example failure (2026-05-11):** After removing social sign-on from both mockups, the rationale blocks still mentioned EE-18 / CDP-293 / "Society as member benefit" until separately cleaned up.

---

## F11 — Heading skip even when count passes

**Pattern:** File has exactly one `<h1>` (gate item #7 by count passes) but heading levels in document order skip — e.g., `h1 → h3 → h3 → h2 ...` or `h2 → h4` without an intervening `h3`. WCAG 1.3.1 + 2.4.6 fail.

**What to check:**
- COUNT alone is insufficient — verify document-order sequence
- Common offenders: doc-wrapper section headings styled as visual h3 when they're top-level (should be h2); annotation cards styled as h4 when they sit at the same conceptual level as form sections (should be h3)

**Verification:**
```python
import re
with open(file) as f: c = f.read()
headings = re.findall(r'<(h[1-6])\b', c)
last = 0
for i, h in enumerate(headings):
    level = int(h[1])
    if last > 0 and level > last + 1:
        print(f"SKIP at pos {i}: h{last} → h{level}")
    last = level
```
**Quote the output.** If skips exist, fix before claiming done.

**Red flag thought:** "I have one h1 so the heading hierarchy passes." Order matters as much as count.

**Example failure (2026-05-12 calibration test):** Both NSLS + Society v2 mockups passed gate item #7 by count (1 h1 each) but had `h1 → h3 → h3 → h3 → h2 ...` order due to "On this page" / "brand contract" / "validated patterns" doc-section headings being styled as h3 when they're conceptually parallel to step section h2s. Also had `h2 → h4` skips on DESIGN RATIONALE annotation cards. Fixed by promoting doc-section h3 → h2 and demoting rationale h4 → h3.

---

## F12 — Brand logo flagged as WCAG 1.4.11 fail (false positive)

**Pattern:** Contrast calculation flags a logo or brand-identifier color as failing WCAG 1.4.11 (non-text UI components need ≥3:1). The flag is technically correct per the math but WCAG 1.4.11's *Notes* exempt logos and brand identifiers from this requirement.

**What to check:**
- Before flagging a 1.4.11 fail on a colored element, identify whether the element is a brand logo, brand identifier, or generic UI component
- WCAG 1.4.11 Notes: *"Exception: ... Logotypes — Text that is part of a logo or brand name has no contrast requirement"* — extended in practice to logo glyphs
- The Google Pay G logo's yellow segment (`#FBBC05`), Apple's logo, PayPal's wordmark italic etc. are brand marks, not UI components

**Verification:**
For any 1.4.11 flag on a sub-3:1 color, ask: "Is this element a brand identifier (logo, wordmark, brand-color glyph)?" If yes, do NOT report as a fail — annotate as "WCAG 1.4.11 logo exemption applies." If no, report and fix.

**Red flag thought:** "The contrast calculator flagged Google's yellow at 1.71:1 — must fix." Logos are exempt. The brand mark is the unit of recognition, not each color individually.

**Example failure-to-prevent (2026-05-12 calibration test):** Calibration script reported Google Pay G logo's yellow segment at 1.71:1 on white as a 1.4.11 fail. In context this is a false positive — the G logo is Google's brand mark and exempt. Catalog updated to require brand-identifier checking before reporting any 1.4.11 contrast fail.

---

## F13 — Orphan CSS after HTML removal

**Pattern:** HTML using a CSS class is removed but the CSS class definition stays in the stylesheet. No rendering issue (no element to render) but the stylesheet grows over time with dead rules, and it signals that the removal wasn't a complete cleanup. Sister failure to F10 (orphan HTML/text references) but specifically about CSS.

**What to check:**
After removing an HTML pattern (a feature, a component, a section), grep the stylesheet for the CSS classes that were used by the removed HTML. If those classes still exist with no consumers, they're orphans.

**Verification:**
```bash
# After removing HTML using class "foo", check if .foo CSS is still defined:
grep -E "\.(foo)\b" <file>
```
If matches return CSS rule definitions but no HTML consumers, remove the CSS too — or note explicitly why it's being kept (e.g., reusable utility class).

**Red flag thought:** "I removed the HTML, the CSS doesn't render anything anyway." True for rendering, but the CSS is still dead code, signaling sloppy cleanup, and inflates file size. F10 covered HTML/text orphans; F13 covers the parallel CSS case.

**Example failure (2026-05-12 calibration test):** After removing the social sign-on HTML from both mockups, the `.social-row`, `.btn-social`, `.btn-social.google`, `.btn-social.apple`, `.btn-social .social-icon`, `.social-divider` CSS rules remained in the Society file's stylesheet. Society file had 5+ orphan CSS class definitions. NSLS file had the same orphan CSS plus the `/* Social sign-on (EE-18 unlock) */` comment block. Calibration test surfaced this; original F10 catalog didn't anticipate the CSS-side cleanup.

---

## F14 — No real responsive breakpoint logic

**Pattern:** Mockup demonstrates "mobile" and "desktop" as side-by-side fixed-width device frames in a documentation wrapper, but the actual content has no `@media` queries beyond the doc wrapper itself. No tablet breakpoint defined. No fluid layout between mobile width and desktop width.

**What to check:**
- Count `@media` queries; verify they apply to CONTENT, not just doc-wrapper stacking
- Are mobile / tablet / desktop breakpoints explicitly defined and documented?
- Does the content reflow gracefully at intermediate widths (768px, 1024px)?

**Verification:**
```bash
grep -nE "@media" <file>
```
Expect at least 2-3 content breakpoints (typical: 480/768/1024 or your design system's tokens). If only 1 query exists and it's for `.device-row { grid-template-columns: 1fr; }` (doc-wrapper only), the design has NO responsive content logic — flag as a code-readiness gap.

**Red flag thought:** "Mobile and desktop look right, so the responsive design is done." Two snapshots ≠ continuous responsive behavior. The doc-wrapper stacking is not the same as content reflow.

**Example failure (2026-05-12 calibration test):** Society file had 1 content `@media` query (`@media (max-width: 1100px)` for doc-wrapper grid). NSLS file had 1 (`@media (max-width: 1180px)` for doc-wrapper). Neither had tablet breakpoints or content-level responsive logic. Resolved by adding an explicit "Breakpoint specification" annotation block documenting intended breakpoints (mobile ≤767, tablet 768-1023, desktop ≥1024) so engineers translating to code have explicit intent.

---

## F15 — Fixed-px sizing dominates fluid units (accessibility scaling break)

**Pattern:** Layout, type, and spacing are defined in `px` instead of `rem`. Breaks WCAG 1.4.4 (Resize Text) for users who increase browser default font-size. Also harder to theme + scale.

**What to check:**
```bash
grep -oE "[0-9]+px" <file> | wc -l
grep -oE "[0-9.]+rem\b" <file> | wc -l
```
Aim for >50% rem-based for typography and spacing tokens. Px is acceptable for: borders (1-2px hairlines), exact-pixel decorative elements, container max-widths.

**Red flag thought:** "Px is precise; rem is for engineers." Px is precise but inaccessible. WCAG 1.4.4 needs text to scale to 200% without breaking. Rem scales with the user's chosen browser font-size; px doesn't.

**Example failure (2026-05-12 calibration test):** Society file: 314 px values, 0 rem. NSLS file: 309 px values, 0 rem. Both files have type, spacing, and layout entirely in px. Real WCAG 1.4.4 risk if a user increases browser font size.

---

## F16 — Form error/invalid states undefined

**Pattern:** Forms render inputs but have no styling for error/invalid states. No `.error`, `:invalid`, or `[aria-invalid]` CSS. No error-message containers. No `aria-describedby` linking error text to the failing input.

**What to check:**
```bash
grep -cE ":disabled|\.error|\.invalid|aria-invalid|\[aria-invalid\]" <file>
```
Expect > 0 if the design includes forms. WCAG 3.3.1 (Error Identification) + 3.3.3 (Error Suggestion) require visible + programmatic error indication.

**Red flag thought:** "Error states aren't visible in the happy-path mockup; I'll add them later." Forms ship with error states or they're not done. The validation logic depends on the styles existing.

**Example failure (2026-05-12 calibration test):** Both NSLS + Society mockups had 0 error/invalid state styles. All form fields rendered as the happy-path only. WCAG 3.3.1/3.3.3 unfulfillable without designed error visuals + linked aria-describedby messages.

---

## F17 — Missing `<main>` landmark + sparse ARIA on forms

**Pattern:** HTML has `<nav>`, `<header>`, `<section>`s but no `<main>` landmark. Forms have inputs without `aria-required`, `aria-describedby` (for helper text), `aria-invalid` (for errors). No `aria-live` regions for status messages.

**What to check:**
```bash
grep -c "<main\b" <file>          # expect 1
grep -oE 'aria-required' <file> | wc -l   # expect > 0 if form has required fields
grep -oE 'aria-describedby' <file> | wc -l  # expect > 0 if helper text exists
grep -oE 'aria-live' <file> | wc -l        # expect > 0 if status messages exist
```

WCAG 2.4.1 (Bypass Blocks) + 1.3.1 (Info and Relationships) — landmarks and ARIA are how screen readers navigate the page.

**Red flag thought:** "I have `<header>` and `<nav>` and `<section>`s — that's enough landmarks." `<main>` is the load-bearing one for "skip to main content." Without it, screen-reader users can't jump past the nav.

**Example failure (2026-05-12 calibration test):** Both NSLS + Society mockups: 0 `<main>` landmarks. 0 `aria-required` despite required-ish fields. 0 `aria-describedby` despite helper text (`.helper`, `.hint`). 0 `aria-live`. 7 aria-label (Society) and 6 (NSLS) — good coverage on icon buttons but the form semantics gap is real.

---

## F18 — Inline styles mixed with stylesheet (code-readiness concern)

**Pattern:** HTML elements have `style="..."` attributes mixing with class-based styles in the stylesheet. Makes refactoring harder, theme switching harder, and signals one-off decisions that should have been tokens.

**What to check:**
```bash
grep -oE 'style="[^"]*"' <file> | wc -l
```
Aim for < 5 inline styles in a production-ready mockup. Inline styles are acceptable for: programmatically-set values (e.g., progress bar widths), one-time demonstration overrides — but should be flagged if > 10.

**Red flag thought:** "I'll move the inline styles to CSS later — it doesn't affect rendering." It affects implementability and refactor cost. Engineers translating mockups to components have to find each one and decide whether it's a prop, a CSS var, or a class.

**Example failure (2026-05-12 calibration test):** Society file: 19 inline styles. NSLS file: 29 inline styles. Total 48 inline styles. Each represents a decision an engineer would have to make about how to extract it.

---

## F19 — Color tokens incomplete

**Pattern:** Stylesheet defines `:root { --color-X: ...; }` design tokens but the rest of the CSS uses a mix of `var(--color-X)` and hardcoded hex literals. Theme switching impossible. Brand-color updates require find-and-replace.

**What to check:**
```bash
grep -oE "#[0-9A-Fa-f]{3,6}" <file> | wc -l    # hex literals
grep -oE "var\(--[a-z-]+\)" <file> | wc -l      # var() refs
```
Aim for var() refs >> hex literals (rough target: >80% tokenized). Hex literals are acceptable for: brand logos (defined in SVG), payment provider colors (PayPal blue, Google brand colors), one-off illustration.

**Red flag thought:** "Some hex literals are fine, they're brand colors." Some are — payment provider colors, logo glyphs. Most aren't. If "Society Black" appears as `#1E1414` in 20 places, those should all be `var(--society-black)`.

**Example failure (2026-05-12 calibration test):** Society file: 39 hex literals vs 58 var() refs (only 60% tokenized). NSLS file: 41 hex literals vs 152 var() refs (79% tokenized — closer but still missing). Mostly the Apple Pay / Google Pay / PayPal brand colors are correctly hex (acceptable), but other one-off colors slip through.

---

## How this list grows

When a new failure mode emerges during real work, add it here with the same structure: pattern, what to check, verification, red flag thought, example failure dated.

The list should grow as the skill is used. A skill that doesn't accumulate failure modes is either being used rarely, being used uncritically, or being used by an agent that's not catching its own misses.
