# Airtable API

## When to Use It

Use the Airtable API when your automation needs to read or write structured records — employee data, meeting notes, goal updates, registrations, etc.

Airtable is the data layer. It's not a runtime host. Your code runs somewhere else (Railway, GAS, Cloudflare Workers) and calls the Airtable API to read/write data.

## API Keys — Use Scoped Tokens

Always use a scoped personal access token, not the legacy API key.

**Never use your personal token in shared code.** Create a token scoped to the specific bases your automation needs. Store it as an environment variable (`AIRTABLE_API_TOKEN`).

To create a token: go to [airtable.com/create/tokens](https://airtable.com/create/tokens), give it a name, add the scopes you need (`data.records:read`, `data.records:write`, `schema.bases:read`), and restrict it to the relevant bases.

## Common Patterns

**List records:**
```python
import requests

headers = {"Authorization": f"Bearer {token}"}
url = f"https://api.airtable.com/v0/{base_id}/{table_id}"
params = {"filterByFormula": "{status}='Active'"}
resp = requests.get(url, headers=headers, params=params)
records = resp.json()["records"]
```

**Create a record:**
```python
data = {"fields": {"Name": "Alice", "Department": "Engineering"}}
resp = requests.post(url, headers=headers, json=data)
```

**Update a record:**
```python
record_id = "recXXXXXX"
data = {"fields": {"status": "Complete"}}
resp = requests.patch(f"{url}/{record_id}", headers=headers, json=data)
```

**Upsert (create or update based on a field match):**
```python
data = {
    "records": [{"fields": {"email": "alice@nsls.org", "score": 90}}],
    "performUpsert": {"fieldsToMergeOn": ["email"]}
}
resp = requests.patch(url, headers=headers, json=data)
```

Use upsert to avoid separate existence checks. It's one API call instead of two.

## Rate Limits

5 requests per second per base. If you're processing many records in a loop, add a small delay (`time.sleep(0.2)`) between requests or batch your writes (up to 10 records per create/update call).

## Key Gotchas

**Select fields need plain strings, not `{id: selXXX}` objects.**
When using field IDs as payload keys, pass the option name as a plain string: `"Not Started"`, not `{"id": "selXXXXXX"}`. The object format silently fails.

**`filterByFormula` uses field names, not field IDs.**
`{status}='Active'` works. `{fldJleDMJFfcj5gPN}='Active'` returns 0 results. Field IDs only work in `filterByFormula` when you also pass `returnFieldsByFieldId=true` on the request.

**`ARRAYJOIN` on linked record fields returns display names, not record IDs.**
`FIND('recXXX', ARRAYJOIN({linked_field},'|'))` always fails because Airtable returns the linked record's name, not its ID. To filter by linked record ID, either add a formula field that surfaces the record ID, or fetch all records and filter in Python using the API-returned ID array.

**Single-record GET doesn't support `fields[]` filtering.**
`GET /v0/{base}/{table}/{recordId}?fields[]=fldXXX` returns `INVALID_REQUEST_UNKNOWN`. Only works on list endpoints. For single-record GETs, fetch the full record and pick fields from the response.

**Formula fields and views with filters can't be created via the API.**
`POST /meta/bases/{baseId}/tables/{tableId}/fields` returns `UNSUPPORTED_FIELD_TYPE_FOR_CREATE` for formula fields. Create these manually in the Airtable UI.

**Scoped tokens can't add new select options.**
If you try to write a value to a single/multi-select field that doesn't exist as an option yet, the request will fail. Add the option in the Airtable UI first, then write to it via the API.
