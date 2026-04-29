# Netlify App Implementation

When the app is a static site on Netlify — typically an HTML deck, a generated dashboard, or a single-file presentation — there is no Node/Rails/Django server to host the OIDC client. Netlify **Edge Functions** are the BFF. The site stays static, four small Edge Functions handle login / callback / logout / gating, and a stateless cookie holds the session.

This pattern was validated end-to-end on the Q1 LOP dashboard (April 2026): static `index.html` + `tree.html` + `data.json` on `nsls-q1-2026.netlify.app`, gated to `@nsls.org` plus a small board allowlist.

## When to use this pattern

- App's UI is static — generated HTML, no SSR
- Already on Netlify and you want to keep deploy speed
- A small group needs access (e.g. `@nsls.org` + a few external emails)
- You don't need refresh tokens (presentations / dashboards are short sessions)

When this pattern is wrong:

- App needs SSR or DB writes during a request → use Vercel / Railway / Cloud Run with `references/web-app-implementation.md`
- Public site that doesn't need auth → don't add this complexity

## Why Edge Functions, not regular Functions

Regular Netlify Functions run on Node. Edge Functions run on Deno with web standards (`Request`, `Response`, `crypto.subtle`, `fetch`). Two reasons to prefer Edge:

1. The gate runs in front of every request and Edge runs at the CDN — single-digit-millisecond overhead vs ~50ms for a regular function cold start
2. One runtime for all four files keeps shared helpers (`_lib.ts`) trivial — no Node/Deno import-style mismatch

## File layout

```
your-site/
├── index.html              # existing static content
├── netlify.toml            # publish dir + build (existing)
├── netlify/
│   └── edge-functions/
│       ├── _lib.ts         # OIDC + cookie helpers shared across the others
│       ├── auth-login.ts   # GET /auth/login
│       ├── auth-callback.ts # GET /auth/callback
│       ├── auth-logout.ts  # GET /auth/logout
│       └── gate.ts         # gates everything except /auth/* and public assets
├── CLIENT_REGISTRATION.json # JSON to hand to the admin
└── .env.example             # env-var template
```

`netlify.toml` does **not** need any new entries — Edge Functions use file-based routing via `export const config = { path: "..." }` in each file.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Library | `npm:jose@5` only | ~80 lines of OIDC code; bundles small; readable |
| Session storage | Stateless JWT in HTTP-only cookie | No external store needed; survives redeploys; SESSION_SECRET signs it |
| Tx storage (state/nonce/PKCE) | Short-lived signed JWT cookie, 10-min TTL | Survives the redirect to auth.nsls.org and back without a server-side store |
| Gating mechanism | Edge Function with `path: "/*"`, `excludedPath` for `/auth/*` and public assets | Single declaration point; no per-page wiring |
| Allowlist | Suffix match on `@nsls.org` plus comma-separated env var of explicit emails | Update via Netlify UI, no redeploy |

## `_lib.ts` — shared helpers

```ts
// netlify/edge-functions/_lib.ts
import { SignJWT, jwtVerify, createRemoteJWKSet } from "npm:jose@5";

const enc = new TextEncoder();

export const SESSION_COOKIE = "app_session";
export const TX_COOKIE = "app_oidc_tx";

export function env(name: string): string {
  const v = Netlify.env.get(name);
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
}

export function envOptional(name: string, fallback = ""): string {
  return Netlify.env.get(name) ?? fallback;
}

let _discovery: any = null;
let _jwks: ReturnType<typeof createRemoteJWKSet> | null = null;

export async function discover() {
  if (_discovery) return _discovery;
  const issuer = env("OIDC_ISSUER_URL");
  const res = await fetch(`${issuer}/.well-known/openid-configuration`);
  if (!res.ok) throw new Error(`OIDC discovery failed: ${res.status}`);
  _discovery = await res.json();
  _jwks = createRemoteJWKSet(new URL(_discovery.jwks_uri));
  return _discovery;
}

export async function getJwks() {
  if (!_jwks) await discover();
  return _jwks!;
}

function b64url(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function randomB64url(byteLen = 32): string {
  const buf = new Uint8Array(byteLen);
  crypto.getRandomValues(buf);
  return b64url(buf);
}

export async function pkceChallenge(verifier: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", enc.encode(verifier));
  return b64url(digest);
}

function sessionKey(): Uint8Array {
  return enc.encode(env("SESSION_SECRET"));
}

export async function signCookieJwt(payload: Record<string, unknown>, ttlSeconds: number) {
  return await new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${ttlSeconds}s`)
    .sign(sessionKey());
}

export async function verifyCookieJwt<T = Record<string, unknown>>(token: string): Promise<T | null> {
  try {
    const { payload } = await jwtVerify(token, sessionKey());
    return payload as unknown as T;
  } catch {
    return null;
  }
}

