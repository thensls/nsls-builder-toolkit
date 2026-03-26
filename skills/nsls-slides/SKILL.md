---
name: nsls-slides
description: >-
  Generate on-brand NSLS/Society PowerPoint presentations and upload them to
  Google Drive as Google Slides. Uses Society brand fonts (HW Cigars + Inter)
  and color palette. Trigger phrases: nsls slides, make a presentation, create
  slides, build a deck, society presentation, nsls deck, pptx
category: nsls
version: 1.0.0
key_capabilities: pptx_creator.py, upload-and-convert
when_to_use: Generating branded NSLS/Society slide decks, presentations, pitch decks
---

# NSLS Slides Skill

## Purpose

Generate branded NSLS/Society PowerPoint presentations from structured JSON content
and upload them to Google Drive as native Google Slides.

**Pipeline** (mirrors the `.docx` → Google Doc workflow exactly):
1. Claude generates slide content as JSON
2. `pptx_creator.py` builds a branded `.pptx`
3. `drive_manager.rb upload-and-convert` uploads + converts to Google Slides
4. Returns the Google Slides URL

## Brand Tokens

### Colors

| Name      | Hex       | Usage                          |
|-----------|-----------|--------------------------------|
| cream     | `#FAF8EE` | Primary background             |
| espresso  | `#201414` | Primary text, dark backgrounds |
| yellow    | `#F2DA4E` | Accent, section dividers       |
| lavender  | `#969BDE` | Accent                         |
| pink      | `#F3AEE6` | Accent                         |
| green     | `#9BD778` | Accent                         |
| taupe     | `#C8BDAF` | Accent, neutral warmth         |

### Typography

| Role      | Font              | Size  | Leading | Tracking |
|-----------|-------------------|-------|---------|----------|
| Logotype  | HW Cigars SemiBold| —     | —       | —        |
| Headline  | HW Cigars Medium  | 70pt  | 70pt    | -5       |
| Subhead   | Inter Regular     | 25pt  | 28pt    | 0        |
| Body      | Inter Regular     | 10pt  | 15pt    | 0        |
| Buttons   | Inter Regular     | 10pt  | —       | +5       |

*Note: pptx_creator.py uses proportionally scaled sizes optimized for slide legibility.*

### Fonts

- **HW Cigars**: Purchased from Heavyweight type foundry. Installed at `~/Library/Fonts/`.
  Files: `HW Cigars Medium.otf`, `HW Cigars SemiBold.otf`
- **Inter**: Free Google variable font. Use system name `"Inter"`.

## Slide Layouts

### `title` — Hero slide
Large Cigars Medium headline + Inter subhead on cream background.

```json
{
  "layout": "title",
  "headline": "Find your people.\nFind your path.",
  "subhead": "The community-driven success platform."
}
```

### `section` — Section divider
Bold headline on a brand color background. Defaults to yellow.

```json
{
  "layout": "section",
  "text": "Our Mission",
  "bg": "yellow"
}
```

### `content` — Title + body/bullets
Cigars title + yellow rule + Inter body text and/or bulleted list.

```json
{
  "layout": "content",
  "title": "What We Offer",
  "body": "Optional intro paragraph.",
  "bullets": ["Point one", "Point two", "Point three"]
}
```

### `two_column` — Side-by-side columns
Title + yellow rule + two equal text columns.

```json
{
  "layout": "two_column",
  "title": "Then vs. Now",
  "left": "Left column content.",
  "right": "Right column content."
}
```

### `quote` — Pull quote
Large centered quote in Cigars Medium on brand color background.

```json
{
  "layout": "quote",
  "text": "Leadership is not about a title.",
  "attribution": "— John Maxwell",
  "bg": "lavender"
}
```

**Valid `bg` values**: `cream`, `yellow`, `lavender`, `pink`, `green`, `taupe`, `espresso`

## Full Workflow

### Step 1 — Generate JSON content

Claude drafts the slide structure as JSON. Work with Kevin to define:
- Number and order of slides
- Layout for each slide
- Specific copy per slide

### Step 2 — Generate the .pptx (and optionally a PDF)

