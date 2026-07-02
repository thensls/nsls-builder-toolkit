import { flattenSubsteps, nextIndex, prevIndex, clampIndex, progressPct } from "./player-core.mjs";
import { interpolate } from "./interpolate.mjs"; // build copies interpolate.mjs alongside player.js (see build-prototype.mjs)
import { scoreAssessment, resolveAnswerIds, buildCards } from "./assessment-score.mjs"; // build copies it alongside player.js
import {
  CHAT_ROW_USER, CHAT_ROW_AI, CHAT_BUBBLE_USER, CHAT_BUBBLE_AI, msOptionHtml,
  CAROUSEL_WRAP, CAROUSEL_DECK, CAROUSEL_CARD, CAROUSEL_CARD_INNER,
  CAROUSEL_TITLE_BASE, CAROUSEL_BODY, CAROUSEL_RESULT, CAROUSEL_RESULT_SMALL, CAROUSEL_DESC,
  CAROUSEL_ARROW_LEFT, CAROUSEL_ARROW_RIGHT, CAROUSEL_DOTS, CAROUSEL_DOT, CAROUSEL_DOT_ACTIVE,
  CAROUSEL_COLOR_CLASSES, CAROUSEL_COLOR_FALLBACK,
  POS_ACTIVE, POS_NEXT, POS_PREV, POS_HIDDEN,
} from "./runtime-classes.mjs"; // build copies it alongside player.js

const KEY = "tp.v1";
const track = window.__TRACK__;            // injected by build (the full track object)
const screens = window.__SCREENS__;        // injected by build: array of pre-rendered HTML strings
const subs = flattenSubsteps(track);
// Synthetic prerequisite profile: { slug: { value, from } } from prerequisite
// tracks, seeded so cross-track generate/chat steps resolve in the demo. The
// prompt-context note labels these as synthetic; real answers override them.
const prereqProfile = window.__PREREQ_PROFILE__ || {};
const prereqValues = Object.fromEntries(
  Object.entries(prereqProfile).map(([slug, meta]) => [slug, meta && meta.value]));
// Slugs this track collects/produces itself — used to tell "entered this demo"
// from "synthetic prerequisite" in the context note.
const ownSlugs = new Set(subs.map((s) => s && s.slug).filter(Boolean));
const root = document.getElementById("tp-body");
const bar = document.getElementById("tp-progress-bar");

let state = load();
let chatInFlight = false;  // true while a chat stream is running — prevents double-sends
let aiController = null;   // AbortController for the current in-flight AI stream (generate or chat)
let autoTimer = null;      // pending auto-progress timer (image-multiselect autoProgressOnSelect)

function load() {
  // Seed synthetic prerequisite values as the base; real answers (entered this
  // run, restored from localStorage) always override them.
  try {
    const s = JSON.parse(localStorage.getItem(KEY));
    if (s) return { i: clampIndex(s.i, subs.length), answers: { ...prereqValues, ...(s.answers || {}) }, chat: s.chat || {} };
  } catch { /* corrupt — fall through */ }
  return { i: 0, answers: { ...prereqValues }, chat: {} };
}
function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }

// NOTE: this hand-rolled HTML escaper intentionally duplicates `esc` in
// render-substep.mjs. player.js runs in the browser as a standalone copied
// file and does not import the render module. Keep the two in sync.
const escapeHtml = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Chat prompts may return JSON like { "feedback": "...", "freeChat": "..." } —
// the app displays only the freeChat portion (ChatInterface extractDisplayContent).
function extractDisplayContent(content) {
  const trimmed = String(content || "").trim();
  if (!trimmed.startsWith("{")) return content;
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed.freeChat === "string") return parsed.freeChat;
  } catch { /* not valid JSON — show as-is */ }
  return content;
}

