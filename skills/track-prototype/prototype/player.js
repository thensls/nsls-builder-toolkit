import { flattenSubsteps, nextIndex, prevIndex, clampIndex, progressPct } from "./player-core.mjs";
import { interpolate } from "./interpolate.mjs"; // build copies interpolate.mjs alongside player.js (see build-prototype.mjs)

const KEY = "tp.v1";
const track = window.__TRACK__;            // injected by build (the full track object)
const screens = window.__SCREENS__;        // injected by build: array of pre-rendered HTML strings
const subs = flattenSubsteps(track);
const root = document.getElementById("tp-body");
const bar = document.getElementById("tp-progress-bar");

let state = load();
let chatInFlight = false;  // true while a chat stream is running — prevents double-sends
let aiController = null;   // AbortController for the current in-flight AI stream (generate or chat)

function load() {
  try {
    const s = JSON.parse(localStorage.getItem(KEY));
    if (s) return { i: clampIndex(s.i, subs.length), answers: s.answers || {}, chat: s.chat || {} };
  } catch { /* corrupt — fall through */ }
  return { i: 0, answers: {}, chat: {} };
}
function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }

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
  wire();
  // Kick off AI after the screen is visible (non-blocking)
  maybeRunGenerateAI();
  wireChatAI();
}

function captureCurrent() {
  const input = root.querySelector("[data-input]");
  if (input && input.dataset.slug) state.answers[input.dataset.slug] = input.value.trim();
  const grid = root.querySelector("[data-slug][data-multi]");
  if (grid) {
    const chosen = [...grid.querySelectorAll('[data-option][aria-selected="true"]')].map((b) => b.dataset.value);
    state.answers[grid.dataset.slug] = chosen.join(", "); // always write — empty when deselected, so stale data clears
  }
}

function advance() { captureCurrent(); state.i = nextIndex(state.i, subs.length); persist(); aiController?.abort(); chatInFlight = false; render(); }
function back() { captureCurrent(); state.i = prevIndex(state.i, subs.length); persist(); aiController?.abort(); chatInFlight = false; render(); }

function wire() {
  root.querySelector("[data-next]")?.addEventListener("click", advance);
  document.getElementById("tp-back")?.toggleAttribute("disabled", state.i === 0);
  root.querySelectorAll("[data-option]").forEach((opt) => opt.addEventListener("click", () => {
    const grid = opt.closest("[data-slug]");
    if (!grid) return;
    const multi = grid.dataset.multi === "true";
    if (!multi) grid.querySelectorAll("[data-option]").forEach((o) => o.setAttribute("aria-selected", "false"));
    opt.setAttribute("aria-selected", opt.getAttribute("aria-selected") === "true" ? "false" : "true");
  }));
  root.querySelector("[data-input]")?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); advance(); } });
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
    { type: "generate", template: sub.aiPromptConfig?.template || sub.prompt, profile: state.answers },
    (d) => { out.textContent += d; },
    aiController.signal
  );

  out.classList.remove("is-writing");
  if (!ok) {
    // Fallback: restore the baked sample (critical guarantee)
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
      state.chat[slug].push({ role: "assistant", content: aiBubble.textContent });
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
// DOM helper — create and append a chat bubble, return the element.
// ---------------------------------------------------------------------------
function appendBubble(log, role, content) {
  const el = document.createElement("div");
  el.className = role === "user"
    ? "tp-bubble tp-bubble-user"
    : "tp-bubble tp-bubble-ai";
  el.textContent = content;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
  return el;
}

document.getElementById("tp-back").addEventListener("click", back);
document.getElementById("tp-reset")?.addEventListener("click", () => {
  localStorage.removeItem(KEY);
  state = { i: 0, answers: {}, chat: {} };
  aiController?.abort(); chatInFlight = false;
  render();
});
render();
