# Syncing the design kit from ignite-next

The design kit is HAND-MIRRORED from ignite-next and drifts. Re-sync when the app's
visual language changes.

**Pinned source commit:** ad6bf06edecb1d2fcfd7dbf7408d28cfb45112e4

## Steps
1. `cd /path/to/ignite-next && git fetch && git log -1 --format=%H` — note the new SHA.
   (The local clone may be months stale — always fetch first.)
2. Regenerate tokens:
   `node scripts/extract-tokens.mjs --from <ignite-next>/src/app/globals.css --out prototype/design-kit/tokens.css`
   A non-empty `git diff` on tokens.css is your drift alarm.
   (Note: the extractor pulls the brand palette from BOTH the `:root` blocks and the
   `@theme inline` block's direct-hex properties — see extract-tokens.mjs.)
3. Diff the renderers since the pinned SHA:
   `git -C <ignite-next> diff <pinned-sha>..HEAD -- src/components/SubStepRenderer.tsx src/components/fields src/components/ui/button.tsx src/app/globals.css`
   Hand-update `components.css` / `render-substep.mjs` for any changed classNames.
4. Re-run the gallery through a browser (serve `prototype/design-kit/` and screenshot `gallery.html`) and eyeball.
   For a fuller check, build a real track and drive it with `scripts/walk.mjs` (requires Playwright — see its header).
5. Update the pinned SHA above and the watermark date.

## What is mechanical vs hand-authored
- Mechanical (re-run extract-tokens): colors, radius, font vars.
- Hand-authored (diff + edit): component CSS, substep routing.

## Vendored assessment scoring data
`scripts/data/assessment-scoring-weights.json` and `scripts/data/assessment-types.json`
are COPIED VERBATIM from ignite-next `src/data/`. The build bakes them into
`window.__ASSESSMENT__` so the player can compute real personality results client-side
(`scripts/lib/assessment-score.mjs`, a faithful port of `src/services/assessmentComputation.ts`
+ `src/lib/assessmentUtils.ts`). Re-copy both files when the app updates its scoring weights
or framework descriptions. The join is by `answerId` (matches production) — never by option
text: in the Clarity track only ~50/84 option texts match a weights `optionText`, but ~81/84
answerIds match.
