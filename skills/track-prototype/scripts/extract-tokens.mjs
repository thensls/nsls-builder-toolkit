// Mechanically lift the :root custom-property block from ignite-next globals.css into
// a standalone tokens.css. Run via SYNC.md when the app's design changes.
// Usage: node extract-tokens.mjs --from <path-to-ignite-next>/src/app/globals.css \
//          --out ../prototype/design-kit/tokens.css
import { readFileSync, writeFileSync } from "node:fs";

const START = "/* >>> GENERATED FROM ignite-next globals.css — DO NOT EDIT BY HAND <<< */";
const END = "/* <<< END GENERATED <<< */";

/**
 * Extract custom properties from a CSS block body string.
 * Only returns lines that start with --prop: value (single-line values only).
 * Skips multi-line values (like font stacks that span lines).
 */
function extractProps(body) {
  return body
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => /^--[a-z0-9-]+\s*:[^;]+;/i.test(l));
}

export function extractTokensCss(globalsSrc) {
  // Strip @theme inline { ... } blocks before scanning for :root
  const themePattern = /@theme\s+inline\s*\{([\s\S]*?)\}/g;
  const themeMatches = [];
  let tm;
  while ((tm = themePattern.exec(globalsSrc)) !== null) {
    themeMatches.push(tm[1]);
  }
  const withoutTheme = globalsSrc.replace(/@theme\s+inline\s*\{[\s\S]*?\}/g, "");

  // Collect props from ALL :root { ... } blocks (not .dark, not @theme)
  const rootPattern = /(?:^|\n):root\s*\{([\s\S]*?)\}/g;
  const props = [];
  let m;
  while ((m = rootPattern.exec(withoutTheme)) !== null) {
    extractProps(m[1]).forEach((p) => props.push(p));
  }

  // Also capture direct hex/value properties from @theme inline (not var() references)
  // These are properties like --color-light: #fff7f1 that only exist in @theme
  const themeProps = [];
  for (const body of themeMatches) {
    body.split("\n")
      .map((l) => l.trim())
      .filter((l) => /^--[a-z0-9-]+\s*:\s*#/i.test(l)) // only direct hex values
      .forEach((p) => themeProps.push(p));
  }

  const allProps = [...props, ...themeProps];

  return `${START}\n:root {\n${allProps.map((p) => "  " + p).join("\n")}\n}\n${END}\n`;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const from = args[args.indexOf("--from") + 1];
  const out = args[args.indexOf("--out") + 1];
  if (!from || !out) {
    console.error("Usage: extract-tokens.mjs --from <globals.css> --out <tokens.css>");
    process.exit(2);
  }
  writeFileSync(out, extractTokensCss(readFileSync(from, "utf8")));
  console.log(`Wrote ${out}`);
}
