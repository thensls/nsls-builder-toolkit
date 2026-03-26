# gws CLI — Full Command Reference

Generated from `gws --help` and subcommand help output.

---

## Global Usage

```
gws <service> <resource> [sub-resource] <method> [flags]
gws schema <service.resource.method> [--resolve-refs]
```

---

## Global Flags

| Flag | Description |
|------|-------------|
| `--params <JSON>` | URL/query parameters as JSON |
| `--json <JSON>` | Request body as JSON (POST/PATCH/PUT) |
| `--upload <PATH>` | Local file to upload as media content (multipart) |
| `--upload-content-type <MIME>` | MIME type of uploaded file (auto-detected from extension if omitted) |
| `--output <PATH>` | Output file path for binary responses |
| `--format <FMT>` | Output format: `json` (default), `table`, `yaml`, `csv` |
| `--api-version <VER>` | Override API version (e.g., `v2`, `v3`) |
| `--page-all` | Auto-paginate, one JSON line per page (NDJSON) |
| `--page-limit <N>` | Max pages with `--page-all` (default: 10) |
| `--page-delay <MS>` | Delay between pages in ms (default: 100) |
| `--dry-run` | Validate request locally without sending to the API |
| `--sanitize <TEMPLATE>` | Sanitize responses through Model Armor template |
| `-h, --help` | Print help |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | API error — Google returned an error response |
| `2` | Auth error — credentials missing or invalid |
| `3` | Validation error — bad arguments or input |
| `4` | Discovery error — could not fetch API schema |
| `5` | Internal error — unexpected failure |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_WORKSPACE_CLI_TOKEN` | Pre-obtained OAuth2 access token (highest priority) |
| `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE` | Path to OAuth credentials JSON file |
| `GOOGLE_WORKSPACE_CLI_CLIENT_ID` | OAuth client ID (for `gws auth login`) |
| `GOOGLE_WORKSPACE_CLI_CLIENT_SECRET` | OAuth client secret (for `gws auth login`) |
| `GOOGLE_WORKSPACE_CLI_CONFIG_DIR` | Override config directory (default: `~/.config/gws`) |
| `GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND` | Keyring backend: `keyring` (default) or `file` |
| `GOOGLE_WORKSPACE_CLI_SANITIZE_TEMPLATE` | Default Model Armor template |
| `GOOGLE_WORKSPACE_CLI_SANITIZE_MODE` | Sanitization mode: `warn` (default) or `block` |
| `GOOGLE_WORKSPACE_PROJECT_ID` | Override GCP project ID for quota and billing |
| `GOOGLE_WORKSPACE_CLI_LOG` | Log level for stderr (e.g., `gws=debug`) |
| `GOOGLE_WORKSPACE_CLI_LOG_FILE` | Directory for JSON log files (daily rotation) |

---

## Available Services

| Service | Alias | Description |
|---------|-------|-------------|
| `drive` | — | Manage files, folders, and shared drives |
| `sheets` | — | Read and write spreadsheets |
| `gmail` | — | Send, read, and manage email |
| `calendar` | — | Manage calendars and events |
| `admin-reports` | `reports` | Audit logs and usage reports |
| `docs` | — | Read and write Google Docs |
| `slides` | — | Read and write presentations |
| `tasks` | — | Manage task lists and tasks |
| `people` | — | Manage contacts and profiles |
| `chat` | — | Manage Chat spaces and messages |
| `classroom` | — | Manage classes, rosters, and coursework |
| `forms` | — | Read and write Google Forms |
| `keep` | — | Manage Google Keep notes |
| `meet` | — | Manage Google Meet conferences |
| `events` | — | Subscribe to Google Workspace events |
| `modelarmor` | — | Filter user-generated content for safety |
| `workflow` | `wf` | Cross-service productivity workflows |

---

## `sheets` Service

### Helper Commands

#### `gws sheets +read`

Read values from a spreadsheet (read-only, never modifies).

```
gws sheets +read --spreadsheet <ID> --range <RANGE> [--format <FMT>]
```

| Option | Description |
|--------|-------------|
| `--spreadsheet <ID>` | Spreadsheet ID (required) |
| `--range <RANGE>` | Range to read, e.g. `Sheet1!A1:B2` or just `Sheet1` (required) |
| `--format <FMT>` | `json` (default), `table`, `yaml`, `csv` |

Examples:
```bash
gws sheets +read --spreadsheet ID --range "Sheet1!A1:D10"
gws sheets +read --spreadsheet ID --range Sheet1
gws sheets +read --spreadsheet ID --range Sheet1 --format csv
```

#### `gws sheets +append`

Append rows to a spreadsheet.

```
gws sheets +append --spreadsheet <ID> [--values <CSV>] [--json-values <JSON>]
```

| Option | Description |
|--------|-------------|
| `--spreadsheet <ID>` | Spreadsheet ID (required) |
| `--values <CSV>` | Comma-separated values for a single row |
| `--json-values <JSON>` | JSON array of rows, e.g. `[["a","b"],["c","d"]]` |

Examples:
```bash
gws sheets +append --spreadsheet ID --values 'Alice,100,true'
gws sheets +append --spreadsheet ID --json-values '[["a","b"],["c","d"]]'
```

---

### `sheets spreadsheets` Commands

#### `create`

Creates a new spreadsheet.

```bash
gws sheets spreadsheets create --json '{"properties": {"title": "Sheet Title"}}'
```

Returns the full spreadsheet object (includes `spreadsheetId`).

#### `get`

Returns metadata for a spreadsheet. Grid data is not included by default.

```bash
gws sheets spreadsheets get \
  --params '{"spreadsheetId": "ID"}'

