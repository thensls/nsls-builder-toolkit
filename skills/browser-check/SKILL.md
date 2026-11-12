---
name: browser-check
description: >
  Use when you have built or changed anything people see in a web browser — a page, form,
  dashboard, site, prototype, or web app — and are about to call it done, hand it over,
  or open a PR. Runs Expect (expect-cli), which reads the git diff, writes a test plan,
  and drives a real headless browser to check the change works — through an NSLS wrapper
  that forces vendor telemetry off and never copies browser cookies. Trigger phrases:
  browser check, check it in a browser, test the page, does the UI work, expect,
  expect.dev, expect-cli, click through it, smoke test the site, verify the frontend,
  test my changes in a browser.
---

# Browser check (Expect)

Tests and code review read the code. Neither one opens the page. This skill does: it runs
[Expect](https://www.expect.dev/) (`expect-cli`, by Million Software), which reads what
changed in git, writes a test plan for those changes, and has Claude drive a real headless
browser through it. You get pass/fail per step in about 1–5 minutes.

**Where it sits in the standard workflow:**

```
ce-brainstorm → ce-plan → ce-work → /browser-check → ce-code-review → PR
```

Run it after the work is built and before you claim it works. "The page works" is a claim
`verification-before-completion` asks you to back with evidence. For anything with a web
UI, this run is that evidence.

**Skip it for** backend-only changes, scripts, data pipelines, Slack bots, and Google
Docs or Slides. There is no page to open.

## The one command: always the wrapper

Start the dev server first (or have a staging URL). Then, from inside the repo:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/skills/browser-check/scripts/browser-check.sh" \
  --url http://localhost:3000 \
  --message "<what must be true, in plain words — see below>" \
  [--target changes|unstaged|branch]
```

Run it with the Bash tool's `run_in_background: true`. It takes 1–5 minutes and you are
told when it finishes. It prints a JSON result on stdout and a one-line safety check on
stderr.

**Never run `npx expect-cli` (or any other copy of Expect) directly, and never run `expect init` or `expect add skill`.**
Those skip every protection below. `init` also installs Expect's own `/expect` skill and MCP
server with cookies and telemetry on by default. The wrapper accepts only `--url`,
`--message` and `--target`, and refuses everything else, including profile, CDP, cookie
and headed options.

### What the wrapper forces, every run

| Protection | How | Verified 2026-11-12 on 0.1.3 |
|---|---|---|
| **No vendor telemetry** | `NO_TELEMETRY=1` turns off the PostHog analytics. That flag does **not** cover Expect's Axiom traces or its expect.dev version check, and an environment variable can't reach Expect's browser server (the agent starts it with a fixed env list). So the wrapper keeps a private, pinned install of Expect (`~/.cache/nsls-browser-check/`) and adds `block-telemetry.cjs` to the first line of every Expect entry point, refusing `*.posthog.com`, `*.axiom.co` and `*.expect.dev`. If the patch isn't in place, it refuses to run. | Network capture of a full run. Flag only: ~175 connection samples to `api.axiom.co`. Wrapper: **zero** connections to any telemetry address; 26 Axiom attempts and 1 version check refused, across 13 Expect processes. |
| **No cookies copied** | `--ci` (in 0.1.3, `--no-cookies` on its own does nothing; only `--ci` actually turns cookies off), Expect's profile/CDP/cookie env vars unset, and the agent told never to ask for cookies. | Headless mode hardcodes an empty cookie list. All test sessions logged `cookie_count: 0`. |
| **Checked afterwards** | Expect logs every browser session with `cookie_count` and `is_external_browser`. If any new session isn't `0` / `false`, the wrapper exits **3** with the log line. | Checked against real logs and planted bad lines. |
| Pinned version | `expect-cli@0.1.3`, installed privately on first run (~15s). Bump on purpose, after re-running the network capture and `test/test_browser_check_wrapper.py`. | — |
| Headless, no prompts | `--ci --browser-mode headless`, stdin closed | — |

Why the after-run check exists: Expect's browser tool lets the *agent* pass
`cookies: true` mid-run, and nothing in Expect stops it, even in `--ci` mode. The run's
instructions tell it not to, and the log check catches it if it does anyway.

### Writing `--message`

This is the acceptance criteria. Expect plans from the diff **and** this message, so name
the things that must be true, not "test it":

- Weak: `--message "test the signup page"`
- Strong: `--message "On /signup, submitting an empty form shows an error under each required field; a valid email + password reaches /welcome; no console errors at 375px wide"`

Never put a password or token in `--message`. It ends up in the plan, the logs and the
transcript.

## Reading the result

```json
{ "status": "passed", "steps": [ {"title": "...", "status": "passed"}, ... ],
  "summary": "8 passed, 0 failed, 1 skipped out of 9 steps" }
```

1. **Exit code 3** means the safety check failed: a session loaded cookies or attached to a
   real browser. Stop. Tell the builder, and don't trust or reuse that run.
2. **`status: "failed"`** — read the failed step titles, fix, run again. Don't open the PR
   on a failed run. (It does fail when it should. A wrong-heading test came back
   `4 passed, 1 failed`.)
3. **`status: "passed"`** — before you believe it, match every acceptance criterion in your
   `--message` to a step title. A run can pass while never testing the thing you changed:
   if a criterion has no step, the check didn't happen. Re-run with a sharper message.
4. **`skipped`** steps are not passes. Say which were skipped and why.
5. Report it in one line, with numbers: *"Browser check: 8/9 passed, 1 skipped (no test
   script in repo), 93s, against localhost:3000."* Put the same line in the PR description.

Expect also runs its own extra checks (mobile and desktop widths, console errors, an
accessibility audit, performance). Read those too. They are often where the real problem is.

## Pages behind a login

**Not supported, on purpose.** The only way Expect reaches a logged-in page is by
copying cookies from a real browser, and the wrapper never allows that. A step that
needs a login comes back failed with "needs login".

What to do instead:
- Test the page on **local** with your app's dev-mode auth bypass or a seeded test
  session (most frameworks have one), and point `--url` at it.
- Or check the logged-out parts with Expect and the logged-in parts by hand, and say so
  in the PR.

## Don't let it write to real systems

Expect's agent submits forms and presses buttons to test them. Against production, that
means real emails sent, real records created, real charges. For any flow that writes
(sign-up, payment, invite, send, delete, import), test against **local or staging only**.
Read-only pages on production are fine.

## What leaves your machine

- **The page content and diff go to Claude** (Anthropic), through your own Claude Code
  login. That's the same place your code already goes. It fits the NSLS data rule, so
  member data stays on Claude.
- **Nothing goes to Million or its vendors.** The wrapper blocks PostHog, Axiom and
  expect.dev. That's why you must never bypass it.
- **Recordings stay local, but get shared.** Expect saves a `.webm` screen recording and a
  performance trace of every run in `/tmp/expect-artifacts/`, which other accounts on the
  machine can read. If a page showed member data, delete them after reviewing:
  `rm -f /tmp/expect-artifacts/session-*.webm`.
- **Files it adds to your repo:** `.expect/` (logs, gitignores itself) and
  `.claude/settings.local.json` (allows its own `mcp__browser__*` tools). Neither is
  committed by default. Leave them out of commits.

License is FSL-1.1-MIT (source-available, free to use internally, becomes MIT after two
years). No account and no API key are needed. Runs use your Claude Code login.

## Gotchas

| Symptom | Cause | Fix |
|---|---|---|
| "No changes to test" | Nothing in the chosen target | `--target branch`, or commit/stage your work first |
| Passes on a page that's obviously broken | Message too vague, or the dev server is serving an old build | Check step titles against your criteria; restart the dev server (`rm -rf .next` for Next.js) |
| Can't reach the page | Dev server not running, or on another port | `curl -s <url>` first |
| Every step fails "needs login" | No cookies, by design | See *Pages behind a login* |
| `WARNING - no browser session was logged` | Expect never opened a browser (crashed early, or bad URL) | Read the JSON; treat the run as not done |
| Exit code 3 | Safety check tripped | See *Reading the result*, step 1 |

## Not yet standard

- **CI on every PR** (`expect add github-action`). It needs a Claude API key as a repo
  secret and runs outside this wrapper. Ask Kevin before adding it to a `thensls` repo.
- **Watch mode** (`expect watch`). This reruns on every save and also runs outside the
  wrapper. Not supported.
