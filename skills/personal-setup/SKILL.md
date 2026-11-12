---
name: personal-setup
description: >-
  Bootstrapper for NSLS personal productivity setup. Ships in the org Builder
  Toolkit so /personal-setup ALWAYS resolves — even before the personal kit is
  installed. Installs and enables the personal toolkit if missing, syncs its
  pointer skills so they appear without a restart, then hands off to the full
  personal-setup flow (light config by default; Obsidian as an advanced opt-in).
  Use when the builder says /personal-setup, or wants daily/weekly planning skills.
---

# personal-setup — org-kit bootstrapper

**Why this exists:** the full `/personal-setup` lives in the *personal* toolkit
(`nsls-personal-toolkit`). Before that kit is installed, typing `/personal-setup`
used to error with "Unknown command" — exactly when a new builder wants it. This
thin skill ships in the org kit so the command works from the moment the org
toolkit installs. It installs the personal kit on demand, then delegates.

Keep it hand-held: **one question at a time**, plain language, and never dump a
checklist for the builder to run themselves.

## Step 1: Is the personal toolkit already installed?

```bash
PT="$HOME/.claude/local-plugins/nsls-personal-toolkit"
FULL_SKILL="$PT/skills/personal-setup/SKILL.md"
if [ -f "$FULL_SKILL" ]; then echo "PERSONAL_KIT_PRESENT"; else echo "PERSONAL_KIT_MISSING"; fi
```

- **PERSONAL_KIT_PRESENT** → skip to Step 3 (delegate).
- **PERSONAL_KIT_MISSING** → Step 2 installs it.

## Step 2: Install + enable the personal toolkit (only if missing)

Tell the builder: "One sec — grabbing the personal productivity skills."

### 2a. First, the copy NSLS delivers through Claude (no GitHub)

NSLS's Claude organization can deliver the personal toolkit, and this toolkit's
session hook copies it into place. Ask it to do that now:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.sh" personal-delivery now
```

`${CLAUDE_PLUGIN_ROOT}` is this toolkit's own folder; Claude Code fills it in.
If it appears here as written, use the folder two levels above this SKILL.md.

Read the first word of what it prints:

- **`PERSONAL_TOOLKIT_READY`** → the personal toolkit is installed, kept current
  by Claude, and its skills are already pointed at. **Skip the rest of Step 2**
  (no clone, no settings change, no pointer sync) and go to Step 3.
- **`PERSONAL_TOOLKIT_NOT_DELIVERED`** → NSLS is not delivering it to this
  account on this computer. Carry on with 2b.
- **Anything else, or nothing** → the delivered copy is still arriving, or this
  toolkit is an older one without the command. Wait a minute and run it once
  more; if the answer is the same, carry on with 2b.

### 2b. Otherwise, from GitHub

Install, **preserving any existing `.env`** (the org `/nsls-setmeup` may have written
`BUILDER_EMAIL` into this dir before the kit was cloned — cloning into a
non-empty dir would otherwise fail and silently no-op):

```bash
PT="$HOME/.claude/local-plugins/nsls-personal-toolkit"
# Repo/branch overridable for fork testing (matches install.sh's
# NSLS_PERSONAL_REPO). Defaults are production.
REPO_URL="${NSLS_PERSONAL_REPO:-https://github.com/thensls/nsls-personal-toolkit.git}"
PERSONAL_BRANCH="${NSLS_PERSONAL_BRANCH:-main}"

if [ -d "$PT/.git" ]; then
  git -C "$PT" pull --ff-only 2>/dev/null || true
  echo "Personal toolkit updated."
else
  # Preserve a pre-written .env across the clone.
  SAVED_ENV=""
  if [ -f "$PT/.env" ]; then SAVED_ENV="$(mktemp)"; cp "$PT/.env" "$SAVED_ENV"; fi
  rm -rf "$PT"
  mkdir -p "$(dirname "$PT")"
  if git clone --branch "$PERSONAL_BRANCH" "$REPO_URL" "$PT" --quiet; then
    [ -n "$SAVED_ENV" ] && cp "$SAVED_ENV" "$PT/.env"
    echo "Personal toolkit installed."
  else
    [ -n "$SAVED_ENV" ] && { mkdir -p "$PT"; cp "$SAVED_ENV" "$PT/.env"; }
    echo "CLONE_FAILED"
  fi
  [ -n "$SAVED_ENV" ] && rm -f "$SAVED_ENV"
