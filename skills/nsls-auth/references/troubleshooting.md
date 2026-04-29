# Troubleshooting

When the integration breaks, work the loop: **TRY → OBSERVE → DIAGNOSE → ADAPT → TRY AGAIN.** Don't randomly tweak. Read the actual error or behavior, find it in the table, work the diagnosis.

## Authorization → Callback

### `state` mismatch on callback

Symptom: callback handler rejects the request because `state` in the URL doesn't match the stored value, or there is no stored value at all.

Diagnose:

- Did the login route actually store `state` server-side? Inspect the session store before redirect.
- Is the session store shared across processes? In-memory session won't survive a load balancer or a serverless cold start.
- Did the user navigate to the callback URL directly without an outstanding login transaction? That should fail — and does.
- Are you using cookies with `SameSite=Strict`? The cross-origin redirect from `auth.nsls.org` may not send the cookie. Try `SameSite=Lax` for the OIDC transaction cookie.

Fix: persistent session store (Redis, Postgres, encrypted cookie), `SameSite=Lax`, log the stored vs. received `state` to confirm.

### `invalid_grant` on token exchange

Most common error in the integration. Three causes:

1. `redirect_uri` in the token exchange differs from the one sent in the authorize request. They must be byte-identical, including any query string.
2. The authorization code was already used. Codes are single-use.
3. PKCE `code_verifier` does not match the `code_challenge` originally sent. Verify the verifier is the exact same one stored at login start.

Fix: log all three values at login start and at callback, compare. Often the issue is a trailing slash, a different port in dev, or a regenerated verifier on each request.

### `invalid_redirect_uri` on the authorize request

The redirect URI sent isn't registered exactly on the client.

Diagnose: `npm run admin -- clients show <client_id>` (or check the Admin Portal). Compare to what your app sends.

Fix: re-register the client with the correct `redirect_uris`. They are exact-match — no wildcards, no path normalization.

### `unsupported_grant_type` on token exchange

You're using a flow other than `authorization_code` (or `refresh_token`). NSLS Auth only supports those two.

Fix: switch to authorization code flow. No implicit, no password grant.

## ID Token Validation

### Signature verification fails

Symptom: JWT library throws `JWS signature verification failed` or similar.

Diagnose:

- Is the local clock skewed? OIDC validation tolerates minor skew but not minutes. Check NTP.
- Is the JWKS cache stale? NSLS Auth rotates keys; your cache must refresh on miss.
- Is the `kid` in the token header present in your JWKS? If not, force a JWKS re-fetch.

Fix: use a library that handles JWKS rotation (`openid-client`, `jose` with `createRemoteJWKSet`, `authlib`). Don't pin the JWKS at startup and never refresh.

### `iss` mismatch

`iss` claim doesn't match the configured issuer URL.

Diagnose: did you point at a non-prod auth instance? `staging-auth.nsls.org` vs `auth.nsls.org`?

Fix: match `OIDC_ISSUER_URL` to the environment.

### `nonce` mismatch

Diagnose: same as `state` — server-side storage didn't survive the redirect.

Fix: same as `state` — persistent server-side session store.

## Session

### Login loop after callback

Symptom: callback succeeds, app redirects to `/`, `/` immediately redirects back to `/auth/login`.

Diagnose:

- Is the session cookie being set? Check the `Set-Cookie` header on the callback response.
- Is the session cookie scoped correctly? Domain, path, SameSite, Secure (on HTTPS).
- Is the session lookup on `/` failing immediately? Log the cookie and the lookup result.

Fix: make sure the callback response sets a cookie that the app's session middleware can read on the next request. Common bug: setting the cookie but reading from a different store.

### `401 invalid_token` from `/oidc/userinfo`

Access token expired, revoked, or the token was for an ineligible user.

Fix: clear the local app session, force fresh login. If you have a refresh token, attempt refresh first; if that also fails, force fresh login.

## Refresh Tokens

### `invalid_grant` on refresh

Central session was revoked. Causes:

- User reset their password
- User was disabled
- Refresh token rotation: an older token was used after a newer one was issued
- Client config was rotated (rare)

Fix: delete stored refresh token, clear local session, force fresh login. This is normal — don't try to recover.

### Refresh token rotates but next request uses old token

NSLS Auth may rotate the refresh token. When the response includes a new `refresh_token`, replace the stored one immediately. Don't keep using the old one.

Fix: in the refresh handler, always check `result.refresh_token` and persist if present.

### Parallel refresh requests fight each other

Two requests in flight both try to use the same refresh token. The second one fails because the first already rotated the token.

Fix: serialize refresh per session. A simple per-session mutex or a cached promise works.

