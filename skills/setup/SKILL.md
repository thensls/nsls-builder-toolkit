---
name: setup
description: >-
  Claude Code only.
  Alias for /nsls-setmeup, the NSLS Builder Toolkit onboarding. Kept so old docs
  and muscle memory that still say "/setup" keep working. The primary command is
  /nsls-setmeup, renamed because a bare /setup collided with another skill.
---

<!-- claude-code-only:start (same words in every skill that has this note; change them in _shared/references/skill-surfaces.json) -->
> **Claude Code only.** This skill needs the person's own computer, so check
> where you are first, going by what your own instructions say you are running in.
> In **Claude Code** (a terminal, or the Code tab in the Claude app), skip this
> note. In **an ordinary Claude chat or a Cowork task** (its files live in a
> sandbox such as `/sessions/...`, not on their computer), stop and follow
> nothing else in this skill. If the person asked for this skill, or what they
> want can't be done here without it, reply with only this sentence:
> "This skill only works in Claude Code on your computer, so switch to Claude Code (the Code tab in the Claude app) and run it there."
> Otherwise don't mention this skill; help the way you would without it.
> Unsure which? Run `echo "$CLAUDE_CODE_ENTRYPOINT"` (PowerShell:
> `$env:CLAUDE_CODE_ENTRYPOINT`): `local-agent` is Cowork, and any other
> answer, blank included, is Claude Code. No way to run a command means chat.
<!-- claude-code-only:end -->

Run the NSLS Builder Toolkit onboarding skill with the Skill tool:
`Skill(nsls-builder-toolkit:nsls-setmeup)`. On an install where that name isn't
found, use `Skill(nsls-setmeup)`. If neither loads, read the skill file and follow it:
`${CLAUDE_PLUGIN_ROOT}/skills/nsls-setmeup/SKILL.md` on a plugin install (Claude Code
fills in that path). Otherwise use
`$CLAUDE_CONFIG_DIR/local-plugins/nsls-builder-toolkit/skills/nsls-setmeup/SKILL.md`,
where `$CLAUDE_CONFIG_DIR` defaults to `~/.claude`.
