#!/usr/bin/env node
/**
 * build_prompt_pack.mjs — export a developer prompt pack from a track.json.
 *
 * For every `generate` and `chat` substep in a track, emit:
 *   - the verbatim prompt (generate: aiPromptConfig.template; chat: chatSystemPrompt)
 *   - the profile data object the runtime passes ALONGSIDE it (the collected
 *     answers available at that point), with a synthetic representative value per
 *     field — the exact object a developer's data model must produce
 *   - a filled example: the prompt + that object, i.e. what the model receives
 *
 * Grounded in the real runtime contract (track-prototype/prototype/player.js):
 * a generate/chat substep sends its template/system string VERBATIM plus
 * `profile: state.answers` (collected answers keyed by slug). {slug} tokens are
 * NOT substituted inside generate/chat prompts — the prompt reads the profile
 * block. This pack shows devs that object so they verify the embed, not rebuild it.
 *
 * Usage:  node build_prompt_pack.mjs <track.json> [out-basename]
 *   → writes <out-basename>.json (structured) and <out-basename>.md (readable).
 *   Default out-basename: "prompt-pack".
 *
 * No dependencies (Node built-ins only). The skill layer may refine the
 * synthetic values with better domain judgment before handing the pack to devs.
 */
import { readFileSync, writeFileSync } from "node:fs";

const TOKEN_RE = /\{([a-z0-9][a-z0-9-]*)\}/g;

