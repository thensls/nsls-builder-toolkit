---
name: add-domain
description: >-
  Put an app, dashboard, or deck on a branded nsls.org subdomain — e.g.
  signal.nsls.org. Use when someone says "add a subdomain", "brand this URL",
  "put X on nsls.org", "custom domain", "give my app a real URL", "make a
  nice link for this deck", or names a target like "signal.nsls.org". Works
  for apps on Railway, Vercel, and Netlify. Safe by construction: it can only
  create subdomain CNAME records and physically cannot touch email, the apex,
  www, auth, or the domain's plumbing.
---

# Add a branded nsls.org subdomain

Turn `something.up.railway.app` (or `.vercel.app` / `.netlify.app`) into
`signal.nsls.org` in one flow. You never touch AWS — a scoped proxy does the
DNS change, and it is incapable of breaking anything but the subdomain you ask
for.

## Before you start

This skill calls the `nsls-dns-proxy` service. It reads two values from your
Claude Code environment (the `env` block in `~/.claude/settings.json`):

- `NSLS_DNS_PROXY_URL` — the deployed proxy:
  `https://nsls-dns-proxy-production.up.railway.app`
  (note the `-production` — the bare `nsls-dns-proxy.up.railway.app` host 404s)
- `NSLS_DNS_PROXY_TOKEN` — the shared bearer token. It's a secret, so it lives
  in no repo. Self-serve it from the nsls.org-gated doc (sign in with your NSLS
  Google account): https://docs.google.com/document/d/19hXZEgdgacnvzDIza6t5o26Zm7UpcFiYMPOknynukR8/edit
  (Source of truth is the Doppler project `nsls-dns-proxy` → `PROXY_AUTH_TOKEN`.)

Confirm both are set and the service is up before doing anything else:

```bash
echo "URL=$NSLS_DNS_PROXY_URL"            # should print the -production host
curl -s "$NSLS_DNS_PROXY_URL/health"      # expect {"ok":true,"service":"nsls-dns-proxy",...}
```

If either var is missing, run `/connect` and pick **NSLS DNS Proxy** — it writes
both into your `settings.json` `env` block. Then stop until they're set.

## Why this is safe (say this if asked)

The proxy holds one AWS credential scoped so it can **only** create/update/
delete `CNAME`/`A`/`AAAA` records under `nsls.org`. AWS itself denies the apex,
`www`, `auth`, MX (email), NS, SOA, and any `_underscore` record. There is no
way — through this skill or otherwise with that key — to take down email or the
website. Worst case is a mis-pointed subdomain, which this same skill reverses.

## Flow

### 1. Gather two things

- **The subdomain** they want: e.g. `signal` → becomes `signal.nsls.org`.
- **The app's current host URL**: e.g. `employee-profiles.up.railway.app`.
  Ask which platform it's on if unclear (Railway / Vercel / Netlify).

Heartbeat: `Branding signal.nsls.org → employee-profiles.up.railway.app (Railway).`

### 2. Claim the custom domain on the host platform FIRST

The host must know about the domain or it won't issue an HTTPS certificate.
**Order matters: do this before the DNS record**, because the platform tells you
the exact CNAME target to use.

- **Railway:** `railway domain <domain> --service <svc> --json`. The JSON
  returns two things you need: `dnsRecords[].requiredValue` (the CNAME target —
  use *that*, it may differ from the `.up.railway.app` URL) and
  `status.verificationToken` (a `railway-verify=...` string). Railway requires
  an **ownership-verification TXT** at `_railway-verify.<sub>.nsls.org` set to
  that token, or it stays in `VALIDATING_OWNERSHIP` and never issues a cert.
  The proxy creates this for you via its dedicated `POST /railway-verify`
  endpoint (backed by a separate, ultra-narrow credential that can write only
  `_railway-verify.*` TXT records — nothing else). So the Railway flow is:
  fetch the token → `POST /railway-verify {subdomain, token}` → then the CNAME.
  (Vercel and Netlify don't need this — their CNAME alone verifies.)
- **Vercel:** `vercel domains add signal.nsls.org <project>` — Vercel shows the
  CNAME target (`cname.vercel-dns.com`).
- **Netlify:** Site → Domain settings → Add custom domain — Netlify shows the
  CNAME target.

Capture the **CNAME target the platform gives you**. If the platform just
confirms the `.up.railway.app`/`.vercel.app`/`.netlify.app` hostname, use that.

### 2b. Railway only — create the ownership-verification TXT

Skip this for Vercel/Netlify. For Railway, take the `railway-verify=...` token
from step 2 and have the proxy write the TXT (its narrow verify credential):

```bash
curl -sX POST "$NSLS_DNS_PROXY_URL/railway-verify" \
  -H "authorization: Bearer $NSLS_DNS_PROXY_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"subdomain":"signal","token":"railway-verify=<token from railway status>"}'
```

If `/health` shows `"railwayVerify": false`, the verify credential isn't
configured on the proxy — fall back to an admin adding the TXT once, and flag it.

### 3. Dry-run the DNS change

```bash
curl -sX POST "$NSLS_DNS_PROXY_URL/domains" \
  -H "authorization: Bearer $NSLS_DNS_PROXY_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"subdomain":"signal","target":"<cname target from step 2>","dryRun":true}'
```

Show the user the `willCreate` payload and confirm before the real change.
If the proxy returns a 400, relay the message plainly (e.g. "auth.nsls.org is
protected") — don't retry around it.

### 4. Create the record

Same call without `dryRun`. On success you get back `{ url: "https://signal.nsls.org", status: "PENDING" }`.

### 5. Verify

```bash
dig +short signal.nsls.org CNAME      # should show the target
```

DNS propagates in a minute or two; the host platform issues TLS shortly after.
Tell the user: *"signal.nsls.org is live (HTTPS may take a couple of minutes
while the cert issues)."* Don't claim it's verified until `dig` resolves.

## Listing / removing

- List everything managed: `GET $NSLS_DNS_PROXY_URL/domains`
- Remove one: `DELETE $NSLS_DNS_PROXY_URL/domains/signal.nsls.org`

## Guardrails for you (the agent)

- Never suggest editing Route 53 directly or asking for AWS credentials — the
  proxy is the only path, on purpose.
- Never try to create `www`, `auth`, the apex, MX/TXT/NS, or `_`-prefixed
  names. The proxy will refuse; don't work around it.
- Always dry-run and confirm before a real change.
- If `dig` doesn't resolve after a few minutes, check that step 2 (claiming the
  domain on the host platform) actually completed — that's the usual culprit,
  not the DNS record.
