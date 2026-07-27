#!/bin/bash
# Sync pointer skills from the plugin to ~/.claude/skills/
# Creates pointers for new plugin skills, updates existing pointers,
# skips user's custom (non-pointer) skills.

PLUGIN_DIR="$HOME/.claude/local-plugins/nsls-builder-toolkit"
SKILLS_DIR="$HOME/.claude/skills"
MARKER="local-plugins/nsls-builder-toolkit"

[ -d "$PLUGIN_DIR/skills" ] || exit 0
mkdir -p "$SKILLS_DIR"

created=0
for skill_dir in "$PLUGIN_DIR/skills"/*/; do
  skill=$(basename "$skill_dir")
  dest="$SKILLS_DIR/$skill"
  src="$skill_dir/SKILL.md"
  [ -f "$src" ] || continue

  # Skip if user has a custom (non-pointer) skill
  if [ -d "$dest" ] && [ -f "$dest/SKILL.md" ]; then
    grep -q "$MARKER" "$dest/SKILL.md" 2>/dev/null || continue
  fi

  # Extract name from frontmatter
  name=$(grep "^name:" "$src" | head -1 | sed 's/name: *//')
  [ -z "$name" ] && continue

  # Extract description
  desc=$(python3 -c "
import re, sys
with open('$src', encoding='utf-8') as f: content = f.read()
fm = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if not fm: sys.exit(0)
m = re.search(r'description:\s*>-?\s*\n((?:[ \t]+.+\n?)+)', fm.group(1))
if m: print(' '.join(l.strip() for l in m.group(1).strip().split('\n')))
else:
    m = re.search(r'description:[ \t]*(.+)', fm.group(1), re.MULTILINE)
    if m:
        d = m.group(1).strip()
        # Strip the YAML quotes off a single-line scalar. A description written
        # as description: 'Brain dump...' reaches this fallback with its
        # delimiters attached, and they land verbatim in the pointer.
        # chr(34)/chr(39)/chr(92) are a double-quote, a single-quote and a
        # backslash: this script is embedded in a double-quoted shell string,
        # where a literal double-quote would end it early.
        q = d[:1]
        if len(d) > 1 and d[-1:] == q and q in (chr(34), chr(39)):
            d = d[1:-1]
            if q == chr(34):
                d = d.replace(chr(92) + chr(34), chr(34)).replace(chr(92) * 2, chr(92))
            else:
                d = d.replace(chr(39) * 2, chr(39))
        if d: print(d)
" 2>/dev/null)
  [ -z "$desc" ] && desc="NSLS Builder Toolkit skill: $skill"

  mkdir -p "$dest"
  cat > "$dest/SKILL.md" << POINTER
---
name: $name
description: >-
  $desc
---

Read and follow the full skill at \`~/.claude/local-plugins/nsls-builder-toolkit/skills/$skill/SKILL.md\`.
POINTER
  created=$((created + 1))
done

# Output count if any were created/updated (silent otherwise)
[ $created -gt 0 ] && echo "$created skill pointers synced" >&2
