# Downstream App Integration Guide

## Purpose

Use this document when migrating an NSLS-controlled web application to authenticate through NSLS Auth at `https://auth.nsls.org`.

## What NSLS Auth Is

NSLS Auth is the centralized OpenID Connect (OIDC) provider for NSLS-owned applications.

It provides:

1. one shared authentication domain
2. centralized login, registration, password reset, and email verification
3. one OIDC issuer for downstream web apps
4. social sign-in through Google, Microsoft, and Apple
5. shared identity claims for NSLS first-party products

It does not provide:

1. a shared browser cookie across unrelated domains such as `.nsls.org` and `thesociety.org`
2. downstream app-specific fine-grained authorization policy or per-app role management
3. public SPA-only client support
4. global logout across every downstream app

## Integration Model

The downstream app must integrate as either a confidential OIDC web client or a public OIDC native client.

That means:

1. web apps have a server or backend-for-frontend layer and store the client secret on the server only
2. native apps act as public clients without a client secret, using an in-app browser for the flow
3. the browser is redirected to `auth.nsls.org` for sign-in
4. the app receives an authorization code on its callback URL
5. the app exchanges that code securely for tokens
6. the app validates the ID token and creates its own local session

This is the intended SSO model:

1. the browser signs in once on `auth.nsls.org`
2. later, a second app sends the browser to `auth.nsls.org/oidc/authorize`
3. NSLS Auth sees the existing auth-domain session
4. NSLS Auth immediately redirects back to the second app with a fresh authorization code

This works even when the apps are on different top-level domains such as `app.nsls.org` and `thesociety.org`, because the SSO session lives on the auth domain, not on the app domains.

## Ownership Boundaries

NSLS Auth owns:

1. user authentication
2. login and registration UX
3. account recovery and verification
4. social identity federation
5. auth-wide coarse roles such as `admin` and `staff`
6. OIDC discovery, authorization, token, userinfo, JWKS, revocation, introspection, and logout endpoints

The downstream app owns:

1. its own local app session
2. its own fine-grained authorization rules and any app-specific roles or permissions
3. its own app cookies
4. its own callback route and code exchange logic
5. its own logout UX and post-logout cleanup

## Hard Requirements

Every downstream app integration must follow these rules:

1. use the authorization code flow only
2. use PKCE on every authorization request
3. register exact redirect URIs
4. use `https` redirect URIs (or custom URI schemes for native applications)
5. use a valid client auth method: `client_secret_basic` or `client_secret_post` for web apps, or `none` for native apps
6. request only supported scopes: `openid`, `profile`, `email`, optional `offline_access`, and optional `roles`
7. keep any client secret out of browser or native client code
8. create the app's own local session after login
9. treat `sub` as the stable user identifier
10. do not key identity off email alone after migration

If the app is a pure web SPA with no backend, add a backend-for-frontend before migrating. Pure web browser public clients are not supported, though native mobile applications are explicitly supported.

## Core Endpoints

Always start from the discovery document:

```text
https://auth.nsls.org/.well-known/openid-configuration
```

Core endpoints:

| Purpose | Endpoint |
| --- | --- |
| Discovery | `/.well-known/openid-configuration` |
| Authorization | `/oidc/authorize` |
| Token | `/oidc/token` |
| UserInfo | `/oidc/userinfo` |
| JWKS | `/oidc/jwks` |
| Logout | `/oidc/logout` |
| Introspection | `/oidc/introspection` |
| Revocation | `/oidc/revocation` |

Downstream apps should read these from discovery at startup and should not hardcode endpoint paths beyond the issuer unless they have a strong operational reason.

## Supported Scopes And Claims

Supported scopes:

| Scope | Meaning |
| --- | --- |
| `openid` | Required for every login. Provides the stable subject identifier and auth context claims. |
| `email` | Returns `email` and `email_verified`. |
| `profile` | Returns `name`, `given_name`, `family_name`, and optional `picture`. |
| `offline_access` | Allows refresh-token issuance. |
| `roles` | Returns auth-wide coarse role claims such as `admin` or `staff`. This scope is optional and must be requested explicitly by the app. |

Current claim set exposed by NSLS Auth:

