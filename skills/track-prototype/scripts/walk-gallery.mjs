// Gallery harness: drives a served prototype through EVERY screen, fills each
// with a persona answer-set, waits for live AI on generate/chat screens,
// captures a full-page screenshot per screen, and writes report.json for the
// Phase-2 focus-group panel. The panel judges the rendered run-through, not
// track.json.
//
// Requires Playwright (`npm i playwright && npx playwright install chromium`).
// Usage: node scripts/walk-gallery.mjs <targetUrl> [outDir] [--answers <path>]
//   targetUrl — URL of the served baked prototype (named to avoid shadowing the
//               built-in URL global)
//   outDir    — output directory (default ./focus-group/run)
//               screenshots → <outDir>/shots/step-NN.png
//               report      → <outDir>/report.json
//   --answers — persona answer-set JSON (default scripts/personas/maya.answers.json)
//
// Exit 0 always — capture tool only; the panel + scorecard decide pass/fail.
//
// The fragile per-fieldType fill decision and stream-stability check live in the
// pure, unit-tested module scripts/lib/walk-autofill.mjs. This file is thin glue.

import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { planFill, isStreamStable } from "./lib/walk-autofill.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const positional = [];
  let answers;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--answers") { answers = argv[++i]; continue; }
    positional.push(argv[i]);
  }
  return { targetUrl: positional[0], outDir: positional[1], answersPath: answers };
}

const { targetUrl, outDir: outArg, answersPath: answersArg } = parseArgs(process.argv.slice(2));
const outDir = outArg || "./focus-group/run";
const answersPath = answersArg || join(HERE, "personas", "maya.answers.json");

if (!targetUrl) {
  console.error("Usage: node scripts/walk-gallery.mjs <targetUrl> [outDir] [--answers <path>]");
  process.exit(1);
}

const answers = JSON.parse(readFileSync(answersPath, "utf8"));

const shotsDir = join(outDir, "shots");
mkdirSync(shotsDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 480, height: 900 } });

