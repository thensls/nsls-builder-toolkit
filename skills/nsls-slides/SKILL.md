---
name: nsls-slides
description: >-
  Generate on-brand NSLS or Society PowerPoint presentations and upload them to
  Google Drive as Google Slides. Supports two brands: NSLS (honor society —
  Lexend Deca + Avenir, navy/teal/gold) and Society (by the NSLS — HW Cigars +
  Inter, cream/yellow). Always ask the user which brand before creating slides.
  Trigger phrases: nsls slides, make a presentation, create slides, build a
  deck, society presentation, nsls deck, pptx
category: nsls
version: 2.0.0
key_capabilities: pptx_creator.py, gws upload to Google Slides
when_to_use: Generating branded NSLS or Society slide decks, presentations, pitch decks
---

# NSLS Slides Skill

## Purpose

Generate branded PowerPoint presentations from structured JSON content
and upload them to Google Drive as native Google Slides.

**Before creating any slides, ask the user:**
> "Do you want this to be NSLS branded, or Society branded?"

- **NSLS** — the honor society brand (nsls.org). Navy/teal/gold, Lexend Deca + Avenir.
- **Society** — the new brand (Society by the NSLS). Cream/yellow, HW Cigars + Inter.

Pass `--brand nsls` or `--brand society` to `pptx_creator.py`.

**Pipeline** (mirrors the `.docx` → Google Doc workflow exactly):
1. Claude generates slide content as JSON
2. `pptx_creator.py --brand {nsls|society}` builds a branded `.pptx`
3. `gws drive files create --upload` uploads the `.pptx` and converts it to Google Slides
4. Returns the Google Slides URL

---

## Brand Tokens

### Society Brand (default — `--brand society`)

#### Colors

| Name      | Hex       | Usage                          |
|-----------|-----------|--------------------------------|
| cream     | `#FAF8EE` | Primary background             |
| espresso  | `#201414` | Primary text, dark backgrounds |
| yellow    | `#F2DA4E` | Accent, section dividers       |
| lavender  | `#969BDE` | Accent                         |
| pink      | `#F3AEE6` | Accent                         |
| green     | `#9BD778` | Accent                         |
| taupe     | `#C8BDAF` | Accent, neutral warmth         |

#### Typography

| Role      | Font              | Size  |
|-----------|-------------------|-------|
| Headline  | HW Cigars Medium  | 70pt  |
| Logotype  | HW Cigars SemiBold| —     |
| Body      | Inter Regular     | 10pt  |

**Fonts**: HW Cigars — purchased from Heavyweight type foundry, installed at `~/Library/Fonts/`. Inter — free Google font.

**Valid `bg` values**: `cream`, `yellow`, `lavender`, `pink`, `green`, `taupe`, `espresso`

---

### NSLS Brand (`--brand nsls`)

#### Colors

| Name      | Hex       | Usage                          |
|-----------|-----------|--------------------------------|
| white     | `#FFFFFF` | Primary background             |
| navy      | `#18315A` | Dark backgrounds, accent       |
| darkblue  | `#425B76` | Secondary text / backgrounds   |
| bluegray  | `#33475B` | Primary text                   |
| teal      | `#0091AE` | Links, CTA accent              |
| gold      | `#EEB117` | Honor society gold accent      |
| lightblue | `#E5F5F8` | Light accent backgrounds       |
| nearblack | `#191919` | Near-black text                |

#### Typography

| Role      | Font         | Size  |
|-----------|-------------|-------|
| Headline  | Lexend Deca | 70pt  |
| Logotype  | Lexend Deca | —     |
| Body      | Avenir      | 10pt  |

**Fonts**: Lexend Deca — free Google font. Avenir — macOS system font.

**Valid `bg` values**: `white`, `navy`, `darkblue`, `bluegray`, `teal`, `gold`, `lightblue`, `nearblack`

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

