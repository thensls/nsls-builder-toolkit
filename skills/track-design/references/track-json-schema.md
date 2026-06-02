# Ignite-Next Track JSON Schema Reference

This document is the contract for `src/data/tracks-export.json`. A JSON generator and a JSON validator both target it. Field names are quoted verbatim from `prisma/schema.prisma` and `prisma/seed.ts`. When this doc conflicts with those source files, the source files win.

---

## 1. Loading Mechanism

| Item | Value |
|------|-------|
| Import file | `src/data/tracks-export.json` — a JSON **array** of track objects |
| Loader | `prisma/seed.ts` |
| Command | `pnpm db:seed` |
| Key | Upsert by `id` on Track, Step, and SubStep |
| Stale content | Anything in the DB whose `id` is absent from the JSON gets `isActive = false` (not deleted) |
| `--fresh` mode | Wipes all tracks, steps, substeps, and user data, then recreates. Refuses against any connection string containing `sslmode=require` or `neon.tech` unless `ALLOW_FRESH_SEED=true` is set |
| Admin authoring path | tRPC `*.create` mutations (the admin UI) — **not** the bulk import path |

There is no separate import script. The only import path is `pnpm db:seed` reading `tracks-export.json`.

**How the export is produced:** Run `pnpm tsx scripts/export-tracks.ts` (or the equivalent npm script). It queries the DB for `isActive: true, isDraft: false` tracks, serializes them, and overwrites `tracks-export.json`.

---

## 2. Track Object

### Required fields (author must supply)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Stable unique string (cuid-style). Also used as `trackGroupId` — seed writes `trackGroupId: track.id` |
| `title` | `string` | |
| `steps` | `Step[]` | Array of step objects; see Section 3 |

### Optional fields (seed reads these if present)

| Field | Type | Seed default if absent |
|-------|------|------------------------|
| `slug` | `string` | Auto-generated from `title` via `generateSlug` (unique within the seed run) |
| `description` | `string \| null` | `null` |
| `onEnter` | `string \| null` | `null` |
| `onComplete` | `string \| null` | `null` |
| `isLocked` | `boolean` | `false` |
| `imageUrl` | `string \| null` | Present in export, but **seed does not read it** — Track `imageUrl` is not written during seeding |

### Fields the author MUST NOT emit

These are set by the seed or are DB-managed and will be ignored or overwritten:

- `trackGroupId` — seed always sets this to `track.id`
- `version` — always set to `1` by seed
- `isDraft` — always set to `false` by seed
- `order` — set to array index by seed
- `isActive` — managed by stale-deactivation logic
- `createdAt`, `updatedAt` — DB-managed timestamps

---

## 3. Step Object

### Required fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Stable unique string |
| `title` | `string` | |
| `substeps` | `SubStep[]` | Array of substep objects; see Section 4 |

### Optional fields

| Field | Type | Seed default if absent |
|-------|------|------------------------|
| `slug` | `string` | Auto-generated from `title` (unique within the track) |
| `description` | `string \| null` | `null` |
| `imageUrl` | `string \| null` | `null` |
| `onEnter` | `string \| null` | `null` |
| `onComplete` | `string \| null` | `null` |

### Auto-managed — never emit

`order` (array index), `trackId`, `version`, `isActive`, `createdAt`, `updatedAt`

---

## 4. SubStep Object

### Required fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | `string` | Stable unique string |
| `title` | `string` | |
| `prompt` | `string` | Display text shown above the interaction |
| `type` | `string` | See Section 6 for valid values |

`slug` is optional — if absent, auto-generated from `title` (unique within the step).

### Optional fields with seed defaults

Every field below is read by `buildSubstepData` in `seed.ts`. Absence is detected via `"fieldName" in sub`.