// ---------------------------------------------------------------------------
// Streaming helper
// ANY failure returns false so the caller can keep/restore the baked sample.
// ---------------------------------------------------------------------------
async function streamFromProxy(body, onDelta, signal) {
  const p = window.__PROXY__; if (!p) return false;
  try {
    const res = await fetch(p.url + "/api/generate", { method: "POST",
      headers: { "Content-Type": "application/json", "X-Proxy-Token": p.token || "" }, body: JSON.stringify(body), signal });
    if (!res.ok || !res.body) return false;
    const reader = res.body.getReader(); const dec = new TextDecoder();
    for (;;) { const { value, done } = await reader.read(); if (done) break; onDelta(dec.decode(value, { stream: true })); }
    const tail = dec.decode(); if (tail) onDelta(tail);   // flush any trailing multi-byte char
    return true;
  } catch { return false; }   // ANY failure (incl. AbortError) → caller keeps the baked sample (critical)
}

// ---------------------------------------------------------------------------
// Render + wire
// ---------------------------------------------------------------------------
function render() {
  root.innerHTML = interpolate(screens[state.i], state.answers); // fill {slug} live
  bar.style.width = progressPct(state.i, subs.length) + "%";
  populateInheritedOptions(); // narrowing pattern: build options from a prior answer
  wire();
  // Kick off AI after the screen is visible (non-blocking)
  maybeRunGenerateAI();
  wireChatAI();
  // Compute + render the real personality scores when an assessment-results screen shows
  maybeRunAssessmentResults();
  // Author aid: show what data fed an AI step, grouped real vs synthetic-prereq.
  renderPromptContextNote();
}

// ---------------------------------------------------------------------------
// Prompt-context note — a sticky on generate/chat screens listing the profile
// fields feeding the prompt, grouped by origin (entered this demo vs synthetic
// prerequisite). Lets the track author confirm the context behind the AI output
// they're seeing. It is the live-demo twin of the prompt-pack data object.
// ---------------------------------------------------------------------------
function renderPromptContextNote() {
  const sub = subs[state.i];
  if (!sub || (sub.type !== "generate" && sub.type !== "chat")) return;
  const entered = [], synthetic = [];
  for (const [slug, val] of Object.entries(state.answers)) {
    if (val == null || val === "") continue;
    if (ownSlugs.has(slug)) entered.push([slug, val]);
    else if (prereqProfile[slug]) synthetic.push([slug, val, (prereqProfile[slug] || {}).from]);
  }
  // v1 grounds GENERATE substeps only (the generate POST forwards the spec; chat
  // does not). Only claim "grounded" where it's actually true.
  const groundingSpec = sub.type === "generate" ? sub.aiPromptConfig?.grounding : null;
  if (!entered.length && !synthetic.length && !groundingSpec) return;
  const clip = (v) => { const s = String(v); return escapeHtml(s.length > 70 ? s.slice(0, 67) + "…" : s); };
  const group = (title, rows) => rows.length
    ? `<div style="margin-top:6px"><div style="font-weight:600;opacity:.7;text-transform:uppercase;letter-spacing:.04em;font-size:9px">${title}</div>`
      + rows.map((r) => `<div style="margin-top:2px"><code style="opacity:.85">${escapeHtml(r[0])}</code> = ${clip(r[1])}`
        + (r[2] ? ` <em style="opacity:.6">(${escapeHtml(r[2])})</em>` : "") + `</div>`).join("") + `</div>`
    : "";
  const note = document.createElement("div");
  note.className = "tp-context-note";
  note.setAttribute("style",
    "position:fixed;right:12px;bottom:12px;max-width:300px;max-height:45vh;overflow:auto;z-index:50;"
    + "background:#fffbe6;border:1px solid #e6d9a8;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.15);"
    + "padding:10px 12px;font-size:11px;line-height:1.35;color:#3d2f1f;font-family:system-ui,sans-serif");
  // Grounded line: this substep pulls REAL cited figures (via the proxy) for the
  // mapped major, so the numbers in the output are real, not model-guessed.
  let groundedBlock = "";
  if (groundingSpec) {
    const majorSlug = groundingSpec.from?.major;
    const majorVal = majorSlug ? state.answers[majorSlug] : null;
    groundedBlock = `<div style="margin-top:6px"><div style="font-weight:600;opacity:.7;text-transform:uppercase;letter-spacing:.04em;font-size:9px">Grounded — real data</div>`
      + `<div style="margin-top:2px">🔎 Real BLS figures injected for `
      + `<code style="opacity:.85">${escapeHtml(majorVal || majorSlug || "major")}</code></div></div>`;
  }
  note.innerHTML = `<div style="font-weight:700;font-size:11px;margin-bottom:2px">📌 Prompt context note</div>`
    + `<div style="opacity:.6;font-size:10px;margin-bottom:4px">Data behind this AI output</div>`
    + group("Entered in this demo", entered)
    + group("Synthetic — prerequisite", synthetic)
    + groundedBlock;
  root.appendChild(note);
}