| Claim | Notes |
| --- | --- |
| `sub` | Stable NSLS Auth subject. Use this as the primary external identity key. |
| `email` | Current email address when the `email` scope is granted. |
| `email_verified` | Boolean email verification state when the `email` scope is granted. |
| `given_name` | First name when the `profile` scope is granted. |
| `family_name` | Last name when the `profile` scope is granted. |
| `name` | Full display name when the `profile` scope is granted. |
| `picture` | Canonical cross-app avatar URL when the `profile` scope is granted and a canonical picture is set. |
| `roles` | Auth-wide coarse roles when the `roles` scope is granted and the user has active roles. Emitted as a SCIM-style array such as `[{"value":"admin","display":"Admin"},{"value":"staff","display":"Staff"}]`. |
| `acr` | Authentication context class reference. |
| `amr` | Authentication methods reference array. |

Typical `acr` and `amr` examples:

1. password login: `acr=urn:nsls:auth:password`, `amr=["pwd"]`
2. Google login: `acr=urn:nsls:auth:google`, `amr=["google"]`
3. Microsoft login: `acr=urn:nsls:auth:microsoft`, `amr=["microsoft"]`
4. linked-provider flow may include multiple `amr` values

Use `sub` for identity. Treat `acr` and `amr` as authentication context signals, not as application authorization roles.

When the app requests `roles`, authorize off `roles[*].value`, not `acr` or `amr`.

Important role-claim behavior:

1. `roles` is omitted unless the app was granted the `roles` scope
2. `roles` is omitted when the user has no active auth-wide roles
3. a user may have zero, one, or many active roles at the same time
4. treat `roles` as an unordered additive set, not a primary-role field
5. already-issued ID tokens do not update in place after a role change
6. use `/oidc/userinfo` or force a fresh login when the app needs the newest role state immediately

### Checking `admin` And `staff` In A Downstream App

For internal apps, the usual pattern is to map `roles[*].value` into a set and check for the exact role keys you care about.

Example:

```ts
type RoleClaim = {
  value: string;
  display?: string;
};

function roleSet(roles: RoleClaim[] | undefined) {
  return new Set((roles || []).map((role) => role.value));
}

const grantedRoles = roleSet(claims.roles);

const isAdmin = grantedRoles.has('admin');
const isStaff = grantedRoles.has('staff');

// Example internal-app policy:
const canAccessAdminScreens = isAdmin;
const canAccessStaffScreens = isStaff || isAdmin;
```

Notes:

1. request the `roles` scope or the `roles` claim will be omitted
2. read `roles` from the validated ID token at login time, or from `/oidc/userinfo` when you need the freshest role state
3. a missing `roles` claim means the user currently has no granted auth-wide roles for app authorization purposes
4. do not assume `admin` automatically implies `staff` unless your app explicitly chooses that policy

## Client Registration

Each downstream app must be registered as its own OIDC client.

Examples:

1. `app.nsls.org` should be its own client
2. `thesociety.org` should be its own client
3. a mobile API gateway or admin app should be separate clients if they have different callback URLs or secrets

### Choose Client Metadata

For each app, define:

1. `client_id`
2. `client_name`
3. optional `logo_uri`
4. optional `auth_ui`
5. optional `auth_page`
6. `application_type` (`web` or `native`)
7. `client_secret` (required for `web`, omitted for `native` public clients)
8. optional `can_manage_own_picture`
9. `token_endpoint_auth_method`
10. `grant_types`
11. `response_types`
12. `scope`
13. `redirect_uris`
14. `post_logout_redirect_uris`

`client_name` is the downstream app name shown on the shared login and registration pages.

Branding metadata is split into three separate concerns:

1. `logo_uri`: optional app mark shown on generic auth pages and the Symfony-style login variant
2. `auth_ui`: optional shared color palette for branded auth pages
3. `auth_page`: optional layout and content metadata for richer auth interaction presentation

`auth_ui` is color-only. Layout or image fields do not belong inside `auth_ui`.

Current `auth_page` behavior:

1. `variant: "societyLogin"` enables the Society-style login and registration presentation
2. if you omit Society-specific content fields, built-in defaults from the current Society screen are used
3. `variant: "symfonyLogin"` enables the Symfony-style login presentation for sign-in only
4. registration, password reset, email verification, forgot-password, provider-link confirmation, account management, and similar adjacent pages keep the generic shared shell
5. those adjacent account pages still use the downstream app `logo_uri` and `auth_ui` colors
6. the Society-style login/register pages keep the fixed Society mark instead of the downstream app logo
7. `symfonyLogin` currently only uses `variant`; other `auth_page` fields are ignored

Recommended defaults for a normal server-rendered or BFF-backed web app:

```json
[
  {
    "client_id": "thesociety-web",
    "client_name": "The Society Web",
    "application_type": "web",
    "logo_uri": "https://thesociety.org/static/auth-logo.png",
    "auth_ui": {
      "backgroundColor": "#fff7f1",
      "panelColor": "#fff7f1",
      "textColor": "#003250",
      "accentColor": "#f16b68",
      "primaryButtonColor": "#003250",
      "primaryButtonTextColor": "#ffffff"
    },
    "auth_page": {
      "variant": "societyLogin",
      "displayFont": "hermeneusOne",
      "bodyFont": "hankenGrotesk",
      "heroImageUri": "https://thesociety.org/static/auth-hero.jpg",
      "heroImageAlt": "Students collaborating",
      "introEyebrow": "Welcome",
      "introTitle": "Career.\nCoaching.\nClarity.",
      "introBody": "Welcome to Society (beta), a new platform for success from the NSLS.",
      "footerLogoUri": "https://thesociety.org/static/footer-logo.png",
      "footerLogoAlt": "NSLS"
    },
    "client_secret": "replace-with-a-long-random-secret",
    "token_endpoint_auth_method": "client_secret_post",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "scope": "openid profile email offline_access",
    "redirect_uris": ["https://thesociety.org/auth/callback"],
    "post_logout_redirect_uris": ["https://thesociety.org/logout/callback"]
  }
]
```

Recommended defaults for a native app (e.g. React Native):

```json
[
  {
    "client_id": "thesociety-mobile",
    "client_name": "The Society Mobile",
    "application_type": "native",
    "token_endpoint_auth_method": "none",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "scope": "openid profile email offline_access",
    "redirect_uris": ["thesocietyapp://oauth2/callback"],
    "post_logout_redirect_uris": ["thesocietyapp://oauth2/logout"]
  }
]
```

`application_type` is immutable after registration. To switch a client between `web` and `native`, delete it and recreate it with the new type.

For native apps, redirect URIs may use `https:`, loopback `http:`, or a private custom scheme such as `thesocietyapp://oauth2/callback`. Browser-reserved schemes such as `javascript:` and `data:` are rejected.

Use `refresh_token` and `offline_access` only if the app actually needs session renewal without a fresh browser roundtrip.

Add `roles` to the registered scope only if the app needs coarse auth-wide role checks from NSLS Auth.

Enable `can_manage_own_picture` only for trusted first-party clients that need to update the current authenticated user's canonical cross-app avatar in NSLS Auth.

If you set `logo_uri`, it must be an absolute `https:` URL without fragments or userinfo. Generic shared auth pages and the Symfony-style login variant use it directly, so host it on infrastructure you control.

If you set `auth_ui`, the allowed keys are:

1. `backgroundColor`
2. `panelColor`
3. `textColor`
4. `accentColor`
5. `primaryButtonColor`
6. `primaryButtonTextColor`

If you set `auth_page`, the current supported keys are:

1. `variant` for all auth-page variants
2. `heroImageUri` for `societyLogin`
3. `heroImageAlt` for `societyLogin`
4. `displayFont` for `societyLogin`
5. `bodyFont` for `societyLogin`
6. `introEyebrow` for `societyLogin`
7. `introTitle` for `societyLogin`
8. `introBody` for `societyLogin`
9. `footerLogoUri` for `societyLogin`
10. `footerLogoAlt` for `societyLogin`

All branding URLs in `logo_uri` and `auth_page` must be absolute `https:` URLs without fragments or userinfo.

Current bundled `societyLogin` font options are:

1. `displayFont`: `fraunces` or `hermeneusOne`
2. `bodyFont`: `inter` or `hankenGrotesk`