> **To get a field's default, OMIT the key entirely. Do NOT emit an explicit `null`.** The seed uses `"field" in sub ? sub.field : default`, and `in` is true for an explicit `null` — so `null` overrides the default and is written to the DB. This matters for fields with non-null defaults (`showTitle`, `celebrationShowConfetti`, `celebrationConfettiCount`, `celebrationShowPath`, `freeResponseEnabled`, `autoProgressOnSelect`, `isAssessmentQuestion`, and the array fields `suggestions`, `dropdownOptions`, `checkboxOptions`, `bannerTexts`, `celebrationTasks`). The JSON generator must only include keys it intends to set.

| Field | Type | Seed default |
|-------|------|--------------|
| `fieldType` | `string \| null` | `null` |
| `showTitle` | `boolean` | `false` |
| `callout` | `string \| null` | `null` |
| `calloutMode` | `string \| null` | `null` — values in practice: `"text"` |
| `calloutPrompt` | `string \| null` | `null` |
| `calloutManual` | `string \| null` | `null` |
| `calloutGenerated` | `string \| null` | `null` |
| `chatSystemPrompt` | `string \| null` | `null` — system prompt fed to the LLM for `chat` substeps |
| `aiLastGeneratedAt` | `string \| null` | `null` — ISO-8601 string; seed converts to `Date` |
| `aiGeneratedTitle` | `string \| null` | `null` |
| `aiGeneratedMessage` | `string \| null` | `null` |
| `suggestions` | `string[]` | `[]` |
| `options` | `Json \| null` | `null` — see Section 7 for shape variants |
| `validationRules` | `Json \| null` | `null` |
| `aiPromptConfig` | `Json \| null` | `null` — see Section 7 for shape |
| `imageUrl` | `string \| null` | `null` |
| `imagePrompt` | `string \| null` | `null` |
| `multiselectMode` | `string \| null` | `null` — `"manual"` or `"reference"` in practice |
| `multiselectPrompt` | `string \| null` | `null` |
| `multiselectSchema` | `string \| null` | `null` — stringified JSON schema |
| `optionsSourceSlug` | `string \| null` | `null` — slug of a prior substep whose collected response populates the options list |
| `multiselectMinSelections` | `number \| null` | `null` |
| `multiselectMaxSelections` | `number \| null` | `null` |
| `dropdownOptions` | `string[]` | `[]` |
| `textFieldLabel` | `string \| null` | `null` |
| `helpText` | `string \| null` | `null` — tooltip shown on hover of the `?` icon |
| `checkboxOptions` | `string[]` | `[]` |
| `freeResponseEnabled` | `boolean` | `false` |
| `freeResponseLabel` | `string \| null` | `null` |
| `bannerTexts` | `string[]` | `[]` |
| `celebrationTasks` | `string[]` | `[]` |
| `celebrationNextStepsTitle` | `string \| null` | `null` |
| `celebrationNextStepsDescription` | `string \| null` | `null` |
| `celebrationButtonText` | `string \| null` | `null` |
| `celebrationShowConfetti` | `boolean` | `true` |
| `celebrationConfettiCount` | `number \| null` | `30` |
| `celebrationShowPath` | `boolean` | `false` |
| `celebrationCompletedSection` | `string \| null` | `null` |
| `celebrationNextSection` | `string \| null` | `null` |
| `celebrationHighlightSlug` | `string \| null` | `null` — slug of a prior substep whose response is displayed as a highlight card |
| `celebrationHighlightTitle` | `string \| null` | `null` — label for the highlight card |
| `isAssessmentQuestion` | `boolean` | `false` |
| `assessmentSectionName` | `string \| null` | `null` |
| `assessmentSectionNumber` | `number \| null` | `null` |
| `assessmentTotalSections` | `number \| null` | `null` |
| `assessmentQuestionNumber` | `number \| null` | `null` |
| `assessmentQuestionsInSection` | `number \| null` | `null` |
| `autoProgressOnSelect` | `boolean` | `false` — auto-submits when a single option is selected |
| `onEnter` | `string \| null` | `null` |
| `onExit` | `string \| null` | `null` |
| `nextSubStepId` | `string \| null` | `null` |
| `nextStepId` | `string \| null` | `null` |
| `nextTrackId` | `string \| null` | `null` |

