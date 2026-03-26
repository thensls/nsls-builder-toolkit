---
name: google-slides-api
description: >-
  Programmatically edit Google Slides using the google-apis-slides_v1 Ruby gem.
  Use when modifying an existing presentation via API — adding slides, tables,
  text, styling. Not for creating from scratch (use board-deck skill instead).
category: google
version: 1.0.0
when_to_use: Editing existing Google Slides presentations via API — inserting slides, tables, updating cell content, fixing formatting
---

# Google Slides API Skill (Ruby)

## Purpose

Edit live Google Slides presentations using the `google-apis-slides_v1` Ruby gem
and existing OAuth credentials at `~/.claude/.google/`.

Use this when:
- Adding a slide to an existing deck
- Rebuilding or updating a table in an existing slide
- Inserting/updating text content in existing slides
- Bulk-formatting existing table cells

For creating a deck from scratch, use the `board-deck` skill (PPTX pipeline) instead.

---

## Setup

```ruby
require 'google/apis/slides_v1'
require 'googleauth'
require 'json'
require 'yaml'

S = Google::Apis::SlidesV1

def authorize
  yaml_data = YAML.load(File.read(File.expand_path('~/.claude/.google/token.json')))
  token_data = JSON.parse(yaml_data['default'])
  client_data = JSON.parse(File.read(File.expand_path('~/.claude/.google/client_secret.json')))
  installed = client_data['installed'] || client_data['web']
  credentials = Google::Auth::UserRefreshCredentials.new(
    client_id: installed['client_id'],
    client_secret: installed['client_secret'],
    scope: ['https://www.googleapis.com/auth/presentations'],
    access_token: token_data['access_token'],
    refresh_token: token_data['refresh_token'],
    expires_at: token_data['expiration_time_millis'] ? Time.at(token_data['expiration_time_millis'] / 1000.0) : nil
  )
  credentials.fetch_access_token! if credentials.expired?
  credentials
end

service = S::SlidesService.new
service.authorization = authorize
```

Install the gem if missing:
```bash
gem install google-apis-slides_v1
```

---

## Critical Gotchas

### 1. `object_id_prop` NOT `object_id`

**The #1 source of silent failures.** Ruby's `BasicObject#object_id` is a
built-in method on every object. The gem renames all `objectId` API fields to
`object_id_prop` to avoid the collision.

Affects every request type:
- `InsertTextRequest.new(object_id_prop: shape_id, ...)`
- `UpdateTextStyleRequest.new(object_id_prop: shape_id, ...)`
- `DeleteObjectRequest.new(object_id_prop: shape_id)`
- `UpdateTableCellPropertiesRequest.new(object_id_prop: table_id, ...)`
- `DeleteTextRequest.new(object_id_prop: table_id, ...)`

Using `object_id:` silently passes `nil` or Ruby's memory address — the API
returns "object not found" with an empty object ID in the error message.

```ruby
# WRONG — silently fails
S::InsertTextRequest.new(object_id: title_id, text: 'Hello')

# RIGHT
S::InsertTextRequest.new(object_id_prop: title_id, text: 'Hello')
```

### 2. Font sizes must use `unit: 'PT'` not `unit: 'EMU'`

Dimensions for positions/sizes use `'EMU'`. Font sizes use `'PT'`.
Mixing them up produces ~1pt (essentially invisible) fonts.

```ruby
# WRONG — produces ~0pt font (12 EMU = 0.013mm)
S::Dimension.new(magnitude: 12, unit: 'EMU')

# RIGHT
S::Dimension.new(magnitude: 12, unit: 'PT')
```

**Always have two helpers:**
```ruby
def emu(n) = S::Dimension.new(magnitude: n.to_f, unit: 'EMU')  # positions, sizes
def pt(n)  = S::Dimension.new(magnitude: n.to_f, unit: 'PT')   # font sizes only
```

