---
name: setup
description: >-
  Alias for /nsls-setmeup, the NSLS Builder Toolkit onboarding. Kept so old docs
  and muscle memory that still say "/setup" keep working. The primary command is
  /nsls-setmeup, renamed because a bare /setup collided with another skill.
---

Run the NSLS Builder Toolkit onboarding skill with the Skill tool:
`Skill(nsls-builder-toolkit:nsls-setmeup)`. On an install where that name isn't
found, use `Skill(nsls-setmeup)`. If neither loads, read the skill file and follow it:
`${CLAUDE_PLUGIN_ROOT}/skills/nsls-setmeup/SKILL.md` on a plugin install (Claude Code
fills in that path). Otherwise use
`$CLAUDE_CONFIG_DIR/local-plugins/nsls-builder-toolkit/skills/nsls-setmeup/SKILL.md`,
where `$CLAUDE_CONFIG_DIR` defaults to `~/.claude`.
