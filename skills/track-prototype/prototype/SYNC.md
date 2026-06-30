# Syncing the design kit from ignite-next

The prototype renders the REAL app's markup and CSS — not a hand-mirrored
approximation. Three things are extracted from ignite-next and committed here:

| Artifact | How it's produced | Committed where |
|---|---|---|
| `design-kit/app.css` | Real Tailwind v4 compile of the app's `globals.css` theme over the prototype markup corpus (`scripts/build-design-kit.mjs`) | `prototype/design-kit/app.css` |
| `design-kit/fonts/*` | Copied verbatim from `ignite-next/public/fonts` (the files `globals.css` declares: Hanken Grotesk variable, HermeneusOne, Rand 400/500/700) | `prototype/design-kit/fonts/` |
| Markup | Hand-transcribed from the app's components into `scripts/lib/render-substep.mjs` + `prototype/template.html` + `scripts/lib/runtime-classes.mjs` | source files |

`design-kit/proto.css` is the only hand-authored stylesheet: selected-state
mapping (`[aria-selected]` instead of React className toggles), the streaming
caret, confetti, carousel stack positions, watermark. Keep it tiny.

**Pinned source commit:** 31376f4526e9dcf8e452af4dd81121b30f8c9877
(also stamped in the header of `design-kit/app.css`)

> Re-synced 2026-06-30 across the ignite-next rebrand: the warm cream/charcoal
> palette (light `#faf7ef`, dark `#1e1414`, primary `#1e1414`) + HW Cigars
> display font replaced the old navy/coral + Hanken/Rand kit. `FONT_FILES` now
> lists the HW Cigars woff2s; body copy is Inter (Next-injected at runtime), so
> the static build falls back to a system grotesque via `--font-inter` in proto.css.

## Markup ↔ component map

| Prototype source | Real component(s) |
|---|---|
| `render-substep.mjs` screen skeleton | `SubStepRenderer.tsx` (layoutMode="page") |
| `render-substep.mjs` field renderers | `src/components/fields/*.tsx` |
| `render-substep.mjs` buttonClass() | `src/components/ui/button.tsx` (cva) |
| `render-substep.mjs` chat / celebration / generate / results | `ChatInterface.tsx`, `DeviceEmulator/CelebrationContent.tsx`, generate branch of `SubStepRenderer.tsx`, `AssessmentResults.tsx` |
| `render-substep.mjs` progress tracker | `PersonalityProgressTracker.tsx` (fallback variant) |
| `runtime-classes.mjs` (player-generated DOM) | `ChatInterface.tsx` bubbles, `MultiSelectInput.tsx` cards, `StackedCarousel.tsx` |
| `template.html` chrome | `TrackHeader.tsx` + `SubStepNavigation.tsx` + `page.tsx` `#main-grid-content` |

## Re-sync steps (when ignite-next changes)

1. `cd /path/to/ignite-next && git fetch && git log -1 --format=%H` — note the new SHA.
   (The local clone may be months stale — always fetch first.)
2. Diff the sources of truth since the pinned SHA:
   ```
   git -C <ignite-next> diff <pinned-sha>..HEAD -- \
     src/app/globals.css src/components/SubStepRenderer.tsx src/components/fields \
     src/components/ui/button.tsx src/components/ChatInterface.tsx \
     src/components/DeviceEmulator/CelebrationContent.tsx src/components/StackedCarousel.tsx \
     src/components/TrackHeader.tsx src/components/SubStepNavigation.tsx \
     "src/app/[trackSlug]/[...segments]/page.tsx" public/fonts
   ```
   Hand-update the corresponding renderer/template/runtime-classes markup for
   any changed classNames or structure (see the map above).
3. Recompile the design kit (one-time tool setup, then a single command):
   ```
   mkdir -p /tmp/twkit && cd /tmp/twkit && \
     npm i tailwindcss@4 @tailwindcss/cli@4 @tailwindcss/typography tailwindcss-animate
   node scripts/build-design-kit.mjs --app /path/to/ignite-next --tools /tmp/twkit
   ```
   This regenerates `design-kit/app.css` (theme + utilities for every class the
   renderer/template/player can emit) and refreshes `design-kit/fonts/`.
   A non-empty `git diff` on app.css is your drift alarm.
4. `node --test scripts/**/*.test.mjs` — markup assertions catch accidental drift.
5. Build a real track and walk it:
   ```
   node scripts/build-prototype.mjs track.json --out /tmp/build \
     --assets <ignite-next>/public [--proxy-url … --proxy-token …]
   npx --yes serve -l 4173 /tmp/build
   node scripts/walk-gallery.mjs http://localhost:4173 /tmp/walk
   ```
   `report.json.problems` must be empty; eyeball the screenshots against the app.
6. Update the pinned SHA above (the app.css header updates automatically).

## Builds stay dependency-free

`build-prototype.mjs` only COPIES the committed design kit — Tailwind is needed
exclusively at authoring time (step 3). Never add a package.json to the skill.

## Real images & videos

Tracks reference app assets by root-relative URL (`/img/...`, `/video/...`).
Pass `--assets <ignite-next>/public` to `build-prototype.mjs` and it copies
ONLY the referenced files into the build (collectAssetPaths/copyTrackAssets),
preserving paths. Missing files are reported, never fatal. Without `--assets`
the build logs how many references will 404.

## Known divergences from the app (accepted, static-player limits)

- **fieldType `select`** renders a styled native `<select>` (the app uses a
  Radix dropdown). Carries `data-input` — walkers use the fill path.
- **dropdown-with-checkboxes** renders a static wheel SVG + a 0-10 pill scale
  (the app's ProfileWheel slider is canvas-interactive); answer capture is the
  joined pill/checkbox selection, not the app's JSON shape.
- **dream-job accordions** use native `<details>`; tapping the header also
  selects (the app selects only via the inner button).
- **education/work** forms are visually faithful but capture a single text
  value (the school/company field) instead of structured entries.
- **markdown** in generate/chat output renders as plain text (no react-markdown).
- **framer-motion** transitions are approximated with CSS keyframes; confetti is
  a CSS approximation of react-confetti-explosion.

## Vendored assessment scoring data

`scripts/data/assessment-scoring-weights.json` and `scripts/data/assessment-types.json`
are COPIED VERBATIM from ignite-next `src/data/`. The build bakes them into
`window.__ASSESSMENT__` so the player can compute real personality results client-side
(`scripts/lib/assessment-score.mjs`, a faithful port of `src/services/assessmentComputation.ts`
+ `src/lib/assessmentUtils.ts`). The results screen renders them with the real
`StackedCarousel` markup (colored framework headers, stacked cards, dots).
Re-copy both files when the app updates its scoring weights or framework
descriptions. The join is by `answerId` (matches production) — never by option
text: in the Clarity track only ~50/84 option texts match a weights `optionText`,
but ~81/84 answerIds match.

### `big5.introversion` is intentionally dropped (faithful to prod)

The vendored weights carry 4 `"introversion": 0.9` big5 entries. The scorer does
NOT count them — and neither does production. `assessmentComputation.ts`
initializes big5 with exactly `{openness, conscientiousness, extraversion,
agreeableness, neuroticism}` and tallies with `if (key in scores.big5)`, so
`introversion` is a dead key in the app too (its only use is these data rows;
there is no introversion→negative-extraversion mapping). We mirror that exactly:
the preview must reflect production, not "fix" it. Do not add an `introversion`
key to `emptyScores()` and do not edit the vendored JSON.
