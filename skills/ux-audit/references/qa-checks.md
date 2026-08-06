# QA Layer — functional build checks

The other three layers ask *"will this be hard to use?"* This one asks *"does it actually work?"* A page can score well on usability, UX and accessibility and still ship broken links, a layout that collapses at 768px, or a form with no error state.

Run these against the artifact you were given. For each check, **quote the result — never paraphrase.** If a check could not be run against this input, mark it `not auditable from this input` rather than passing it silently.

Finding prefix: `QA.<area>` — e.g. `QA.links`, `QA.responsive`, `QA.forms`.

---

## QA.links — destinations resolve and behave

- Every `href` resolves. Fetch each one; quote the status code. A 200 is a pass, a 3xx needs the final destination checked, 4xx/5xx is P0 if it's a primary CTA.
- No `href="#"`, `href=""`, or placeholder URLs (`example.com`, `TODO`, `lorem`) left in.
- External links carry `target="_blank"` **with** `rel="noopener noreferrer"`. `target="_blank"` without `rel` is a security finding, not a nit.
- Internal links use the app's client-side routing rather than forcing a full page reload, where the framework supports it.
- Anchor targets exist — every `href="#section"` has a matching `id`.

```bash
grep -oE 'href="[^"]*"' <file> | sort -u
```

## QA.responsive — real breakpoint logic, not doc-wrapper stacking

- Real `@media` queries acting on **content**, at minimum: mobile ≤767px, tablet 768–1023px, desktop ≥1024px.
- No horizontal scroll at 320px, 375px and 768px.
- Content parity across breakpoints — mobile is not a truncated desktop. No dropped bullets, links, or pricing. Differences must be deliberate and stated.
- Images carry `max-width: 100%`. Wide content (tables, code blocks, diagrams) scrolls inside its own container rather than pushing the page.
- If the artifact is a *demonstration* (side-by-side device frames) rather than production code, it must carry an explicit breakpoint specification block so engineers have unambiguous intent. See F14.

## QA.errors — nothing broken at runtime

- No console errors or warnings on load and on primary interaction.
- No failed network requests (404s on assets, blocked mixed content, CSP violations).
- No unresolved template variables rendered to the user (`{{ }}`, `undefined`, `NaN`, `[object Object]`).
- Images have real `src` values that load; none are broken.

## QA.targets — hit areas are usable

- Interactive targets ≥ **44×44 CSS px** (WCAG 2.5.5 AAA / practical mobile floor). 24×24 is the 2.2 AA minimum — treat 44 as the target and 24 as the hard fail.
- Adjacent targets have ≥ 8px separation so a thumb can't hit two.
- Nothing interactive sits under a fixed header/footer at any breakpoint.

## QA.forms — the unhappy path is designed

- Error and invalid states defined: `.error` / `:invalid` styling, a real error-message container, `aria-invalid` and `aria-describedby` wiring the message to the failing input. Happy-path-only forms fail WCAG 3.3.1 and 3.3.3. See F16.
- `aria-required` on required fields; `autocomplete` and `inputmode` set correctly (`email`, `tel`, `numeric`, `one-time-code`).
- Submit is guarded against double-fire while a request is in flight.
- Labels are real `<label for>` elements, not placeholder text doing double duty.

## QA.semantics — structure is machine-readable

- Exactly one `<main>` landmark wrapping the content; `<nav>`, `<header>`, `<footer>` used where they apply.
- Exactly one `<h1>`, and **no skipped levels in document order** — h1→h3 without h2 fails WCAG 1.3.1. This fails by ORDER even when the COUNT passes. See F11.
- `aria-live` regions for status messages (confirmations, error toasts).

```bash
grep -oE "<h[1-6]" <file> | sort | uniq -c    # count
```
Then walk the headings in document order and flag any `level > last + 1`.

## QA.code — handoff-ready, not demo-ready

- Inline `style="..."` attributes < 10; styling lives in the stylesheet. See F18.
- Colors reference tokens (`var(--token)`) rather than scattered hex literals. Third-party marks (Apple/Google/PayPal) are the legitimate exception. See F19.
- Critical typography and spacing in `rem`, not `px`, so user text scaling works (WCAG 1.4.4). See F15.
- No orphans after any removal — grep for stale references to removed elements, and for CSS class definitions whose HTML consumers are gone. See F13.

## QA.consistency — the artifact agrees with itself

- Rationale blocks, legends, tables of contents and annotations match the current state of the design, not a previous revision.
- Repeated components (cards, buttons, form rows) are actually consistent — same spacing, same weights, same corner radii.
- Adjacent components in a group can be told apart at a one-second glance. Two buttons at identical visual weight read as one control regardless of their labels. See F4.
- Terminology is used correctly and consistently for the moment it appears at. If a domain term's meaning is uncertain, ask rather than guess — mislabelling a state the user hasn't reached yet is a content-correctness bug, not a copy preference. See F5.

---

## What this layer is not

- **Not an automated scan.** axe-core, Lighthouse and WAVE catch programmatic issues this cannot. Run them alongside.
- **Not cross-browser testing.** Findings here are structural. Real Safari/Firefox/Chrome behavior needs real browsers.
- **Not a test suite.** This checks the artifact in front of you. It does not replace unit, integration or e2e tests.