// Mirror the track schema / validator: an omitted slug is auto-derived from title.
function slugify(s) {
  return String(s).toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

// Synthetic representative values — keyword match on slug first, then fieldType,
// then a labeled fallback. Never real member data.
function synthValue(slug, fieldType) {
  const s = (slug || "").toLowerCase();
  const kw = [
    [/(^|-)major($|-)|field-of-study/, "Marketing"],
    [/state|location|region|city|address/, "Ohio"],
    [/(^|-)name($|-)|full-name|first-name/, "Jordan Lee"],
    [/email/, "jordan.lee@example.edu"],
    [/salary|income|target-pay|compensation/, "$65,000"],
    [/cost|budget|expense|rent/, "$2,400/month"],
    [/dream-job|target-role|role|job-title|occupation/, "Product Manager"],
    [/goal|objective|aspiration/, "Become a product manager within 18 months"],
    [/strength/, "Strategic; Empathetic; Analytical"],
    [/value/, "Growth; Integrity; Impact"],
    [/inspiration|motivation|interest/, "Building things that help people"],
    [/personality|profile/, "Analytical, people-oriented, driven"],
    [/school|college|university/, "State University"],
    [/year|grad|class-of/, "Junior"],
    [/mentor/, "Alex Rivera, Director of Product"],
  ];
  for (const [re, v] of kw) if (re.test(s)) return v;
  switch (fieldType) {
    case "number": return 42;
    case "multiselect":
    case "multipleSelect": return ["<option A>", "<option B>"];
    case "email": return "jordan.lee@example.edu";
    default: return `<sample ${slug || "value"}>`;
  }
}

function extractPrompt(sub) {
  if (sub.type === "generate") {
    const cfg = sub.aiPromptConfig || {};
    if (cfg.template) return { text: cfg.template, field: "aiPromptConfig.template", note: null };
    if (cfg.promptId)
      return {
        text: null, field: "aiPromptConfig.promptId",
        note: `Prompt-by-ID reference "${cfg.promptId}" — resolved from the Prompt table at runtime; no inline template in the track JSON. Export the Prompt row separately.`,
      };
    if (sub.prompt) return { text: sub.prompt, field: "prompt (fallback)", note: "No aiPromptConfig; runtime falls back to the display `prompt`." };
    return { text: null, field: null, note: "No template found." };
  }
  if (sub.type === "chat")
    return { text: sub.chatSystemPrompt ?? null, field: "chatSystemPrompt",
      note: sub.chatSystemPrompt === undefined ? "No chatSystemPrompt set." : null };
  return { text: null, field: null, note: null };
}

function build(tracks) {
  const out = [];
  // `available` accumulates ACROSS tracks: pass a track plus its prerequisites in
  // order (e.g. [Welcome, Personal Insights, Clarity]) and a dependent track's
  // prompts see upstream fields, matching the runtime's cross-track profile
  // (the validator's assumed-prerequisite tokens). Single-track input just uses
  // its own fields.
  const available = []; // collect/generate/computed slugs seen so far, in order
  for (const track of tracks) {
    for (const step of track.steps || []) {
      for (const sub of step.substeps || []) {
        if (sub.type === "generate" || sub.type === "chat") {
          const { text, field, note } = extractPrompt(sub);
          const contract = {};
          for (const slug of available) contract[slug.slug] = {
            from_substep: slug.id, source_type: slug.source_type,
            fieldType: slug.fieldType || "text",
            example: synthValue(slug.slug, slug.fieldType),
          };
          const tokens = text ? [...new Set([...text.matchAll(TOKEN_RE)].map((m) => m[1]))] : [];
          out.push({
            track: track.id || track.title,
            step: step.title,
            substep_id: sub.id,
            slug: sub.slug || slugify(sub.title || "") || null,
            type: sub.type,
            executeOn: sub.aiPromptConfig?.executeOn || null,
            prompt_field: field,
            prompt: text,
            note,
            tokens_in_prompt: tokens, // author intent; NOT substituted at runtime
            profile_contract: contract,
          });
        }
        // What the runtime stores in the profile (state.answers):
        //  - collect responses (member-entered)
        //  - generate outputs (the validator treats these as downstream data)
        //    → slug auto-derived from title when omitted, matching the validator.
        //  - an `assessment-results` substep with an explicit slug writes the
        //    computed personality profile (player.js maybeRunAssessmentResults,
        //    gated on sub.slug) — regardless of the substep's `type`.
        if (sub.type === "collect" || sub.type === "generate") {
          const slug = sub.slug || slugify(sub.title || "");
          if (slug)
            available.push({
              slug, id: sub.id, fieldType: sub.fieldType,
              source_type: sub.type === "collect" ? "collected" : "generated",
            });
        } else if (sub.fieldType === "assessment-results" && sub.slug) {
          available.push({
            slug: sub.slug, id: sub.id, fieldType: sub.fieldType,
            source_type: "computed",
          });
        }
      }
    }
  }
  return out;
}

function toMarkdown(entries) {
  const L = [];
  L.push("# Developer Prompt Pack");
  L.push("");
  L.push("Every `generate` / `chat` substep in the track, with the exact prompt and the");
  L.push("**data object it draws from** — the member's stored responses, keyed by slug.");
  L.push("");
  L.push("**Runtime contract.** In the live app, `{slug}` tokens in `template` /");
  L.push("`chatSystemPrompt` / `prompt` are replaced with the member's stored response");
  L.push("for that slug (track schema §8). So the data your model must provide is the");
  L.push("stored-response object below; every `{slug}` in the prompt resolves from it.");
  L.push("(The standalone *prototype* player differs — it sends the template verbatim");
  L.push("plus the whole profile block rather than substituting — but the shipped");
  L.push("implementation substitutes, so wire the tokens to these values.)");
  L.push("");
  for (const e of entries) {
    L.push(`## ${e.step} — \`${e.substep_id}\` (${e.type})`);
    if (e.executeOn) L.push(`_executeOn: ${e.executeOn}_`);
    L.push("");
    if (e.note) L.push(`> ${e.note}`);
    if (e.prompt != null) {
      L.push(`**Prompt** (\`${e.prompt_field}\`, sent verbatim):`);
      L.push("```text");
      L.push(e.prompt);
      L.push("```");
    }
    if (e.tokens_in_prompt.length)
      L.push(`_Tokens in the prompt (resolved from the data object below at runtime): ${e.tokens_in_prompt.map((t) => "`{" + t + "}`").join(", ")}_`);
    L.push("");
    L.push("**data object your model must provide** (stored responses; representative values):");
    L.push("```json");
    const obj = {};
    for (const [slug, meta] of Object.entries(e.profile_contract)) obj[slug] = meta.example;
    L.push(JSON.stringify(obj, null, 2));
    L.push("```");
    if (Object.keys(e.profile_contract).length) {
      L.push("");
      L.push("| key | from substep | origin | type |");
      L.push("|---|---|---|---|");
      for (const [slug, meta] of Object.entries(e.profile_contract))
        L.push(`| \`${slug}\` | \`${meta.from_substep}\` | ${meta.source_type} | ${meta.fieldType} |`);
    } else {
      L.push("_(no collected fields available before this substep)_");
    }
    L.push("");
  }
  return L.join("\n");
}

function main() {
  const [, , inPath, outBase = "prompt-pack"] = process.argv;
  if (!inPath) {
    console.error("usage: build_prompt_pack.mjs <track.json> [out-basename]");
    process.exit(1);
  }
  let raw;
  try {
    raw = JSON.parse(readFileSync(inPath, "utf-8"));
  } catch (err) {
    console.error(`Could not read/parse "${inPath}": ${err.message}`);
    process.exit(1);
  }
  const tracks = Array.isArray(raw) ? raw : [raw];
  const entries = build(tracks);
  writeFileSync(`${outBase}.json`, JSON.stringify(entries, null, 2));
  writeFileSync(`${outBase}.md`, toMarkdown(entries));
  console.log(`Wrote ${outBase}.json and ${outBase}.md — ${entries.length} AI substep(s).`);
}

main();