// Collect console errors and uncaught page errors throughout the walk.
// Ignore browser-level 404s for resources static dev servers routinely omit
// (favicon.ico, robots.txt) and cosmetic option-image 404s — server/asset noise,
// not prototype bugs.
const IGNORE_RE = /favicon\.ico|robots\.txt/i;
const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error" && !IGNORE_RE.test(msg.text()))
    consoleErrors.push(`console.error: ${msg.text()}`);
});
page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e)}`));

await page.goto(targetUrl, { waitUntil: "domcontentloaded" });

// ---------------------------------------------------------------------------
// Total screen count + flattened substeps — read from the injected globals.
// window.__SCREENS__ is the array of pre-rendered HTML; window.__TRACK__ is the
// full track object. We flatten the track once in the page to get an ordered
// descriptor list (slug / type / fieldType / autoProgressOnSelect) aligned with
// the player index, so the walker knows what each screen wants without scraping.
// ---------------------------------------------------------------------------
const meta = await page.evaluate(() => {
  const track = window.__TRACK__;
  const subs = [];
  for (const step of track?.steps || [])
    for (const sub of step.substeps || step.subSteps || [])
      subs.push({
        slug: sub.slug || null,
        type: sub.type || null,
        fieldType: sub.fieldType || null,
        autoProgress: !!sub.autoProgressOnSelect,
      });
  return {
    totalScreens: Array.isArray(window.__SCREENS__) ? window.__SCREENS__.length : null,
    subs,
  };
});
const totalScreens = meta.totalScreens;
const substeps = meta.subs;

// Current player index — reads the tp.v1 localStorage key the prototype writes.
async function playerIndex() {
  return page.evaluate(() => {
    try { return JSON.parse(localStorage.getItem("tp.v1"))?.i ?? null; }
    catch { return null; }
  });
}

// Kind classifier — infers screen type from visible DOM cues (mirrors the
// substep types from render-substep.mjs).
async function classifyKind() {
  return page.evaluate(() => {
    if (document.querySelector(".tp-celebration")) return "celebration";
    if (document.querySelector("[data-chat]")) return "chat";
    if (document.querySelector(".tp-ai-output, .tp-ai-placeholder")) return "generate";
    if (document.querySelector("[data-input], .tp-options")) return "collect";
    if (document.querySelector("[data-next]")) return "banner";
    return "unknown";
  });
}

async function contentHash() {
  return page.evaluate(() => document.body.innerText.trim());
}

// Read the option-grid descriptor from the current screen: the slug carried by
// the grid (or input) and the list of rendered [data-option] values.
async function readScreenDescriptor(fallback) {
  const dom = await page.evaluate(() => {
    const input = document.querySelector("[data-input]");
    const grid = document.querySelector("[data-slug][data-multi]");
    const optionValues = grid
      ? [...grid.querySelectorAll("[data-option]")].map((o) => o.getAttribute("data-value"))
      : [];
    return {
      inputSlug: input ? input.getAttribute("data-slug") : null,
      gridSlug: grid ? grid.getAttribute("data-slug") : null,
      hasInput: !!input,
      optionValues,
    };
  });
  const slug = dom.inputSlug || dom.gridSlug || fallback.slug || null;
  return {
    slug,
    fieldType: fallback.fieldType,
    autoProgress: fallback.autoProgress,
    hasInput: dom.hasInput,
    optionValues: dom.optionValues,
  };
}

// Poll .tp-ai-output until its text length stabilizes (stream complete) or a
// timeout. Returns when stable/timed-out — never hangs.
async function waitForStream(selector, { interval = 600, maxMs = 30000, window = 3 } = {}) {
  const lengths = [];
  const deadline = Date.now() + maxMs;
  for (;;) {
    const len = await page.evaluate((sel) => {
      const el = document.querySelector(sel);
      return el ? el.textContent.length : -1;
    }, selector);
    lengths.push(len);
    if (isStreamStable(lengths, window) && len > 0) return;
    if (Date.now() >= deadline) return;
    await page.waitForTimeout(interval);
  }
}

const TOKEN_RE = /\{[a-z0-9-]+\}/i;
// Generous safety bound: real screen count + slack. Falls back to a fixed cap
// only when __SCREENS__ wasn't injected.
const MAX_STEPS = (totalScreens !== null ? totalScreens : 140) + 10;

const steps = [];
const problems = [];
let prevHash = null;

for (let step = 1; step <= MAX_STEPS; step++) {
  await page.waitForTimeout(250);

  const idxBefore = await playerIndex();
  const descriptor = await readScreenDescriptor(substeps[idxBefore] || {});
  const kind = await classifyKind();

  // --- Wait for live AI on generate screens BEFORE capturing -----------------
  if (kind === "generate") {
    await waitForStream(".tp-ai-output");
  }

  // --- Capture text/title/screenshot ----------------------------------------
  const text = (await page.evaluate(() => document.body.innerText)).trim();
  const title = await page.evaluate(() => {
    const h = document.querySelector(".tp-title, h2, h1");
    return h ? h.innerText.trim() : "";
  });
  const hasUnresolvedToken = TOKEN_RE.test(text);

  if (text.length < 3) problems.push(`step ${step}: BLANK`);
  if (hasUnresolvedToken) problems.push(`step ${step}: UNRESOLVED TOKEN (${(text.match(TOKEN_RE) || [])[0]})`);

  const shotName = `step-${String(step).padStart(2, "0")}.png`;
  await page.screenshot({ path: join(shotsDir, shotName), fullPage: true });
  steps.push({ step, title, kind, text, hasUnresolvedToken, screenshot: `shots/${shotName}` });

  // --- Are we on the last screen? -------------------------------------------
  // The player clamps nextIndex at n-1, so Continue on the last screen is a
  // no-op by design — detect it cleanly via the index, not a STUCK.
  if (totalScreens !== null && idxBefore !== null && idxBefore >= totalScreens - 1) break;

  const nextBtn = page.locator("[data-next]");
  const hasNext = (await nextBtn.count()) > 0;

  // --- Chat screen: send a persona reply, wait for the AI bubble, Continue ---
  if (kind === "chat") {
    const chatInput = page.locator("[data-chat-input]");
    const chatSend = page.locator("[data-chat-send]");
    if ((await chatInput.count()) > 0 && (await chatSend.count()) > 0) {
      const reply = answers[descriptor.slug] || answers["chat-reply"] ||
        "Thanks — that resonates. Tell me more about what to do next.";
      await chatInput.first().fill(String(reply)).catch(() => {});
      const beforeBubbles = await page.evaluate(() =>
        document.querySelectorAll("[data-chat-log] .tp-bubble-ai").length);
      await chatSend.first().click().catch(() => {});
      // Wait for a new AI bubble to appear and finish streaming.
      await page.waitForFunction(
        (n) => document.querySelectorAll("[data-chat-log] .tp-bubble-ai").length > n,
        beforeBubbles, { timeout: 15000 }
      ).catch(() => {});
      await waitForStream("[data-chat-log] .tp-bubble-ai:last-child", { maxMs: 30000 });
    }
    // Re-screenshot after the reply so the gallery shows the exchange.
    await page.screenshot({ path: join(shotsDir, shotName), fullPage: true });
    steps[steps.length - 1].text = (await page.evaluate(() => document.body.innerText)).trim();
  }

  if (!hasNext && kind !== "chat") break; // genuinely no way forward

  // --- Fill the screen via the pure planner ---------------------------------
  if (kind === "collect" || (descriptor.hasInput || descriptor.optionValues.length > 0)) {
    const plan = planFill(descriptor, answers[descriptor.slug]);
    if (plan.problem) problems.push(`step ${step}: ${plan.problem}`);

    if (plan.action === "fill") {
      await page.locator("[data-input]").first().fill(plan.value).catch(() => {});
    } else if (plan.action === "click-options") {
      let advancedByOption = false;
      for (const value of plan.values) {
        const opt = page.locator(`[data-option][data-value="${cssEscape(value)}"]`);
        if ((await opt.count()) === 0) continue;
        await opt.first().click().catch(() => {});
        await page.waitForTimeout(120);
        // autoProgressOnSelect: clicking may advance the player with no Continue.
        if (plan.autoProgress) {
          const idxNow = await playerIndex();
          if (idxNow !== null && idxBefore !== null && idxNow > idxBefore) {
            advancedByOption = true;
            break;
          }
        }
      }
      if (advancedByOption) {
        // Player already moved on — do NOT click Continue (would double-advance).
        prevHash = await contentHash();
        continue;
      }
    }
    // plan.action === "none" → nothing to fill; just advance via Continue.
  }

  // --- Loop detection (content unchanged since last step) -------------------
  const beforeHash = await contentHash();
  if (prevHash !== null && beforeHash === prevHash) {
    problems.push(`step ${step}: LOOP DETECTED (content unchanged since last step)`);
    break;
  }
  prevHash = beforeHash;

  // --- Advance via Continue --------------------------------------------------
  await nextBtn.first().click().catch(() => {});
  await page.waitForTimeout(300);

  const afterHash = await contentHash();
  const idxAfter = await playerIndex();
  const advancedByIndex = idxAfter !== null && idxBefore !== null && idxAfter > idxBefore;
  if (beforeHash === afterHash && !advancedByIndex) {
    problems.push(`step ${step}: STUCK (no advance after click)`);
    break;
  }
}

// CSS.escape isn't available in node; escape a string for use inside an
// attribute selector value. We wrap values in double quotes, so escape "\" and
// '"'. Option texts may contain commas/quotes — this keeps the whole string.
function cssEscape(value) {
  return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

for (const err of consoleErrors) problems.push(err);

const report = { buildUrl: targetUrl, steps, problems };
const reportPath = join(outDir, "report.json");
writeFileSync(reportPath, JSON.stringify(report, null, 2));

await browser.close();

const summary = `walk-gallery: ${steps.length} screen(s) captured → ${reportPath}` +
  (problems.length ? ` — ${problems.length} problem(s)` : " — no problems");
console.log(summary);

process.exit(0);
