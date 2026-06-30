// AUTHORING-TIME tool (not part of a prototype build): compiles the committed
// design-kit/app.css from the REAL ignite-next Tailwind v4 theme.
//
// How it works
//   1. Renders a "kitchen sink" corpus: one screen per substep fieldType via the
//      real renderer (render-substep.mjs), plus template.html (chrome) and every
//      runtime class the player generates (runtime-classes.mjs).
//   2. Builds an input.css = `@import "tailwindcss" source(none)` + @source the
//      corpus + the app's OWN globals.css (theme vars, @font-face, custom
//      component styles like .step-input), with /fonts/ rewritten to ./fonts/.
//   3. Runs the Tailwind v4 CLI over it → design-kit/app.css (committed).
//   4. Copies the app's font files into design-kit/fonts/.
//
// Prototype BUILDS stay dependency-free: they only copy the committed output.
// Re-run this script whenever render-substep.mjs / runtime-classes.mjs /
// template.html markup changes, or when ignite-next's globals.css changes.
//
// Usage:
//   node scripts/build-design-kit.mjs --app /path/to/ignite-next [--tools /tmp/twkit]
//   --app    ignite-next checkout (source of globals.css + public/fonts)
//   --tools  a dir whose node_modules contains tailwindcss@4 + @tailwindcss/cli
//            + @tailwindcss/typography + tailwindcss-animate. Create one with:
//            mkdir -p /tmp/twkit && cd /tmp/twkit && npm i tailwindcss@4 \
//              @tailwindcss/cli@4 @tailwindcss/typography tailwindcss-animate

import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { renderSubstep } from "./lib/render-substep.mjs";
import { runtimeClassCorpus } from "./lib/runtime-classes.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const PROTO = join(HERE, "..", "prototype");
const KIT = join(PROTO, "design-kit");

// Font files declared by the app's @font-face blocks (globals.css). The current
// rebrand ships HW Cigars (display/headings); body copy is Inter, injected by
// Next at runtime, so the static prototype falls back to system sans for body.
const FONT_FILES = [
  "HWCigars-Regular.woff2",
  "HWCigars-SemiBold.woff2",
  "HWCigars-Bold.woff2",
];

// --- Kitchen-sink corpus: exercise every markup path the renderer can emit ---
export function kitchenSinkSubsteps() {
  const opt = (t, extra = {}) => ({ text: t, ...extra });
  return [
    { id: "k-banner", slug: "k-banner", title: "Banner", type: "say", fieldType: "banner", prompt: "Welcome to the track.", imageUrl: "/img/intro/intro-1.png", callout: "A helpful callout." },
    { id: "k-banner-multi", slug: "k-banner-multi", title: "BannerM", type: "say", fieldType: "banner-multiple", prompt: "Line zero", bannerTexts: ["Line one", "Line two"] },
    { id: "k-text", slug: "k-text", title: "Text", showTitle: true, type: "collect", fieldType: "text", prompt: "Your name?", suggestions: ["Maya", "Jordan"] },
    { id: "k-currency", slug: "k-currency", title: "Currency", type: "collect", fieldType: "currency", prompt: "Target salary?", textFieldLabel: "Annual salary" },
    { id: "k-select", slug: "k-select", title: "Select", type: "collect", fieldType: "select", prompt: "Pick one.", options: ["A", "B", "C"] },
    { id: "k-multicheck", slug: "k-multicheck", title: "MultiCheck", type: "collect", fieldType: "multi-checkbox", prompt: "Pick all.", options: ["One", "Two"] },
    { id: "k-radio", slug: "k-radio", title: "Radio", type: "collect", fieldType: "radio", prompt: "Choose.", options: ["Yes", "No"] },
    { id: "k-ms", slug: "k-ms", title: "MultiSelect", type: "collect", fieldType: "multi-select", prompt: "Pick 3.", multiselectMinSelections: 3, multiselectMaxSelections: 3,
      options: [opt("Alpha – first thing"), opt("Beta", { description: "second", imageUrl: "/img/x.png" }), opt("Gamma")] },
    { id: "k-ms-ref", slug: "k-ms-ref", title: "Narrow", type: "collect", fieldType: "multi-select", prompt: "Narrow down.", optionsSourceSlug: "k-ms" },
    { id: "k-im", slug: "k-im", title: "ImageSelect", type: "collect", fieldType: "image-multiselect", prompt: "I'm more likely to…", autoProgressOnSelect: true,
      options: [opt("Plan it", { imageUrl: "/img/a.png", answerId: "a1" }), opt("Feel it", { imageUrl: "/img/b.png", answerId: "a2" })] },
    { id: "k-wheel", slug: "k-wheel", title: "Career Clarity Rating", type: "collect", fieldType: "dropdown-with-checkboxes", prompt: "Rate your clarity.",
      textFieldLabel: "What feels unclear?", dropdownOptions: ["1", "2", "3"], checkboxOptions: ["Industry", "Role"] },
    { id: "k-edu", slug: "k-edu", title: "Education", type: "collect", fieldType: "education", prompt: "Your education?" },
    { id: "k-work", slug: "k-work", title: "Work", type: "collect", fieldType: "work", prompt: "Your work?" },
    { id: "k-djs", slug: "k-djs", title: "DreamJob", type: "collect", fieldType: "dream-job-select", prompt: "Pick a dream job.",
      options: [{ text: "Coach", shortDescription: "Helps people", detailedDescription: "A long detailed description of coaching as a career path that runs over one hundred characters to exercise the detail branch." }] },
    { id: "k-djr", slug: "k-djr", title: "Requirements", type: "collect", fieldType: "dream-job-requirements", prompt: "Review these.",
      options: [{ title: "Degree", shortDescription: "Usually required", detailedDescription: "A long detailed description of degree requirements that also runs over one hundred characters to exercise the markdown-detail branch." }] },
    { id: "k-gen", slug: "k-gen", title: "Snapshot", showTitle: true, type: "generate", fieldType: "text", prompt: "Here's what we heard:", callout: "Generated content note.", aiPromptConfig: { template: "x" } },
    { id: "k-chat", slug: "k-chat", title: "Coach", type: "chat", fieldType: "text", prompt: "Hello! Let's talk." },
    { id: "k-results", slug: "k-results", title: "Results", type: "say", fieldType: "assessment-results", prompt: "" },
    { id: "k-cel", slug: "k-cel", title: "Celebration", type: "say", fieldType: "celebration", prompt: "You did it!", callout: "Nice work.",
      celebrationTasks: ["Built a profile"], celebrationNextStepsTitle: "Onboarding", celebrationNextStepsDescription: "What we learned:", imageUrl: "/img/steps/onboarding/celebration.png" },
    { id: "k-cel-vid", slug: "k-cel-vid", title: "Section done", type: "say", fieldType: "celebration", prompt: "",
      celebrationCompletedSection: "Professional Environment", celebrationNextSection: "Interests", imageUrl: "/video/x.mp4" },
  ];
}