### Auto-managed — never emit

`order` (array index within the substep list), `stepId`, `version`, `isActive`, `createdAt`, `updatedAt`

---

## 5. Admin-Only Fields — Never Include in Import JSON

These fields exist in the Prisma `SubStep` model but are **never exported** by `export-tracks.ts` and are **never written** by `buildSubstepData` in `seed.ts`. On first create the seed explicitly sets them to `null`; on upsert update it omits them entirely so existing production values are preserved.

| Field | Purpose (for reference) |
|-------|-------------------------|
| `promptMode` | `"text"` or `"ai"` — controls how `prompt` is sourced |
| `promptAiPrompt` | AI prompt used to generate the `prompt` field |
| `promptGenerated` | Cached AI-generated prompt text |
| `suggestionsMode` | `"manual"` or `"prompt"` |
| `suggestionsPrompt` | AI prompt for generating suggestions |
| `suggestionsSchema` | Optional JSON schema for AI suggestion response |
| `suggestionsMin` | Minimum number of suggestions to generate |
| `suggestionsMax` | Maximum number of suggestions to generate |
| `multiselectGenerationMin` | Min items AI should generate |
| `multiselectGenerationMax` | Max items AI should generate |
| `contextTag` | Context extraction tag (e.g., `"profile:name"`) — not in export |
| `celebrationShowProfileButton` | Whether to show a profile button on celebration screens — not in export |

**Prompt author note:** `seed.ts` documents this exclusion list in its `buildSubstepData` JSDoc comment. Verify the list by reading lines 28–32 of `prisma/seed.ts`.

**Correction from task prompt:** The task prompt listed `contextTag` and `celebrationShowProfileButton` under admin-only fields. Confirmed against `export-tracks.ts` — neither field appears in the export output. Both are correctly classified as admin-only / never emit.

---

## 6. Value Vocabulary

### `type` values

| Value | Meaning |
|-------|---------|
| `"say"` | Display-only content; no user input collected |
| `"collect"` | Collects user input; `fieldType` controls the input widget |
| `"generate"` | AI generates content and displays it; `aiPromptConfig` drives the generation |
| `"chat"` | Conversational AI exchange; `chatSystemPrompt` provides LLM instructions |
| `"ai-process"` | In the Prisma schema but **not present in any exported track** as of this writing |

**Important:** `type` is a plain `String` column in Postgres — not a DB-enforced enum. The app code enforces valid values at the component-routing layer.

### Common `fieldType` values

These are the values observed in `tracks-export.json`. The field is a plain string — not a DB enum. **This table is a descriptive guide only** — `type` and `fieldType` are plain strings, and the pairings listed here are conventions observed in the live data, not validation rules. Do not build a strict per-type `fieldType` validator from this table.

| Value | Used with `type` | Notes |
|-------|-----------------|-------|
| `"text"` | `say`, `collect`, `chat`, `generate` | Most common value; all `generate` substeps use it; `say` uses it for text-display variants |
| `"select"` | `collect` | |
| `"multi-select"` | `collect` | |
| `"image-multiselect"` | `collect` | |
| `"dropdown-with-checkboxes"` | `collect` | |
| `"currency"` | `collect` | |
| `"education"` | `collect` | |
| `"work"` | `collect` | |
| `"banner"` | `say` | |
| `"banner-multiple"` | `say` | |
| `"celebration"` | `say` | |
| `"assessment-results"` | `say` | |
| `"dream-job-select"` | `collect` | |
| `"dream-job-requirements"` | `collect` | |
| `""` (empty string) | `chat` | Present but empty; observed on `chat` substeps |

**Not observed in current export (valid per CLAUDE.md, zero instances in `tracks-export.json`):** `"textarea"` — accepted by the app as a `collect` field type but not present in any exported track as of this writing.

---

## 7. Complex Field Shapes

### `options`

Three valid shapes, depending on context:

**Simple string array** (rare in practice; more common for `collect` text inputs):
```json
["Option A", "Option B"]
```