// ---------------------------------------------------------------------------
// Assessment results — compute-on-render (mirrors maybeRunGenerateAI).
// Scores the user's chosen answers client-side from window.__ASSESSMENT__
// (weights + types, baked by the build) and renders the REAL stacked-carousel
// markup (StackedCarousel.tsx) into [data-assessment-results].
// ---------------------------------------------------------------------------
function maybeRunAssessmentResults() {
  const sub = subs[state.i];
  if (!sub || sub.fieldType !== "assessment-results") return;
  const out = root.querySelector("[data-assessment-results]");
  if (!out) return;

  const data = window.__ASSESSMENT__;
  if (!data || !Array.isArray(data.weights)) {
    out.textContent = "Assessment scoring data not available in this preview.";
    return;
  }

  const answerIds = resolveAnswerIds(track, state.answers);
  if (answerIds.length === 0) {
    out.textContent = "Complete the personality questions to see your results.";
    return;
  }

  const results = scoreAssessment({ answerIds, weights: data.weights, types: data.types });
  const cards = results.cards || buildCards(results, data.types || {});
  renderAssessmentCarousel(out, cards);

  // Expose the computed profile as a {slug} value so downstream substeps (e.g. the
  // coach chat's {your-personality-profile}) interpolate the real summary instead of
  // rendering the literal token. Mirrors the app, where the profile is available to
  // the coach. Always overwrite: this slug is only ever the computed profile (never a
  // user-typed answer), so a revisit after changing earlier answers must refresh it to
  // match the recomputed carousel — not keep a stale summary.
  if (sub.slug) {
    state.answers[sub.slug] = cards
      .map((c) => `${c.title}: ${c.result}`)
      .join("; ");
  }
}

// Stacked carousel — mirrors StackedCarousel.tsx (active/next/prev card stack,
// arrows, dots). Position transforms live in design-kit/proto.css.
function renderAssessmentCarousel(out, cards) {
  const colorCls = (c) => CAROUSEL_COLOR_CLASSES[c] || CAROUSEL_COLOR_FALLBACK;
  const cardHtml = (c) =>
    `<div class="tp-result-card ${CAROUSEL_CARD} ${POS_HIDDEN}">` +
    `<div class="${CAROUSEL_CARD_INNER}">` +
    `<h3 class="${CAROUSEL_TITLE_BASE} ${colorCls(c.color)}">${escapeHtml(c.title)}</h3>` +
    `<div class="${CAROUSEL_BODY}">` +
    `<div class="${c.title === "Big Five" ? CAROUSEL_RESULT_SMALL : CAROUSEL_RESULT}" style="white-space:pre-line">${escapeHtml(c.result)}</div>` +
    `<div class="${CAROUSEL_DESC}">${escapeHtml(c.description)}</div>` +
    `</div></div></div>`;

  const ARROW_L = '<svg class="h-10 w-10 hover:opacity-80" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24Zm32.49,140.49a12,12,0,0,1-17,17l-48-48a12,12,0,0,1,0-17l48-48a12,12,0,0,1,17,17L121,125Z" transform="translate(8 3)"/></svg>';
  const ARROW_R = '<svg class="h-10 w-10 hover:opacity-80" viewBox="0 0 256 256" fill="currentColor"><path d="M128,24A104,104,0,1,0,232,128,104.11,104.11,0,0,0,128,24ZM160.49,133.49l-48,48a12,12,0,0,1-17-17L135,124,95.51,85.49a12,12,0,0,1,17-17l48,48A12,12,0,0,1,160.49,133.49Z" transform="translate(-8 3)"/></svg>';

  out.innerHTML =
    `<div class="${CAROUSEL_WRAP}">` +
    `<div class="${CAROUSEL_DECK}">${cards.map(cardHtml).join("")}</div>` +
    `<div class="${CAROUSEL_ARROW_LEFT}" data-carousel-prev>${ARROW_L}</div>` +
    `<div class="${CAROUSEL_ARROW_RIGHT}" data-carousel-next>${ARROW_R}</div>` +
    `<div class="${CAROUSEL_DOTS}">${cards.map((_, i) =>
      `<button class="${CAROUSEL_DOT}" data-carousel-dot="${i}" aria-label="Go to slide ${i + 1}"></button>`).join("")}</div>` +
    `</div>`;

  const els = [...out.querySelectorAll(".tp-result-card")];
  const dots = [...out.querySelectorAll("[data-carousel-dot]")];
  let active = 0;
  const apply = () => {
    const n = els.length;
    els.forEach((el, i) => {
      const diff = (i - active + n) % n;
      el.classList.remove(POS_ACTIVE, POS_NEXT, POS_PREV, POS_HIDDEN);
      el.classList.add(diff === 0 ? POS_ACTIVE : diff === 1 ? POS_NEXT : diff === n - 1 ? POS_PREV : POS_HIDDEN);
    });
    dots.forEach((d, i) => { d.className = i === active ? CAROUSEL_DOT_ACTIVE : CAROUSEL_DOT; d.setAttribute("data-carousel-dot", i); });
  };
  out.querySelector("[data-carousel-prev]")?.addEventListener("click", () => { active = (active - 1 + els.length) % els.length; apply(); });
  out.querySelector("[data-carousel-next]")?.addEventListener("click", () => { active = (active + 1) % els.length; apply(); });
  dots.forEach((d, i) => d.addEventListener("click", () => { active = i; apply(); }));
  apply();
}

