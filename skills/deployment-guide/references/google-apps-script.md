# Google Apps Script

## When to Use It

Use Google Apps Script (GAS) when your automation is tied to a Google Sheet, Doc, or Form — or when you need to send email through Google Workspace.

GAS is the right choice for:
- Processing spreadsheet data on a schedule or when rows change
- Sending email triggered by a form submission or row edit
- Lightweight web endpoints that interact with Google data
- Anything that doesn't need persistent state or long runtime

Don't use GAS for Slack bots, anything with heavy dependencies, or tasks that take more than 6 minutes to run (the execution limit).

## Bound vs. Standalone Scripts

**Bound script**: attached to a specific Sheet, Doc, or Form. Lives inside that file. Access it from the file's **Extensions → Apps Script** menu. Shares the file owner's identity and can access that file directly without any OAuth setup.

**Standalone script**: lives at [script.google.com](https://script.google.com) independently of any file. Use this when your script touches multiple sheets or isn't tied to one file.

For most NSLS automations that live in a spreadsheet, use a bound script.

## Creating a Script

**Bound to a sheet:**
1. Open the Google Sheet.
2. Click **Extensions → Apps Script**.
3. Write your code in the editor.
4. Click **Save** (floppy disk icon).

**Standalone:**
1. Go to [script.google.com](https://script.google.com).
2. Click **New project**.
3. Write your code.

## Triggers

Triggers run your functions automatically. Set them up under **Triggers** (clock icon in the left sidebar).

**Time-based trigger**: runs a function on a schedule (every hour, every day, every Monday at 9am, etc.).

**On-edit trigger**: runs when any cell in a bound sheet is edited. Use `e.range` to know which cell changed.

**On-form-submit trigger**: runs when a Google Form linked to the sheet receives a submission. `e.values` gives you the form responses as an array.

To add a trigger programmatically:
```javascript
function createTrigger() {
  ScriptApp.newTrigger('myFunction')
    .timeBased()
    .everyDays(1)
    .atHour(9)
    .create();
}
```

Only run `createTrigger()` once — each call creates a new trigger, and duplicates will cause your function to run multiple times.

## Connecting to External APIs

Use `UrlFetchApp` for HTTP requests:

```javascript
function callExternalAPI() {
  const token = PropertiesService.getScriptProperties().getProperty('AIRTABLE_TOKEN');
  const options = {
    method: 'get',
    headers: { Authorization: `Bearer ${token}` },
    muteHttpExceptions: true
  };
  const response = UrlFetchApp.fetch('https://api.airtable.com/v0/...', options);
  const data = JSON.parse(response.getContentText());
  return data;
}
```

Store secrets in **Script Properties**, not hardcoded in the script. Go to **Project Settings → Script Properties** to add them. Access them with `PropertiesService.getScriptProperties().getProperty('KEY')`.

## Deploying as a Web App

A GAS web app is a public (or restricted) HTTP endpoint that runs your `doGet` or `doPost` function.

```javascript
function doPost(e) {
  const payload = JSON.parse(e.postData.contents);
  // process payload
  return ContentService.createTextOutput(JSON.stringify({ ok: true }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

To deploy:
1. Click **Deploy → New deployment**.
2. Select type: **Web app**.
3. Set **Execute as**: Me (uses your Google identity to access Sheets, etc.).
4. Set **Who has access**: Anyone (if called by external services) or NSLS only.
5. Click **Deploy** and copy the URL.

Each new deployment gets a new URL. To update without changing the URL, use **Manage deployments → Edit** on an existing deployment.

## Permissions and Sharing

The first time a trigger runs or a web app is called, GAS will prompt for OAuth authorization. You need to authorize it under your own Google account.

For scripts that run unattended (triggers, web apps), set **Execute as: Me** so the script always runs with your permissions — not the permissions of whoever triggers it.

To let teammates edit the script, share the Sheet (for bound scripts) or the standalone script project with them at [script.google.com](https://script.google.com).