export function buildCorpus() {
  // Progress-tracker markup needs ctx.progress — fake one entry for k-im.
  const ctx = { samples: { "k-gen": "Sample generated text.", "k-chat": "Seed reply." },
    progress: { "k-im": { section: 1, totalSections: 5, question: 2, questionsInSection: 10 } } };
  const screens = kitchenSinkSubsteps().map((s) => renderSubstep(s, ctx)).join("\n");
  const chrome = readFileSync(join(PROTO, "template.html"), "utf8");
  return `<!-- Tailwind scan corpus — generated by build-design-kit.mjs, not served -->\n${chrome}\n${screens}\n${runtimeClassCorpus()}`;
}

function parseArgs(argv) {
  const get = (f) => { const i = argv.indexOf(f); return i !== -1 ? argv[i + 1] : undefined; };
  return { app: get("--app"), tools: get("--tools") || "/tmp/twkit" };
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  const { app, tools } = parseArgs(process.argv.slice(2));
  if (!app || !existsSync(join(app, "src", "app", "globals.css"))) {
    console.error("Usage: node scripts/build-design-kit.mjs --app /path/to/ignite-next [--tools /tmp/twkit]");
    process.exit(2);
  }
  const cli = join(tools, "node_modules", ".bin", "tailwindcss");
  if (!existsSync(cli)) {
    console.error(`Tailwind CLI not found at ${cli}. See the header of this script for setup.`);
    process.exit(2);
  }

  // 1. Corpus
  const work = join(tools, "tp-design-kit-work");
  mkdirSync(work, { recursive: true });
  writeFileSync(join(work, "corpus.html"), buildCorpus());

  // 2. Input CSS = app globals.css with our import/source preamble + local font paths
  let globals = readFileSync(join(app, "src", "app", "globals.css"), "utf8");
  globals = globals
    .replace(/@import\s+"tailwindcss"\s*;/, "") // we add our own import with source(none)
    .replace(/url\(\/fonts\//g, "url(./fonts/");
  const input = `@import "tailwindcss" source(none);\n@source "./corpus.html";\n${globals}`;
  writeFileSync(join(work, "input.css"), input);

  // 3. Compile
  execFileSync(cli, ["-i", join(work, "input.css"), "-o", join(work, "out.css")], { cwd: work, stdio: "inherit" });
  let css = readFileSync(join(work, "out.css"), "utf8");

  let sha = "unknown";
  try { sha = execFileSync("git", ["-C", app, "rev-parse", "HEAD"]).toString().trim(); } catch { /* not a git checkout */ }
  const header = `/* GENERATED by scripts/build-design-kit.mjs — DO NOT EDIT BY HAND.\n` +
    ` * Real Tailwind v4 compile of ignite-next's theme (globals.css) over the\n` +
    ` * prototype markup corpus. Source commit: ${sha}\n` +
    ` * Built: ${new Date().toISOString().slice(0, 10)} — re-sync steps: prototype/SYNC.md */\n`;
  writeFileSync(join(KIT, "app.css"), header + css);

  // 4. Fonts
  const fontsOut = join(KIT, "fonts");
  mkdirSync(fontsOut, { recursive: true });
  let fontsCopied = 0;
  for (const f of FONT_FILES) {
    const src = join(app, "public", "fonts", f);
    if (existsSync(src)) { cpSync(src, join(fontsOut, f)); fontsCopied++; }
    else console.warn(`font missing in app: ${f}`);
  }
  console.log(`design-kit: app.css ${(css.length / 1024).toFixed(0)}KB (source ${sha.slice(0, 7)}), fonts ${fontsCopied}/${FONT_FILES.length}`);
}
