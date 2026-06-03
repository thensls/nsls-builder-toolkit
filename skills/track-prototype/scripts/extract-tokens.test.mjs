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