**Rich objects for `collect` with image-based or routed selection:**
```json
[
  {
    "text": "Creating a plan to address the issue",
    "answerId": "1737073145427x700685284803346400",
    "imageUrl": "/img/assessment/1737073145427x700685284803346400.png"
  }
]
```

Optional keys on collect option objects: `text` (required), `answerId`, `imageUrl`, `imagePrompt`, `nextSubStepId`

**Description objects for `generate`:**
```json
[
  {
    "text": "High-stakes, deadline-driven teams",
    "description": "Fast-paced projects with tight deadlines and clear accountability"
  }
]
```

### `aiPromptConfig`

Two shapes observed in the export:

**Prompt-by-ID reference** (looked up from the `Prompt` table at runtime):
```json
{ "promptId": "inspirations" }
```

**Inline template** (with optional model and execute trigger):
```json
{
  "model": "gpt-4o",
  "template": "You have access to all user data...",
  "executeOn": "enter"
}
```

Keys: `promptId` (string), `model` (string, defaults to `"gpt-4o-2024-08-06"` from the Prompt model), `template` (string), `executeOn` (string — `"enter"` observed).

### `multiselectSchema`

A stringified JSON schema. Store as a `string`, not a parsed object:
```json
"multiselectSchema": "{\"type\":\"array\",\"items\":{\"type\":\"string\"}}"
```

### `validationRules`

`Json?` in the schema. In practice often an empty array `[]` or `null`. Shape is app-defined and not validated by seed.

---

## 8. Token Mechanics

Tokens are `{slug}` placeholders in string fields (typically `prompt`, `chatSystemPrompt`, or `template` inside `aiPromptConfig`). At runtime the app replaces `{some-slug}` with the user's previously stored response for the substep whose `slug` is `some-slug`.

Rules:
- The token slug must match the `slug` of a substep that was collected **earlier** in the user's current session, OR a profile field from a completed prerequisite track.
- `optionsSourceSlug` is related but distinct: it tells the multi-select widget to use a prior substep's collected response array as its option list (e.g., `"optionsSourceSlug": "values-selection"` in `multiselectMode: "reference"`).
- Responses are keyed by `(userId, subStepId)` in the `Response` table. The slug is the human-readable address used in JSON authoring; the runtime resolves it to the DB `subStepId`.

---

## 9. Real Examples (verbatim from `tracks-export.json`)

### `say` (banner type)

```json
{
  "id": "cmla9qdrf0005sytvbuyhok5r",
  "slug": "intro-1",
  "title": "Intro 1",
  "prompt": "Ignite is here to help you launch a successful and fulfilling career. You can try it out now, by training your Coach and building your Personal Profile.\n\nOur goal is to give you the tools and connections to turn your potential into progress.",
  "type": "say",
  "fieldType": "banner",
  "showTitle": false,
  "callout": "",
  "calloutMode": "text",
  "chatSystemPrompt": null,
  "calloutPrompt": null,
  "calloutManual": "",
  "calloutGenerated": null,
  "suggestions": [],
  "options": [],
  "validationRules": [],
  "aiPromptConfig": null,
  "imageUrl": "/img/intro/intro-1.png",
  "imagePrompt": null,
  "multiselectMode": "manual",
  "multiselectPrompt": null,
  "multiselectSchema": null,
  "optionsSourceSlug": null,
  "multiselectMinSelections": null,
  "multiselectMaxSelections": null,
  "dropdownOptions": [],
  "textFieldLabel": null,
  "helpText": null,
  "checkboxOptions": [],
  "freeResponseEnabled": false,
  "freeResponseLabel": null,
  "bannerTexts": [],
  "celebrationTasks": [],
  "celebrationNextStepsTitle": null,
  "celebrationNextStepsDescription": null,
  "celebrationButtonText": null,
  "celebrationShowConfetti": true,
  "celebrationConfettiCount": 30,
  "celebrationShowPath": false,
  "celebrationCompletedSection": null,
  "celebrationNextSection": null,
  "celebrationHighlightSlug": null,
  "celebrationHighlightTitle": null,
  "isAssessmentQuestion": false,
  "autoProgressOnSelect": false,
  "aiLastGeneratedAt": null,
  "aiGeneratedTitle": null,
  "aiGeneratedMessage": null,
  "onEnter": null,
  "onExit": null,
  "nextSubStepId": null,
  "nextStepId": null,
  "nextTrackId": null
}
```