# Include grid data
gws sheets spreadsheets get \
  --params '{"spreadsheetId": "ID", "includeGridData": true}'
```

Useful `params` keys:
- `spreadsheetId` (required)
- `includeGridData` — boolean, includes cell values
- `ranges` — array of ranges to include when `includeGridData` is true

#### `getByDataFilter`

Returns spreadsheet data matching specified data filters.

```bash
gws sheets spreadsheets getByDataFilter \
  --params '{"spreadsheetId": "ID"}' \
  --json '{"dataFilters": [{"gridRange": {"sheetId": 0}}]}'
```

#### `batchUpdate`

Applies one or more structural/formatting updates. All requests are validated before any are applied — if one fails, none are applied.

```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId": "ID"}' \
  --json '{"requests": [...]}'
```

Common request types in the `requests` array:

| Request type | What it does |
|---|---|
| `addSheet` | Add a new sheet/tab |
| `deleteSheet` | Delete a sheet by `sheetId` |
| `updateSheetProperties` | Rename, recolor, resize a sheet |
| `repeatCell` | Apply formatting to a range of cells |
| `mergeCells` | Merge a range of cells |
| `unmergeCells` | Unmerge cells |
| `updateBorders` | Set cell borders |
| `updateDimensionProperties` | Resize rows or columns |
| `insertDimension` | Insert rows or columns |
| `deleteDimension` | Delete rows or columns |
| `sortRange` | Sort a range by one or more columns |
| `setDataValidation` | Add dropdown validation to cells |
| `setBasicFilter` | Add a basic filter to a range |
| `addConditionalFormatRule` | Add conditional formatting |
| `copyPaste` | Copy a range and paste it elsewhere |
| `moveDimension` | Move rows or columns |

Example — bold the header row:
```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId": "ID"}' \
  --json '{
    "requests": [{
      "repeatCell": {
        "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
        "cell": {
          "userEnteredFormat": {
            "textFormat": {"bold": true}
          }
        },
        "fields": "userEnteredFormat.textFormat.bold"
      }
    }]
  }'
```

Example — add a new sheet tab:
```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId": "ID"}' \
  --json '{"requests": [{"addSheet": {"properties": {"title": "New Tab"}}}]}'
```

Example — freeze top row:
```bash
gws sheets spreadsheets batchUpdate \
  --params '{"spreadsheetId": "ID"}' \
  --json '{
    "requests": [{
      "updateSheetProperties": {
        "properties": {
          "sheetId": 0,
          "gridProperties": {"frozenRowCount": 1}
        },
        "fields": "gridProperties.frozenRowCount"
      }
    }]
  }'
