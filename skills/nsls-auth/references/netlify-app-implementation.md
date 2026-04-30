# Netlify App Implementation

When the app is a static site on Netlify — typically an HTML deck, a generated dashboard, or a single-file presentation — there is no Node/Rails/Django server to host the OIDC client. Netlify **Edge Functions** are the BFF. The site stays static, four small Edge Functions handle login / callback / logout / gating, and a stateless cookie holds the session.

This pattern was validated end-to-end on the Q1 LOP dashboard (April 2026): static `index.html` + `tree.html` + `data.json` on `nsls-q1-2026.netlify.app`, gated to a small allowlist managed at `auth.nsls.org`.

## When to use this pattern

- App's UI is static — generated HTML, no SSR
- Already on Netlify and you want to keep deploy speed
- A small group needs access (e.g. `*@nsls.org` plus a few external emails)
- You don't need refresh tokens (presentations / dashboards are short sessions)

When this pattern is wrong:

- App needs SSR or DB writes during a request → use Vercel / Railway / Cloud Run with `references/web-app-implementation.md`
- Public site that doesn't need auth → don't add this complexity

## Why Edge Functions, not regular Functions

Regular Netlify Functions run on Node. Edge Functions run on Deno with web standards (`Request`, `Response`, `crypto.subtle`, `fetch`). Two reasons to prefer Edge:

1. The gate runs in front of every request and Edge runs at the CDN — single-digit-millisecond overhead vs ~50ms for a regular function cold start
2. One runtime for all four files keeps shared helpers trivial — no Node/Deno import-style mismatch

## File layout

```
your-site/
├── index.html              # existing static content
├── netlify.toml            # publish dir + build (existing)
├── netlify/
│   └── edge-functions/
│       ├── shared/
│       │   └── util.ts     # OIDC + cookie helpers shared across the others
│       ├── auth-login.ts   # GET /auth/login
│       ├── auth-callback.ts # GET /auth/callback
│       ├── auth-logout.ts  # GET /auth/logout
│       └── gate.ts         # gates everything except /auth/* and public assets
├── CLIENT_REGISTRATION.json # JSON to hand to the admin
└── .env.example             # env-var template
```

`netlify.toml` does **not** need any new entries — Edge Functions use file-based routing via `export const config = { path: "..." }` in each file.

**Why `shared/util.ts` and not `_lib.ts` at the root?** Any `.ts` file at the **root** of `netlify/edge-functions/` is auto-registered as an Edge Function entry point. A leading underscore does **not** opt out. If your shared helper sits at the root, the bundler tries to register it and fails with `Default export must be a function`. Put shared code in a subdirectory — those are not auto-registered, only imported.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Library | `jose@5` via `https://esm.sh/jose@5.x.x` | ~80 lines of OIDC code; bundles small; readable. **Use the `esm.sh` URL form, not `npm:jose@5`** — the npm specifier doesn't reliably resolve in Netlify Edge Function bundling and fails with `Could not resolve "npm:jose@5"`. |
| Session storage | Stateless JWT in HTTP-only cookie | No external store needed; survives redeploys; SESSION_SECRET signs it |
| Tx storage (state/nonce/PKCE) | Short-lived signed JWT cookie, 10-min TTL | Survives the redirect to auth.nsls.org and back without a server-side store |
| Gating mechanism | Edge Function with `path: "/*"`, `excludedPath` for `/auth/*` and public assets | Single declaration point; no per-page wiring |
| Allowlist | Per-client "Allowed Users" field on the OIDC client at `auth.nsls.org` (supports wildcards like `*@nsls.org`) | Single source of truth. Updates take effect immediately — no redeploy, no Netlify env touch. App-side allowlist code is unnecessary duplication. |

## `shared/util.ts` — shared helpers

```ts
// netlify/edge-functions/shared/util.ts
import { SignJWT, jwtVerify, createRemoteJWKSet } from "https://esm.sh/jose@5.9.6";

const enc = new TextEncoder();

export const SESSION_COOKIE = "app_session";
export const TX_COOKIE = "app_oidc_tx";

export function env(name: string): string {
  const v = Netlify.env.get(name);
  if (!v) throw new Error(`Missing env var: ${name}`);
  return v;
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
```

No `isAllowedEmail` helper — access control lives in the OIDC client's Allowed Users field at `auth.nsls.org`. If the user reaches the callback with a valid ID token, they're authorized.

## `auth-login.ts` — start authorize

```ts
// netlify/edge-functions/auth-login.ts
import {
  discover, env, pkceChallenge, randomB64url, setCookie, signCookieJwt, TX_COOKIE,
} from "./shared/util.ts";

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

## `auth-callback.ts` — exchange + validate

```ts
// netlify/edge-functions/auth-callback.ts
import { jwtVerify } from "https://esm.sh/jose@5.9.6";
import {
  clearCookie, discover, env, getJwks, readCookie,
  SESSION_COOKIE, setCookie, signCookieJwt, TX_COOKIE, verifyCookieJwt,
} from "./shared/util.ts";

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
    console.error(`Token exchange failed: ${tokenRes.status} ${body}`);
    return new Response("Authentication failed. Please try again or contact support.", { status: 502 });
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

  // No app-side allowlist check — auth.nsls.org's per-client Allowed Users
  // field already gated this user before issuing tokens. If they got here,
  // they're authorized.

  const session = await signCookieJwt(
    { sub: payload.sub, email: payload.email, name: payload.name ?? "" },
    8 * 60 * 60,
  );

  const headers = new Headers({ Location: "/" });
  headers.append("Set-Cookie", setCookie(SESSION_COOKIE, session, { maxAge: 8 * 60 * 60 }));
  headers.append("Set-Cookie", clearCookie(TX_COOKIE));
  return new Response(null, { status: 302, headers });
};