export function readCookie(req: Request, name: string): string | null {
  const cookie = req.headers.get("cookie") ?? "";
  const match = cookie.match(new RegExp(`(?:^|; )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setCookie(name: string, value: string, opts: { maxAge: number; path?: string }): string {
  return [
    `${name}=${encodeURIComponent(value)}`,
    `Max-Age=${opts.maxAge}`,
    `Path=${opts.path ?? "/"}`,
    "HttpOnly",
    "Secure",
    "SameSite=Lax",
  ].join("; ");
}

export function clearCookie(name: string, path = "/"): string {
  return `${name}=; Max-Age=0; Path=${path}; HttpOnly; Secure; SameSite=Lax`;
}

export function isAllowedEmail(email: unknown): boolean {
  if (typeof email !== "string" || !email) return false;
  const e = email.toLowerCase();
  if (e.endsWith("@nsls.org")) return true;
  const list = envOptional("BOARD_ALLOWED_EMAILS")
    .toLowerCase().split(",").map((s) => s.trim()).filter(Boolean);
  return list.includes(e);
}
```

## `auth-login.ts` — start authorize

```ts
// netlify/edge-functions/auth-login.ts
import {
  discover, env, pkceChallenge, randomB64url, setCookie, signCookieJwt, TX_COOKIE,
} from "./_lib.ts";

export default async (_req: Request) => {
  const d = await discover();
  const state = randomB64url(24);
  const nonce = randomB64url(24);
  const verifier = randomB64url(48);
  const challenge = await pkceChallenge(verifier);

  const tx = await signCookieJwt({ state, nonce, verifier }, 600);

  const authorize = new URL(d.authorization_endpoint);
  authorize.searchParams.set("client_id", env("OIDC_CLIENT_ID"));
  authorize.searchParams.set("redirect_uri", env("OIDC_REDIRECT_URI"));
  authorize.searchParams.set("response_type", "code");
  authorize.searchParams.set("scope", "openid email profile");
  authorize.searchParams.set("state", state);
  authorize.searchParams.set("nonce", nonce);
  authorize.searchParams.set("code_challenge", challenge);
  authorize.searchParams.set("code_challenge_method", "S256");

  const headers = new Headers({ Location: authorize.toString() });
  headers.append("Set-Cookie", setCookie(TX_COOKIE, tx, { maxAge: 600 }));
  return new Response(null, { status: 302, headers });
};

export const config = { path: "/auth/login" };
```

## `auth-callback.ts` — exchange + validate + allowlist

```ts
// netlify/edge-functions/auth-callback.ts
import { jwtVerify } from "npm:jose@5";
import {
  clearCookie, discover, env, getJwks, isAllowedEmail, readCookie,
  SESSION_COOKIE, setCookie, signCookieJwt, TX_COOKIE, verifyCookieJwt,
} from "./_lib.ts";

interface Tx { state: string; nonce: string; verifier: string }

export default async (req: Request) => {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  if (!code || !state) return new Response("Missing code or state", { status: 400 });

  const txToken = readCookie(req, TX_COOKIE);
  if (!txToken) return new Response("No outstanding login transaction", { status: 400 });

  const tx = await verifyCookieJwt<Tx>(txToken);
  if (!tx || tx.state !== state) {
    return new Response("Invalid state — possible CSRF or expired login", { status: 400 });
  }

  const d = await discover();
  const tokenRes = await fetch(d.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: env("OIDC_REDIRECT_URI"),
      client_id: env("OIDC_CLIENT_ID"),
      client_secret: env("OIDC_CLIENT_SECRET"),
      code_verifier: tx.verifier,
    }),
  });
  if (!tokenRes.ok) {
    const body = await tokenRes.text();
    return new Response(`Token exchange failed: ${tokenRes.status} ${body}`, { status: 502 });
  }

  const { id_token: idToken } = await tokenRes.json();
  if (!idToken) return new Response("No id_token in token response", { status: 502 });

  const { payload } = await jwtVerify(idToken, await getJwks(), {
    issuer: env("OIDC_ISSUER_URL"),
    audience: env("OIDC_CLIENT_ID"),
  });
  if (payload.nonce !== tx.nonce) {
    return new Response("Nonce mismatch", { status: 400 });
  }

  if (!isAllowedEmail(payload.email)) {
    const headers = new Headers({ "Content-Type": "text/html; charset=utf-8" });
    headers.append("Set-Cookie", clearCookie(TX_COOKIE));
    return new Response(forbiddenHtml(String(payload.email ?? "")), { status: 403, headers });
  }

  const session = await signCookieJwt(
    { sub: payload.sub, email: payload.email, name: payload.name ?? "" },
    8 * 60 * 60,
  );

  const headers = new Headers({ Location: "/" });
  headers.append("Set-Cookie", setCookie(SESSION_COOKIE, session, { maxAge: 8 * 60 * 60 }));
  headers.append("Set-Cookie", clearCookie(TX_COOKIE));
  return new Response(null, { status: 302, headers });
};

function forbiddenHtml(email: string): string {
  // Minimal branded forbidden page — customize per app.
  return `<!doctype html><html><head><title>Access denied</title></head>
<body style="font-family:system-ui;max-width:480px;margin:80px auto;padding:0 24px">
<h1>Access denied</h1>
<p><code>${email.replace(/[&<>"']/g, "")}</code> isn't on the allowlist.</p>
<p><a href="/auth/logout">Sign out and try a different account</a></p>
</body></html>`;
}

export const config = { path: "/auth/callback" };
```

## `auth-logout.ts` — clear session, RP-initiated logout

```ts
// netlify/edge-functions/auth-logout.ts
import { clearCookie, discover, env, SESSION_COOKIE } from "./_lib.ts";

export default async (_req: Request) => {
  const d = await discover();
  const url = new URL(d.end_session_endpoint);
  url.searchParams.set("client_id", env("OIDC_CLIENT_ID"));
  url.searchParams.set("post_logout_redirect_uri", env("OIDC_POST_LOGOUT_REDIRECT_URI"));

  const headers = new Headers({ Location: url.toString() });
  headers.append("Set-Cookie", clearCookie(SESSION_COOKIE));
  return new Response(null, { status: 302, headers });
};

export const config = { path: "/auth/logout" };
```

## `gate.ts` — protect every page

```ts
// netlify/edge-functions/gate.ts
import { readCookie, SESSION_COOKIE, verifyCookieJwt } from "./_lib.ts";

interface Session { email?: string; sub?: string }

export default async (req: Request) => {
  const token = readCookie(req, SESSION_COOKIE);
  const session = token ? await verifyCookieJwt<Session>(token) : null;
  if (session?.email) return; // pass through to origin

  const url = new URL(req.url);
  return Response.redirect(new URL("/auth/login", url).toString(), 302);
};

export const config = {
  path: "/*",
  excludedPath: ["/auth/*", "/logo.png", "/favicon.ico", "/favicon.svg", "/robots.txt"],
};
```

## Required env vars

Set in Netlify UI → Site settings → Environment variables. Edge Functions read `Netlify.env.get(...)` at request time, so changes to `BOARD_ALLOWED_EMAILS` take effect on the next visit — no redeploy.

| Var | Example |
|---|---|
| `OIDC_ISSUER_URL` | `https://auth.nsls.org` |
| `OIDC_CLIENT_ID` | `your-app-web` |
| `OIDC_CLIENT_SECRET` | (the secret the admin pasted into the registration form) |
| `OIDC_REDIRECT_URI` | `https://your-site.netlify.app/auth/callback` |
| `OIDC_POST_LOGOUT_REDIRECT_URI` | `https://your-site.netlify.app/auth/login?status=signed_out` |
| `SESSION_SECRET` | output of `openssl rand -base64 48` |
| `BOARD_ALLOWED_EMAILS` | comma-separated non-`@nsls.org` emails |

## Allowlist patterns

The `isAllowedEmail` helper in `_lib.ts` handles the common case: `@nsls.org` plus a small list of board emails. Adapt for your app:

```ts
// Only the SLT
const SLT = ["kprentiss@nsls.org", "anish@nsls.org", /* ... */];
return SLT.includes(email.toLowerCase());

// Roles-based — request `roles` scope, check in callback
const roles = (payload.roles as Array<{ value: string }> | undefined) ?? [];
if (!roles.some((r) => r.value === "admin" || r.value === "staff")) {
  return forbiddenResponse();
}

// Multi-domain
const allowedDomains = ["nsls.org", "thesociety.org"];
const domain = email.toLowerCase().split("@")[1];
return allowedDomains.includes(domain);
```

## Failure modes specific to Netlify

| Symptom | Cause | Fix |
|---|---|---|
| Login loop after callback | `SESSION_SECRET` changed between login start and callback (e.g. set mid-deploy) | Set the secret once and leave it stable across deploys |
| `Token exchange failed: 400 invalid_grant` | `OIDC_REDIRECT_URI` env var doesn't byte-match what's registered on the client | Both must be `https://<site>.netlify.app/auth/callback` exactly |
| Edge Function not running on a path you expected to gate | `excludedPath` is too broad, or the path matched another Edge Function first | Order Edge Function declarations by specificity; check with `netlify functions:list --edge` |
| `Netlify.env.get(...)` returns `undefined` in local dev | Local env vars aren't auto-injected into Edge Functions | Run with `netlify dev` (not `netlify build && netlify serve`) so env vars are wired in |
| 503 from `auth.nsls.org` discovery | Cold start hit the issuer, transient | Module-level discovery cache (`_discovery`) absorbs subsequent requests |

## What this pattern doesn't give you

- **Refresh tokens.** Edge Functions are stateless and don't persist refresh tokens server-side. The 8-hour session forces a fresh login when expired. Add `offline_access` + Netlify Blobs (or external KV) only if you genuinely need longer sessions.
- **Per-user customization in the static HTML.** The HTML is served as-is; it doesn't see the user. Render user-specific data via a separate Edge Function that returns JSON the page fetches client-side, gated by the same session cookie.
- **Sign-out across tabs.** Logout clears the cookie for the requesting browser; other browsers / devices stay signed in until their session JWT expires.
