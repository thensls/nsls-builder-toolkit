# Web App Implementation

Reference patterns for wiring NSLS Auth into a server-rendered or BFF-backed web app. The integration guide (`integration-guide.md`) is the source of truth for the protocol; this file shows how to express it in real code.

## Library Recommendations

Pick a library that handles discovery, PKCE, and JWKS rotation. Don't roll those yourself.

| Stack | Library | Why |
|---|---|---|
| Node / Express / Fastify | `openid-client` (panva) | Reference implementation. Handles discovery, PKCE, JWKS, ID token validation correctly. |
| Next.js (App Router) | `openid-client` in route handlers, OR NextAuth.js with a generic OIDC provider | NextAuth is faster to wire but more opaque. `openid-client` directly is more explicit. |
| Python / FastAPI / Flask | `authlib` | Mature OIDC client. `python-jose` + `httpx` works if you want fewer dependencies. |
| Ruby / Rails | `omniauth_openid_connect` | Standard OmniAuth strategy for OIDC. |
| Go | `github.com/coreos/go-oidc` + `golang.org/x/oauth2` | Coreos provider handles discovery + ID token validation. |

## Node + Express + openid-client

Minimal happy-path login + callback + logout. Production code needs more around session storage and error handling, but this is the shape.

```js
// auth.js — top-level await requires ESM ("type": "module" in package.json).
// For CommonJS, wrap discovery in an async init function the rest of the app awaits before serving.
import { Issuer, generators } from 'openid-client';
import session from 'express-session';

const issuer = await Issuer.discover(process.env.OIDC_ISSUER_URL);

export const oidcClient = new issuer.Client({
  client_id: process.env.OIDC_CLIENT_ID,
  client_secret: process.env.OIDC_CLIENT_SECRET,
  redirect_uris: [process.env.OIDC_REDIRECT_URI],
  post_logout_redirect_uris: [process.env.OIDC_POST_LOGOUT_REDIRECT_URI],
  response_types: ['code'],
  token_endpoint_auth_method: 'client_secret_post',
});

export const oidcScopes = process.env.OIDC_SCOPES || 'openid profile email';
```

```js
// routes/auth.js
import express from 'express';
import { generators } from 'openid-client';
import { oidcClient, oidcScopes } from '../auth.js';
import { findOrCreateUserByIssuerSub, createAppSession, destroyAppSession } from '../users.js';

const router = express.Router();

router.get('/auth/login', (req, res) => {
  const state = generators.state();
  const nonce = generators.nonce();
  const code_verifier = generators.codeVerifier();
  const code_challenge = generators.codeChallenge(code_verifier);

  // Store server-side, keyed to this browser's session.
  req.session.oidc = { state, nonce, code_verifier };

  const url = oidcClient.authorizationUrl({
    scope: oidcScopes,
    state,
    nonce,
    code_challenge,
    code_challenge_method: 'S256',
  });

  res.redirect(url);
});

router.get('/auth/callback', async (req, res, next) => {
  try {
    const stored = req.session.oidc;
    if (!stored) {
      return res.status(400).send('No outstanding login transaction');
    }
    delete req.session.oidc;

    const params = oidcClient.callbackParams(req);
    const tokenSet = await oidcClient.callback(
      process.env.OIDC_REDIRECT_URI,
      params,
      {
        state: stored.state,
        nonce: stored.nonce,
        code_verifier: stored.code_verifier,
      }
    );

    // openid-client validates iss, aud, nonce, exp, signature for us.
    const claims = tokenSet.claims();
    const user = await findOrCreateUserByIssuerSub({
      issuer: claims.iss,
      sub: claims.sub,
      claims,
    });

    await createAppSession(req, user, tokenSet);
    res.redirect('/');
  } catch (err) {
    next(err);
  }
});

router.post('/auth/logout', async (req, res) => {
  await destroyAppSession(req);
  const url = oidcClient.endSessionUrl({
    post_logout_redirect_uri: process.env.OIDC_POST_LOGOUT_REDIRECT_URI,
    client_id: process.env.OIDC_CLIENT_ID,
  });
  res.redirect(url);
});

export default router;
```

Notes:

- `req.session.oidc` must persist across the redirect. Use a real session store (Redis, Postgres) — not the default in-memory store in production.
- `findOrCreateUserByIssuerSub` does the identity mapping. The unique key is `(claims.iss, claims.sub)`. Update profile snapshot fields from claims. Never re-link by email after the first login.
- `createAppSession` issues your app's own cookie. Do not store the raw `access_token` or `id_token` in browser-accessible storage.

## Next.js App Router

In App Router, do the OIDC dance in route handlers under `app/api/auth/`. Same flow as Express, but the request/response shape is different.

```ts
// app/api/auth/callback/route.ts
import { NextResponse } from 'next/server';
import { oidcClient } from '@/lib/oidc';
import { cookies } from 'next/headers';
import { findOrCreateUserByIssuerSub, createAppSession } from '@/lib/users';

export async function GET(req: Request) {
  const cookieStore = cookies();
  const stored = JSON.parse(cookieStore.get('oidc-tx')?.value ?? 'null');
  if (!stored) {
    return NextResponse.json({ error: 'No outstanding login transaction' }, { status: 400 });
  }

  const url = new URL(req.url);
  const params = Object.fromEntries(url.searchParams);
  const tokenSet = await oidcClient.callback(
    process.env.OIDC_REDIRECT_URI!,
    params,
    {
      state: stored.state,
      nonce: stored.nonce,
      code_verifier: stored.code_verifier,
    }
  );

  const claims = tokenSet.claims();
  const user = await findOrCreateUserByIssuerSub({
    issuer: claims.iss,
    sub: claims.sub,
    claims,
  });

  const response = NextResponse.redirect(new URL('/', req.url));
  response.cookies.delete('oidc-tx');
  await createAppSession(response, user, tokenSet);
  return response;
}
```

The login route generates the same `state` / `nonce` / `code_verifier` triple, stores it in an HTTP-only cookie (or server-side keyed by an opaque cookie value), and redirects to `oidcClient.authorizationUrl(...)`.

## NextAuth.js (alternative for Next.js)

If the team is already on NextAuth, use the generic OIDC provider:

```ts
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth';

const handler = NextAuth({
  providers: [
    {
      id: 'nsls',
      name: 'NSLS',
      type: 'oauth',
      wellKnown: `${process.env.OIDC_ISSUER_URL}/.well-known/openid-configuration`,
      clientId: process.env.OIDC_CLIENT_ID,
      clientSecret: process.env.OIDC_CLIENT_SECRET,
      authorization: { params: { scope: process.env.OIDC_SCOPES } },
      idToken: true,
      checks: ['pkce', 'state', 'nonce'],
      profile(profile) {
        return {
          id: profile.sub,
          email: profile.email,
          name: profile.name,
          image: profile.picture,
        };
      },
    },
  ],
  callbacks: {
    async signIn({ account, profile }) {
      // Persist (account.provider, account.providerAccountId) → (issuer, sub)
      return true;
    },
    async session({ session, token }) {
      // Surface roles to the client only if you need them on the client.
      return session;
    },
  },
});

export { handler as GET, handler as POST };
```

NextAuth handles PKCE, state, nonce, and ID token validation when `checks: ['pkce', 'state', 'nonce']` is set.

## Python / FastAPI + authlib

```python
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
from fastapi import APIRouter, Request
import os

oauth = OAuth()
oauth.register(
    name="nsls",
    server_metadata_url=f"{os.environ['OIDC_ISSUER_URL']}/.well-known/openid-configuration",
    client_id=os.environ["OIDC_CLIENT_ID"],
    client_secret=os.environ["OIDC_CLIENT_SECRET"],
    client_kwargs={"scope": os.environ.get("OIDC_SCOPES", "openid profile email")},
)

router = APIRouter()

@router.get("/auth/login")
async def login(request: Request):
    redirect_uri = os.environ["OIDC_REDIRECT_URI"]
    return await oauth.nsls.authorize_redirect(request, redirect_uri)

@router.get("/auth/callback")
async def callback(request: Request):
    token = await oauth.nsls.authorize_access_token(request)
    claims = token["userinfo"]  # ID token claims, validated by authlib
    user = await find_or_create_user(issuer=claims["iss"], sub=claims["sub"], claims=claims)
    request.session["user_id"] = user.id
    return RedirectResponse("/")
```

