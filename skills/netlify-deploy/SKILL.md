---
name: netlify-deploy
description: Deploy a static HTML file (or directory) to Netlify and visually review it with Playwright. Use after creating a frontend presentation or page that needs to be published and verified. Handles CLI setup, auth, content-type gotchas, and screenshot-based review.
---

# Netlify Deploy + Playwright Review Skill

Deploy a static site to Netlify and run a visual quality check using Playwright MCP screenshots. This skill encodes all the gotchas encountered in production so you don't repeat them.

---

## Prerequisites

### 1. Netlify CLI — Check Version First

**CRITICAL**: Old versions of `netlify-cli` (e.g., `2.0.0-beta.5`) silently fail. Commands like `netlify sites:create` produce no output or error. Always verify:

```bash
netlify --version
```

If version is anything below `20.x`, update immediately:

```bash
npm install -g netlify-cli@latest
```

Confirm: `netlify-cli/24.x.x` or higher.

### 2. Auth Token

The Netlify auth token is stored at:
```
~/.netlify/config.json
```

Look under `.users[userId].auth.token`. Retrieve it with:

```bash
node -e "const c=require(process.env.HOME+'/.netlify/config.json'); const uid=Object.keys(c.users)[0]; console.log(c.users[uid].auth.token)"
```

Save to a variable for use in deploy commands:
```bash
export NETLIFY_AUTH_TOKEN=$(node -e "const c=require(process.env.HOME+'/.netlify/config.json'); const uid=Object.keys(c.users)[0]; console.log(c.users[uid].auth.token)")
```

### 3. Site ID

You need `NETLIFY_SITE_ID` — the UUID of the target Netlify site. Find it at:
- Netlify dashboard → Site settings → General → Site ID
- Or via: `netlify sites:list` (once CLI is authenticated)

---

## Gotcha: Never Use the API Zip Method

**DO NOT** deploy by zipping files and POSTing to the Netlify API directly:

```bash
# ❌ WRONG — This serves files as text/plain, not text/html
zip -j /tmp/site.zip /path/to/file.html
curl -X POST "https://api.netlify.com/api/v1/sites/$SITE_ID/deploys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/zip" \
  --data-binary @/tmp/site.zip
```

**Why it fails**: The API zip deploy method ignores MIME types and serves all files as `application/octet-stream` or `text/plain`. Browsers will show raw HTML source instead of rendering the page.

**Always use the CLI instead** (see Phase 2 below).

---

## Phase 1: Prepare the Deploy Directory

The Netlify CLI deploys a **directory**, not a single file. The entry point must be named `index.html`.

```bash
# Create a clean temp directory
mkdir -p /tmp/site-deploy

# Copy your main file as index.html
cp /path/to/your-presentation.html /tmp/site-deploy/index.html

# Optional: add a _headers file to ensure correct content type
cat > /tmp/site-deploy/_headers << 'EOF'
/*
  Content-Type: text/html; charset=UTF-8
EOF
```

**Note**: The `_headers` file is optional but adds an extra safety net for content-type.

---

## Phase 2: Deploy to Netlify

```bash
cd /tmp/site-deploy

NETLIFY_AUTH_TOKEN=<token> NETLIFY_SITE_ID=<site-id> netlify deploy --dir=. --prod
```

**Key flags:**
- `--dir=.` — deploy the current directory
- `--prod` — deploy to production (not a preview URL)
- Auth via env vars avoids needing `netlify link` (which requires interactive prompts)

**Verify content-type after deploy:**

```bash
curl -sI https://your-site.netlify.app | grep -i content-type
```

Expected: `content-type: text/html; charset=UTF-8`

If you see `text/plain` — you used the API zip method. Re-deploy with the CLI.

---

## Phase 3: Visual Review with Playwright

After deploy, use Playwright MCP to screenshot every slide/page and check for visual issues.

### Setup

