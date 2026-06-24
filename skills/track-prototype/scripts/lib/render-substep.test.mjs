import { test } from "node:test";
import assert from "node:assert/strict";
import { renderSubstep, safeUrl, computeAssessmentProgress } from "./render-substep.mjs";

test("safeUrl drops javascript: and other unsafe schemes, keeps safe ones", () => {
  assert.equal(safeUrl("javascript:alert(1)"), "");
  assert.equal(safeUrl("data:text/html,<x>"), "");
  assert.equal(safeUrl("/img/a.png"), "/img/a.png");
  assert.equal(safeUrl("https://x/y.png"), "https://x/y.png");
  assert.equal(safeUrl("intro.png"), "intro.png");
  assert.equal(safeUrl("data:image/png;base64,AAAA"), "data:image/png;base64,AAAA");
});

test("safeUrl strips control chars so a tab can't smuggle a javascript: scheme", () => {
  assert.equal(safeUrl("java\tscript:alert(1)"), "");
  assert.equal(safeUrl("java\nscript:alert(1)"), "");
});

test("option with a javascript: imageUrl emits no img tag", () => {
  const html = renderSubstep({ id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "image-multiselect",
    options: [{ text: "A", imageUrl: "javascript:alert(1)" }] }, {});
  assert.doesNotMatch(html, /javascript:/);
  assert.doesNotMatch(html, /<img/);
});

test("say/banner renders prompt + a Continue button", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "Welcome", type: "say", fieldType: "banner" }, {});
  assert.match(html, /Welcome/);
  assert.match(html, /data-next/);
  assert.match(html, /class="[^"]*tp-btn/);
});

test("collect/text renders an input bound by data-input + data-slug", () => {
  const html = renderSubstep({ id: "x", slug: "name", title: "Name", prompt: "Your name?", type: "collect", fieldType: "text" }, {});
  assert.match(html, /data-input/);
  assert.match(html, /data-slug="name"/);
});

test("collect/multi-select renders one option button per option", () => {
  const sub = { id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "multi-select",
    options: [{ text: "A" }, { text: "B" }] };
  const html = renderSubstep(sub, {});
  assert.equal((html.match(/data-option/g) || []).length, 2);
});

test("dropdown-with-checkboxes with dropdownOptions and no options renders one button per dropdown option", () => {
  const sub = { id: "x", slug: "scale", title: "S", prompt: "Rate", type: "collect", fieldType: "dropdown-with-checkboxes",
    dropdownOptions: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"] };
  const html = renderSubstep(sub, {});
  assert.equal((html.match(/data-option/g) || []).length, 10);
});

test("checkboxOptions are appended after dropdownOptions", () => {
  const sub = { id: "x", slug: "scale", title: "S", prompt: "Rate", type: "collect", fieldType: "dropdown-with-checkboxes",
    dropdownOptions: ["1", "2"], checkboxOptions: ["Not sure"] };
  const html = renderSubstep(sub, {});
  assert.equal((html.match(/data-option/g) || []).length, 3);
  // checkbox option renders after the dropdown options
  assert.ok(html.indexOf('data-value="Not sure"') > html.indexOf('data-value="2"'));
});

test("optionsSourceSlug renders a data-options-source attribute on the grid", () => {
  const sub = { id: "x", slug: "narrow", title: "N", prompt: "Narrow down", type: "collect", fieldType: "multi-select",
    optionsSourceSlug: "strengths-12" };
  const html = renderSubstep(sub, {});
  assert.match(html, /data-options-source="strengths-12"/);
});

test("a substep without optionsSourceSlug renders no data-options-source attribute", () => {
  const sub = { id: "x", slug: "v", title: "V", prompt: "Pick", type: "collect", fieldType: "multi-select",
    options: [{ text: "A" }, { text: "B" }] };
  const html = renderSubstep(sub, {});
  assert.doesNotMatch(html, /data-options-source/);
});

test("generate renders the baked sample when provided", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" },
    { samples: { cs: "Your career statement draft." } });
  assert.match(html, /Your career statement draft\./);
});

test("generate without a sample renders a clearly-marked placeholder", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "CS", prompt: "Draft:", type: "generate", fieldType: "text" }, {});
  assert.match(html, /tp-ai-placeholder/);
});

test("unknown fieldType falls back to a generic text screen (no throw)", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "P", type: "collect", fieldType: "totally-new" }, {});
  assert.match(html, /P/);
});

test("chat renders data-chat-log, data-chat-input, data-chat-send and a seed bubble", () => {
  const html = renderSubstep({ id: "x", slug: "coach", title: "Coach", prompt: "Hello!", type: "chat", fieldType: "text" },
    { samples: { coach: "I am your coach." } });
  assert.match(html, /data-chat-log/);
  assert.match(html, /data-chat-input/);
  assert.match(html, /data-chat-send/);
  assert.match(html, /I am your coach\./);   // seed bubble present
});

test("chat without a sample still renders the interactive hooks with a fallback seed", () => {
  const html = renderSubstep({ id: "x", slug: "coach", title: "Coach", prompt: "Hello!", type: "chat", fieldType: "text" }, {});
  assert.match(html, /data-chat-log/);
  assert.match(html, /data-chat-input/);
  assert.match(html, /data-chat-send/);
});