### `collect` — simple text

```json
{
  "id": "cmla9qdrj0008sytve6wz89vs",
  "slug": "name",
  "title": "Name",
  "prompt": "What do you want to be called?",
  "type": "collect",
  "fieldType": "text",
  "showTitle": false,
  "callout": "",
  "calloutMode": "text",
  "chatSystemPrompt": null,
  "calloutPrompt": null,
  "calloutManual": "",
  "calloutGenerated": null,
  "suggestions": [],
  "options": [],
  "validationRules": [],
  "aiPromptConfig": null,
  "imageUrl": null,
  "imagePrompt": null,
  "multiselectMode": "manual",
  "multiselectPrompt": null,
  "multiselectSchema": null,
  "optionsSourceSlug": null,
  "multiselectMinSelections": null,
  "multiselectMaxSelections": null,
  "dropdownOptions": [],
  "textFieldLabel": null,
  "helpText": null,
  "checkboxOptions": [],
  "freeResponseEnabled": false,
  "freeResponseLabel": null,
  "bannerTexts": [],
  "celebrationTasks": [],
  "celebrationNextStepsTitle": null,
  "celebrationNextStepsDescription": null,
  "celebrationButtonText": null,
  "celebrationShowConfetti": true,
  "celebrationConfettiCount": 30,
  "celebrationShowPath": false,
  "autoProgressOnSelect": false,
  "aiLastGeneratedAt": null,
  "aiGeneratedTitle": null,
  "aiGeneratedMessage": null,
  "onEnter": null,
  "onExit": null,
  "nextSubStepId": null,
  "nextStepId": null,
  "nextTrackId": null
}
```

### `collect` — image-multiselect with rich option objects

```json
{
  "id": "cmla9qdsa000ksytvhnz8mrf3",
  "slug": "question-1",
  "title": "Question 1",
  "prompt": "When dealing with a stressful situation, I'm more likely to start by:",
  "type": "collect",
  "fieldType": "image-multiselect",
  "showTitle": false,
  "callout": "",
  "calloutMode": "text",
  "chatSystemPrompt": null,
  "suggestions": [],
  "options": [
    {
      "text": "Creating a plan to address the issue",
      "answerId": "1737073145427x700685284803346400",
      "imageUrl": "/img/assessment/1737073145427x700685284803346400.png"
    },
    {
      "text": "Processing my feelings and/or seeking support",
      "answerId": "1737073157096x776507020994412500",
      "imageUrl": "/img/assessment/1737073157096x776507020994412500.png"
    }
  ],
  "validationRules": [],
  "aiPromptConfig": null,
  "imageUrl": "",
  "imagePrompt": "",
  "multiselectMode": "manual",
  "multiselectPrompt": "",
  "multiselectSchema": "",
  "optionsSourceSlug": null,
  "multiselectMinSelections": null,
  "multiselectMaxSelections": null,
  "dropdownOptions": [],
  "textFieldLabel": "",
  "helpText": null,
  "checkboxOptions": [],
  "freeResponseEnabled": false,
  "freeResponseLabel": null,
  "isAssessmentQuestion": true,
  "autoProgressOnSelect": true,
  "aiLastGeneratedAt": null,
  "aiGeneratedTitle": null,
  "aiGeneratedMessage": null,
  "onEnter": null,
  "onExit": null,
  "nextSubStepId": null,
  "nextStepId": null,
  "nextTrackId": null
}
```

### `chat`

