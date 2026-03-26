# Val Town

Val Town is a serverless platform for JS/TS where saving code deploys it instantly. Write a function, hit save, get a live URL. Built-in SQLite, blob storage, cron, and email.

## When to Use

- Webhook receivers (Slack, GitHub, Airtable, Stripe)
- Cron jobs and scheduled tasks
- Small APIs (< 10 min execution)
- Prototypes and internal tools
- Bot logic that doesn't need persistent connections (no WebSockets)

## When NOT to Use

- Long-running processes (use Railway)
- Need Python, Go, or non-JS languages (use Railway)
- Need global edge distribution (use Cloudflare Workers)
- Need WebSocket connections (use Railway)
- Heavy computation or large file processing

## Key Concepts

**Val** — a unit of deployed code. Every save creates a new version. Instant rollbacks.

**Projects** — multi-file vals with folders, branches, and merging. Feature branches get separate URLs.

**Runtime** — Deno-based. TypeScript and JavaScript. npm packages work via `npm:` specifier (no install step).

## Getting Started

### Web Editor (fastest)

1. Go to val.town and sign in with the NSLS team account
2. Create a new val
3. Write your code
4. Save — it's deployed

### CLI (for local development)

Install:
```bash
deno install --global jsr:@valtown/vt
```

Key commands:
```bash
vt clone <val-name>          # pull val locally
vt watch                     # auto-sync local edits on save
vt branch <name>             # create a feature branch
vt checkout <branch>         # switch branches
```

Auth: set `VAL_TOWN_API_KEY` env var (get from val.town/settings/api).

## HTTP Endpoints

Every val with a default export that takes a Request gets a public URL.

```typescript
export default function(req: Request): Response {
  return new Response("Hello from NSLS!");
}
```

URL format: `https://<username>-<val-name>.web.val.run`

Works with Hono and other web frameworks:

```typescript
import { Hono } from "npm:hono";

const app = new Hono();

app.get("/", (c) => c.text("Hello"));
app.post("/webhook", async (c) => {
  const body = await c.req.json();
  // handle webhook
  return c.json({ ok: true });
});

export default app.fetch;
```

## Cron / Scheduled

Add a cron expression or interval to run a val on a schedule.

```typescript
// Runs every hour
export default async function() {
  // check something, send an alert, sync data
}
```

Configure schedule in the val settings (web UI) or via the API.

- Free tier: minimum 15-minute intervals
- Pro/Teams: minimum 1-minute intervals

## SQLite

Each val gets a built-in SQLite database. ACID transactions, indexes.

```typescript
import { sqlite } from "https://esm.town/v/std/sqlite";

// Create table
await sqlite.execute(`CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  name TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)`);

// Insert
await sqlite.execute("INSERT INTO events (name) VALUES (?)", ["deployment"]);

// Query
const results = await sqlite.execute("SELECT * FROM events");
```

Storage limits: 10 MB free, 1 GB on Pro/Teams.

## Blob Storage

For unstructured data (JSON, images, files).

```typescript
import { blob } from "https://esm.town/v/std/blob";

// Store
await blob.set("config", JSON.stringify({ key: "value" }));

// Retrieve
const data = await blob.get("config");

// List
const keys = await blob.list();
```

Note: blob storage is NOT concurrency-safe. Don't write to the same key from multiple concurrent requests. Use SQLite for concurrent access.

## Secrets / Environment Variables

Set via the val settings sidebar in the web editor.

Access in code:
```typescript
const apiKey = Deno.env.get("AIRTABLE_API_KEY");
// or
const apiKey = process.env.AIRTABLE_API_KEY;
```

On Teams plan, use Environment Groups to share secrets across vals.

## Email

Send emails (free tier: only to yourself; Pro: to anyone):

```typescript
import { email } from "https://esm.town/v/std/email";

await email({
  to: "user@nsls.org",
  subject: "Alert",
  text: "Something happened",
});
```

Rate limit: 100 emails/minute.

## Limitations

| Limit | Free | Pro/Teams |
|-------|------|-----------|
| Execution time per run | 1 min | 10 min |
| Daily runs | 100,000 | 1,000,000+ |
| Cron minimum interval | 15 min | 1 min |
| Storage (SQLite + blob) | 10 MB | 1 GB |
| Private vals | 5 | Unlimited |
| Custom domains | 0 | 10+ |

Other limits:
- Single region (Ohio) — latency penalty for users far from US East
- No filesystem access — use blob storage
- JS/TS only — no Python, Go, etc.
- Max 1,000 files per val, 100 branches per val
- No native binary packages

## Cost

NSLS uses a Teams account. Most vals will fit comfortably in the included allocation. Kevin monitors usage via the team dashboard.

## After Deploying

Register your automation: say "register this automation" to track it in the Automation Tracker.