Load Playwright tools first:
```
ToolSearch: select:mcp__plugin_playwright_playwright__browser_navigate
```

### Viewport

Always review at **1440×900** (standard laptop/presentation screen):

```javascript
// Via browser_run_code or browser_resize
await page.setViewportSize({ width: 1440, height: 900 });
```

Or use the `browser_resize` tool with width=1440, height=900.

### Navigation Pattern for Scroll-Snap Slides

Slide decks use CSS `scroll-snap`. Navigate via the **nav buttons** in the DOM, not `window.scrollTo()` — scroll-snap will intercept and animate.

```javascript
// Get all nav buttons (typically ▲ ▼ arrows or slide dots)
const buttons = await page.$$('nav button');
// buttons[1] = next slide (buttons[0] = prev)
await buttons[1].click();
```

**CRITICAL: Wait 1000–1200ms after each click before screenshotting.**

Scroll-snap animations take ~600ms. If you screenshot immediately, you capture a mid-transition blur. Always wait:

```javascript
await buttons[1].click();
await page.waitForTimeout(1200); // Wait for scroll-snap animation
await page.screenshot({ path: '/tmp/slide-02.png' });
```

### Full Slide Review Loop

```javascript
// Navigate to site
await page.goto('https://your-site.netlify.app');
await page.waitForTimeout(1500); // Initial load

// Screenshot slide 1
await page.screenshot({ path: '/tmp/slide-01.png' });

// Loop through remaining slides
const buttons = await page.$$('nav button');
const nextBtn = buttons[1]; // Assumes [prev, next] button order

for (let i = 2; i <= SLIDE_COUNT; i++) {
  await nextBtn.click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `/tmp/slide-${String(i).padStart(2,'0')}.png` });
}
```

### What to Review

After capturing screenshots, check each slide for:

| Issue | What to Look For |
|-------|-----------------|
| **Overflow** | Content cut off at bottom or sides |
| **Wrapping** | Bold/key phrases breaking mid-word at line end |
| **Alignment** | Elements not visually centered or mismatched |
| **Count errors** | Numbers in headlines (e.g., "Seven services") that don't match actual item count |
| **Consistency** | Cards/items with different styling (e.g., one card highlighted when others aren't) |
| **Spacing** | Uneven gaps between repeated elements (cards, bullets, pipeline nodes) |

### Common Fixes

**Text wrapping on strong/bold elements:**
```css
.slide strong, .key-phrase { white-space: nowrap; }
```

**Count mismatch in headline:** Read the actual DOM and count children before writing the headline.

**Inconsistent card styling:** Check for stray `style=""` inline attributes that override the class-based design.

**Vertical alignment of grouped elements:** Use `align-self: flex-end` (not `center`) if you want items to align with the bottom of the opposite column.

---

## Phase 4: Iterate

After visual review:

1. Fix issues in the source file (`~/Desktop/presentation.html` or equivalent)
2. Re-copy to deploy dir: `cp source.html /tmp/site-deploy/index.html`
3. Re-deploy: `NETLIFY_AUTH_TOKEN=... NETLIFY_SITE_ID=... netlify deploy --dir=. --prod`
4. Wait ~10-15s for CDN propagation, then re-screenshot

---

## Environment

- **CLI**: `netlify-cli` ≥ 24.x via `npm install -g netlify-cli@latest`
- **Auth**: `~/.netlify/config.json` → `.users[uid].auth.token`
- **Site for SLT slides**: `slt-pipeline-slides.netlify.app` → NETLIFY_SITE_ID = `ea5aa7d1-dfa7-4048-8cae-b185b434ce1e`
- **Deploy dir pattern**: `/tmp/[project]-deploy/index.html`
- **Playwright MCP**: Available via `mcp__plugin_playwright_playwright__*` tools

---

## Related Skills

- **frontend-slides** — Creates the HTML presentations that this skill deploys
- **frontend-design** — For more complex interactive pages
