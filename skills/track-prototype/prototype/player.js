import { flattenSubsteps, nextIndex, prevIndex, clampIndex, progressPct } from "./player-core.mjs";
import { interpolate } from "./interpolate.mjs"; // build copies interpolate.mjs alongside player.js (see build-prototype.mjs)

const KEY = "tp.v1";
const track = window.__TRACK__;            // injected by build (the full track object)
const screens = window.__SCREENS__;        // injected by build: array of pre-rendered HTML strings
const subs = flattenSubsteps(track);
const root = document.getElementById("tp-body");
const bar = document.getElementById("tp-progress-bar");

let state = load();

function load() {
  try { const s = JSON.parse(localStorage.getItem(KEY)); if (s) return { i: clampIndex(s.i, subs.length), answers: s.answers || {} }; }
  catch { /* corrupt — fall through */ }
  return { i: 0, answers: {} };
}
function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }

function render() {
  root.innerHTML = interpolate(screens[state.i], state.answers); // fill {slug} live
  bar.style.width = progressPct(state.i, subs.length) + "%";
  wire();
}

function captureCurrent() {
  const input = root.querySelector("[data-input]");
  if (input && input.dataset.slug) state.answers[input.dataset.slug] = input.value.trim();
  const grid = root.querySelector("[data-slug][data-multi]");
  if (grid) {
    const chosen = [...grid.querySelectorAll('[data-option][aria-selected="true"]')].map((b) => b.dataset.value);
    if (chosen.length) state.answers[grid.dataset.slug] = chosen.join(", ");
  }
}

function advance() { captureCurrent(); state.i = nextIndex(state.i, subs.length); persist(); render(); }
function back() { state.i = prevIndex(state.i, subs.length); persist(); render(); }

function wire() {
  root.querySelector("[data-next]")?.addEventListener("click", advance);
  document.getElementById("tp-back")?.toggleAttribute("disabled", state.i === 0);
  root.querySelectorAll("[data-option]").forEach((opt) => opt.addEventListener("click", () => {
    const grid = opt.closest("[data-slug]");
    const multi = grid?.dataset.multi === "true";
    if (!multi) grid.querySelectorAll("[data-option]").forEach((o) => o.setAttribute("aria-selected", "false"));
    opt.setAttribute("aria-selected", opt.getAttribute("aria-selected") === "true" ? "false" : "true");
  }));
  root.querySelector("[data-input]")?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); advance(); } });
}

document.getElementById("tp-back").addEventListener("click", back);
document.getElementById("tp-reset")?.addEventListener("click", () => { localStorage.removeItem(KEY); state = { i: 0, answers: {} }; render(); });
render();