**Pick one unique filename per run** from the current date and time, such as
`nsls-deck-20260302-1405.pptx`, and write that literal name into every command below
(build, upload, clean-up). Never a fixed name like `presentation.pptx`: the deck is built
in your home folder, so a fixed name could overwrite a file the user already has there, and
step 5 would then delete it. (A shell variable won't carry it between commands, because each
Bash tool call starts a fresh shell.)

**Preflight first, and STOP if it fails:**

Mac/Linux commands here call the launcher by its full path, `~/.local/bin/nsls-python`, so nothing
depends on this session's `PATH`. On Windows, replace it with plain `nsls-python`.

```bash
~/.local/bin/nsls-python -c 'import pptx' && echo PREFLIGHT_OK
```

If you don't see `PREFLIGHT_OK`, don't run the build commands below — the builder would get a raw
import traceback or `command not found`. Say in one plain sentence that the slide tooling needs
repairing and re-run the toolkit installer for them. See "Python environment" under Setup Requirements.

**Repair, by platform** (a launcher the installer just wrote isn't on this session's PATH yet):
- *Mac/Linux:* `curl -fsSL https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.sh | bash`,
  then preflight again.
- *Windows:* `powershell -NoProfile -Command "iwr -useb https://raw.githubusercontent.com/thensls/nsls-builder-toolkit/main/install.ps1 | iex"`,
  then have the builder fully restart Claude Code (Task Manager → End task on every Claude entry,
  reopen, say "back") and preflight again. Never run `install.sh` on Windows.

```bash
# Society brand (default)
echo '<json>' | ~/.local/bin/nsls-python \
  ~/.claude/local-plugins/nsls-builder-toolkit/skills/nsls-slides/scripts/pptx_creator.py \
  --brand society --output ~/nsls-deck-<YYYYMMDD-HHMM>.pptx

# NSLS brand
echo '<json>' | ~/.local/bin/nsls-python \
  ~/.claude/local-plugins/nsls-builder-toolkit/skills/nsls-slides/scripts/pptx_creator.py \
  --brand nsls --output ~/nsls-deck-<YYYYMMDD-HHMM>.pptx

# Add --pdf for font-safe PDF export (works with either brand)
echo '<json>' | ~/.local/bin/nsls-python \
  ~/.claude/local-plugins/nsls-builder-toolkit/skills/nsls-slides/scripts/pptx_creator.py \
  --brand society --output ~/nsls-deck-<YYYYMMDD-HHMM>.pptx --pdf
```

**Font rendering by format:**

| Format | HW Cigars | Inter |
|---|---|---|
| PPTX in PowerPoint (local, font installed) | ✓ | ✓ |
| PPTX in Google Slides | ✗ falls back to Arial | ✓ |
| PDF in Google Drive viewer | ✓ embedded by Keynote | ✓ |

**Use `--pdf` when sharing a link for viewing/presenting.** The PPTX is for editing.
The `--pdf` flag uses Keynote to render and export — requires Keynote installed (it is).

### Step 3 — Pick the Drive folder (optional)

No folder named? Skip this; the deck lands in My Drive. If the user wants it in a folder,
ask for the folder's link: the ID is the part after `/folders/`. Pass it as `parents` in
step 4.

### Step 4 — Upload and convert to Google Slides

Runs on the toolkit's own `gws` profile, the same one `/gdoc-build` uses. If `gws` reports
an auth error or a 403, run `/gdoc-build`'s step 0 (the gws doctor) and retry.

Run it as ONE command, exactly as shown. Each Bash tool call starts a fresh shell, so an
`export` sent on its own is gone by the next call, and `gws` would fall back to its default
profile (a 403, or the wrong Google account).

```bash
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/gws-profiles/nsls-gdocs-skill"; set -o pipefail; cd ~ && gws drive files create \
  --json '{"name":"2026-03-02 - Presentation Title","mimeType":"application/vnd.google-apps.presentation"}' \
  --upload nsls-deck-<YYYYMMDD-HHMM>.pptx \
  --upload-content-type "application/vnd.openxmlformats-officedocument.presentationml.presentation" \
  --format json | tail -10
```