For the Symfony-style login presentation, use:

```json
{
  "auth_page": {
    "variant": "symfonyLogin"
  }
}
```

### Production Registration

In production, the recommended approach is to register or update clients dynamically through the **Admin Portal UI**.
Administrators can log in to the central auth portal, navigate to the "Apps" management section, and interactively register web or native clients without interacting with the CLI.
The portal currently manages `logo_uri`, `auth_ui`, and `auth_page.variant` directly. Richer `societyLogin` content overrides are still managed through JSON client definitions or bootstrap metadata.

Alternatively, you may still use the admin CLI:

For deployed AWS environments in this repository, use [AWS Admin CLI Runbook](./aws/09-admin-cli-runbook.md) to execute the same command as a one-off ECS task with the deployed runtime configuration.

```bash
npm run admin -- clients upsert /path/to/client-definition.json
```

Or through stdin:

```bash
cat /path/to/client-definition.json | npm run admin -- clients upsert -
```

Useful inspection commands:

```bash
npm run admin -- clients list
npm run admin -- clients show thesociety-web
```

### Development And Test Registration

For local development and automated tests, `OIDC_BOOTSTRAP_CLIENTS_JSON` may be used to seed clients automatically.

Do not use `OIDC_BOOTSTRAP_CLIENTS_JSON` in production.

## App Configuration Contract

Every downstream app should have explicit environment variables for its OIDC configuration.

Recommended minimum set:

```dotenv
OIDC_ISSUER_URL=https://auth.nsls.org
OIDC_CLIENT_ID=thesociety-web
OIDC_CLIENT_SECRET=replace-me
OIDC_REDIRECT_URI=https://thesociety.org/auth/callback
OIDC_POST_LOGOUT_REDIRECT_URI=https://thesociety.org/logout/callback
OIDC_SCOPES=openid profile email offline_access
```

Append `roles` to `OIDC_SCOPES` only when the app needs auth-wide coarse roles from NSLS Auth.

Recommended app behavior:

1. fetch discovery from `OIDC_ISSUER_URL/.well-known/openid-configuration`
2. cache the discovery metadata
3. cache and refresh JWKS keys as needed
4. fail startup if critical OIDC configuration is missing

## Login Flow

### Step 1: Redirect To Authorization

When the app needs a login, redirect the browser to the authorization endpoint with:

1. `client_id`
2. `redirect_uri`
3. `response_type=code`
4. `scope`
5. `state`
6. `nonce`
7. `code_challenge`
8. `code_challenge_method=S256`

Example:

```text
GET https://auth.nsls.org/oidc/authorize
  ?client_id=thesociety-web
  &redirect_uri=https%3A%2F%2Fthesociety.org%2Fauth%2Fcallback
  &response_type=code
  &scope=openid%20profile%20email%20offline_access
  &state=<opaque-random-state>
  &nonce=<opaque-random-nonce>
  &code_challenge=<pkce-challenge>
  &code_challenge_method=S256
```

Requirements:

1. generate a new `state` per login attempt
2. generate a new `nonce` per login attempt
3. generate a new PKCE verifier and challenge per login attempt
4. store `state`, `nonce`, and the PKCE verifier server-side until callback completion

### Step 2: User Signs In At NSLS Auth

NSLS Auth handles:

1. local email/password login
2. registration
3. email verification
4. forgot-password and password reset
5. Google, Microsoft, and Apple sign-in
6. centralized SSO session reuse

The downstream app should not render its own username/password form once it has migrated to this system.

### Step 3: Receive The Callback

NSLS Auth redirects the browser back to the app's registered callback URL with:

1. `code`
2. `state`

The app must:

1. verify the returned `state`
2. reject the callback if `state` does not match the stored value
3. reject the callback if the app has no outstanding login transaction for that browser

### Step 4: Exchange The Authorization Code

Exchange the code server-side at the token endpoint.

Example using `client_secret_post`:

```http
POST https://auth.nsls.org/oidc/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
client_id=thesociety-web&
client_secret=<client-secret>&
code=<authorization-code>&
code_verifier=<pkce-verifier>&
redirect_uri=https%3A%2F%2Fthesociety.org%2Fauth%2Fcallback
```

