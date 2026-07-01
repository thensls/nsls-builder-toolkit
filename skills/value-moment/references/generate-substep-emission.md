# Emitting a value moment as an ignite-next `generate` substep

A value moment ships as a `generate` substep in the track JSON — the same substep
type the prototype player and the live Society app already render through the
proxy AI. This file is the exact shape to emit. For the full track/step/substep
grammar, open the `track-design` skill's `references/track-json-schema.md` (Section 7 covers
`aiPromptConfig`; Section 8 covers token mechanics). Never author the JSON from
memory — open that schema at emit time.

## The substep shape

```json
{
  "id": "ss_vm_marketing_careers",
  "slug": "vm-marketing-careers",
  "type": "generate",
  "title": "Careers your Marketing major opens up",
  "prompt": "",
  "aiPromptConfig": {
    "template": "The member's major is {major} and their state is {location}. Write two short second-person paragraphs, warm and specific: (1) 3–4 real roles this major commonly leads into; (2) the directions where demand has been climbing, described QUALITATIVELY. Do NOT state any salary, percentage, growth rate, or ranking. If you feel the pull to add a number, describe the trend in words instead.",
    "executeOn": "enter"
  }
}
```

**`prompt` is required on every substep** (the validator errors on a missing or
`null` `prompt`). For a `generate` substep it's the display text shown above the
generated content — set it to `""` when the generated paragraphs stand alone, or
a short lead-in line. The AI instruction lives in `aiPromptConfig.template`, not
in `prompt`.

This example is a **model-reasoned** moment — it uses only real collected slugs
(`{major}`, `{location}`) and forbids numbers in the prompt. For a **grounded**
moment with real figures, see "The `{data}` token" below (future-only today).

Keys that matter for a value moment:

| Key | Value |
|---|---|
| `id` | **Required** — unique across the whole track (validator errors if missing/duplicate). |
| `slug` | Optional but recommended — unique within the step; falls back to a slugified `title` if omitted. |
| `type` | `"generate"` — always, for a value moment. |
| `title` | **Required** — the screen heading the member sees. |
| `prompt` | **Required** (validator errors if missing/null). Display text above the generated content; `""` is valid. |
| `aiPromptConfig.template` | The authored prompt. Uses `{slug}` tokens for collected data; carries the grounding contract in its own words (see below). |
| `aiPromptConfig.executeOn` | `"enter"` — generate when the member lands on the screen. |
| `aiPromptConfig.model` | Optional; omit to use the app default. |

**Do NOT emit `promptMode`** (or any of the other admin-only fields —
`promptAiPrompt`, `suggestionsMode`, etc.). The schema lists them under
"Admin-Only — Never Include in Import JSON": `seed.ts` never writes them on
import, so an emitted `promptMode` is silently dropped (imported record keeps it
`null`). See the `track-design` skill's `references/track-json-schema.md` §5.

## Token mechanics (the trigger data)

`{slug}` placeholders resolve at runtime to the member's stored response for the
substep with that `slug`, OR to a profile field from a completed prerequisite
track. A value moment's `trigger` fields MUST be slugs from an earlier **`collect`**
substep in the same track (or prerequisite profile tokens) — a token that
resolves to nothing produces a generic, ungrounded paragraph, which is the exact
failure the grounding rule exists to prevent. **Use only collected data as a
trigger:** the validator technically also accepts a slug produced by an earlier
`generate` substep, but the prototype runtime (`player.js`) only forwards
collected answers, so a token pointing at another `generate`'s output validates
yet renders unresolved. For value moments the trigger is always something the
member entered anyway — keep it to `collect` slugs.

**The validator enforces this.** The `track-design` skill's `scripts/validate-track-json.mjs`
scans every string field for `{tokens}` and errors on any token not produced by
an earlier substep (or an assumed prerequisite token passed via `--assume…`). So
an invented token like `{data}` **fails validation today** — and even if it
passed, the runtime player only forwards collected profile answers, so it would
render unresolved. Only emit tokens that a real earlier `collect`/`generate`
substep produces. Verify each token's source before emitting.

## Grounding — how real figures reach the prompt

For a **grounded** value moment, the real figures must reach the prompt without
an unresolved token:

- **Today:** paste the real figures **as literal text inside the template**
  (not as a token), when the set is tiny and stable, and cite the source inline
  so a reviewer can check it. e.g. `"…Ohio marketing-role entry wages (BLS OEWS,
  May 2024): …"`. This validates and renders.
- **Future:** a companion data-fetch tool (see the SKILL's "Companion" section)
  will supply a `{data}` payload (BLS OEWS by SOC/area, O*NET growth outlook) as
  a real, resolvable input. `{data}` is **not a supported token yet** — do not
  emit it until that tool and validator support land. Design grounded prompts so
  a supplied data block drops in cleanly when it does.

For a **model-reasoned** or **illustrative** moment there is no data payload —
the template carries the honesty framing directly (qualitative, or "roughly / as
an illustration") and forbids numbers, as in the example above. See the SKILL's
faithfulness rule.

## Placement

A value moment fires right after the capture that grounds it — a pull-along
moment. Emit it as the next substep after the `collect` whose slug it consumes,
so the member gets value back immediately for what they just entered.