// ---------------------------------------------------------------------------
// Narrowing pattern (optionsSourceSlug): a substep with no inline options
// inherits its choices from the answer the user picked for an upstream slug
// (e.g. pick 12 values, then narrow to 8, then 6). Those options can't be baked
// at build time — populate the empty grid here from state.answers, using the
// REAL MultiSelectInput card markup (shared via runtime-classes.mjs).
// ---------------------------------------------------------------------------
function populateInheritedOptions() {
  const grid = root.querySelector("[data-options-source]");
  if (!grid || grid.querySelector("[data-option]")) return; // already has options
  const sourceSlug = grid.dataset.optionsSource;
  const upstream = state.answers[sourceSlug];
  const values = Array.isArray(upstream)
    ? upstream
    : (typeof upstream === "string" && upstream ? upstream.split(", ") : []);
  grid.innerHTML = values.map((text, i) => msOptionHtml(text, i, escapeHtml)).join("");
}

function captureCurrent() {
  const input = root.querySelector("[data-input]");
  if (input && input.dataset.slug) state.answers[input.dataset.slug] = input.value.trim();
  const grid = root.querySelector("[data-slug][data-multi]");
  if (grid) {
    const chosen = [...grid.querySelectorAll('[data-option][aria-selected="true"]')].map((b) => b.dataset.value);
    // De-dupe: dream-job accordions render two data-option elements per value
    // (summary + Select button); selecting both must not double-count.
    state.answers[grid.dataset.slug] = [...new Set(chosen)].join(", "); // always write — empty when deselected, so stale data clears
  }
}

function advance() { clearTimeout(autoTimer); captureCurrent(); state.i = nextIndex(state.i, subs.length); persist(); aiController?.abort(); chatInFlight = false; render(); }
function back() { clearTimeout(autoTimer); captureCurrent(); state.i = prevIndex(state.i, subs.length); persist(); aiController?.abort(); chatInFlight = false; render(); }

// Live "Selected: N / M required" status for multi-select grids (mirrors the
// validation block in MultiSelectInput.tsx).
function updateMsStatus() {
  const status = root.querySelector("[data-ms-status]");
  const grid = root.querySelector("[data-slug][data-multi]");
  if (!status || !grid) return;
  const count = grid.querySelectorAll('[data-option][aria-selected="true"]').length;
  const countEl = status.querySelector("[data-ms-count]");
  if (countEl) countEl.textContent = String(count);
  const min = parseInt(status.dataset.min, 10);
  const max = parseInt(status.dataset.max, 10);
  const okMin = Number.isNaN(min) || count >= min;
  const okMax = Number.isNaN(max) || count <= max;
  const msgEl = status.querySelector("[data-ms-msg]");
  if (msgEl) {
    msgEl.textContent = !okMin ? `Please select at least ${min} option${min !== 1 ? "s" : ""}`
      : !okMax ? `Please select at most ${max} option${max !== 1 ? "s" : ""}`
      : "Great — selection complete";
  }
  status.classList.toggle("is-valid", okMin && okMax);
}

