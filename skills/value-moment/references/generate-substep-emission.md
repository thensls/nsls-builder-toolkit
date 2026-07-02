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
    "template": "The member's profile data (their major, home state, and other answers) is provided to you alongside this instruction. Read it, then write two short second-person paragraphs, warm and specific: (1) 3–4 real roles the member's major commonly leads into; (2) the directions where demand has been climbing, described QUALITATIVELY. Do NOT state any salary, percentage, growth rate, or ranking. If you feel the pull to add a number, describe the trend in words instead.",
    "executeOn": "enter"
  }
}
```

**`prompt` is required on every substep** (the validator errors on a missing or
`null` `prompt`). For a `generate` substep it's the display text shown above the
generated content — set it to `""` when the generated paragraphs stand alone, or
a short lead-in line. The AI instruction lives in `aiPromptConfig.template`, not
in `prompt`.

**Note the template references the profile block, not `{slug}` tokens** — see
"Token mechanics" below for why. This example is a **model-reasoned** moment: it
forbids numbers in the prompt. For a **grounded** moment with real figures, add a
`grounding` spec — the companion is shipped; see "Grounding" below.

Keys that matter for a value moment:

| Key | Value |
|---|---|
| `id` | **Required** — unique across the whole track (validator errors if missing/duplicate). |
| `slug` | Optional but recommended — unique within the step; falls back to a slugified `title` if omitted. |
| `type` | `"generate"` — always, for a value moment. |
| `title` | **Required** — the screen heading the member sees. |
| `prompt` | **Required** (validator errors if missing/null). Display text above the generated content; `""` is valid. |
| `aiPromptConfig.template` | The authored AI prompt. Reference the supplied profile block for the member's data (NOT `{slug}` tokens — see below); carries the grounding contract in its own words. |
| `aiPromptConfig.executeOn` | `"enter"` — generate when the member lands on the screen. |
| `aiPromptConfig.model` | Optional; omit to use the app default. |

**Do NOT emit `promptMode`** (or any of the other admin-only fields —
`promptAiPrompt`, `suggestionsMode`, etc.). The schema lists them under
"Admin-Only — Never Include in Import JSON": `seed.ts` never writes them on
import, so an emitted `promptMode` is silently dropped (imported record keeps it
`null`). See the `track-design` skill's `references/track-json-schema.md` §5.

## Token mechanics (the trigger data)

There are **two different runtime paths**, and value moments live on the one
that does NOT substitute tokens — get this right or the AI sees literal
`{major}`:

- **Display fields** (`say`/`collect` `prompt`, screen copy): the player calls
  `interpolate(screen, answers)` and replaces `{slug}` with the member's stored
  answer live. Tokens work here.
- **AI fields** (`generate` `aiPromptConfig.template`, `chat` `chatSystemPrompt`):
  the prototype player (`player.js`) sends the template **verbatim** to the proxy
  and passes the member's answers as a **separate `profile` block** — it does NOT
  substitute `{slug}` inside the template. So `{major}` in a `generate` template
  reaches the model as the literal text `{major}`. **Write the template to read
  the supplied profile block** ("the member's major and state are in the profile
  data provided…"), not to embed `{slug}` tokens.

A value moment's `trigger` still names the collected data it depends on (for your
reasoning and for ranking), but the emitted `template` references the **profile
block**, not tokens. The data must still be collected earlier by a `collect`
substep — an empty profile produces a generic, ungrounded paragraph, the exact
failure the grounding rule exists to prevent.

**The validator also scans for tokens.** The `track-design` skill's
`scripts/validate-track-json.mjs` errors on any `{token}` (in any string field)
not produced by an earlier substep, or an assumed prerequisite token passed via
`--assume…`. So an invented token like `{data}` fails validation *and* wouldn't
be substituted in the AI path anyway. If you use a `{slug}` in a display field,
make sure an earlier `collect` substep produces it.

## Grounding — how real figures reach the prompt

For a **grounded** value moment, the real figures must reach the prompt without
an unresolved token:

- **Today:** paste the real figures **as literal text inside the template**
  (not as a token), when the set is tiny and stable, and cite the source inline
  so a reviewer can check it. e.g. `"…Ohio marketing-role entry wages (BLS OEWS,
  May 2024): …"`. This validates and renders.
- **Automatic (grounding companion, v1 shipped):** declare a `grounding` spec on
  the substep's `aiPromptConfig`. At runtime the demo proxy (Track Studio
  `/api/generate`) resolves REAL cited figures from the baked snapshot (NCES
  CIP↔SOC crosswalk + BLS OEWS) for the member's mapped major and **injects them
  into the template** with a strict "use ONLY these figures" instruction — so the
  AI phrases true numbers and invents none. No `{data}` token; the proxy appends
  the block. Shape:
  ```json
  "aiPromptConfig": {
    "template": "The member's major is in the profile. Using ONLY the labor-market figures provided, name the roles it commonly leads to and their pay.",
    "grounding": { "need": ["careers","salary"], "from": { "major": "major", "location": "home-state" } },
    "executeOn": "enter"
  }
  ```
  `from` maps which collected slugs feed the lookup — including **`location`**: map
  it to the member's state slug and the proxy injects that **state's** median wage
  (e.g. Ohio) instead of the national figure. Each career also carries **projected
  % growth** (BLS EP 2024–34). If the major isn't in the snapshot (or a figure is
  missing) the proxy injects less and the prompt stays qualitative — the
  faithfulness fallback. Write the template to *use the provided figures*, never to
  state a number itself. (Covered now: national + per-state salary, growth %, full
  CIP catalog. Fast-follow: metro-level wages.) The authoring-time `--state` flag
  on `lookup-grounding.mjs` previews the same state wages while designing.

For a **model-reasoned** or **illustrative** moment there is no data payload —
the template carries the honesty framing directly (qualitative, or "roughly / as
an illustration") and forbids numbers, as in the example above. See the SKILL's
faithfulness rule.

## Placement

A value moment fires right after the capture that grounds it — a pull-along
moment. Emit it as the next substep after the `collect` whose slug it consumes,
so the member gets value back immediately for what they just entered.
