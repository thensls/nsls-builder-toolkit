# Cloudflare Workers

## When to Use It

Use Cloudflare Workers for edge logic and lightweight APIs that need to be fast and globally distributed. Workers run at Cloudflare's edge, meaning they execute close to the user with very low latency.

Workers are a good fit for:
- Lightweight HTTP APIs (webhooks, simple REST endpoints)
- Request routing or transformation (auth checks, header rewrites)
- Short-lived logic that doesn't need a persistent process
- Key-value lookups backed by Cloudflare KV

Don't use Workers for long-running processes, Slack bots (use Railway), or anything requiring a database with complex queries.

## Getting Access

Message Kevin in Slack: "I need access to Cloudflare Workers to deploy [what you're building]." He'll add you to the NSLS Cloudflare account.

## Wrangler CLI Basics

Wrangler is the official CLI for managing Workers.

**Install:**
```bash
npm install -g wrangler
```

**Authenticate:**
```bash
wrangler login
```

This opens a browser window to authorize Wrangler with your Cloudflare account. Make sure you're logging in with your NSLS account, not a personal one.

**Create a new Worker project:**
```bash
wrangler init my-worker
cd my-worker
```

This creates a `wrangler.toml` config file and a basic `src/index.js` (or `.ts`) entry point.

## Basic Worker Structure

```javascript
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === '/webhook' && request.method === 'POST') {
      const body = await request.json();
      // process body
      return new Response(JSON.stringify({ ok: true }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response('Not found', { status: 404 });
  }
};
```

Every Worker exports a `fetch` handler. It receives the incoming `Request`, your environment bindings (secrets, KV namespaces), and a context object.

## Deploying a Worker

```bash
wrangler deploy
```

This builds and uploads your Worker to Cloudflare. The first deploy creates the Worker. Subsequent deploys update it in place. Cloudflare deploys to all edge locations within about 30 seconds.

To deploy to a specific environment (staging vs. production), define environments in `wrangler.toml`:

```toml
[env.staging]
name = "my-worker-staging"

[env.production]
name = "my-worker"
```

Then deploy with: `wrangler deploy --env production`

## Environment Variables and Secrets

**Plain variables** (non-sensitive, committed to config):
```toml
[vars]
API_BASE_URL = "https://api.example.com"
```

**Secrets** (sensitive, never committed):
```bash
wrangler secret put AIRTABLE_TOKEN
```

Wrangler prompts for the value and stores it encrypted. Access it in code via `env.AIRTABLE_TOKEN`.

Never put secrets in `wrangler.toml` — that file gets committed to git.

## KV Storage

Cloudflare KV is a global key-value store. Use it for caching, simple state, or lookup tables that your Worker needs fast access to.

**Create a KV namespace:**
```bash
wrangler kv:namespace create MY_STORE
```

Wrangler outputs a namespace ID. Add it to `wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "MY_STORE"
id = "your-namespace-id"
```

**Read and write from the Worker:**
```javascript
// Write
await env.MY_STORE.put('key', 'value');
await env.MY_STORE.put('key', JSON.stringify(obj), { expirationTtl: 3600 });

// Read
const value = await env.MY_STORE.get('key');
const obj = await env.MY_STORE.get('key', { type: 'json' });
```

KV is eventually consistent — reads may lag slightly behind writes across regions. For most NSLS use cases this doesn't matter.

## Cost

The free tier covers 100,000 requests per day and 10ms CPU time per request. Nearly all NSLS automations fit within the free tier. Workers that do heavier computation may need the paid plan ($5/month) — check with Kevin before assuming you need it.