Expected response fields:

1. `access_token`
2. `id_token`
3. `token_type`
4. `expires_in`
5. optional `refresh_token` when `offline_access` is granted

### Step 5: Validate The ID Token

After the token exchange:

1. validate the JWT signature using the issuer JWKS
2. verify `iss` matches the NSLS Auth issuer
3. verify `aud` contains the app's `client_id`
4. verify `nonce` matches the stored value
5. verify token time-based claims such as `exp`
6. reject the login if validation fails

Do not skip ID token validation even if the token exchange succeeded.

### Step 6: Create The App Session

After successful ID token validation:

1. find or create the local app user by `issuer + sub`
2. update the local profile snapshot from token or userinfo claims
3. create the app's own session cookie
4. clear temporary login transaction state

Do not store the raw NSLS Auth tokens in browser-accessible storage.

## What To Persist In The App

Minimum recommended identity mapping:

| Field | Purpose |
| --- | --- |
| `auth_issuer` | Distinguishes the identity provider. |
| `auth_subject` | Stable `sub` from NSLS Auth. |
| `email` | Current email snapshot. |
| `email_verified` | Current verification snapshot. |
| `given_name` | Current first-name snapshot. |
| `family_name` | Current last-name snapshot. |
| `display_name` | Current full-name snapshot. |
| `picture_url` | Current canonical cross-app avatar snapshot when available. |
| `last_authenticated_at` | Audit and troubleshooting. |
| `last_claim_sync_at` | Helps with profile refresh decisions. |

Recommended identity key:

```text
(auth_issuer, auth_subject)
```

Do not use email alone as the durable key after migration. Email can change. `sub` is the stable identifier.

## Where To Read User Data

Downstream apps have three normal ways to read identity data.

### 1. ID Token

Use the ID token for immediate post-login identity bootstrap.

Good uses:

1. obtain `sub`
2. read `email` and `email_verified`
3. read `name`, `given_name`, `family_name`, and optional `picture`
4. capture `acr` and `amr`
5. read auth-wide coarse `roles` when the `roles` scope was granted

### 2. UserInfo Endpoint

Use `/oidc/userinfo` when the app needs the current profile claims from NSLS Auth after login.

Example:

```http
GET https://auth.nsls.org/oidc/userinfo
Authorization: Bearer <access-token>
```

Use cases:

1. sync the latest profile snapshot after login
2. refresh claims during a server-side session renewal flow
3. fetch the freshest `picture` value after a picture update
4. fetch the freshest `roles` value after a role change or before a sensitive action
5. verify the user is still eligible before a sensitive action

If userinfo returns `401 invalid_token`, clear the app session and start a fresh login flow.

## Canonical Picture Management For Trusted Clients

This capability is optional. Most downstream apps only need to read `picture`.

Use this feature only when a trusted first-party app must set or clear the current authenticated user's canonical cross-app avatar in NSLS Auth.

### Registration Requirement

The downstream OIDC client must be registered with:

```json
{
  "can_manage_own_picture": true
}
```

Leave this disabled for normal clients that should not write profile pictures.

### Auth And Scope Requirements

The write API requires:

1. a bearer access token
2. an end-user token, not a client-only token
3. `openid` and `profile` in the granted scopes
4. a client whose registration has `can_manage_own_picture=true`

The route updates only the current token subject. The app does not send a user id or subject in the request body.

### Auth Service Runtime Requirement

NSLS Auth must be configured with `PROFILE_PICTURE_ALLOWED_HOSTS`.

Format:

1. comma-separated exact hosts such as `cdn.nsls.org`
2. optional leading-dot suffix patterns such as `.nsls.org`

If `PROFILE_PICTURE_ALLOWED_HOSTS` is empty or unset, picture writes are unavailable in that environment.

### URL Requirements

The `picture` value must be:

1. an absolute `https` URL
2. at most 2048 characters
3. on an allowed host
4. fragment-free
5. free of URL userinfo

Query strings are allowed, but use stable non-expiring URLs whenever possible. Do not send short-lived signed URLs as the canonical picture value unless the app has a deliberate rotation strategy.

### Write API