function wire() {
  // Wire EVERY [data-next] (collect screens can have Continue + Skip)
  root.querySelectorAll("[data-next]").forEach((btn) => btn.addEventListener("click", advance));
  document.getElementById("tp-back")?.toggleAttribute("disabled", state.i === 0);
  root.querySelectorAll("[data-option]").forEach((opt) => opt.addEventListener("click", (e) => {
    const grid = opt.closest("[data-slug]");
    if (!grid) return;
    const multi = grid.dataset.multi === "true";
    const wasSelected = opt.getAttribute("aria-selected") === "true";
    if (!multi) grid.querySelectorAll("[data-option]").forEach((o) => o.setAttribute("aria-selected", "false"));
    opt.setAttribute("aria-selected", wasSelected ? "false" : "true");
    // Mirror the selection onto twin elements with the same value (dream-job
    // accordions carry data-option on both the header and the Select button).
    const v = opt.dataset.value;
    grid.querySelectorAll(`[data-option]`).forEach((o) => {
      if (o !== opt && o.dataset.value === v) o.setAttribute("aria-selected", opt.getAttribute("aria-selected"));
    });
    updateMsStatus();
    // Auto-progress (image-multiselect autoProgressOnSelect): the app advances
    // ~300ms after the pick. advance() clears the timer, so a manual Continue
    // (or the walker) can never double-advance.
    if (grid.dataset.autoProgress === "true" && opt.getAttribute("aria-selected") === "true") {
      clearTimeout(autoTimer);
      autoTimer = setTimeout(advance, 300);
    }
  }));
  // Suggestion chips fill the text input (TextFieldInput suggestions)
  root.querySelectorAll("[data-suggestion]").forEach((btn) => btn.addEventListener("click", () => {
    const input = root.querySelector("[data-input]");
    if (input) { input.value = btn.dataset.suggestion; input.focus(); }
  }));
  // Enter submits a single-line <input>; in the multi-line text <textarea> a bare
  // Enter must insert a newline (Shift+Enter still does), so only Cmd/Ctrl+Enter advances.
  root.querySelector("[data-input]")?.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const isTextarea = e.target.tagName === "TEXTAREA";
    if (isTextarea && !(e.metaKey || e.ctrlKey)) return; // newline in textarea
    e.preventDefault(); advance();
  });
}

// ---------------------------------------------------------------------------
// Generate auto-run
// After rendering a generate substep, stream from proxy if available.
// Falls back to the baked sample on any failure.
// ---------------------------------------------------------------------------
async function maybeRunGenerateAI() {
  const sub = subs[state.i];
  if (!sub || sub.type !== "generate") return;
  if (!window.__PROXY__) return;

  const out = root.querySelector(".tp-ai-output") || root.querySelector(".tp-ai-placeholder");
  if (!out) return;

  const bakedText = out.textContent;
  out.textContent = "";
  out.classList.add("is-writing");

  aiController?.abort();
  aiController = new AbortController();

  const ok = await streamFromProxy(
    // `grounding` (if the substep declares it) lets the proxy inject REAL cited
    // labor-market figures into the template before the AI call — the value-moment
    // grounding companion. Omitted → the proxy forwards the template unchanged.
    { type: "generate", template: sub.aiPromptConfig?.template || sub.prompt, profile: state.answers, grounding: sub.aiPromptConfig?.grounding },
    (d) => { out.textContent += d; },
    aiController.signal
  );

  out.classList.remove("is-writing");
  if (ok) {
    out.classList.add("is-live"); // streamed content must not keep placeholder styling
  } else {
    // Fallback: restore the baked sample (critical guarantee)
    out.classList.remove("is-live");
    out.textContent = bakedText;
  }
}