```bash
# PPTX only
echo '<json>' | /tmp/brand-env/bin/python3 \
  ~/.claude/skills/nsls-slides/scripts/pptx_creator.py \
  --output /tmp/presentation.pptx

# PPTX + PDF (PDF renders HW Cigars correctly everywhere, including Google Drive)
echo '<json>' | /tmp/brand-env/bin/python3 \
  ~/.claude/skills/nsls-slides/scripts/pptx_creator.py \
  --output /tmp/presentation.pptx \
  --pdf
```

**Font rendering by format:**

| Format | HW Cigars | Inter |
|---|---|---|
| PPTX in PowerPoint (local, font installed) | ✓ | ✓ |
| PPTX in Google Slides | ✗ falls back to Arial | ✓ |
| PDF in Google Drive viewer | ✓ embedded by Keynote | ✓ |

**Use `--pdf` when sharing a link for viewing/presenting.** The PPTX is for editing.
The `--pdf` flag uses Keynote to render and export — requires Keynote installed (it is).

### Step 3 — Resolve target folder (optional)

```bash
~/.claude/skills/google-docs/scripts/drive_manager.rb resolve-folder \
  --path "NSLS Presentations/2026"
```

### Step 4 — Upload and convert to Google Slides

```bash
~/.claude/skills/google-docs/scripts/drive_manager.rb upload-and-convert \
  --file /tmp/presentation.pptx \
  --folder-id {folder_id} \
  --name "2026-03-02 - Presentation Title"
```

Returns JSON with `web_view_link` — share that link with Kevin.

### Step 5 — Clean up

```bash
rm /tmp/presentation.pptx
```

## Setup Requirements

### Python environment

The `pptx_creator.py` script requires the `python-pptx` library. The venv at
`/tmp/brand-env` has it installed. For persistence across reboots, reinstall:

```bash
python3 -m venv /tmp/brand-env
/tmp/brand-env/bin/pip install python-pptx pillow -q
```

Or install system-wide (if not in externally-managed env):
```bash
pip3 install python-pptx
```

### Fonts

HW Cigars fonts must be installed at `~/Library/Fonts/`:
- `HW Cigars Medium.otf`
- `HW Cigars SemiBold.otf`

Source files: `/tmp/nsls-cigars-font/HW Cigars/Opentype/` (session temp; back up to permanent location).

To reinstall:
```bash
cp "/path/to/HW Cigars Medium.otf" ~/Library/Fonts/
cp "/path/to/HW Cigars SemiBold.otf" ~/Library/Fonts/
```

### Drive credentials

Uses the shared Google OAuth token from `~/.claude/.google/`. No additional setup
needed if `drive_manager.rb` is already authorized.

## Example: Full End-to-End Run

```bash
# 1. Generate slides JSON (Claude produces this based on Kevin's brief)
cat > /tmp/slides.json <<'JSON'
{
  "slides": [
    {
      "layout": "title",
      "headline": "Society by NSLS\nQ2 2026 Update",
      "subhead": "Leadership development at scale."
    },
    {
      "layout": "section",
      "text": "Key Results",
      "bg": "yellow"
    },
    {
      "layout": "content",
      "title": "Member Growth",
      "bullets": ["15.2M total members", "+18% QoQ activation", "42% Ignite adoption"]
    }
  ]
}
JSON

# 2. Build .pptx
/tmp/brand-env/bin/python3 ~/.claude/skills/nsls-slides/scripts/pptx_creator.py \
  --input /tmp/slides.json \
  --output /tmp/q2-update.pptx

# 3. Upload to Drive as Google Slides
~/.claude/skills/google-docs/scripts/drive_manager.rb upload-and-convert \
  --file /tmp/q2-update.pptx \
  --name "2026 Q2 - Society Update"

# 4. Clean up
rm /tmp/slides.json /tmp/q2-update.pptx
```

## Notes & Future Enhancements

- **Tracking**: The brand spec calls for -5 tracking on headlines. python-pptx supports
  this via XML manipulation (`<a:rPr spc="-500">`). Not implemented in v1 — fonts are
  embedded correctly; tracking is a visual refinement.
- **Logo placement**: Brand spec allows Society® logotype in corner. Could add optional
  logo image insertion once a PNG export of the logotype is available.
- **Image slides**: `python-pptx` supports inserting images. A future `image` layout
  could place a photo within a brand color frame (matching the framing shown in brand deck).
- **Folder default**: Could auto-resolve to a default "NSLS Presentations" Drive folder
  if no `--folder-id` is specified.