Set the current user's canonical picture:

```http
PUT https://auth.nsls.org/account/profile/picture
Authorization: Bearer <access-token>
Content-Type: application/json

{ "picture": "https://cdn.nsls.org/avatars/usr_123.png" }
```

Success response:

```json
{ "picture": "https://cdn.nsls.org/avatars/usr_123.png" }
```

Clear the current user's canonical picture:

```http
DELETE https://auth.nsls.org/account/profile/picture
Authorization: Bearer <access-token>
```

Success response:

```json
{ "picture": null }
```

Failure patterns:

1. `401 invalid_token` for missing, malformed, expired, revoked, or ineligible-user tokens
2. `403 insufficient_scope` when `profile` was not granted
3. `403 access_denied` when the client is not trusted for picture writes
4. `400 invalid_request` when the picture URL fails validation
5. `503 temporarily_unavailable` when picture writes are disabled because no allowed hosts are configured

### Recommended App Flow

Use this sequence:

1. the downstream app uploads or chooses an image in its own system
2. the app obtains a stable HTTPS URL on an NSLS-owned or approved CDN host
3. the app's backend calls the auth picture API with the logged-in user's access token
4. after success, the app calls `/oidc/userinfo`
5. the app updates its local profile snapshot from the returned claims

This minimal version does not support binary upload to NSLS Auth. The downstream app is responsible for producing the final image URL before calling the auth API.

### Freshness Rules

Use `/oidc/userinfo` as the immediate source of truth after a picture write.

Important behavior:

1. `userinfo` returns the updated `picture` immediately
2. newly issued ID tokens also include `picture` when `profile` is granted
3. already-issued ID tokens do not change in place

If the app updates the picture during an existing local session, do not assume the old ID token now reflects the new avatar.

### 3. Discovery And JWKS

Use discovery and JWKS for protocol metadata and signature validation.

Good uses:

1. resolve the authoritative endpoints
2. validate ID token signatures
3. support signing-key rotation without app redeploys

## Session Model

NSLS Auth and the downstream app each maintain their own sessions.

### Central Auth Session

This lives on `auth.nsls.org`.

It enables:

1. reuse of the auth login across multiple downstream apps
2. social-provider handoff and return to the auth domain
3. "sign in once" behavior for later authorization requests

### Downstream App Session

This lives on the app's own domain such as `app.nsls.org` or `thesociety.org`.

It enables:

1. application-specific session duration
2. app-local fine-grained authorization and any app-specific roles
3. app-local cookie security policy
4. app-local logout UX

Important constraint:

There is no browser cookie that can be shared directly between `.nsls.org` and `thesociety.org`. Cross-domain SSO works by redirecting the browser back through `auth.nsls.org`, not by sharing one cookie between apps.

## Refresh Tokens

Only request `offline_access` if the app needs refresh tokens.

If refresh tokens are used:

1. store them server-side only
2. encrypt them at rest
3. bind them to the app's local user and session record
4. never expose them to browser JavaScript
5. replace the stored refresh token when the provider rotates it
6. avoid parallel refresh requests for the same session

Example refresh request:

```http
POST https://auth.nsls.org/oidc/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&
client_id=thesociety-web&
client_secret=<client-secret>&
refresh_token=<stored-refresh-token>
```

If refresh fails with `invalid_grant`:

1. assume the central session or grant is no longer valid
2. delete the local refresh token
3. clear the local app session
4. force a new interactive login

This is expected after events such as password reset, user disablement, or other central auth revocation.

## Logout

Logout is a two-part concern:

1. clear the app's own local session
2. optionally send the browser through the OIDC end-session endpoint

Recommended logout behavior:

1. clear the app session first
2. redirect the browser to the discovered `end_session_endpoint`
3. include `post_logout_redirect_uri` if the app wants the browser returned to a known page
4. land the browser on a signed-out page in the app

### Clean Logout Pattern For Branded Re-Entry

If the app wants logout to return the browser to the centralized, app-branded login page instead of a generic logged-out screen, use this pattern:

1. register an exact `post_logout_redirect_uri` for the client
2. make that URI an app-owned login-start route, not a dead-end placeholder page
3. clear the app's own local session before redirecting to `end_session_endpoint`
4. send both `client_id` and `post_logout_redirect_uri` on the logout request
5. have the app login-start route immediately begin a fresh authorization request
6. if the app wants a signed-out banner, preserve a small status value such as `status=signed_out` when starting that fresh authorization request

Typical web-app example:

1. local app logout endpoint clears the app's own session
2. browser is redirected to:

```text
https://auth.nsls.org/oidc/logout?client_id=thesociety-web&post_logout_redirect_uri=https%3A%2F%2Fapp.example.com%2Foidc%2Flogin%3Fstatus%3Dsigned_out
```

3. NSLS Auth validates that `post_logout_redirect_uri` exactly matches one of the client's registered `post_logout_redirect_uris`
4. NSLS Auth clears the auth session and redirects the browser to the app's login-start route
5. the app login-start route immediately redirects back to `/oidc/authorize`
6. the centralized login page renders with the client's branding and can show a signed-out notice

Important details:

1. `post_logout_redirect_uri` is still a security allowlist, not just a UX hint
2. if the app sends `post_logout_redirect_uri`, it must already be registered on the client exactly
3. if the app wants the centralized branded login after logout, the post-logout URI should point to the app's login-start route, not directly to an app-local farewell page
4. if the app does not send a post-logout redirect URI, the browser may land on a provider-owned logout success page instead of the app-branded login flow

Important boundary:

Logging out from one downstream app does not automatically clear every other downstream app session. Global front-channel and back-channel logout are intentionally out of scope for the current architecture.

## Optional Endpoints

### Revocation

Use the revocation endpoint if the app stores refresh tokens and wants to actively revoke them on logout or disconnect.

Typical use:

1. revoke the app's refresh token
2. delete the app's local token record
3. clear the app session

### Introspection

The introspection endpoint is available, but most downstream web apps do not need it for normal browser login.

Prefer:

1. local ID token validation for login
2. userinfo for current profile claims

Reserve introspection for cases where a server truly needs a live token-state check.

## Recommended Local User Model

A downstream app should separate identity from authorization.

Identity data from NSLS Auth:

1. `auth_issuer`
2. `auth_subject`
3. profile and email claims
4. canonical `picture` when present
5. optional auth-wide coarse `roles`
6. last authentication context

Authorization data owned by the app:

1. app-specific permissions
2. entitlements
3. organization membership
4. feature flags
5. any app-only roles that are not shared auth-wide

Recommended rule:

Use NSLS Auth to answer "who is this user?" and, when requested, "which auth-wide coarse roles does this user hold?"

Use the downstream app to answer "what can this user do here?"

## Migration Plan For An Existing App

Follow this order.

### 1. Inventory The Current Auth Surface

Document:

1. current login entrypoints
2. current logout flow
3. current callback URLs
4. current user identifiers
5. any local password storage
6. any API clients or background jobs affected by the change

### 2. Add External Identity Columns

Add fields for:

1. `auth_issuer`
2. `auth_subject`
3. claim snapshots
4. login timestamps

Make `auth_issuer + auth_subject` unique.

### 3. Register The App As An OIDC Client

Choose the app's:

1. `client_id`
2. `application_type` (web/native)
3. callback URL
4. post-logout redirect URL
5. scopes
6. client secret (if web)

Register the client through the **Admin Portal UI** or by using the admin CLI `npm run admin -- clients upsert`.

### 4. Implement Login Redirect And Callback Handling

Build:

1. a login route that starts the authorization request
2. a callback route that verifies `state`
3. server-side code exchange and ID token validation
4. local session creation

### 5. Map Existing Users Safely

If the app already has users:

1. prefer linking on first login using a verified, trusted business rule
2. if email-based linking is used during migration, do it once and then persist `auth_issuer + auth_subject`
3. do not keep re-linking by email on every login

If there is any doubt about account collision risk, require a supervised migration or explicit user confirmation.

### 6. Switch The UI To Centralized Login

Replace local password entry with:

1. "Sign in with NSLS"
2. optional "Sign out"
3. app pages that rely on the app's local session after callback completion

Do not duplicate password reset, registration, or social login UI in the downstream app.

