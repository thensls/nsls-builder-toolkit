// QA harness: drives a served prototype through every screen, screenshotting each and
// flagging blank screens, unresolved {tokens}, and stuck/no-advance steps.
// Requires Playwright installed (`npm i -D playwright && npx playwright install chromium`).
// Usage: node scripts/walk.mjs http://localhost:3000
// (Used manually for QA now; the Plan-3 focus-group phase builds on this harness.)
import { chromium } from "playwright";
const URL = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 480, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
await page.goto(URL, { waitUntil: "domcontentloaded" });
const problems = [];
for (let step = 1; step <= 25; step++) {
  await page.waitForTimeout(300);
  const text = (await page.evaluate(() => document.body.innerText)).trim();
  if (text.length < 3) problems.push(`step ${step}: BLANK`);
  if (/\{[a-z0-9-]+\}/i.test(text)) problems.push(`step ${step}: UNRESOLVED TOKEN`);
  await page.screenshot({ path: `/tmp/tp-step-${String(step).padStart(2, "0")}.png` });
  const next = page.getByRole("button", { name: /continue|next|okay|got it|finish/i });
  if (await next.count() === 0) break;
  const input = page.locator("[data-input]");
  if (await input.count()) await input.first().fill("Marcus").catch(() => {});
  const before = await page.evaluate(() => document.body.innerText);
  await next.first().click().catch(() => {});
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => document.body.innerText);
  if (before === after) { problems.push(`step ${step}: STUCK (no advance)`); break; }
}
console.log(JSON.stringify({ problems, pageErrors: errors }, null, 2));
await browser.close();
if (problems.length || errors.length) process.exit(1);