## Roles

### `roles` claim missing

Two valid causes:

1. Client wasn't registered with `roles` scope, or the app didn't request `roles` in the authorize call.
2. User has no active auth-wide roles. Empty role set ≠ error.

Fix: confirm scope is requested AND granted. If the user genuinely has no roles, treat it as the empty set.

### Stale role state in a long-lived session

Already-issued ID tokens do not update in place. If the user's roles changed, your local session might still show the old set.

Fix: for sensitive actions, call `/oidc/userinfo` and reread `roles`. Or force a fresh authorize cycle with `prompt=login` to get a fresh ID token.

## Picture Writes (Trusted Clients Only)

### `403 access_denied`

Client wasn't registered with `can_manage_own_picture: true`.

Fix: update client registration. This is a tier 3 operation — get a Kevin / People-Ops admin to do it.

### `403 insufficient_scope`

Token doesn't have `profile` scope.

Fix: app must request `openid profile` (and have it granted).

### `400 invalid_request` on PUT

Picture URL failed validation. Causes:

- Not `https://`
- > 2048 chars
- Has fragment (`#...`) or userinfo (`user:pass@`)
- Host not on the auth service's `PROFILE_PICTURE_ALLOWED_HOSTS` list

Fix: emit a clean stable HTTPS URL on an allowed host.

### `503 temporarily_unavailable`

NSLS Auth has no `PROFILE_PICTURE_ALLOWED_HOSTS` configured for this environment. This is an auth-service config problem, not your app's problem.

Fix: talk to whoever runs the auth service. Picture writes are off in this environment.

### Picture write succeeds but `userinfo` shows old value

Almost never happens — `userinfo` returns the new value immediately. If it doesn't, you may be hitting a cache layer between your app and `auth.nsls.org`.

Fix: check for any caching proxy, send `Cache-Control: no-cache` if needed.

### Already-issued ID token still has old picture

Expected. ID tokens don't update in place. Use `userinfo` for the freshest value, or force a new login.

## Logout

### Logout returns to a generic provider page, not the branded login

`post_logout_redirect_uri` was either not sent, or not registered exactly on the client.

Fix:

1. Confirm the URI is registered in the client config (check `npm run admin -- clients show`).
2. Confirm the app is sending both `client_id` and `post_logout_redirect_uri` on the logout request.
3. Make the URI an app-owned login-start route, not a placeholder farewell page.

### Logout from one app didn't sign me out of another

Expected. NSLS Auth does not currently do front-channel or back-channel logout broadcasts. Each app's session is independent.

Fix: don't promise users that logout is global. Document this in the app if relevant.

## Cross-Domain SSO

### "It worked on `app.nsls.org` but not `thesociety.org`"

Usually because someone tried to share a cookie across both. Cookies do not cross top-level domains.

Fix: SSO works through redirects, not shared cookies. Each app does its own `/oidc/authorize` redirect; if the auth-domain session exists, NSLS Auth returns a code without prompting.

### Second app prompts for login even though first app is signed in

Diagnose: is the second app actually redirecting through `auth.nsls.org`, or is it bouncing the user to its own login form?

Fix: confirm the app's login route immediately redirects to `/oidc/authorize` with no intermediate prompts.

## Bootstrap / Local Dev

### Discovery fetch fails on app startup

Network issue, or `OIDC_ISSUER_URL` is wrong.

Fix: hit `https://auth.nsls.org/.well-known/openid-configuration` from the same machine. If that works, your env config is wrong. If it doesn't, check network / firewall.

### Local development uses HTTPS but NSLS Auth expects exact registered URL

If you registered `https://localhost:3000/auth/callback` but your dev server runs on `http://localhost:3000`, the redirect URI won't match.

Fix: register the exact URL you'll use in dev. For native apps, loopback `http://` is allowed.

### `OIDC_BOOTSTRAP_CLIENTS_JSON` missing in test environment

Local dev uses bootstrap clients seeded from this env var. Production does not — it uses the database.

Fix: set `OIDC_BOOTSTRAP_CLIENTS_JSON` in dev / test only. Never in production.

## Walking the Loop

If you're stuck and the table doesn't help:

1. **TRY** a minimal happy path. Strip everything but login → callback → exchange → claim print.
2. **OBSERVE** the exact error message, status code, response body. Log every step.
3. **DIAGNOSE** by comparing to the spec (`integration-guide.md`). Walk the validation rules one by one.
4. **ADAPT** the smallest possible thing.
5. **TRY AGAIN.**

Never silently retry. Never skip a validation step "just to see if it works." That's how you ship a vulnerability.
