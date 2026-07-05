# gdoc-edit — setup

`gdoc-edit` talks to the Google Docs + Drive APIs through **`gws`** (the Google Workspace
CLI, shipped with the toolkit). Every call runs as **you** — your Google identity, your
document permissions. There is no shared secret and nothing per-person to deploy. Setup is
a one-time `gws auth login`.

If `gws` is already authenticated on your machine (`gws auth status` shows a `storage`
other than `none`), you're done — skip to the smoke test.

---

## Builder setup (the common case, ~2 min)

### 1. Make sure `gws` is installed

```bash
gws --version || curl --proto '=https' --tlsv1.2 -LsSf \
  https://github.com/googleworkspace/cli/releases/latest/download/google-workspace-cli-installer.sh | sh
```

### 2. Get the NSLS OAuth client

`gdoc-edit` uses one shared OAuth **client** (a Desktop client in the `nsls-gdocs-skill`
GCP project). The client is *not* a secret you type — you download it once and drop it in
place. It only lets you *start* a Google sign-in; the actual access is your own per-user
token, minted in the next step.

1. You need read access to the `nsls-gdocs-skill` project. This is granted to a builder
   group once (ask in #builders if `gws docs` fails with a project/permission error).
2. Go to **console.cloud.google.com → project `nsls-gdocs-skill` → APIs & Services →
   Credentials**, find the **"gdoc-edit desktop client"**, and **Download JSON**.
3. Save it as `~/.config/gws/client_secret.json`:

```bash
mkdir -p ~/.config/gws && mv ~/Downloads/client_secret_*.json ~/.config/gws/client_secret.json
```

> Prefer not to touch the console? You can instead set the client via env vars in your
> shell profile (values from the same client): `GOOGLE_WORKSPACE_CLI_CLIENT_ID` and
> `GOOGLE_WORKSPACE_CLI_CLIENT_SECRET`. Either path works.

### 3. Log in (per-user, minimal scopes)

```bash
gws auth login --services docs,drive
```

A browser opens for Google consent. Because the app is **Internal**, only `@nsls.org`
accounts can complete it. `--services docs,drive` requests only the Docs + Drive scopes
this skill needs — not the full Workspace surface. Your refresh token is stored **encrypted**
at `~/.config/gws`; you won't be asked again.

### 4. Smoke test

```bash
S=~/.claude/local-plugins/nsls-builder-toolkit/skills/gdoc-edit/scripts/gdoc.py
python3 $S read     --doc <ANY_DOC_ID_YOU_CAN_OPEN> | head
python3 $S comments --doc <ANY_DOC_ID_YOU_CAN_OPEN>
```

`read` prints the doc text; `comments` prints a JSON array. If you get **exit 2 / auth
error**, re-run step 3. If you get a **project / permission** error, you're missing read
access to `nsls-gdocs-skill` (step 2.1).

---

## What changed from the old webhook

Earlier versions of this skill used a personal Apps Script web app (a `/exec` URL + a
`SHARED_SECRET` in `~/.config/gdoc-edit/config.json`). That was tied to one person's
identity and couldn't be shared safely. **It's retired.** You no longer need
`~/.config/gdoc-edit/config.json` — delete it if you have one. The old Apps Script is kept
for reference at `references/legacy/gas-doc-webhook.gs` only.

---

## Admin: creating the shared OAuth client (one-time, done once for the org)

Only needed once, by whoever stands up the `nsls-gdocs-skill` project. Requires GCP access
to that project.

1. **Reauth gcloud** (interactive): `gcloud auth login` and
   `gcloud config set project nsls-gdocs-skill`.
2. **Create the consent screen + Desktop client** the way `gws auth login` expects:

   ```bash
   gws auth setup --project nsls-gdocs-skill
   ```

   This enables the Workspace APIs on the project and creates the OAuth **consent screen +
   Desktop client**, writing `~/.config/gws/client_secret.json`. (It enables the full set of
   Workspace APIs on this dedicated project — harmless; per-user *token* scope is still
   controlled by the `--services docs,drive` flag at login time.)
3. **Set the consent screen to Internal** (User type: Internal) in the console so only
   `@nsls.org` users can authorize and no Google verification review is needed. Set the app
   name to `NSLS gdoc-edit` and support/developer email to an NSLS address.
4. **Grant the builder group read access** to the project once (e.g. `roles/viewer` on
   `nsls-gdocs-skill` for `gcp-builders@nsls.org`) so builders can download the client JSON
   in step 2 above — a single group grant, not per-person sharing.
5. **Log in and verify** as above (`gws auth login --services docs,drive`, then the smoke
   test). The `client_id` + `client_secret` from `~/.config/gws/client_secret.json` are the
   "client details" to register/track centrally.

Do **not** commit `client_secret.json` (or the id/secret) to the toolkit repo. It's a
Desktop-type client — low sensitivity by Google's model — but the NSLS pattern is that no
credential lives in the repo. Distribution is via project access, not git.