`authlib` validates `iss`, `aud`, `nonce`, signature, and expiry when `authorize_access_token` is called.

## Rails + omniauth_openid_connect

```ruby
# config/initializers/omniauth.rb
Rails.application.config.middleware.use OmniAuth::Builder do
  provider :openid_connect, {
    name: :nsls,
    scope: ENV.fetch("OIDC_SCOPES", "openid profile email").split(" ").map(&:to_sym),
    response_type: :code,
    discovery: true,
    issuer: ENV.fetch("OIDC_ISSUER_URL"),
    client_options: {
      identifier: ENV.fetch("OIDC_CLIENT_ID"),
      secret: ENV.fetch("OIDC_CLIENT_SECRET"),
      redirect_uri: ENV.fetch("OIDC_REDIRECT_URI"),
    },
    pkce: true,
  }
end
```

Routes:

```ruby
# config/routes.rb
get  "/auth/login"               => redirect("/auth/nsls"), as: :auth_login
get  "/auth/nsls/callback"       => "sessions#create"
post "/auth/logout"              => "sessions#destroy"
```

In `SessionsController#create`, read `request.env["omniauth.auth"]`, find or create the user by `(issuer, sub)`, and create the Rails session.

## User Persistence

Recommended schema for the local user record:

```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY,
  auth_issuer     TEXT NOT NULL,
  auth_subject    TEXT NOT NULL,
  email           TEXT,
  email_verified  BOOLEAN,
  given_name      TEXT,
  family_name     TEXT,
  display_name    TEXT,
  picture_url     TEXT,
  last_authenticated_at TIMESTAMPTZ,
  last_claim_sync_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (auth_issuer, auth_subject)
);
```

Identity-mapping logic:

```js
async function findOrCreateUserByIssuerSub({ issuer, sub, claims }) {
  let user = await db.users.findUnique({ where: { auth_issuer_auth_subject: { auth_issuer: issuer, auth_subject: sub } } });
  if (!user) {
    user = await db.users.create({
      data: {
        auth_issuer: issuer,
        auth_subject: sub,
        email: claims.email,
        email_verified: claims.email_verified ?? false,
        given_name: claims.given_name,
        family_name: claims.family_name,
        display_name: claims.name,
        picture_url: claims.picture,
        last_authenticated_at: new Date(),
        last_claim_sync_at: new Date(),
      },
    });
  } else {
    user = await db.users.update({
      where: { id: user.id },
      data: {
        email: claims.email,
        email_verified: claims.email_verified ?? false,
        given_name: claims.given_name,
        family_name: claims.family_name,
        display_name: claims.name,
        picture_url: claims.picture,
        last_authenticated_at: new Date(),
        last_claim_sync_at: new Date(),
      },
    });
  }
  return user;
}
```

## Role Checks

If the client requested the `roles` scope:

```ts
type RoleClaim = { value: string; display?: string };

function roleSet(roles: RoleClaim[] | undefined) {
  return new Set((roles || []).map(r => r.value));
}

const granted = roleSet(claims.roles);
const isAdmin = granted.has('admin');
const isStaff = granted.has('staff');
```

For freshest role state (e.g. before a sensitive action), call `/oidc/userinfo` with the access token. Already-issued ID tokens do not update in place after a role change.

## Refresh Tokens

Only request `offline_access` if the app actually needs refresh. If it does:

- Store refresh tokens encrypted at rest, server-side only.
- Bind to the local user + session record.
- Replace the stored refresh token when NSLS Auth rotates it (the response will include a new `refresh_token`).
- On `invalid_grant`: delete stored refresh token, clear app session, force fresh login.

## Logout: Branded Re-Entry Pattern

For users to land on the centralized branded login page after logout:

1. Register `https://your-app.example.com/auth/login?status=signed_out` as a `post_logout_redirect_uri`.
2. Local logout: clear app session.
3. Redirect browser to `/oidc/logout?client_id=...&post_logout_redirect_uri=...`.
4. NSLS Auth clears the auth-domain session and redirects to your registered login-start URL.
5. Your login-start route immediately begins a fresh `/oidc/authorize` (it sees `?status=signed_out` and can show a "you've been signed out" banner on the next branded login page).

This avoids landing on a generic provider-owned logout page.
