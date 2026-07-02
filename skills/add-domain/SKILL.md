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
  (Netlify never needs this — its CNAME alone verifies. Vercel usually doesn't,
  but see the exception in step 2c.)
- **Vercel:** `vercel domains add signal.nsls.org <project>` (or the dashboard:
  Project → Settings → Domains → Add). Vercel shows the CNAME target
  (`cname.vercel-dns.com`). Usually the CNAME alone verifies — **but** if Vercel
  says *"This domain is linked to another Vercel account"* and asks for a TXT at
  `_vercel.nsls.org`, do step 2c before the CNAME.
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

### 2c. Vercel only — the "linked to another account" TXT

Only needed when Vercel shows *"This domain is linked to another Vercel account"*
and asks for a TXT at `_vercel.nsls.org`. This happens because the `nsls.org`
apex is registered to a different Vercel account (the one that predates this
team); the TXT proves *this* account controls the DNS so it can claim the
subdomain. It does **not** move the domain or touch DNS hosting — nsls.org stays
in Route 53.

Copy the exact `vc-domain-verify=...` value from the Vercel domain screen and
have the proxy append it (same narrow verify credential as Railway):

```bash
curl -sX POST "$NSLS_DNS_PROXY_URL/vercel-verify" \
  -H "authorization: Bearer $NSLS_DNS_PROXY_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"value":"vc-domain-verify=<sub>.nsls.org,<code from Vercel>"}'
```

All Vercel verifications share the single `_vercel.nsls.org` record (one value
per subdomain), so the proxy **appends** — it won't disturb other sites'
verification (e.g. `ignite`). After Vercel flips to *Valid Configuration*, the
value can be removed with `DELETE /vercel-verify` (same body) — optional cleanup.

If `/health` shows `"vercelVerify": false`, the Vercel flow isn't enabled yet —
a one-time admin step: widen the verify IAM policy to include `_vercel.*` and set
`VERCEL_VERIFY=true` in Doppler (see `docs/SETUP.md` §1b in nsls-dns-proxy). Flag
it and fall back to an admin adding the TXT by hand until it's on.

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
