// Replace {slug} tokens with captured values. Single non-recursive pass.
// Unknown tokens are left literal so mis-ordering is visible, not silently blank.
// Slug shape matches track-design's validate-track-json.mjs (lowercase kebab, no /i).
const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/g;

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export function interpolate(text, answers) {
  return String(text).replace(TOKEN_RE, (match, slug) =>
    Object.prototype.hasOwnProperty.call(answers, slug) ? escapeHtml(answers[slug]) : match
  );
}
