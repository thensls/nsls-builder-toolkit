---
name: prompt-pack
description: >-
  Use when you need to hand a Society (ignite-next) track's AI prompts to
  developers ready to implement — the exact prompt text for every generate/chat
  substep plus the profile data object the runtime passes with it, so devs verify
  the data-model embed instead of reverse-engineering the plumbing. Produced from
  a track.json in the design phase or standalone. Triggers: "prompt pack", "export
  the prompts", "developer handoff for prompts", "embed the data in the prompt",
  "prompt data contract", "hand the prompts to devs", "what data does this prompt
  need".
---

# prompt-pack

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** — reading a track's `track.json` and this skill's references. Free.
2. **Configuration / new-content** — running the script to write `prompt-pack.md`
   + `.json` locally, or into a Google Doc for devs. OK by default.
3. **No external writes.** This pack uses **synthetic representative values only** —
   never real member data. Do not pull live member answers into a shared pack
   (that's PII); if a real example is truly needed, anonymize first and confirm.

## Purpose

A developer implementing a track shouldn't have to reverse-engineer two things
at once: *what the prompt says* and *how the member's data reaches it.* This skill
hands them both, resolved: for every `generate`/`chat` substep, the exact prompt
text and the **profile data object the runtime passes alongside it**, with a
representative value per field. The dev plugs in the prompt verbatim and just
confirms their data model produces that object — the plumbing is spelled out, not
inferred.

## The runtime contract (why the pack is shaped this way)

In the **live app**, `{slug}` tokens in `aiPromptConfig.template`,
`chatSystemPrompt`, and `prompt` are replaced at runtime with the member's stored
response for that slug (see the `track-design` skill's
`references/track-json-schema.md` §8). So whether a prompt references data by
`{slug}` tokens or reads it from context, the underlying data contract is the
same: **the set of stored responses the prompt draws on.** The developer's real
job is to *produce that data object* and wire the tokens to it — which is exactly
what the pack makes explicit (the object + which substep each field comes from).

**Prototype vs. live nuance:** the standalone prototype player
(`track-prototype`'s `prototype/player.js`) does *not* substitute tokens inside a
generate/chat template — it sends the template verbatim plus the whole profile
block, so prototype-authored prompts often read the profile block directly. The
shipped implementation substitutes per the schema. Either way the data object is
the contract; the pack gives devs the object so both paths resolve.

## When to use

- In the **design phase**, once `track.json` exists, to generate the dev handoff
  alongside the Student Experience Doc.
- **Standalone**, on any existing track, to answer "what data does this prompt
  need" or to re-export after prompt edits.
- NOT for authoring the prompts (that's `track-design` / `value-moment`) — this
  exports finished ones.

## Quick Start

```bash
node scripts/build_prompt_pack.mjs <track.json> [out-basename]
# → out-basename.md (readable dev handoff) + out-basename.json (structured)
```
No dependencies. Then review + refine the synthetic values (below) and hand devs
the `.md` (or drop it into a Google Doc via `gdoc-build`).

## Process

1. **Run the script** on the track's `track.json`. It walks every step in order,
   and for each `generate`/`chat` substep emits: the verbatim prompt (and which
   field it came from), the tokens written in it (author intent), and the
   **profile contract** — every collected slug available at that point, with a
   synthetic value and its source substep.
2. **Refine the synthetic values with judgment.** The script fills plausible
   defaults by slug/keyword; improve any that read generically so the filled
   example looks real to a developer. Keep them synthetic — never real members.
3. **Handle `promptId` references.** A generate substep using
   `aiPromptConfig.promptId` has no inline template (it's resolved from the Prompt
   table at runtime). The pack flags these; export the referenced Prompt row
   separately so the dev has the actual text.
4. **Deliver.** Hand devs the `.md` (verbatim prompts + the exact profile object
   to produce). Optionally publish as a Google Doc with `gdoc-build`.

## What's in the pack (per AI substep)

- **Prompt** — verbatim, with the source field (`aiPromptConfig.template` or
  `chatSystemPrompt`), sent to the AI as-is.
- **Tokens in the prompt** — any `{slug}` the author wrote; these resolve from
  the data object below at runtime (live app), so each must have a matching key.
- **profile object** — the JSON object the data model must provide, keyed by
  slug, with a representative value each.
- **Source table** — each profile key → the substep that collects it → its type.

## Rules

- **Prompt text is verbatim.** Never paraphrase or "clean up" the exported prompt
  — devs implement exactly what ships.
- **Synthetic values only.** No real member data in a shared pack.
- **Position matters.** The profile object for a substep includes only fields
  collected *before* it — don't add fields the member hasn't entered yet.

## Reference index
- `scripts/build_prompt_pack.mjs` — the extractor (Node, no deps).
- The `track-design` skill's `references/track-json-schema.md` — substep/token grammar.
- `value-moment` — authors the generate prompts this pack exports; same profile-block contract.
