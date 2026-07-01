# Emitting a value moment as an ignite-next `generate` substep

A value moment ships as a `generate` substep in the track JSON — the same substep
type the prototype player and the live Society app already render through the
proxy AI. This file is the exact shape to emit. For the full track/step/substep
grammar, open `track-design/references/track-json-schema.md` (Section 7 covers
`aiPromptConfig`; Section 8 covers token mechanics). Never author the JSON from
memory — open that schema at emit time.

## The substep shape

```json
{
  "type": "generate",
  "promptMode": "text",
  "title": "Careers your Marketing major opens up",
  "aiPromptConfig": {
    "template": "The member's major is {major} and their state is {location}. Using ONLY the labor-market figures provided here — {data} — write two short second-person paragraphs: (1) the three most common careers for this major; (2) the two with the fastest projected demand growth. Warm, specific, plain language. Use only the provided figures; if a figure is missing, describe the trend qualitatively and do not invent a number.",
    "executeOn": "enter"
  }
}
```

Keys that matter for a value moment:

| Key | Value |
|---|---|
| `type` | `"generate"` — always, for a value moment. |
| `promptMode` | `"text"`. |
| `title` | The screen heading the member sees. |
| `aiPromptConfig.template` | The authored prompt. Uses `{slug}` tokens for collected data; carries the grounding contract in its own words (see below). |
| `aiPromptConfig.executeOn` | `"enter"` — generate when the member lands on the screen. |
| `aiPromptConfig.model` | Optional; omit to use the app default. |

## Token mechanics (the trigger data)

`{slug}` placeholders resolve at runtime to the member's stored response for the
substep with that `slug`, OR to a profile field from a completed prerequisite
track. A value moment's `trigger` fields MUST be slugs collected **earlier** in
the same track (or prerequisite profile tokens) — a token that resolves to
nothing produces a generic, ungrounded paragraph, which is the exact failure the
grounding rule exists to prevent. Verify each token's source before emitting.

## The `{data}` token — how grounding reaches the prompt

For a **grounded** value moment, the real figures reach the prompt as context.
Two ways, in preference order:

1. **Fetched at build/runtime by the companion data tool** (future — see the
   SKILL's "Companion" section). The tool supplies a `{data}` payload (e.g. BLS
   OEWS rows by SOC/area, O*NET growth outlook) that the template references. The
   template instructs the model to phrase, not invent.
2. **Pasted into the template at authoring time** as a small literal block, when
   the figure set is tiny and stable. Cite the source inline so a reviewer can
   check it.

For a **model-reasoned** or **illustrative** moment there is no `{data}` token —
the template must instead carry the honesty framing directly (qualitative, or
"roughly / as an illustration"). See the SKILL's faithfulness rule.

## Placement

A value moment fires right after the capture that grounds it — a pull-along
moment. Emit it as the next substep after the `collect` whose slug it consumes,
so the member gets value back immediately for what they just entered.
