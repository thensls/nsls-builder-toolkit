# Brand Styles for Google Docs

Color palettes and style choices that survive `.docx` → Google Docs conversion. Use the constants in `templates/build_doc.py`; this doc is the reference for the values.

## NSLS palette

| Element | Hex / Value | Notes |
|---|---|---|
| Primary navy | `#1A2B4A` | Table headers, H1 color |
| Secondary navy | `#2B4A7A` | H2 color |
| Body text | `#000000` (default) | Calibri 11pt |
| Light grey band | `#F5F7FA` | Alternating row band, code-block background |
| White | `#FFFFFF` | Header text on navy, alternating row |

## Society palette

| Element | Hex / Value | Notes |
|---|---|---|
| Primary brown | `#3D2F1F` | Table headers, H1 color |
| Secondary brown | `#6B4F2F` | H2 color |
| Header text | `#F5E6CB` (cream) | High-contrast on brown |
| Body text | `#000000` | Calibri 11pt |
| Cream band | `#FAF4E8` | Alternating row band, code-block background |

## Typography

| Element | Choice | Why this and not the brand font |
|---|---|---|
| Body | Calibri 11pt | Lexend Deca (NSLS) and HW Cigars (Society) don't survive `.docx` → Google Docs conversion. Calibri renders consistently. Brand expression comes from colors and structure. |
| Headings | Calibri (bold via Heading style) | Same reason. Brand color carries the identity. |
| Code | Consolas 9.5pt | Mono fonts are required for code legibility. Consolas is universally available. |
| Captions / fine print | Calibri 9pt | One step down from body. |

For slides (different rendering pipeline), brand fonts work — see `/nsls-slides`. Docs are constrained.

## Sizes

| Element | Size |
|---|---|
| Doc title | 28pt bold |
| H1 | Heading 1 default (16pt-ish) |
| H2 | Heading 2 default (13pt-ish) |
| H3 | Heading 3 default (11.5pt-ish) |
| Body | 11pt |
| Table cell text | 10pt (10.5pt for headers) |
| Code | 9.5pt |

Don't override the H1/H2/H3 sizes — Google Docs maps the built-in heading styles to its own scale, and overriding the size in `.docx` produces inconsistent results once converted.

## Margins

Standard NSLS doc margins: `top/bottom 2.0cm`, `left/right 2.2cm`. Slightly wider sides than typical Word defaults — leaves more room for tables.

## Table style

Use `'Light Grid Accent 1'` as the base table style. It's a Word built-in that:

- Adds visible cell borders (Google Docs honors them on import)
- Has neutral coloring (we override with our brand colors via `set_cell_bg`)
- Doesn't apply auto-banding (we control banding explicitly per row)

Alternative built-ins that also import cleanly: `'Light List Accent 1'`, `'Medium Shading 1 Accent 1'`. Stick to `Light Grid Accent 1` unless you have a reason to vary.
