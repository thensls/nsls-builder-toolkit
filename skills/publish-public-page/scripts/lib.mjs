/**
 * lib.mjs — pure logic for publish-public-page (no I/O beyond what's passed in).
 * Kept out of publish.mjs so it is unit-tested (see lib.test.mjs).
 */

export const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const SLUG_MAX = 80;
export const RESERVED_SLUGS = new Set(["ph"]);
export const TITLE_MAX = 200;
export const DESCRIPTION_MAX = 2000;
export const HTML_MAX_BYTES = 25 * 1024 * 1024;

export const BASE_URLS = {
  staging: "https://staging.invitations.nsls.org",
  production: "https://invitations.nsls.org",
};
export const ENDPOINT_PATH = "/api/portal/public-pages/publish-by-token";

export class UsageError extends Error {}

const VALUE_FLAGS = ["file", "slug", "title", "description", "token", "stage"];

export function parseArgs(argv) {
  const out = { stage: "staging", allowProduction: false, help: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") { out.help = true; continue; }
    if (arg === "--allow-production") { out.allowProduction = true; continue; }
    let name, value;
    if (arg.startsWith("--") && arg.includes("=")) {
      name = arg.slice(2, arg.indexOf("="));
      value = arg.slice(arg.indexOf("=") + 1);
    } else if (arg.startsWith("--")) {
      name = arg.slice(2);
      value = argv[++i];
      if (value === undefined || value.startsWith("--")) {
        throw new UsageError(`--${name} needs a value`);
      }
    } else {
      throw new UsageError(`Unexpected argument "${arg}"`);
    }
    if (!VALUE_FLAGS.includes(name)) throw new UsageError(`Unknown flag --${name}`);
    out[name] = value;
  }
  return out;
}

/** Returns an error string, or null when the slug is valid. */
export function validateSlug(slug) {
  if (!slug) return "--slug is required";
  if (slug.length > SLUG_MAX) return `Slug is ${slug.length} characters; the maximum is ${SLUG_MAX}.`;
  if (!SLUG_RE.test(slug)) {
    return `Slug "${slug}" is invalid. Use lowercase letters, digits and single hyphens only (e.g. fall-2026-launch), no leading/trailing hyphen.`;
  }
  if (RESERVED_SLUGS.has(slug)) return `Slug "${slug}" is reserved. Pick another.`;
  return null;
}

export function validateMeta({ title, description }) {
  if (!title || !title.trim()) return "--title is required";
  if (title.length > TITLE_MAX) return `Title is ${title.length} characters; the maximum is ${TITLE_MAX}.`;
  if (description !== undefined && description.length > DESCRIPTION_MAX) {
    return `Description is ${description.length} characters; the maximum is ${DESCRIPTION_MAX}.`;
  }
  return null;
}

/**
 * Relaxed PUBLIC-mode HTML check: non-empty, within the size cap, and looks
 * like HTML. External https: references are deliberately allowed.
 */
export function validateHtml(html, sizeBytes = Buffer.byteLength(html, "utf8")) {
  if (!html || !html.trim()) return "The HTML file is empty.";
  if (sizeBytes > HTML_MAX_BYTES) {
    return `File is ${(sizeBytes / 1048576).toFixed(1)} MB; the maximum is ${HTML_MAX_BYTES / 1048576} MB.`;
  }
  const stripped = html
    .replace(/^﻿/, "")
    .replace(/^(?:\s|<!--[\s\S]*?-->)+/, "");
  if (!/^<!doctype html/i.test(stripped) && !/^<html[\s>]/i.test(stripped)) {
    return "File does not look like HTML (expected it to start, after BOM/whitespace/comments, with <!doctype html> or <html>).";
  }
  return null;
}

/** Token precedence: flag, then env, then file contents. Returns {token, source} or null. */
export function resolveToken({ flag, env, fileContents }) {
  for (const [source, v] of [["--token flag", flag], ["NSLS_PUBLISH_TOKEN", env], ["config file", fileContents]]) {
    const t = typeof v === "string" ? v.trim() : "";
    if (t) return { token: t, source };
  }
  return null;
}

export function describeResponse(status, body) {
  const detail = body && typeof body === "object" && typeof body.error === "string" ? ` (${body.error})` : "";
  switch (status) {
    case 200:
      return { ok: true, message: `Published.${body?.publicUrl ? ` ${body.publicUrl}` : ""}` };
    case 401:
      return { ok: false, message: "Token rejected: invalid, expired, or revoked. Generate a new one from the dashboard Marketing Pages page." };
    case 400:
      return { ok: false, message: `The server rejected the request as malformed${detail}. Check the slug, title and HTML.` };
    case 413:
      return { ok: false, message: "The page is too large for the server. Reduce its size (host big images/video elsewhere)." };
    case 409:
      return { ok: false, message: "That slug is already taken. Check docs.nsls.org/<slug> first — if it is your page from an earlier attempt, it already published. Otherwise choose a different slug." };
    case 502:
      return { ok: false, message: "Upstream error. The page MAY ALREADY BE PUBLISHED — open docs.nsls.org/<slug> and check BEFORE retrying (a retry would 409 for a page that did publish)." };
    default:
      return { ok: false, message: `Unexpected response ${status}${detail}. Do not retry blindly; check docs.nsls.org/<slug> first.` };
  }
}
