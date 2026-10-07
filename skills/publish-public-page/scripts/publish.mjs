#!/usr/bin/env node
/**
 * publish.mjs — publish a public marketing page to docs.nsls.org/<slug> using a
 * person-bound publishing token. Plain HTTPS: no AWS, no internal key, no deps.
 *
 * Usage:
 *   node publish.mjs --file page.html --slug fall-launch --title "Fall Launch" \
 *     [--description "..."] [--token <t>] [--stage staging|production --allow-production]
 *
 * Token order: --token, then NSLS_PUBLISH_TOKEN, then ~/.config/nsls/publish-token.
 * The token is never printed or logged.
 */
import { readFileSync, statSync, realpathSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  parseArgs, validateSlug, validateMeta, validateHtml, resolveToken,
  describeResponse, resolveStage, UsageError, ENDPOINT_PATH,
} from "./lib.mjs";

const TOKEN_FILE = join(homedir(), ".config", "nsls", "publish-token");

const USAGE = `Usage: node publish.mjs --file <page.html> --slug <slug> --title <title>
         [--description <text>] [--token <t>]
         [--stage staging|production] [--allow-production]

Publishes to docs.nsls.org/<slug>. Defaults to STAGING. Production requires BOTH
--stage production and --allow-production.
Token: --token, else $NSLS_PUBLISH_TOKEN, else ${TOKEN_FILE}
Slug:  lowercase letters/digits/single hyphens, max 80, "ph" is reserved.`;

function fail(msg, code = 1) {
  console.error(`\n${msg}\n`);
  process.exit(code);
}

async function main() {
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (e) {
    if (e instanceof UsageError) fail(`${e.message}\n\n${USAGE}`, 2);
    throw e;
  }
  if (args.help) { console.log(USAGE); return; }

  if (!args.file) fail(`--file is required\n\n${USAGE}`, 2);
  const slugErr = validateSlug(args.slug);
  if (slugErr) fail(slugErr, 2);
  const metaErr = validateMeta(args);
  if (metaErr) fail(metaErr, 2);

  const st = resolveStage(args.stage, args.allowProduction);
  if (!st.ok) fail(st.message, 2);

  let html, size;
  try {
    size = statSync(args.file).size;
    html = readFileSync(args.file, "utf8");
  } catch (e) {
    fail(`Could not read "${args.file}": ${e.message}`);
  }
  const htmlErr = validateHtml(html, size);
  if (htmlErr) fail(htmlErr);

  let fileContents;
  try { fileContents = readFileSync(TOKEN_FILE, "utf8"); } catch { /* optional */ }
  const resolved = resolveToken({ flag: args.token, env: process.env.NSLS_PUBLISH_TOKEN, fileContents });
  if (!resolved) {
    fail(
      "No publishing token found.\n" +
      "Generate one from the dashboard Marketing Pages page, then either:\n" +
      "  export NSLS_PUBLISH_TOKEN=...   (this shell)\n" +
      `  save it to ${TOKEN_FILE}   (chmod 600)\n` +
      "  or pass --token <t>",
      2,
    );
  }

  if (args.stage === "production") console.warn("\nPRODUCTION: publishing to the live public site.\n");
  console.log(`publish-public-page — stage: ${args.stage}, slug: ${args.slug}, ${(size / 1024).toFixed(1)} KB (token from ${resolved.source})`);

  const body = { token: resolved.token, slug: args.slug, title: args.title, html };
  if (args.description !== undefined) body.description = args.description;

  let res;
  try {
    res = await fetch(st.baseUrl + ENDPOINT_PATH, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(120_000),
    });
  } catch (e) {
    fail(`Network error: ${e.message}\nThe request may or may not have reached the server — check docs.nsls.org/${args.slug} before retrying.`);
  }
  let json;
  try { json = await res.json(); } catch { json = undefined; }
  const result = describeResponse(res.status, json);
  if (!result.ok) fail(result.message);
  console.log(`\n${result.message}\n`);
}

let isMain = false;
try { isMain = realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1]); } catch { /* not a CLI run */ }
if (isMain) {
  main().catch((e) => fail(`Unexpected error: ${e.message}`));
}