```

---

### `sheets spreadsheets values` Commands

All values commands use `spreadsheetId` in `--params`.

#### `get`

Read a single range.

```bash
gws sheets spreadsheets values get \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1:D10"}'
```

Optional params: `majorDimension` (`ROWS` or `COLUMNS`), `valueRenderOption` (`FORMATTED_VALUE`, `UNFORMATTED_VALUE`, `FORMULA`), `dateTimeRenderOption`.

#### `update`

Write to a single range.

```bash
gws sheets spreadsheets values update \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A1:B2", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["Name", "Score"], ["Alice", 95]]}'
```

`valueInputOption` is required: `USER_ENTERED` (parse like the UI) or `RAW` (literal strings).

#### `append`

Append rows after the last row with data in a table.

```bash
gws sheets spreadsheets values append \
  --params '{"spreadsheetId": "ID", "range": "Sheet1", "valueInputOption": "USER_ENTERED"}' \
  --json '{"values": [["New Row", "Data"]]}'
```

#### `clear`

Clear values from a range (does not delete formatting).

```bash
gws sheets spreadsheets values clear \
  --params '{"spreadsheetId": "ID", "range": "Sheet1!A2:Z100"}'
```

#### `batchGet`

Read multiple ranges in one call.

```bash
gws sheets spreadsheets values batchGet \
  --params '{"spreadsheetId": "ID", "ranges": ["Sheet1!A1:B5", "Sheet2!C1:D3"]}'
```

#### `batchUpdate`

Write to multiple ranges in one call.

```bash
gws sheets spreadsheets values batchUpdate \
  --params '{"spreadsheetId": "ID"}' \
  --json '{
    "valueInputOption": "USER_ENTERED",
    "data": [
      {"range": "Sheet1!A1", "values": [["Hello"]]},
      {"range": "Sheet2!B2", "values": [["World"]]}
    ]
  }'
```

#### `batchClear`

Clear multiple ranges.

```bash
gws sheets spreadsheets values batchClear \
  --params '{"spreadsheetId": "ID"}' \
  --json '{"ranges": ["Sheet1!A2:Z100", "Sheet2!A2:Z50"]}'
```

#### `batchGetByDataFilter` / `batchClearByDataFilter` / `batchUpdateByDataFilter`

Data-filter variants that match ranges by metadata filters instead of A1 notation. See `gws schema sheets.spreadsheets.values.batchGetByDataFilter --resolve-refs` for the DataFilter schema.

---

### `sheets spreadsheets sheets` Commands

#### `copyTo`

Copy a single sheet to another spreadsheet.

```bash
gws sheets spreadsheets sheets copyTo \
  --params '{"spreadsheetId": "SOURCE_ID", "sheetId": 0}' \
  --json '{"destinationSpreadsheetId": "DEST_ID"}'
```

`sheetId` is an integer (from `spreadsheets get` → `sheets[].properties.sheetId`), not the spreadsheet URL ID.

---

### `sheets spreadsheets developerMetadata` Commands

Manage key-value metadata attached to spreadsheets, sheets, rows, or columns. Useful for programmatically tagging ranges.

```bash
# Get metadata by ID
gws sheets spreadsheets developerMetadata get \
  --params '{"spreadsheetId": "ID", "metadataId": 123}'

# Search metadata
gws sheets spreadsheets developerMetadata search \
  --params '{"spreadsheetId": "ID"}' \
  --json '{"dataFilters": [{"developerMetadataLookup": {"metadataKey": "my-key"}}]}'
```

---

## Schema Exploration

Use `gws schema` to see the full request/response shape for any method:

```bash
gws schema sheets.spreadsheets.batchUpdate --resolve-refs
gws schema sheets.spreadsheets.values.update --resolve-refs
gws schema sheets.spreadsheets.values.batchUpdate --resolve-refs
gws schema sheets.spreadsheets.create --resolve-refs
```

`--resolve-refs` expands `$ref` pointers so you see the full nested schema inline.

---

## Range Notation

| Notation | Meaning |
|----------|---------|
| `Sheet1` | Entire sheet named "Sheet1" |
| `Sheet1!A1:B10` | Rows 1–10, columns A–B on Sheet1 |
| `A1:B10` | Same range on the first/default sheet |
| `Sheet1!A:A` | Entire column A on Sheet1 |
| `Sheet1!1:1` | Entire row 1 on Sheet1 |
| `'My Sheet'!A1:B5` | Sheet name with spaces (single-quote in A1 notation) |

When passing to `--range` or in JSON `"range"` keys, always quote shell strings that contain `!` or spaces.
