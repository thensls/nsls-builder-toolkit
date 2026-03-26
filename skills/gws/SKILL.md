---
name: gws
description: >-
  Google Workspace Sheets CLI for reading, writing, and formatting Google
  Sheets. This skill should be used when the user wants to work with
  spreadsheets, create sheets, read data from Google Sheets, write data,
  format cells, or automate spreadsheet operations. Trigger on "spreadsheet",
  "google sheets", "gws", "sheet data", "read sheet", "write to sheet".
---

# gws — Google Workspace CLI

## What This Does

Wraps the `gws` CLI to interact with Google Sheets (and other Google Workspace services) from the command line. Use it any time you need to read data from a sheet, write or append rows, create a new spreadsheet, format cells, or run batch updates.

The CLI follows a consistent pattern: `gws <service> <resource> [sub-resource] <method> [flags]`. For Sheets, the service is always `sheets`.

Full reference: `/Users/k/nsls-skills/nsls-builder-toolkit/skills/gws/references/gws-reference.md`

---

## Prerequisites

The `gws` binary must be at `~/bin/gws` or on your PATH. It is sourced from:

- GitHub: https://github.com/googleworkspace/cli

If that repo doesn't exist or the binary isn't available, message Kevin in Slack for the binary.

---

## Authentication

`gws` uses Google OAuth2. Credentials are resolved in this order:

1. `GOOGLE_WORKSPACE_CLI_TOKEN` — pre-obtained OAuth2 access token (highest priority)
2. `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` — path to an OAuth credentials JSON file
3. Stored credentials in `~/.config/gws` (set up via `gws auth login`)

For most workflows, credentials are already configured at `~/.config/gws`. If you get exit code 2 (auth error), the token may have expired — re-run `gws auth login`.

---

## Common Operations

### Read a range (helper — use this first)

```bash
gws sheets +read --spreadsheet SHEET_ID --range "Sheet1!A1:D10"
gws sheets +read --spreadsheet SHEET_ID --range Sheet1        # whole sheet
gws sheets +read --spreadsheet SHEET_ID --range "Sheet1!A1:D10" --format table
gws sheets +read --spreadsheet SHEET_ID --range "Sheet1!A1:D10" --format csv
```

`+read` is read-only and never modifies the spreadsheet. Prefer it over the raw `values get` for simple reads.

### Append a row (helper)

```bash
# Simple single-row append
gws sheets +append --spreadsheet SHEET_ID --values 'Alice,100,true'

# Multi-row bulk insert
gws sheets +append --spreadsheet SHEET_ID --json-values '[["Alice","100"],["Bob","200"]]'
```

Values are appended after the last row that contains data (Google Sheets "smart append" behavior).

### Read a range (raw API)

```bash
gws sheets spreadsheets values get \
  --params '{"spreadsheetId": "SHEET_ID", "range": "Sheet1!A1:D10"}'
```

### Write to a range

```bash
gws sheets spreadsheets values update \
  --params '{"spreadsheetId": "SHEET_ID", "range": "Sheet1!A1:B2", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["Name", "Score"], ["Alice", 95]]}'
```

`valueInputOption` options:
- `USER_ENTERED` — parses values like the Sheets UI (formulas, dates, numbers)
- `RAW` — stores values as-is (strings, no formula parsing)

### Batch read multiple ranges

```bash
gws sheets spreadsheets values batchGet \
  --params '{"spreadsheetId": "SHEET_ID", "ranges": ["Sheet1!A1:B5", "Sheet2!C1:D3"]}'
```

### Batch write multiple ranges

```bash
gws sheets spreadsheets values batchUpdate \
  --params '{"spreadsheetId": "SHEET_ID"}' \
  --json '{
    "valueInputOption": "USER_ENTERED",
    "data": [
      {"range": "Sheet1!A1", "values": [["Hello"]]},
      {"range": "Sheet2!B2", "values": [["World"]]}
    ]
  }'
```

### Clear a range

```bash
gws sheets spreadsheets values clear \
  --params '{"spreadsheetId": "SHEET_ID", "range": "Sheet1!A2:Z100"}'
```

### Create a new spreadsheet

```bash
gws sheets spreadsheets create \
  --json '{"properties": {"title": "My New Sheet"}}'
```

Returns the full spreadsheet object including the new `spreadsheetId`.

### Get spreadsheet metadata

```bash
# Metadata only (no grid data)
gws sheets spreadsheets get \
  --params '{"spreadsheetId": "SHEET_ID"}'

# Include grid data
gws sheets spreadsheets get \
  --params '{"spreadsheetId": "SHEET_ID", "includeGridData": true}'
```

### Format cells and apply structural changes (batchUpdate)

All formatting, adding/deleting sheets, freezing rows, resizing columns, etc. go through `batchUpdate` with a `requests` array:

```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId": "SHEET_ID"}' \
  --json '{
    "requests": [
      {
        "repeatCell": {
          "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
          "cell": {
            "userEnteredFormat": {
              "textFormat": {"bold": true},
              "backgroundColor": {"red": 0.2, "green": 0.4, "blue": 0.8}
            }
          },
          "fields": "userEnteredFormat(textFormat,backgroundColor)"
        }
      }
    ]
  }'
```

Common `requests` types: `repeatCell`, `updateSheetProperties`, `addSheet`, `deleteSheet`, `mergeCells`, `updateDimensionProperties`, `updateBorders`.

### Copy a sheet to another spreadsheet

```bash
gws sheets spreadsheets sheets copyTo \
  --params '{"spreadsheetId": "SOURCE_ID", "sheetId": 0}' \
  --json '{"destinationSpreadsheetId": "DEST_ID"}'
```

---

## Tips and Patterns

**Extract the spreadsheet ID from a URL.**
The ID is the long string between `/d/` and `/edit` in the Sheets URL:
`https://docs.google.com/spreadsheets/d/SHEET_ID/edit`

**Use `--format table` for quick visual inspection.**
```bash
gws sheets +read --spreadsheet SHEET_ID --range "Sheet1!A1:E20" --format table
```

**Use `--format csv` to pipe into other tools.**
```bash
gws sheets +read --spreadsheet SHEET_ID --range Sheet1 --format csv | python3 -c "import sys,csv; ..."
```

**Dry-run before destructive writes.**
```bash
gws sheets spreadsheets values update --dry-run \
  --params '{"spreadsheetId": "SHEET_ID", "range": "Sheet1!A1", "valueInputOption": "RAW"}' \
  --json '{"values": [["test"]]}'
```

**Batch writes are faster and cheaper than single-cell updates.** Prefer `batchUpdate` or `+append --json-values` when writing multiple rows.

**Sheet names with spaces need quotes in range notation.**
`"My Sheet!A1:B10"` — always quote the whole `--range` value.

**`sheetId` in batchUpdate is an integer, not the spreadsheet ID.** Get it from `spreadsheets get` — it's `sheets[].properties.sheetId` (usually 0 for the first tab).

**Use `gws schema` to explore the full API surface.**
```bash
gws schema sheets.spreadsheets.values.update --resolve-refs
gws schema sheets.spreadsheets.batchUpdate --resolve-refs
```

**Exit codes:**
- `0` — success
- `1` — API error (Google returned an error response)
- `2` — auth error (credentials missing or expired)
- `3` — validation error (bad arguments)