### 3. `insertText` appends — always delete first

`insertText` **always appends** to whatever is already in the cell/shape.
It never replaces. If you call it twice, you get duplicate content.

```ruby
# WRONG — second call appends to first, creating duplicate
batch(insert_text_req('Hello'))
batch(insert_text_req('Hello'))  # cell now has "HelloHello"

# RIGHT — delete first, then insert
batch(
  S::Request.new(delete_text: S::DeleteTextRequest.new(
    object_id_prop: shape_id,
    text_range: S::Range.new(type: 'ALL')
  ))
)
batch(insert_text_req('Hello'))
```

For table cells, `DeleteTextRequest` also needs `cell_location`:
```ruby
S::Request.new(delete_text: S::DeleteTextRequest.new(
  object_id_prop: table_id,
  cell_location: S::TableCellLocation.new(row_index: r, column_index: c),
  text_range: S::Range.new(type: 'ALL')
))
```

### 4. Rate limit: 60 writes/minute — design for it

The Google Slides API allows 60 batch write requests per minute per user.
With many table cells, you'll hit this fast.

```ruby
def batch(service, *reqs)
  b = S::BatchUpdatePresentationRequest.new(requests: reqs)
  service.batch_update_presentation(PRES_ID, b)
rescue Google::Apis::RateLimitError
  puts "Rate limited — waiting 65s..."
  sleep 65
  retry
rescue => e
  puts "Error: #{e.message}"
  puts e.body rescue nil
  raise
end
```

**Practical rules:**
- `sleep 1` between every batch call when doing bulk operations
- `sleep 2-3` between heavier operations (create_table, create_slide)
- `sleep 65` and retry on `RateLimitError`
- If building many rows, batch per-row with sleep, not all-at-once

### 5. `updateTextStyle` fails on empty cells

Calling `updateTextStyle` on a table cell with no text throws:
`Invalid requests[N].updateTextStyle: The object has no text.`

Always check which cells have content before applying style:
```ruby
def cells_with_text(service, pres_id, table_id)
  pres = service.get_presentation(pres_id)
  result = []
  pres.slides.each do |slide|
    (slide.page_elements || []).each do |el|
      next unless el.object_id_prop == table_id && el.table
      el.table.table_rows.each_with_index do |row, ri|
        row.table_cells.each_with_index do |cell, ci|
          text = (cell.dig('text','textElements') || [])
                   .map { |te| te.dig('textRun','content').to_s }.join.strip
          result << [ri, ci] unless text.empty?
        end
      end
    end
  end
  result
end

# Then filter before styling:
has_text = cells_with_text(service, PRES_ID, table_id).to_set
cells.each do |ri, ci|
  next unless has_text.include?([ri, ci])
  # ... apply style
end
```

### 6. True slide objectId is NOT `slide.object_id` in Ruby

`slide.object_id` returns Ruby's memory address integer, not the API's string ID.
The API assigns IDs like `g35da4a5ddc8_1_12` or `SLIDES_API1474096947_0`.

