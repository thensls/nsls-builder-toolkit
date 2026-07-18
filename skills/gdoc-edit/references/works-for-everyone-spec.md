# gdoc-edit — "works for everyone" service spec

> **⚠ SUPERSEDED (2026-07-05).** This spec proposed a central Railway service + NSLS Auth
> (OIDC) + an encrypted refresh-token store to get per-user Google access. We no longer need
> any of that: **`gws` (the Google Workspace CLI the toolkit already ships) does per-user
> Google OAuth locally**, and Kevin unblocked the one dependency this spec was stuck on (GCP
> project creation — `nsls-gdocs-skill`). The shipped design is: one shared Desktop OAuth
> client (Internal consent, minimal Docs+Drive scopes) → each builder runs `gws auth login`
> for their own token → `gdoc-edit` calls the Docs/Drive APIs as that builder. It satisfies
> every security property below (per-user permissions, no shared bearer secret, least scope,
> encrypted tokens, revocation) with **zero new infrastructure**; audit is Google Docs Version
> History. See `setup.md` for the live design. This file is kept for history/rationale only.

**Status:** superseded — see banner above. Original goal: any NSLS builder can edit
their own Google Docs through the `gdoc-edit` skill with **no per-person Apps Script setup,
no shared secret**, per-user identity, and a real audit trail.

## Why the current webhook can't be the org answer

The current per-person webhook is deployed **"Execute as: Me"** and gated only by a shared
secret. If we shipped one shared URL+secret to everyone, any holder could **read or write
any document the deploying user can access, impersonating them, with no record of who
actually called** — a classic confused-deputy / privilege-escalation hole. So the org
version must (a) act as the **calling builder**, with **their** permissions, and (b) carry
**no shared bearer secret**.

## Recommended architecture — central service, two identity layers

A small service (Railway — same host pattern the toolkit already uses; secrets via Doppler)
that exposes the same actions as the skill (`read · replace · insert-top · insert-after ·
append · remove · comments`) and uses **two** identities:

1. **NSLS Auth (OIDC, `auth.nsls.org`)** — identifies *which builder* is calling and whether
   they're allowed to use the service. Reuses the `nsls-auth` skill's pattern (Authorization
   Code + PKCE; persist `(issuer, sub)`).
2. **Per-user Google OAuth** — lets the service act on Google Docs **as that builder**, so it
   can only touch docs that builder can already access. The service stores each builder's
   Google **refresh token** (encrypted at rest) after a one-time consent.

```
Claude Code (gdoc-edit skill)
      │  HTTPS + builder's NSLS Auth session token
      ▼
Doc-Edit Service (Railway)
   ├─ NSLS Auth (OIDC) — who is this builder? allowed?
   ├─ per-builder Google refresh token (encrypted) — act AS them
   ├─ Google Docs/Drive API — read/replace/insert/remove/comments
   └─ audit log — builder, action, docId, timestamp
```

**Why this and not the alternatives:** see "Alternatives considered" below. Short version:
this gives per-user permissions + per-user audit + one-time consent, **without** a domain
super-admin artifact (domain-wide delegation) and **without** a shared secret.

## Auth & onboarding flow (answers "install-time vs first-use")

**Recommendation: lazy, first-use auth — do NOT force login at install.**

- The **skill** ships in the Builder Toolkit (so distribution = the existing auto-update; every
  builder already has it after a session-start `git pull`).
- The **service** is the new infra.
- On a builder's **first edit action**, if the service has no Google token for them, the skill
  surfaces exactly the message Davo wanted:
  > "I have a doc-editing skill that needs your one-time authorisation — open this link to
  > sign in with NSLS and grant Google Docs access: `<authorise-url>`"
  They click once (NSLS Auth → Google consent), and from then on it just works (refresh token
  persists). No secrets stored locally.
- `/setup` can *optionally* offer to pre-authorise, but lazy-on-first-use is lower friction and
  is the recommended default. Read actions and write actions both gate on the same one-time
  consent.

## Components & work items

1. **Service** (Railway): action endpoints; NSLS Auth (OIDC) middleware; Google OAuth
   callback + encrypted refresh-token store; Google Docs/Drive API calls; audit log; rate limit.
2. **NSLS Auth client registration** — *tier-3*: produce the client-definition JSON and hand it
   to Kevin / People-Ops to register (per the `nsls-auth` skill — never self-register; the admin
   generates the `client_secret`).
3. **Google Cloud OAuth client** — a GCP project + OAuth consent screen for the per-user Google
   consent. ⚠ **Dependency/blocker:** Davo's account can't create GCP projects ("No permission to
   create project in organization"). This must be created by a Workspace/GCP admin (Jordan/Kevin).
4. **Skill update** (`scripts/gdoc.py` + SKILL.md): point at the service URL; on a `needs_auth`
   response, print the authorise link; store nothing sensitive locally; drop the per-person
   webhook config path.
5. **Migration:** keep the per-person Apps Script webhook as a fallback during rollout, then
   deprecate once the service is stable.

## Security model

- **Per-user permissions** — the service acts with each builder's Google token, so a builder can
  only reach docs they could already open. No confused deputy.
- **No shared bearer secret.** Calls are authenticated by the builder's NSLS Auth session.
- **Least Google scope** — see scope decision below; prefer the narrowest that still lets us edit
  the docs builders point at.
- **Tokens encrypted at rest**; support revocation (sign-out clears the stored refresh token).
- **Audit every call** — builder identity + action + docId + timestamp.

## Scope decision (needs a call)

To edit an **arbitrary existing** Doc by ID (the whole point), the Google token likely needs
`https://www.googleapis.com/auth/documents` plus enough Drive scope to open by ID and read
comments. `drive.file` (app-created files only) is **not** sufficient for editing docs the app
didn't create. Decide explicitly: broader `documents` + `drive` consent vs. a narrower model
(e.g., only docs explicitly shared to the app). Broader = more capable, bigger consent ask.

## Distribution & shipping

- Ship the **skill change** to `thensls/nsls-builder-toolkit` via PR (the standard channel —
  same as recent skills). Builders get it on the next session-start pull.
- The **service** deploys once (Railway) and is shared by all builders — it's infra, not per-user.
- PR should include: the updated skill, this spec, the NSLS Auth client-definition JSON (for
  Kevin to register), and the GCP OAuth-client request (for the admin).

## Alternatives considered

- **B — Service account with domain-wide delegation (DWD):** zero per-user consent (admin grants
  once), seamless. **Rejected as default:** DWD lets the service impersonate *anyone* in the
  domain for those scopes — a large, dangerous artifact; needs super-admin; full-domain blast
  radius if compromised. Keep as a fallback only if per-user consent proves too high-friction.
- **C — Apps Script "Execute as: User accessing":** no custom service, but every call must carry
  the *caller's* Google OAuth token, so the CLI still needs a per-user OAuth flow — same consent
  cost as A with worse audit/extensibility. Reasonable lightweight stopgap; not the robust answer.
- **Per-person webhook (today):** secure (each secret only exposes that person's Drive) but the
  per-person deploy is the friction we're removing.

## Open questions

- Google scope breadth (above) — Jordan/Bricker comfort with `documents`+`drive` consent.
- Who owns/operates the service (VP Tech / Jordan)?
- Token store: encryption key management (Doppler) + revocation UX.
- Does the GCP OAuth consent screen need Google verification (it does for sensitive scopes used
  outside the org; internal-only app avoids the review) — confirm the app can be "Internal".
