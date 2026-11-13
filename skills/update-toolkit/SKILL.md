---
name: update-toolkit
description: Claude Code only. Update the NSLS builder toolkit to its newest release right now. Use when someone says "update my NSLS toolkit", "update the toolkit", "get the latest toolkit", "get the new skills", or can't find a toolkit skill a colleague told them to try.
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

# Update the NSLS toolkit

The toolkit already checks for a new release every time a session starts. This
is for "I want it now", or for a skill someone was told to try and can't find.

Run this, where `SKILL_DIR` is the directory holding this SKILL.md:

```bash
bash "$SKILL_DIR/../../hooks/run-hook.sh" update
```

It can take up to two minutes. Pass on what it prints in one or two plain
sentences, with no technical detail.

- **Updated:** tell the builder to open a new session to use the update. The
  session they are in keeps the old version.
- **Already up to date:** say so. If they were looking for a particular skill,
  it has probably not been released yet.
- **Did not finish:** suggest trying again in a few minutes.
- **Refused by the copy itself, pinned, or on another branch:** trying again
  will not help. Pass on the reason it gives, and offer the fix from the
  warning or note printed with it, if there is one.
- **Kept up to date by NSLS's Claude organization:** nothing was run and nothing
  needs to be. Tell the builder to open a new session, and a second one if the
  first still shows the old version.
- **Nothing on this machine updates it automatically:** this is printed on top
  of one of the results above, and does not mean the update worked. Report that
  result first, as it is. Then say in one plain sentence that the copy will fall
  behind again, offer the repair it prints, and run that command if they say
  yes. Then have them quit and reopen Claude.