Get the true ID via:
- **From a batch create response**: `resp.replies.first.create_slide.object_id_prop`
- **From raw HTTP**: fetch the presentation JSON and read `slides[N]['objectId']`
- **Never** use `slide.object_id` (the Ruby gem's in-memory integer)

```ruby
# Get true IDs via raw HTTP
uri = URI("https://slides.googleapis.com/v1/presentations/#{PRES_ID}?fields=slides(objectId)")
req = Net::HTTP::Get.new(uri)
req['Authorization'] = "Bearer #{token}"
res = Net::HTTP.start(uri.hostname, uri.port, use_ssl: true) { |h| h.request(req) }
slides = JSON.parse(res.body)['slides']
true_ids = slides.map { |s| s['objectId'] }
```

### 7. Rate limit failures leave partial data

If a batch call fails mid-table-build, some rows are inserted, others aren't.
Design insertion loops to be **idempotent**:
- Insert one row at a time (not all in one batch)
- Check existing cell content before inserting
- Use `deleteText` + `insertText` as an upsert pattern

```ruby
# Idempotent row insert
def upsert_cell(service, table_id, row, col, text, ...)
  # Delete existing content first (no-op if empty)
  begin
    batch(service, delete_text_req(table_id, row, col))
  rescue => e
    # Ignore "no text" error on empty cells
    raise unless e.body.include?('no text')
  end
  # Then insert fresh
  batch(service, insert_text_req(table_id, row, col, text))
end
```

### 8. Column widths are independent from table `size.width`

When you create a table, you set a `size.width`. But column widths are set
separately via `updateTableColumnProperties`. The actual rendered width =
sum of all column widths, which can exceed the declared size.

The declared `size.width` from `get_presentation` may lag or be wrong — always
trust the sum of `tableColumns[].columnWidth` for the actual rendered width.

### 9. ROUND_RECTANGLE shapes can hold title text directly

The existing NSLS board deck slides store the title text **inside** the
ROUND_RECTANGLE background shape (not in a separate TEXT_BOX overlaid on top).
This means:
- `updateTextStyle` / `updateParagraphStyle` on the ROUND_RECTANGLE updates the title
- You can change alignment, font, size directly on the shape's text
- Slide 8 uses a different pattern: separate transparent TEXT_BOX over the band

---

## Minimum Font Size Rule

**Never set font sizes below 11pt in table cells.**

At 11pt+, text is legible in a board presentation. Below that, Google Slides'
auto-fit may scale it down further, making it unreadable.

| Content type | Minimum | Recommended |
|---|---|---|
| Table header | 11pt | 11pt |
| Table data (goal/key column) | 11pt | 11pt bold |
| Table data (status/description) | 10pt | 10pt (acceptable for long text) |
| Table data (name/date short columns) | 10pt | 10pt |
| Slide title (ROUND_RECTANGLE) | 12pt | 13pt |

---

## Standard Table Pattern (Board Deck Style)

```ruby
NAVY      = S::RgbColor.new(red: 0.08235294, green: 0.12156863, blue: 0.3019608)
WHITE     = S::RgbColor.new(red: 1.0, green: 1.0, blue: 1.0)
LIGHT_ROW = S::RgbColor.new(red: 0.9490196, green: 0.9607843, blue: 0.96862745)

def create_table(service, slide_id, tx:, ty:, col_widths:, nrows:, headers:, data:)
  # 1. Create table
  tr  = S::AffineTransform.new(scale_x: 1.0, scale_y: 1.0,
                                translate_x: tx.to_f, translate_y: ty.to_f, unit: 'EMU')
  sz  = S::Size.new(width: emu(col_widths.sum), height: emu((nrows+1)*520000))
  props = S::PageElementProperties.new(page_object_id: slide_id, size: sz, transform: tr)
  resp = batch(service, S::Request.new(create_table: S::CreateTableRequest.new(
    element_properties: props, rows: nrows + 1, columns: col_widths.length
  )))
  tbl_id = resp.replies.first.create_table.object_id_prop
  sleep 1

  # 2. Set column widths
  batch(service, *col_widths.each_with_index.map { |w, ci|
    S::Request.new(update_table_column_properties: S::UpdateTableColumnPropertiesRequest.new(
      object_id_prop: tbl_id, column_indices: [ci],
      table_column_properties: S::TableColumnProperties.new(column_width: emu(w)),
      fields: 'columnWidth'
    ))
  })
  sleep 1

  # 3. Header row
  header_reqs = headers.each_with_index.flat_map do |h, ci|
    loc = S::TableCellLocation.new(row_index: 0, column_index: ci)
    [
      S::Request.new(insert_text: S::InsertTextRequest.new(
        object_id_prop: tbl_id, cell_location: loc, text: h)),
      S::Request.new(update_text_style: S::UpdateTextStyleRequest.new(
        object_id_prop: tbl_id, cell_location: loc,
        style: S::TextStyle.new(bold: true, font_family: 'Poppins', font_size: pt(11),
          foreground_color: S::OptionalColor.new(opaque_color: S::OpaqueColor.new(rgb_color: WHITE)),
          weighted_font_family: S::WeightedFontFamily.new(font_family: 'Poppins', weight: 700)),
        text_range: S::Range.new(type: 'ALL'), fields: 'bold,fontFamily,fontSize,foregroundColor,weightedFontFamily'
      )),
      S::Request.new(update_table_cell_properties: S::UpdateTableCellPropertiesRequest.new(
        object_id_prop: tbl_id,
        table_range: S::TableRange.new(location: loc, row_span: 1, column_span: 1),
        table_cell_properties: S::TableCellProperties.new(
          table_cell_background_fill: S::TableCellBackgroundFill.new(
            solid_fill: S::SolidFill.new(color: S::OpaqueColor.new(rgb_color: NAVY), alpha: 1.0)),
          content_alignment: 'MIDDLE'),
        fields: 'tableCellBackgroundFill,contentAlignment'
      ))
    ]
  end
  batch(service, *header_reqs)
  sleep 1

  # 4. Data rows — one per batch to survive rate limits
  data.each_with_index do |row, ri|
    row_bg = (ri.even?) ? LIGHT_ROW : WHITE
    cell_reqs = row.each_with_index.flat_map do |cell, ci|
      loc = S::TableCellLocation.new(row_index: ri + 1, column_index: ci)
      bg_req = S::Request.new(update_table_cell_properties: S::UpdateTableCellPropertiesRequest.new(
        object_id_prop: tbl_id,
        table_range: S::TableRange.new(location: loc, row_span: 1, column_span: 1),
        table_cell_properties: S::TableCellProperties.new(
          table_cell_background_fill: S::TableCellBackgroundFill.new(
            solid_fill: S::SolidFill.new(color: S::OpaqueColor.new(rgb_color: row_bg), alpha: 1.0)),
          content_alignment: 'TOP'),
        fields: 'tableCellBackgroundFill,contentAlignment'
      ))
      next [bg_req] if cell[:text].to_s.empty?
      [
        bg_req,
        S::Request.new(insert_text: S::InsertTextRequest.new(
          object_id_prop: tbl_id, cell_location: loc, text: cell[:text])),
        S::Request.new(update_text_style: S::UpdateTextStyleRequest.new(
          object_id_prop: tbl_id, cell_location: loc,
          style: S::TextStyle.new(
            bold: cell[:bold] || false,
            font_family: 'Poppins',
            font_size: pt(cell[:font_pt] || 11),
            foreground_color: S::OptionalColor.new(opaque_color: S::OpaqueColor.new(rgb_color: NAVY)),
            weighted_font_family: S::WeightedFontFamily.new(
              font_family: 'Poppins', weight: (cell[:bold] ? 700 : 400))),
          text_range: S::Range.new(type: 'ALL'),
          fields: 'bold,fontFamily,fontSize,foregroundColor,weightedFontFamily'
        ))
      ]
    end
    batch(service, *cell_reqs.flatten)
    sleep 1
  end

  tbl_id
end
```

---

## Goals Table (L2 Goals — Board Deck Standard)

As of March 2026, the NSLS board deck L2 goals tables use **5 columns**:

| Column | Header | Font | Width (EMU) | Notes |
|--------|--------|------|-------------|-------|
| 0 | L2 GOAL | 11pt bold | 2338725 | Goal description |
| 1 | HEALTH | 11pt | 956750 | Emoji + status |
| 2 | STATUS UPDATE | 10pt | 2551325 | Narrative update |
| 3 | OWNER | 10pt | 1063050 | DRI name from Airtable |
| 4 | DEADLINE | 11pt | 956750 | Date from Airtable |

Pull DRI + deadline from Airtable `appHDEHQA4bvlWwQq`:
- L2 Goals table: `tblpvFlUEy9GJflzB`, filter `AND({Year}='2026',{Status}='Active')`
- DRI name: `User (from DRI)` lookup field → array, take `[0]['name']`
- Deadline: `Deadline` date field (YYYY-MM-DD → format as M/D/YYYY for display)

L1 Goals table: `tblFLHHpQUVpLrDjb`
- SMART goal: `L1 as Smart Goal` field
- DRI: `User (from DRI)` lookup field
- Note: L1 table has **no deadline field** — use 12/31/2026 for all 2026 goals

---

## Title Slide Format Reference

**Slide 8 ("Where we stand")** is the reference for interior slide title format:
- Shape: transparent TEXT_BOX (NOT ROUND_RECTANGLE with fill)
- Transform: `scaleX=1.7983, scaleY=0.1283, tx=-44975, ty=402950`
- Size: `3000000 x 3000000` EMU (actual rendered = 5394900 x 384900)
- Font: Red Hat Display, 19pt, weight 900, bold
- Color: `rgb(0.161, 0.235, 0.376)` (dark navy)
- Alignment: LEFT (START) — always left-justify titles

The existing L2 goal slides use a different pattern (text inside ROUND_RECTANGLE),
which was inherited from the template. New slides should use the TEXT_BOX pattern.

---

## Evals

Before shipping any Slides API script, verify:

### Font Checks
- [ ] All `Dimension` objects for **font sizes** use `unit: 'PT'` (not `'EMU'`)
- [ ] All `Dimension` objects for **positions/sizes** use `unit: 'EMU'`
- [ ] No table data cell font size below **11pt** (10pt acceptable for STATUS/OWNER columns)
- [ ] No title/header font size below **12pt**

### Object ID Checks
- [ ] Every request uses `object_id_prop:` not `object_id:`
- [ ] Slide IDs come from batch create responses (`.object_id_prop`) or raw HTTP JSON
- [ ] Never use `slide.object_id` (returns Ruby memory address)

### Text Content Checks
- [ ] Before `insertText`, check if cell already has content (use `deleteText` first)
- [ ] `updateTextStyle` only called on cells that have text
- [ ] Rate limit handling: `sleep 1` between batch calls, `sleep 65` + retry on 429

### Visual Verification
- [ ] Open the presentation in browser after API changes
- [ ] Check at least 3 representative slides (first, last, one with long text)
- [ ] Verify OWNER and DEADLINE columns are visible (not auto-scaled to near-zero)
- [ ] Confirm title text is left-justified

### Data Integrity
- [ ] All L2 rows have content in all 5 columns (GOAL, HEALTH, STATUS, OWNER, DEADLINE)
- [ ] L1 SMART goals match Airtable `L1 as Smart Goal` field exactly (not theme descriptions)
- [ ] DRI names match Airtable `User (from DRI)` lookup field

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `The object () could not be found` | Used `object_id:` instead of `object_id_prop:` | Replace all `object_id:` with `object_id_prop:` |
| Fonts appear as ~1pt / invisible | Font Dimension uses `unit: 'EMU'` | Change to `unit: 'PT'` |
| Cell content duplicated | `insertText` called without `deleteText` first | Add `deleteText` (range: ALL) before inserting |
| `The object has no text` | `updateTextStyle` on empty cell | Check cells_with_text before styling |
| `Quota exceeded` 429 | Too many batch writes per minute | `sleep 65` then retry; add `sleep 1` between calls |
| Partial data (some rows empty) | Rate limit killed mid-loop | Use per-row batching; check cell content and re-insert idempotently |
| Wrong slide ID | Used Ruby `slide.object_id` | Fetch via raw HTTP or use `resp.replies.first.create_slide.object_id_prop` |