// ---------------------------------------------------------------------------
// Multi-turn chat wiring
// Wires data-chat-send (and Enter on data-chat-input) for the current screen.
// Maintains state.chat[slug] (array of {role, content}) persisted to localStorage.
// ---------------------------------------------------------------------------
function wireChatAI() {
  const sub = subs[state.i];
  if (!sub || sub.type !== "chat") return;

  const chatEl = root.querySelector("[data-chat]");
  if (!chatEl) return;

  const slug = chatEl.dataset.slug || sub.slug || String(state.i);
  const log = chatEl.querySelector("[data-chat-log]");
  const inputEl = root.querySelector("[data-chat-input]");
  const sendBtn = root.querySelector("[data-chat-send]");
  if (!log || !inputEl || !sendBtn) return;

  // Initialise history from persisted state (replay bubbles from history on revisit)
  state.chat = state.chat || {};
  if (!state.chat[slug]) state.chat[slug] = [];

  // Replay any history that isn't already in the static HTML (user returned to this screen)
  // The static HTML already has the seed bubble(s); only replay extra turns.
  const history = state.chat[slug];
  if (history.length > 0) {
    history.forEach(({ role, content }) => appendBubble(log, role, content));
  }

  async function sendMessage() {
    if (chatInFlight) return;
    const text = inputEl.value.trim();
    if (!text) return;

    // Add user bubble immediately
    appendBubble(log, "user", text);
    state.chat[slug].push({ role: "user", content: text });
    inputEl.value = "";

    if (!window.__PROXY__) {
      // No proxy — show a static fallback inline and persist the turn
      const fallbackText = "(Preview AI unavailable — proxy not configured.)";
      appendBubble(log, "assistant", fallbackText);
      state.chat[slug].push({ role: "assistant", content: fallbackText });
      persist();
      return;
    }

    // Lock UI
    chatInFlight = true;
    inputEl.disabled = true;
    sendBtn.disabled = true;

    // Create empty AI bubble for streaming
    const aiBubble = appendBubble(log, "assistant", "");
    aiBubble.classList.add("is-writing");

    // Build messages array including the user turn we just pushed
    const messages = [...state.chat[slug]]; // already has the user turn

    aiController?.abort();
    aiController = new AbortController();

    const ok = await streamFromProxy(
      { type: "chat", system: sub.chatSystemPrompt, profile: state.answers, messages },
      (d) => { aiBubble.textContent += d; },
      aiController.signal
    );

    aiBubble.classList.remove("is-writing");

    if (ok) {
      // Mirror the app: if the model returned {feedback, freeChat} JSON, show
      // (and persist) only the freeChat text once the stream is complete.
      const display = extractDisplayContent(aiBubble.textContent);
      aiBubble.textContent = display;
      state.chat[slug].push({ role: "assistant", content: display });
    } else {
      // Fallback: replace empty bubble with something useful
      const fallback = "(preview AI unavailable)";
      aiBubble.textContent = fallback;
      state.chat[slug].push({ role: "assistant", content: fallback });
    }

    persist();

    // Unlock UI
    chatInFlight = false;
    inputEl.disabled = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); sendMessage(); } });
}

// ---------------------------------------------------------------------------
// DOM helper — append a chat message using the REAL ChatInterface markup
// (justify row + bubble). Returns the BUBBLE element (streaming writes there).
// ---------------------------------------------------------------------------
function appendBubble(log, role, content) {
  const row = document.createElement("div");
  row.className = role === "user" ? CHAT_ROW_USER : CHAT_ROW_AI;
  const el = document.createElement("div");
  el.className = role === "user" ? CHAT_BUBBLE_USER : CHAT_BUBBLE_AI;
  el.textContent = content;
  row.appendChild(el);
  log.appendChild(row);
  log.scrollTop = log.scrollHeight;
  return el;
}

document.getElementById("tp-back").addEventListener("click", back);
document.getElementById("tp-reset")?.addEventListener("click", () => {
  localStorage.removeItem(KEY);
  // Re-seed the synthetic prerequisite values so cross-track generate/chat still
  // resolve after a reset (only the real, entered answers are cleared).
  state = { i: 0, answers: { ...prereqValues }, chat: {} };
  aiController?.abort(); chatInFlight = false;
  render();
});
render();