export const config = { path: "/auth/callback" };
```

## `auth-logout.ts` — clear session, RP-initiated logout

```ts
// netlify/edge-functions/auth-logout.ts
import { clearCookie, discover, env, SESSION_COOKIE } from "./shared/util.ts";

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
import { readCookie, SESSION_COOKIE, verifyCookieJwt } from "./shared/util.ts";

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

Set in Netlify UI → Site settings → Environment variables. Edge Functions read `Netlify.env.get(...)` at request time.

| Var | Example |
|---|---|
| `OIDC_ISSUER_URL` | `https://auth.nsls.org` |
| `OIDC_CLIENT_ID` | `your-app-web` |
| `OIDC_CLIENT_SECRET` | output of "Generate Secret" in the Admin Portal — copy once, store in 1Password, paste into Netlify |
| `OIDC_REDIRECT_URI` | `https://your-site.netlify.app/auth/callback` |
| `OIDC_POST_LOGOUT_REDIRECT_URI` | `https://your-site.netlify.app/auth/login?status=signed_out` |
| `SESSION_SECRET` | output of `openssl rand -base64 48` |

**Set secrets without leaking them into your shell history or any chat transcript.** For the client secret, copy from the Admin Portal directly into 1Password, then from 1Password into the Netlify UI (or `netlify env:set OIDC_CLIENT_SECRET 'value'` from a terminal). For `SESSION_SECRET`, pipe straight in: `netlify env:set SESSION_SECRET "$(openssl rand -base64 48)" --context production`. **Do not** run `netlify env:list --plain` — it dumps every value, including secrets, to stdout.

## Managing access — the auth-side allowlist

The OIDC client at `auth.nsls.org` has an **Allowed Users** field. Edit it directly to control who can sign in.

- One email per line
- Wildcards work: `*@nsls.org` covers everyone with an NSLS staff email
- Add specific external emails (board members, contractors) on their own lines
- Leaving the field blank lets any auth-eligible user authenticate — usually wrong; explicit list is safer

Why this beats an app-side allowlist:

- **Single source of truth.** Two allowlists drift; one doesn't.
- **No redeploy.** UI edit takes effect on the next sign-in.
- **Auditable.** Admin Portal changes are logged centrally.
- **Per-client scoping.** The list applies only to this OIDC client, so adding someone here doesn't expose them to every other NSLS app.

If you need finer-grained authorization than "can sign in / can't" — e.g. admin vs. read-only inside the app — that's app-level role logic, not identity. Request the `roles` scope and decide in your code:

```ts
const roles = (payload.roles as Array<{ value: string }> | undefined) ?? [];
const isAdmin = roles.some((r) => r.value === "admin");
```

## Failure modes specific to Netlify

| Symptom | Cause | Fix |
|---|---|---|
| Build fails: `Could not resolve "npm:jose@5"` | Netlify Edge Function bundler doesn't reliably resolve `npm:` specifiers | Use `https://esm.sh/jose@5.9.6` (or any pinned 5.x) instead |
| Build fails: `Default export in '_lib.ts' must be a function` | Any `.ts` at the root of `netlify/edge-functions/` is auto-registered as an entry point — leading underscores don't opt out | Move shared helpers into a subdirectory (`shared/util.ts`); subdirectory files are imported but not auto-registered |
| Login loop after callback | `SESSION_SECRET` changed between login start and callback (e.g. set mid-deploy, or rotated) | Set the secret once and leave it stable; users mid-flow when you rotate will need to start over |
| `Token exchange failed: 400 invalid_grant` | `OIDC_REDIRECT_URI` env var doesn't byte-match what's registered on the client | Both must be `https://<site>.netlify.app/auth/callback` exactly — including trailing characters |
| Edge Function not running on a path you expected to gate | `excludedPath` is too broad, or the path matched another Edge Function first | Order Edge Function declarations by specificity; check with `netlify functions:list --edge` |
| `Netlify.env.get(...)` returns `undefined` in local dev | Local env vars aren't auto-injected into Edge Functions | Run with `netlify dev` (not `netlify build && netlify serve`) so env vars are wired in |
| 503 from `auth.nsls.org` discovery | Cold start hit the issuer, transient | Module-level discovery cache (`_discovery`) absorbs subsequent requests |

## What this pattern doesn't give you

- **Refresh tokens.** Edge Functions are stateless and don't persist refresh tokens server-side. The 8-hour session forces a fresh login when expired. Add `offline_access` + Netlify Blobs (or external KV) only if you genuinely need longer sessions.
- **Per-user customization in the static HTML.** The HTML is served as-is; it doesn't see the user. Render user-specific data via a separate Edge Function that returns JSON the page fetches client-side, gated by the same session cookie.
- **Sign-out across tabs.** Logout clears the cookie for the requesting browser; other browsers / devices stay signed in until their session JWT expires.