// --- Fidelity pass: real ignite-next markup ----------------------------------

test("image-multiselect renders the real ImageMultiselectInput card classes, single-select", () => {
  const html = renderSubstep({ id: "x", slug: "q1", title: "Q", prompt: "Pick", type: "collect", fieldType: "image-multiselect",
    options: [{ text: "Plan it", imageUrl: "/img/a.png" }] }, {});
  assert.match(html, /data-multi="false"/);                    // single-select like the app
  assert.match(html, /rounded-xl overflow-hidden transition-all bg-medium/); // card
  assert.match(html, /h-48 bg-mediumPlus overflow-hidden aspect-square/);    // image section
  assert.match(html, /bg-success/);                            // selection badge
  assert.match(html, /src="\/img\/a\.png"/);
});

test("image-multiselect with autoProgressOnSelect hides Continue and marks the grid", () => {
  const sub = { id: "x", slug: "q1", title: "Q", prompt: "P", type: "collect", fieldType: "image-multiselect",
    autoProgressOnSelect: true, options: [{ text: "A" }] };
  const html = renderSubstep(sub, {});
  assert.match(html, /data-auto-progress="true"/);
  assert.doesNotMatch(html, /data-next/);                      // app hides Continue here
});

test("image-multiselect without autoProgress keeps the sticky Continue row", () => {
  const sub = { id: "x", slug: "q1", title: "Q", prompt: "P", type: "collect", fieldType: "image-multiselect",
    options: [{ text: "A" }] };
  const html = renderSubstep(sub, {});
  assert.match(html, /data-next/);
  assert.match(html, /sticky bottom-0/);                       // app's sticky footer
});

test("collect/select renders a native <select data-input> styled like the app trigger", () => {
  const html = renderSubstep({ id: "x", slug: "age", title: "Age", prompt: "Age?", type: "collect", fieldType: "select",
    options: ["18", "19"] }, {});
  assert.match(html, /<select[^>]*data-input[^>]*data-slug="age"/);
  assert.match(html, /border-2 border-mediumPlus bg-light/);   // selectTriggerVariants
  assert.match(html, /<option value="18">18<\/option>/);
  assert.doesNotMatch(html, /data-option/);                    // no grid — walker uses the fill path
});

test("multi-select renders the 2-col grid with min/max status and real card classes", () => {
  const html = renderSubstep({ id: "x", slug: "vals", title: "V", prompt: "Pick", type: "collect", fieldType: "multi-select",
    multiselectMinSelections: 3, multiselectMaxSelections: 3,
    options: [{ text: "Alpha – the first" }, { text: "Beta" }] }, {});
  assert.match(html, /grid grid-cols-2/);
  assert.match(html, /Please select at least 3 options/);
  assert.match(html, /data-ms-status/);
  assert.match(html, /<span class="[^"]*font-semibold[^"]*">Alpha<\/span>/); // dash-split title
  assert.match(html, /the first/);                                           // dash-split description
});

test("say screens use the app page skeleton (substep-content + bg-light section)", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "Welcome", type: "say", fieldType: "banner" }, {});
  assert.match(html, /id="substep-content"/);
  assert.match(html, /px-4 py-8 sm:px-8 sm:py-12 bg-light/);
  assert.match(html, /id="substep-content-inner"/);
});

test("substep imageUrl renders the app's rounded image block", () => {
  const html = renderSubstep({ id: "x", title: "T", prompt: "P", type: "say", fieldType: "banner", imageUrl: "/img/intro/intro-1.png" }, {});
  assert.match(html, /max-h-\[38dvh\]/);
  assert.match(html, /src="\/img\/intro\/intro-1\.png"/);
});

test("chat renders real ChatInterface rows/bubbles and keeps the contract hooks", () => {
  const html = renderSubstep({ id: "x", slug: "coach", title: "C", prompt: "Hi!", type: "chat", fieldType: "text" },
    { samples: { coach: "Seed." } });
  assert.match(html, /flex justify-start/);                     // bubble row
  assert.match(html, /tp-bubble tp-bubble-ai/);                 // walker contract class
  assert.match(html, /bg-medium text-dark rounded-tl-none!/);   // app bubble classes
  assert.match(html, /step-input w-full resize-none/);          // app textarea styling
  assert.match(html, /data-chat-send/);
  assert.match(html, /data-next/);                              // way to advance
});

test("generate renders the title pill + content card around .tp-ai-output", () => {
  const html = renderSubstep({ id: "x", slug: "cs", title: "Career Statement", prompt: "Draft:", type: "generate", fieldType: "text" },
    { samples: { cs: "Your draft." } });
  assert.match(html, /rounded-full text-sm font-medium bg-mocha text-light/); // pill
  assert.match(html, /rounded-2xl px-6 pt-8 pb-6 -mt-5 bg-medium/);           // card
  assert.match(html, /tp-ai-output/);
  assert.match(html, /Your draft\./);
});