- **Build the deck in `~` and run `gws` from `~`.** `--upload` rejects a path outside the
  current directory, so a deck in `/tmp` fails.
- To upload into a folder, add `"parents":["<folder_id>"]` to the JSON.
- The reply's `mimeType` must be `application/vnd.google-apps.presentation`. Give the user
  `https://docs.google.com/presentation/d/<id>/edit`.
- `pipefail` is load-bearing: without it `tail` hides a failed upload and the command still
  exits 0.
- **On Windows:** use `/gdoc-build`'s Windows upload recipe with two values swapped:
  `"mimeType":"application/vnd.google-apps.presentation"` and the `.pptx` content type above.
  It covers PowerShell 5.1's quote-stripping of `--json`. The script lives at
  `$env:USERPROFILE\.claude\local-plugins\nsls-builder-toolkit\skills\nsls-slides\scripts\pptx_creator.py`.

### Step 5 — Clean up

Remove only this run's file, by its exact name:

```bash
rm ~/nsls-deck-<YYYYMMDD-HHMM>.pptx
```

## Setup Requirements

### Python environment

The `pptx_creator.py` script requires `python-pptx` (plus `pillow` and `lxml`).
**The toolkit installer provisions all of it** into `~/.local/lib/nsls-pydeps` and
writes the `nsls-python` launcher — the right interpreter with those libraries
already importable. Run the script with `nsls-python`, as the commands above do.

Nothing to set up on a machine that ran the installer. Verify with:

```bash
~/.local/bin/nsls-python -c 'import pptx, PIL, lxml; print("slides deps OK")'
```

If that fails, **re-run the toolkit installer** — it reinstalls the libraries and
rewrites the launcher. Manual repair, if you need one:

```bash
~/.local/bin/nsls-python -m pip install --upgrade python-pptx pillow --target ~/.local/lib/nsls-pydeps -q
```

> The old pattern here was a venv at `/tmp/brand-env`. Don't go back to it: macOS
> cleans `/tmp`, so those slides broke every few days and each fix looked like a
> fresh Python problem to the builder. `~/.local/lib/nsls-pydeps` is durable.
> Never invoke a pinned version like `python3.12` either — plenty of Macs don't
> have it, and `python-pptx` runs on any 3.10-3.14.

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

Uses the toolkit's `gws` profile (`~/.config/gws-profiles/nsls-gdocs-skill`), shared with
`/gdoc-build` and `/gdoc-edit`. Set it up or repair it with `/gdoc-build`'s step 0.

## Example: Full End-to-End Run

```bash
# 1. Generate slides JSON (Claude produces this based on Kevin's brief)
cat > ~/nsls-deck-20260302-1405.json <<'JSON'
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
~/.local/bin/nsls-python \
  ~/.claude/local-plugins/nsls-builder-toolkit/skills/nsls-slides/scripts/pptx_creator.py \
  --input ~/nsls-deck-20260302-1405.json \
  --output ~/nsls-deck-20260302-1405.pptx

# 3. Upload to Drive as Google Slides
# (one command: the profile export must share the gws call's shell)
export GOOGLE_WORKSPACE_CLI_CONFIG_DIR="$HOME/.config/gws-profiles/nsls-gdocs-skill"; set -o pipefail; cd ~ && gws drive files create \
  --json '{"name":"2026 Q2 - Society Update","mimeType":"application/vnd.google-apps.presentation"}' \
  --upload nsls-deck-20260302-1405.pptx \
  --upload-content-type "application/vnd.openxmlformats-officedocument.presentationml.presentation" \
  --format json | tail -10

# 4. Clean up
rm ~/nsls-deck-20260302-1405.json ~/nsls-deck-20260302-1405.pptx
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