### 7. Remove Legacy Credential Ownership

After cutover:

1. stop authenticating against the app's local password store
2. stop issuing new app-local login credentials if central auth is now authoritative
3. keep only the app-local authorization and profile snapshot data that still serves the app

## Implementation Checklist

An app integration is complete when all items below are true.

1. the app is registered as an OIDC client in NSLS Auth
2. the app uses discovery from the NSLS Auth issuer
3. the app starts login with authorization code + PKCE
4. the callback verifies `state`
5. the token exchange is server-side only
6. the ID token is fully validated
7. the app persists `auth_issuer + auth_subject`
8. the app creates its own local session
9. the app uses `sub` as the durable identity key
10. the app can fetch user claims from userinfo when needed
11. the app handles refresh-token renewal or explicitly chooses not to use refresh tokens
12. the app clears its own local session on logout
13. if the app uses RP-initiated logout, its exact post-logout redirect URL is registered on the client
14. if the app wants branded re-entry after logout, the post-logout redirect returns to the app's login-start route and not a placeholder page
15. the app never stores the client secret or refresh token in browser code
16. local password login has been removed or disabled if the migration is complete

## Validation Checklist

After implementation, validate these behaviors manually or in automated tests.

1. first-time login redirects to `auth.nsls.org`, completes successfully, and returns to the app callback
2. the app creates a local session after code exchange
3. the app stores the stable `sub`
4. a second downstream app can start an authorization request and receive a code without an extra login prompt when the central auth session already exists
5. userinfo returns the expected claims for the granted scopes
6. if the app requests `roles`, ID token and userinfo return the expected `roles` claim shape
7. the app behaves correctly when `email_verified=false`
8. if the client is trusted for picture writes, updating `picture` succeeds only for allowed hosts and userinfo reflects the new value immediately
9. if the client is trusted for picture writes, deleting `picture` clears it from userinfo and future ID tokens
10. logout clears the app's own session
11. if the app uses `end_session_endpoint`, logout redirects through NSLS Auth and returns only to a registered `post_logout_redirect_uri`
12. if the app uses branded re-entry after logout, the returned login flow shows the expected signed-out state without a dead-end placeholder page
13. refresh failure forces reauthentication
14. disabling a user centrally causes downstream renewal or userinfo access to fail as expected
15. password reset or other central revocation invalidates old refresh tokens as expected
16. changing a user's auth-wide role invalidates stale central auth state and userinfo returns the new role set after reauthentication

## Common Mistakes To Avoid

Do not do any of the following:

1. do not embed a client secret in browser JavaScript
2. do not use the implicit flow
3. do not skip PKCE because the app is confidential
4. do not trust email as the durable user key
5. do not assume one cookie can be shared between `app.nsls.org` and `thesociety.org`
6. do not treat NSLS Auth access tokens as your app's own session cookie
7. do not build app-local password reset or registration flows after migrating
8. do not request unsupported scopes such as `groups`
9. do not use non-HTTPS redirect URIs outside loopback local development
10. do not assume logout from one app will log the user out everywhere
11. do not store expiring signed image URLs as the canonical `picture` unless you intentionally rotate them
12. do not send arbitrary user ids to the picture API; it only supports the current authenticated subject
13. do not use `acr` or `amr` as authorization roles
14. do not assume an already-issued ID token reflects a role change; use userinfo or a fresh login when you need current role state

## Suggested Agent Execution Order

When an agent is asked to migrate a downstream app, it should usually work in this order:

1. inspect the app's current auth entrypoints and session model
2. add `auth_issuer` and `auth_subject` storage to the app's user model
3. add OIDC config to the app environment
4. implement login redirect with `state`, `nonce`, and PKCE
5. implement callback verification and token exchange
6. validate the ID token and create the local session
7. add optional userinfo sync
8. if needed, add trusted picture-write integration and userinfo refresh
9. implement logout cleanup
10. remove or disable legacy local-auth entrypoints
11. add integration tests for first login, repeat login, logout, and revoked-session behavior

## Related Documents

1. [README](../README.md)
2. [Architecture](./ARCHITECTURE.md)
3. [External Dependencies](./EXTERNAL_DEPENDENCIES.md)
