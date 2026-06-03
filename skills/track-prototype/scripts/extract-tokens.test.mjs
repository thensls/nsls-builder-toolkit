import { test } from "node:test";
import assert from "node:assert/strict";
import { extractTokensCss } from "./extract-tokens.mjs";

const globals = `
:root {
  --primary: #f16b68;
  --color-light: #fff7f1;
  --radius: 0.5rem;
}
.dark { --primary: #000; }
@theme inline { --color-primary: var(--primary); }
`;

test("emits a :root block with the custom properties between markers", () => {
  const css = extractTokensCss(globals);
  assert.match(css, /GENERATED FROM ignite-next/);
  assert.match(css, /--primary:\s*#f16b68;/);
  assert.match(css, /--color-light:\s*#fff7f1;/);
  assert.match(css, /--radius:\s*0\.5rem;/);
});

test("does not include @theme inline mappings", () => {
  assert.doesNotMatch(extractTokensCss(globals), /--color-primary/);
});

// Regression test mirroring ignite-next's ACTUAL structure: the brand palette lives in
// @theme inline as direct hex, --primary lives in a second :root block, and @theme also
// has var() mappings that must be excluded. If the extended extraction regresses, the
// prototype ships colorless while the simpler tests above still pass — this guards that.
const igniteShaped = `
:root {
  --font-geist-sans: ui-sans-serif,
    system-ui;
}
@theme inline {
  --color-primary: var(--primary);
  --color-light: #fff7f1;
  --color-mediumPlus: #e9ddd3;
  --secondary: oklch(0.97 0 0);
}
:root {
  --primary: #f16b68;
  --radius: 0.5rem;
}
.dark { --primary: #000; }
`;

test("captures hex from @theme inline and props from a second :root block", () => {
  const css = extractTokensCss(igniteShaped);
  assert.match(css, /--primary:\s*#f16b68;/);          // second :root block
  assert.match(css, /--radius:\s*0\.5rem;/);            // second :root block
  assert.match(css, /--color-light:\s*#fff7f1;/);       // @theme hex
  assert.match(css, /--color-mediumPlus:\s*#e9ddd3;/);  // @theme hex (camelCase)
});

test("excludes @theme var() mappings and non-hex values, and .dark overrides", () => {
  const css = extractTokensCss(igniteShaped);
  assert.doesNotMatch(css, /--color-primary/);  // var() mapping in @theme
  assert.doesNotMatch(css, /--secondary/);       // oklch() in @theme, not hex
  assert.doesNotMatch(css, /#000/);              // .dark override must not leak
});