```json
{
  "id": "cmla9qdsb001vsytvbqqili14",
  "slug": "personality-chat",
  "title": "Personality Chat",
  "prompt": "Would you like to talk more about your personality results",
  "type": "chat",
  "fieldType": "text",
  "showTitle": false,
  "chatSystemPrompt": "[AI CONTEXT BLOCK]\n\nYou are an **AI Career Specialist** who helps people find work that aligns not only with what they do well, but with who they truly are. ... [~4000 chars truncated — full system prompt in the export file]",
  "callout": "",
  "calloutMode": "text",
  "suggestions": [],
  "options": [],
  "validationRules": [],
  "aiPromptConfig": null,
  "imageUrl": null,
  "imagePrompt": null,
  "multiselectMode": null,
  "multiselectPrompt": null,
  "multiselectSchema": null,
  "optionsSourceSlug": null,
  "multiselectMinSelections": null,
  "multiselectMaxSelections": null,
  "dropdownOptions": [],
  "freeResponseEnabled": false,
  "autoProgressOnSelect": false,
  "onEnter": null,
  "onExit": null,
  "nextSubStepId": null,
  "nextStepId": null,
  "nextTrackId": null
}
```

### `generate`

```json
{
  "id": "cmla9qduq002qsytvfvxsd79e",
  "slug": "work-environment-result",
  "title": "work environment result",
  "prompt": "Based on all your responses so far, here's a description of the work environment that best fits you:",
  "type": "generate",
  "fieldType": "text",
  "showTitle": false,
  "chatSystemPrompt": null,
  "suggestions": [],
  "options": [
    {
      "text": "High-stakes, deadline-driven teams",
      "description": "Fast-paced projects with tight deadlines and clear accountability"
    },
    {
      "text": "Minimal supervision, maximum autonomy",
      "description": "Freedom to set own pace and prioritize tasks under pressure"
    }
  ],
  "validationRules": [],
  "aiPromptConfig": {
    "model": "gpt-4o",
    "template": "You have access to all user data that includes results across 5 personality tests ... [template truncated — ~600 chars]",
    "executeOn": "enter"
  },
  "imageUrl": null,
  "imagePrompt": null,
  "multiselectMode": "manual",
  "multiselectPrompt": null,
  "multiselectSchema": null,
  "optionsSourceSlug": null,
  "autoProgressOnSelect": false,
  "onEnter": null,
  "onExit": null,
  "nextSubStepId": null,
  "nextStepId": null,
  "nextTrackId": null
}
```

---

## Discrepancies from Task Prompt — Corrections Applied

1. **Track `slug` is not optional in Prisma schema** — the schema declares `slug String` (no `?`), but the seed auto-generates it from `title` if absent from the JSON. So the slug is optional *in the JSON* but required *in the DB*. The author may omit it and let seed generate it, or supply a stable slug.

2. **Track `imageUrl` is exported but silently ignored by seed** — the task prompt says "exported but not read by seed." Confirmed: `trackData` in `seed.ts` (lines 285–296) does not include `imageUrl`. The track's image must be set via the admin UI after seeding.

3. **`ai-process` type exists in schema but has zero instances in the live export** — confirmed by inspecting all 132 substeps. The type is defined but unused.

4. **`aiPromptConfig` shape is NOT `{ model, template, executeOn }`** — that shape exists for some substeps, but the primary real-world shape is `{ "promptId": "inspirations" }` (a lookup reference), and sometimes a hybrid `{ "promptId": ..., "template": ... }`. The `model` and `executeOn` keys are optional and omitted when the prompt-by-ID pattern is used.

5. **`contextTag` and `celebrationShowProfileButton` are correctly admin-only** — neither appears in `export-tracks.ts` output. Confirmed against source.

6. **`freeResponseEnabled` default** — seed.ts line 83 confirms default is `false` when absent.

7. **No `{slug}` token placeholders found in the live export** — token substitution is documented in the app architecture but no current track uses `{slug}` tokens in `prompt` fields. Token patterns appear as Markdown-style references inside `chatSystemPrompt` and `aiPromptConfig.template` (e.g., data injected by the runtime context builder), not as `{slug}` placeholders keyed to collected responses.
