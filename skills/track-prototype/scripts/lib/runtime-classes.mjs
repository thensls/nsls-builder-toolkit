// Class strings for markup the PLAYER generates at runtime (chat bubbles,
// inherited option grids, assessment carousel). Shared between:
//   - player.js (browser, copied into the build) — builds the DOM with them
//   - render-substep.mjs (build time) — uses the same strings for baked markup
//   - build-design-kit.mjs (authoring time) — includes them in the Tailwind
//     scan corpus so the compiled app.css contains every runtime class.
//
// These class lists are mirrored from the REAL ignite-next components
// (ChatInterface.tsx, MultiSelectInput.tsx, StackedCarousel.tsx). If the app
// changes its classes, update here and re-run scripts/build-design-kit.mjs.
//
// No DOM, no imports — safe in node tests and the browser.

// --- Chat (ChatInterface.tsx) -----------------------------------------------
export const CHAT_ROW_USER = "flex justify-end";
export const CHAT_ROW_AI = "flex justify-start";
// tp-bubble / tp-bubble-* are walker contract classes; the rest mirrors the app.
export const CHAT_BUBBLE_USER =
  "tp-bubble tp-bubble-user max-w-[90%] text-base px-4 py-4 rounded-xl bg-dark text-light rounded-br-none!";
export const CHAT_BUBBLE_AI =
  "tp-bubble tp-bubble-ai max-w-[90%] text-base px-4 py-4 rounded-xl bg-medium text-dark hover:bg-medium/90 rounded-tl-none!";

// --- Multi-select grid buttons (MultiSelectInput.tsx) ------------------------
// Used both for baked options and for options the player populates at runtime
// from an upstream answer (optionsSourceSlug narrowing). Selected state is
// driven by [aria-selected="true"] via design-kit/proto.css.
export const MS_OPTION =
  "tp-ms relative flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all border-medium bg-medium/25 hover:border-mocha hover:bg-medium cursor-pointer";
export const MS_TITLE = "text-base font-semibold text-left text-dark";
export const MS_DESC = "text-sm mt-1 text-left text-dark/50";
export const MS_CHECK_WRAP = "tp-check absolute top-2 right-2";
// Selected badge — green circle (MultiSelectInput.tsx uses bg-green, no shadow).
export const MS_CHECK_BADGE =
  "w-5 h-5 rounded-full bg-green flex items-center justify-center";
// Inline check (stroke) used inside the badge — mirrors the app's inline svg.
export const MS_CHECK_SVG =
  '<svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/></svg>';

// Build one multi-select option button (player + renderer share this).
// `escape` is injected because the player and the renderer carry their own
// HTML escapers (player.js must stay standalone in the browser).
export function msOptionHtml(text, index, escape) {
  const e = escape;
  return `<button type="button" class="${MS_OPTION}" style="min-height:120px" data-option data-value="${e(text)}" data-index="${index}"><div class="flex flex-col items-start w-full"><span class="${MS_TITLE}">${e(text)}</span></div><div class="${MS_CHECK_WRAP}"><div class="${MS_CHECK_BADGE}">${MS_CHECK_SVG}</div></div></button>`;
}

// --- Assessment results carousel (StackedCarousel.tsx) -----------------------
export const CAROUSEL_WRAP = "relative w-full max-w-xl mx-auto px-4 mt-12 mb-12";
export const CAROUSEL_DECK = "relative w-full overflow-visible grid grid-cols-1";
export const CAROUSEL_CARD =
  "col-start-1 row-start-1 mx-auto w-[85%] rounded-xl bg-medium shadow-lg transition-all duration-500 ease-in-out";
export const CAROUSEL_CARD_INNER = "w-full border-0 overflow-hidden rounded-xl";
export const CAROUSEL_TITLE_BASE = "m-0 p-4 text-xl font-bold text-center";
export const CAROUSEL_BODY = "flex flex-col items-center justify-center p-6";
export const CAROUSEL_RESULT =
  "text-dark text-center font-bold mb-2 max-w-[275px] text-pretty text-xl";
export const CAROUSEL_RESULT_SMALL =
  "text-dark text-center font-bold mb-2 max-w-[275px] text-pretty text-base";
export const CAROUSEL_DESC = "text-center text-dark";
export const CAROUSEL_ARROW_LEFT =
  "text-primary absolute top-1/2 left-0 z-40 -translate-y-1/2 cursor-pointer";
export const CAROUSEL_ARROW_RIGHT =
  "text-primary absolute top-1/2 right-0 z-40 -translate-y-1/2 cursor-pointer";
export const CAROUSEL_DOTS = "mt-6 flex justify-center gap-2";
export const CAROUSEL_DOT = "h-2.5 w-2.5 rounded-full transition-all bg-mediumPlus hover:bg-mediumPlus/80";
export const CAROUSEL_DOT_ACTIVE = "h-2.5 rounded-full transition-all bg-primary w-6";

// Framework color → header classes (StackedCarousel getColorClass).
export const CAROUSEL_COLOR_CLASSES = {
  "myers-briggs": "bg-myersBriggs text-myersBriggs-contrast",
  enneagram: "bg-enneagram text-enneagram-contrast",
  "holland-code": "bg-hollandCode text-hollandCode-contrast",
  disc: "bg-disc text-disc-contrast",
  "big-five": "bg-bigFive text-bigFive-contrast",
};
export const CAROUSEL_COLOR_FALLBACK = "bg-gray-600 text-white";

// Stack position classes (transforms live in design-kit/proto.css because they
// use arbitrary values the app expresses inline via framer/tailwind).
export const POS_ACTIVE = "tp-pos-active";
export const POS_NEXT = "tp-pos-next";
export const POS_PREV = "tp-pos-prev";
export const POS_HIDDEN = "tp-pos-hidden";

// Every class above as one HTML comment-ish blob for the Tailwind scanner.
// build-design-kit.mjs writes this into the corpus so runtime-only classes
// (never present in baked screens) still get compiled into app.css.
export function runtimeClassCorpus() {
  const all = [
    CHAT_ROW_USER, CHAT_ROW_AI, CHAT_BUBBLE_USER, CHAT_BUBBLE_AI,
    MS_OPTION, MS_TITLE, MS_DESC, MS_CHECK_WRAP, MS_CHECK_BADGE,
    // NOTE: MS_CHECK_SVG is an <svg> markup fragment, not a class string — it's
    // excluded here (its inner classes are scanned via the rendered markup corpus).
    CAROUSEL_WRAP, CAROUSEL_DECK, CAROUSEL_CARD, CAROUSEL_CARD_INNER,
    CAROUSEL_TITLE_BASE, CAROUSEL_BODY, CAROUSEL_RESULT, CAROUSEL_RESULT_SMALL,
    CAROUSEL_DESC, CAROUSEL_ARROW_LEFT, CAROUSEL_ARROW_RIGHT,
    CAROUSEL_DOTS, CAROUSEL_DOT, CAROUSEL_DOT_ACTIVE,
    ...Object.values(CAROUSEL_COLOR_CLASSES), CAROUSEL_COLOR_FALLBACK,
  ];
  return `<div class="${all.join(" ").replace(/"/g, "'")}"></div>`;
}