fi
```

If it prints `CLONE_FAILED`, don't proceed, and don't assume it was the network.
The personal toolkit's repository may be private, and then a clone needs a
GitHub sign-in that most people don't have and don't need. Say one plain
sentence: *"The personal toolkit comes through Claude now, and it isn't switched
on for you here yet."* Then offer the way forward that fits:

- **Most people:** in Claude's settings, under plugins, install
  **nsls-personal-toolkit** from NSLS's list, start a new session, and say
  `/personal-setup` again. If it isn't in the list, they should message the NSLS
  AI team.
- **Someone who keeps their own copy on GitHub** (and says so): help them sign in
  to GitHub (`gh auth login`), then run this step again.
- **Offline:** try again once they are back online.

Enable it in settings.json (merge, don't clobber other keys). **Use the block
for the builder's platform.**

> ⚠️ **On Windows, do NOT use `python3` for this.** Stock Win11 `python`/`python3`
> is a Microsoft Store stub that prints "Python was not found" and **exits 0** —
> the merge silently no-ops and the plugin is never enabled (the pointer skills
> still sync, so it *looks* like it worked). Use the PowerShell block. The bash
> blocks elsewhere in this step are Mac/Linux-shaped; on Windows mirror
> `install.ps1` (a `git clone`/`git pull` works either way; use PowerShell for
> the settings merge and pointer sync).

**macOS / Linux** — read with `utf-8-sig` so a BOM left by an older Windows
installer doesn't break `json.load`:

```bash
python3 -c "
import json, os
p = os.path.expanduser('~/.claude/settings.json')
cfg = json.load(open(p, encoding='utf-8-sig')) if os.path.exists(p) else {}
cfg.setdefault('enabledPlugins', {})['nsls-personal-toolkit@local'] = True
with open(p, 'w', encoding='utf-8') as f: json.dump(cfg, f, indent=2)
# VERIFY by re-reading — never trust the exit code alone.
chk = json.load(open(p, encoding='utf-8-sig'))
print('ENABLED_OK' if chk.get('enabledPlugins', {}).get('nsls-personal-toolkit@local') else 'ENABLE_FAILED')
"
```

**Windows** — native PowerShell (mirrors `install.ps1`), BOM-less write so
downstream `json.load` doesn't choke:

```powershell
$p = Join-Path $env:USERPROFILE '.claude\settings.json'
$cfg = if (Test-Path $p) { Get-Content $p -Raw | ConvertFrom-Json } else { [pscustomobject]@{} }
if (-not ($cfg.PSObject.Properties.Name -contains 'enabledPlugins') -or $null -eq $cfg.enabledPlugins) {
  $cfg | Add-Member -NotePropertyName enabledPlugins -NotePropertyValue ([pscustomobject]@{}) -Force
}
$cfg.enabledPlugins | Add-Member -NotePropertyName 'nsls-personal-toolkit@local' -NotePropertyValue $true -Force
[System.IO.File]::WriteAllText($p, ($cfg | ConvertTo-Json -Depth 12), (New-Object System.Text.UTF8Encoding $false))
# VERIFY by re-reading — don't trust exit codes.
$chk = Get-Content $p -Raw | ConvertFrom-Json
if ($chk.enabledPlugins.'nsls-personal-toolkit@local') { Write-Host 'ENABLED_OK' } else { Write-Host 'ENABLE_FAILED' }
```

**Confirm the output is `ENABLED_OK`.** If it prints `ENABLE_FAILED` (or nothing
at all — the Windows `python3` stub does exactly that), the merge did NOT take:
tell the builder plainly and retry, and do **not** proceed as if the plugin is
enabled (pointer skills still sync either way, which otherwise hides the miss).

Sync the personal kit's pointer skills into `~/.claude/skills/` so they appear
**without a restart** (pointer skills load live; only MCP servers/hooks need a
restart). This also re-points `personal-setup` at the full skill, handing off
cleanly from this bootstrapper:

```bash
PT="$HOME/.claude/local-plugins/nsls-personal-toolkit"
SKILLS_DIR="$HOME/.claude/skills"
mkdir -p "$SKILLS_DIR"
for skill_dir in "$PT/skills"/*/; do
  skill=$(basename "$skill_dir"); src="$skill_dir/SKILL.md"; dest="$SKILLS_DIR/$skill"
  [ -f "$src" ] || continue
  # Only overwrite our own pointers or empty slots, never a user's custom skill.
  if [ -f "$dest/SKILL.md" ] && ! grep -q "local-plugins/nsls-" "$dest/SKILL.md" 2>/dev/null; then continue; fi
  name=$(grep "^name:" "$src" | head -1 | sed 's/name: *//'); [ -z "$name" ] && continue
  mkdir -p "$dest"
  printf -- '---\nname: %s\ndescription: >-\n  NSLS personal toolkit skill: %s\n---\n\nRead and follow the full skill at `%s`.\n' \
    "$name" "$skill" "$src" > "$dest/SKILL.md"
done
echo "Personal skills synced."
```

## Step 3: Delegate to the full personal-setup flow

The full skill owns the actual config, including the **light-vs-advanced tiering**
(light notes folder by default; Obsidian vault as an advanced opt-in). Read and
follow it now:

```
$HOME/.claude/local-plugins/nsls-personal-toolkit/skills/personal-setup/SKILL.md
```

Follow that skill's instructions from here. Default the builder to the **light**
tier unless they ask for the full Obsidian setup. If the personal kit was only
just installed this session and something it needs (an MCP server or hook)
requires a restart, say so plainly and tell them to run `/personal-setup` again
after restarting — but the light config and pointer skills work right now.
