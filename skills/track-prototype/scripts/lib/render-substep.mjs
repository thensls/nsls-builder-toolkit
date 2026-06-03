// Render one substep to static HTML using design-kit classes (tp- prefix to avoid
// collisions). The player wires behavior via data-* hooks and does {slug} interpolation
// at runtime. ctx.samples[slug] supplies baked AI text for generate/chat.

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Prototypes deploy to public URLs, so drop any imageUrl whose scheme isn't safe
// (blocks javascript:/vbscript:/data:text). Allows http(s), protocol-relative,
// root/relative paths, and data:image/. Returns "" for anything else.
export function safeUrl(u) {
  const s = String(u ?? "").trim();
  if (s === "") return "";
  if (/^(https?:\/\/|\/\/|\/|\.\/|\.\.\/)/i.test(s)) return s;
  if (/^data:image\//i.test(s)) return s;
  if (/^[a-z][a-z0-9+.-]*:/i.test(s)) return ""; // any other explicit scheme -> drop
  return s; // bare relative filename (e.g. "intro.png")
}

const continueBtn = (label = "Continue") =>
  `<button class="tp-btn tp-btn-default tp-btn-lg" data-next>${esc(label)}</button>`;

function renderSay(sub) {
  if (sub.fieldType === "celebration") return renderCelebration(sub);
  // banner / banner-multiple / default say
  const extra = (sub.bannerTexts || []).map((t) => `<p class="tp-banner-line" data-tpl>${esc(t)}</p>`).join("");
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p>${extra}</div>${continueBtn()}`;
}

function renderCelebration(sub) {
  const tasks = (sub.celebrationTasks || [])
    .map((t) => `<li class="tp-task">${esc(t)}</li>`).join("");
  const next = sub.celebrationNextStepsTitle
    ? `<div class="tp-next"><h3>${esc(sub.celebrationNextStepsTitle)}</h3><p data-tpl>${esc(sub.celebrationNextStepsDescription || "")}</p></div>`
    : "";
  return `<div class="tp-celebration">
    <div class="tp-confetti" data-confetti></div>
    <p class="tp-prose" data-tpl>${esc(sub.prompt)}</p>
    ${tasks ? `<ul class="tp-tasks">${tasks}</ul>` : ""}
    ${next}
  </div>${continueBtn(sub.celebrationButtonText || "Okay, got it!")}`;
}

function optionList(sub) {
  const opts = Array.isArray(sub.options) ? sub.options : [];
  return opts.map((o, i) => {
    const text = typeof o === "string" ? o : (o.text ?? "");
    const desc = typeof o === "object" && o.description ? `<span class="tp-opt-desc">${esc(o.description)}</span>` : "";
    const safeImg = typeof o === "object" ? safeUrl(o.imageUrl) : "";
    const img = safeImg ? `<img class="tp-opt-img" src="${esc(safeImg)}" alt="">` : "";
    return `<button class="tp-option" data-option data-value="${esc(text)}" data-index="${i}">${img}<span>${esc(text)}</span>${desc}</button>`;
  }).join("");
}

function renderCollect(sub) {
  const slug = esc(sub.slug || "");
  const prompt = `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div>`;
  switch (sub.fieldType) {
    case "select":
    case "multi-select":
    case "image-multiselect":
    case "dropdown-with-checkboxes":
      return `${prompt}<div class="tp-options tp-options-grid" data-slug="${slug}" data-multi="${sub.fieldType !== "select"}">${optionList(sub)}</div>${continueBtn()}`;
    case "currency":
      return `${prompt}<div class="tp-input-wrap"><span class="tp-currency">$</span><input class="tp-input tp-input-currency" type="number" data-input data-slug="${slug}" placeholder="0"></div>${continueBtn()}`;
    default: // text, textarea, work, education, dream-job-*, unknown -> generic text capture
      return `${prompt}<input class="tp-input" type="text" data-input data-slug="${slug}" placeholder="Type your answer…">${continueBtn()}`;
  }
}

function renderGenerate(sub, ctx) {
  const sample = ctx.samples && ctx.samples[sub.slug];
  const body = sample
    ? `<div class="tp-ai-output">${esc(sample)}</div>`
    : `<div class="tp-ai-placeholder">AI would write this from your answers. (No sample baked in.)</div>`;
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div>${body}${continueBtn()}`;
}

function renderChat(sub, ctx) {
  const sample = (ctx.samples && ctx.samples[sub.slug]) || "Tell me what's on your mind.";
  return `<div class="tp-chat">
    <div class="tp-bubble tp-bubble-ai" data-tpl>${esc(sub.prompt)}</div>
    <div class="tp-bubble tp-bubble-ai">${esc(sample)}</div>
  </div>${continueBtn("Continue")}`;
}

function renderAssessmentResults(sub) {
  return `<div class="tp-prose"><p data-tpl>${esc(sub.prompt)}</p></div><div class="tp-results">Assessment results display</div>${continueBtn()}`;
}

export function renderSubstep(sub, ctx = {}) {
  const title = sub.showTitle && sub.title ? `<h2 class="tp-title">${esc(sub.title)}</h2>` : "";
  let inner;
  if (sub.fieldType === "assessment-results") inner = renderAssessmentResults(sub);
  else if (sub.type === "chat") inner = renderChat(sub, ctx);
  else if (sub.type === "generate") inner = renderGenerate(sub, ctx);
  else if (sub.type === "say") inner = renderSay(sub);
  else inner = renderCollect(sub);
  return `<section class="tp-screen" data-substep="${esc(sub.id)}">${title}${inner}</section>`;
}