test("celebration: section-completion format renders Congrats + section name + Continue", () => {
  const html = renderSubstep({ id: "x", title: "Done", prompt: "", type: "say", fieldType: "celebration",
    celebrationCompletedSection: "Professional Environment", celebrationNextSection: "Interests" }, {});
  assert.match(html, /Congrats! You have completed:/);
  assert.match(html, /Professional Environment/);
  assert.match(html, /Next Up: Interests/);
  assert.match(html, /data-next/);
});

test("celebration with a /video/ imageUrl renders a <video> hero", () => {
  const html = renderSubstep({ id: "x", title: "Done", prompt: "Nice", type: "say", fieldType: "celebration",
    imageUrl: "/video/complete.mp4" }, {});
  assert.match(html, /<video src="\/video\/complete\.mp4"/);
  assert.match(html, /autoplay loop muted playsinline/);
});

test("dropdown-with-checkboxes renders the wheel svg + scale + checkbox rows", () => {
  const html = renderSubstep({ id: "x", slug: "dc", title: "Career Clarity Rating", prompt: "Rate.", type: "collect",
    fieldType: "dropdown-with-checkboxes", textFieldLabel: "What's unclear?",
    dropdownOptions: ["1", "2"], checkboxOptions: ["Industry"] }, {});
  assert.match(html, /tp-wheel/);
  assert.match(html, /Career Clarity/);                          // wheel label
  assert.match(html, /Very Unclear/);                            // clarity min label
  assert.equal((html.match(/data-option/g) || []).length, 3);    // 2 scale + 1 checkbox
});

test("education renders the real entry form; school field carries the data-input", () => {
  const html = renderSubstep({ id: "x", slug: "edu", title: "E", prompt: "School?", type: "collect", fieldType: "education" }, {});
  assert.match(html, /School Name/);
  assert.match(html, /Major \/ Field of Study/);
  assert.match(html, /Add Education/);
  assert.match(html, /data-input data-slug="edu"/);
  assert.match(html, /Skip \(edit in profile\)/);                // app's skip button
});

test("dream-job-select renders accordion items with data-option on header and select button", () => {
  const html = renderSubstep({ id: "x", slug: "dj", title: "DJ", prompt: "Pick", type: "collect", fieldType: "dream-job-select",
    options: [{ text: "Coach", shortDescription: "Helps people", detailedDescription: "Long detail ".repeat(12) }] }, {});
  assert.match(html, /<details/);
  assert.match(html, /Select This Job/);
  assert.equal((html.match(/data-option/g) || []).length, 2);    // summary + button (same value)
  assert.match(html, /Helps people/);
});

test("assessment-results renders the results shell with the carousel mount point", () => {
  const html = renderSubstep({ id: "x", title: "R", prompt: "", type: "say", fieldType: "assessment-results" }, {});
  assert.match(html, /Personality Assessment Results/);
  assert.match(html, /data-assessment-results/);
});

test("personality progress tracker renders when ctx.progress has this substep", () => {
  const sub = { id: "q9", slug: "q9", title: "Q", prompt: "P", type: "collect", fieldType: "image-multiselect", options: [{ text: "A" }] };
  const html = renderSubstep(sub, { progress: { q9: { section: 2, totalSections: 5, question: 3, questionsInSection: 10 } } });
  assert.match(html, /Personality Assessment/);
  assert.match(html, /Section 2 of 5/);
  assert.match(html, /Question 3 of 10/);
});

test("computeAssessmentProgress: sections split on celebrations, needs >= 40 questions", () => {
  const q = (i) => ({ id: `q${i}`, type: "collect", fieldType: "image-multiselect" });
  const cel = (i) => ({ id: `c${i}`, type: "say", fieldType: "celebration" });
  const subs40 = [...Array.from({ length: 20 }, (_, i) => q(i)), cel(1), ...Array.from({ length: 20 }, (_, i) => q(20 + i)), cel(2)];
  const p = computeAssessmentProgress(subs40);
  assert.deepEqual(p.q0, { section: 1, totalSections: 2, question: 1, questionsInSection: 20 });
  assert.deepEqual(p.q39, { section: 2, totalSections: 2, question: 20, questionsInSection: 20 });
  // below the 40-question threshold → no tracker
  assert.deepEqual(computeAssessmentProgress([q(1), q(2), cel(1)]), {});
});

test("text collect renders step-input + suggestion chips", () => {
  const html = renderSubstep({ id: "x", slug: "name", title: "N", prompt: "Name?", type: "collect", fieldType: "text",
    suggestions: ["Maya"] }, {});
  assert.match(html, /step-input w-full/);
  assert.match(html, /data-suggestion="Maya"/);
  assert.match(html, /border-dashed border-mediumPlus/);         // suggestion button variant
});

test("currency renders the $ prefix and pl-8 input", () => {
  const html = renderSubstep({ id: "x", slug: "sal", title: "S", prompt: "Salary?", type: "collect", fieldType: "currency" }, {});
  assert.match(html, />\$<\/div>/);
  assert.match(html, /step-input w-full pl-8/);
  assert.match(html, /inputmode="decimal"/);
});
