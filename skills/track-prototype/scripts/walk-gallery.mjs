// Gallery harness: drives a served prototype through every screen, captures a
// full-page screenshot per screen, and writes report.json for the Phase-2
// focus-group panel.  The panel judges the rendered run-through, not track.json.
//
// Requires Playwright (`npm i -D playwright && npx playwright install chromium`).
// Usage: node scripts/walk-gallery.mjs <targetUrl> [outDir]
//   targetUrl — URL of the served baked prototype (arg 2; named to avoid
//               shadowing the built-in URL global)
//   outDir    — output directory, default ./focus-group/run
//               screenshots → <outDir>/shots/step-NN.png
//               report     → <outDir>/report.json
//
// Exit 0 always — capture tool only; the panel + scorecard decide pass/fail.

import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const targetUrl = process.argv[2];
const outDir = process.argv[3] || "./focus-group/run";

if (!targetUrl) {
  console.error("Usage: node scripts/walk-gallery.mjs <targetUrl> [outDir]");
  process.exit(1);
}

const shotsDir = join(outDir, "shots");
mkdirSync(shotsDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 480, height: 900 } });

// Collect console errors and uncaught page errors throughout the walk.
// Ignore browser-level 404s for resources that static dev servers routinely omit
// (favicon.ico, robots.txt) — these are server noise, not prototype bugs.
const IGNORE_RE = /favicon\.ico|robots\.txt/i;
const consoleErrors = [];
page.on("console", (msg) => {
  if (msg.type() === "error" && !IGNORE_RE.test(msg.text()))
    consoleErrors.push(`console.error: ${msg.text()}`);
});
page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${String(e)}`));

await page.goto(targetUrl, { waitUntil: "domcontentloaded" });

// ---------------------------------------------------------------------------
// Total screen count — read from window.__SCREENS__ if the prototype injected
// it (standard baked build).  Used to detect the last screen cleanly without a
// false-positive STUCK (the player clamps nextIndex at n-1, so clicking
// Continue on the last screen is a no-op by design, not a bug).
// Falls back to null when the page doesn't expose __SCREENS__ (safe: hash-diff
// logic still detects genuine stuck/loop conditions in that case).
// ---------------------------------------------------------------------------
const totalScreens = await page.evaluate(() =>
  Array.isArray(window.__SCREENS__) ? window.__SCREENS__.length : null
);

// Current player index — reads the tp.v1 localStorage key the prototype writes.
// Returns null when localStorage isn't available or the key is absent.
async function playerIndex() {
  return page.evaluate(() => {
    try { return JSON.parse(localStorage.getItem("tp.v1"))?.i ?? null; }
    catch { return null; }
  });
}

// ---------------------------------------------------------------------------
// Kind classifier — infers screen type from visible cues in the DOM.
// Types mirror the substep types from render-substep.mjs:
//   banner      — say/info screen (no input, just a Continue button)
//   collect     — any data-input or data-option grid
//   generate    — .tp-ai-output or .tp-ai-placeholder present
//   chat        — data-chat present
//   celebration — .tp-celebration present
//   unknown     — fallback
// ---------------------------------------------------------------------------
async function classifyKind() {
  return page.evaluate(() => {
    if (document.querySelector(".tp-celebration")) return "celebration";
    if (document.querySelector("[data-chat]")) return "chat";
    if (document.querySelector(".tp-ai-output, .tp-ai-placeholder")) return "generate";
    if (document.querySelector("[data-input], .tp-options")) return "collect";
    // A banner/say screen has a Continue button but no input
    if (document.querySelector("[data-next]")) return "banner";
    return "unknown";
  });
}

// ---------------------------------------------------------------------------
// Content hash — used for loop / stuck detection (stable hash = no advance).
// ---------------------------------------------------------------------------
async function contentHash() {
  return page.evaluate(() => document.body.innerText.trim());
}

const MAX_STEPS = 25;
const TOKEN_RE = /\{[a-z0-9-]+\}/i;

const steps = [];
const problems = [];

let prevHash = null;

for (let step = 1; step <= MAX_STEPS; step++) {
  await page.waitForTimeout(300);

  // Capture visible text.
  const text = (await page.evaluate(() => document.body.innerText)).trim();

  // Capture title (h2.tp-title if present, else first heading, else "").
  const title = await page.evaluate(() => {
    const h = document.querySelector(".tp-title, h2, h1");
    return h ? h.innerText.trim() : "";
  });

  const kind = await classifyKind();
  const hasUnresolvedToken = TOKEN_RE.test(text);

  // Diagnostics
  if (text.length < 3) problems.push(`step ${step}: BLANK`);
  if (hasUnresolvedToken) problems.push(`step ${step}: UNRESOLVED TOKEN`);

  // Full-page screenshot
  const shotFile = join(shotsDir, `step-${String(step).padStart(2, "0")}.png`);
  await page.screenshot({ path: shotFile, fullPage: true });

  steps.push({
    step,
    title,
    kind,
    text,
    hasUnresolvedToken,
    screenshot: `shots/step-${String(step).padStart(2, "0")}.png`,
  });

  // Check for a Continue/advance button.  If none, we've reached the end.
  const nextBtn = page.getByRole("button", {
    name: /continue|next|okay|got it|okay,\s*got it|finish/i,
  });
  if ((await nextBtn.count()) === 0) break;

  // If the prototype exposes its screen list, use the player index to detect
  // the last screen cleanly — the player's nextIndex clamps at n-1 by design,
  // so clicking Continue on the last screen is a no-op, not a bug.
  if (totalScreens !== null) {
    const idx = await playerIndex();
    if (idx !== null && idx >= totalScreens - 1) break;
  }

  // Fill visible text inputs generically so the prototype advances.
  const textInput = page.locator("[data-input]");
  if (await textInput.count()) {
    await textInput.first().fill("Marcus").catch(() => {});
  }

  // Select the first option in any option grid that has nothing selected yet.
  const firstUnselected = page.locator(
    '[data-option][aria-selected="false"]'
  );
  if ((await firstUnselected.count()) > 0) {
    await firstUnselected.first().click().catch(() => {});
    await page.waitForTimeout(100);
  }

  const beforeHash = await contentHash();

  // Detect content-hash loop before clicking (same as where we started this step).
  if (prevHash !== null && beforeHash === prevHash) {
    problems.push(`step ${step}: LOOP DETECTED (content unchanged since last step)`);
    break;
  }
  prevHash = beforeHash;

  await nextBtn.first().click().catch(() => {});
  await page.waitForTimeout(300);

  const afterHash = await contentHash();
  if (beforeHash === afterHash) {
    // Fallback for non-prototype pages: hash didn't change despite a click.
    problems.push(`step ${step}: STUCK (no advance after click)`);
    break;
  }
}

// Append any console/page errors collected during the run.
for (const err of consoleErrors) problems.push(err);

const report = {
  buildUrl: targetUrl,
  steps,
  problems,
};

const reportPath = join(outDir, "report.json");
writeFileSync(reportPath, JSON.stringify(report, null, 2));

await browser.close();

const summary = `walk-gallery: ${steps.length} screen(s) captured → ${reportPath}` +
  (problems.length ? ` — ${problems.length} problem(s)` : " — no problems");
console.log(summary);

// Always exit 0 — capture tool, not pass/fail gate.
process.exit(0);
