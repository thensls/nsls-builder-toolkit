---
name: slack
description: >-
  Read and search the NSLS Slack workspace — channels, messages, threads,
  reactions, user profiles, and team conversations. Use when anyone asks
  about team discussions, decisions, what was said about a topic, channel
  activity, who said what, or context that lives in Slack rather than in
  a database. Cross-references with /data-intel for the full picture.
  Trigger phrases: slack, channel, message, thread, who said, what did
  the team say, discussion, reaction, conversation, check slack.
---

# /slack — NSLS Slack Intelligence

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (listing channels, reading messages, searching users, viewing reactions) — runs without friction. This is the skill's default mode.
2. **Configuration** (marking channels as read, managing user groups) — never proactively offered. If explicitly requested: explain what will change, confirm, then proceed.
3. **Write operations** (posting messages, adding reactions, creating user groups) — never proactively offered. If explicitly requested: explain exactly where the message will appear and who will see it, confirm the content, confirm the channel, then proceed. Messages posted appear as the "Claude Code MCP" bot — teammates will see it.

## Purpose

Slack holds the context that no database captures — the team's reasoning, reactions, decisions, and discussions. This skill makes that context queryable through conversation. Not just "search Slack" but knowing which channels to check, how to read the team's signals, and how to combine Slack context with data from other systems for the full picture. If Slack tools aren't available, run `/connect` first.

## NSLS Slack Workspace

- **Workspace:** theNSLS
- **~590 users** across the organization
- **Bot identity:** Messages and searches appear as `claude_code_mcp`

If Slack tools aren't available, run `/connect` to set up the connection.

## What the Bot Can See

| Data | Accessible? | Notes |
|------|:-----------:|-------|
| Public channel messages | ✅ | All public channels |
| Private channel messages | ✅ | Only channels the bot has been invited to via `/invite @Claude Code MCP` |
| DM metadata | ✅ | Can see who has DMs, not content unless bot is a participant |
| Message text | ✅ | Full message content |
| Sender (username + real name) | ✅ | |
| Timestamps | ✅ | |
| Reactions (emoji + counts) | ✅ | e.g., `sunrise_over_mountains:1`, `green_heart:1` |
| Thread indicators | ✅ | Can see threads exist and read thread replies |
| File/attachment count | ✅ | Knows how many files are attached |
| File content (images, videos) | ❌ | Only metadata — cannot view actual images or play videos |
| Bot names | ✅ | e.g., "Society Feedback River n8n bot" |

## Key Channels

| Channel | What's There |
|---------|-------------|
| `#society-github` | All GitHub activity — PRs, commits, merges for ignite-next |
| `#society-feedback-river` | Live user chat messages from Society (via n8n pipeline, PII-scrubbed) |
| `#society-testing` | QA, bug reports, staging/production testing |
| `#society-exceptions` | PostHog exception alerts |
| `#company-allstaff` | Company-wide announcements |
| `#revops` | Revenue operations |
| `#chapter-spotlight` | Chapter highlights and stories |

This is a starting point. Use `channels_list` to discover other channels. Ask the user what channel they're looking for if it's not obvious.

## Tools Available

All prefixed with `mcp__slack-workspace__`:

| Tool | What It Does | Tier |
|------|-------------|------|
| `channels_list` | List channels by type (public, private, DM) | 1 — read |
| `conversations_history` | Read messages from a channel or DM by ID or `#name` | 1 — read |
| `conversations_replies` | Read thread replies | 1 — read |
| `users_search` | Search for users by name | 1 — read |
| `usergroups_list` | List user groups | 1 — read |
| `usergroups_me` | Show groups the bot belongs to | 1 — read |

### Accessing Private Channels

The bot only sees channels it's been invited to. If a user asks about a private channel the bot can't access:

1. Explain: "The bot needs to be invited to that channel first."
2. Tell them how: In the channel, type `/invite @Claude Code MCP` or go to channel settings → Integrations → Add apps.
3. Warn them: Teammates in the channel will see a message: "[You] added an integration to this channel: Claude Code MCP." There is no way to do this silently.
4. After invite: Restart Claude Code (`Shift+Cmd+P` → "Developer: Reload Window") to refresh the channel cache.

### Private Channel Gotcha

`channels_list` with `channel_types: "private_channel"` may return empty even when the bot has been invited to private channels. Use `conversations_history` with `#channel-name` directly — it works even when the list doesn't show the channel.

## How to Execute

1. **Identify the right channel(s).** Use the Key Channels table above, or `channels_list` to discover. If the user names a topic, think about which channel would discuss it.
2. **Pull messages.** `conversations_history` with the channel ID or `#channel-name`. Default is last 24 hours — adjust the `limit` parameter for broader timeframes (e.g., `7d`, `30d`, `50` messages).
3. **Check threads.** Important discussions often happen in threads. If a message has replies, use `conversations_replies` to get the full conversation.
4. **Read the signals.** Reactions tell you how the team felt about something. Multiple 💚 or 🎉 = positive reception. 👀 = people noticed. No reactions on an important post = possible gap.
5. **Cross-reference.** Slack context + data from other systems = intelligence. A PostHog metric + the Slack thread where the team discussed it = the full story. Use `/data-intel` for the cross-system view.
6. **Summarize for the audience.** The user probably doesn't want every message — they want the key points, decisions, and reactions.

## Diagnostic Loop (When Searches Come Up Empty)

1. **Channel not visible?** Try `conversations_history` with `#channel-name` directly. The bot may have access even if `channels_list` doesn't show it.
2. **No messages in timeframe?** Broaden the `limit` parameter — try `7d` or `30d` instead of `1d`.
3. **Wrong channel?** The topic might be discussed in a different channel than expected. Try listing all channels and scanning names.
4. **Bot not invited?** For private channels, the bot must be explicitly invited. Tell the user how.
5. **Cache stale?** If the bot was just invited to a channel, restart Claude Code to refresh the cache.
6. **User not found?** `users_search` does partial name matching. Try first name, last name, or username separately.

## Output Guidelines

- **For someone asking "what did the team say about X":** Summarize the key messages, who said them, and the overall sentiment (reactions). Don't dump every message.
- **For cross-referencing with data:** "PostHog shows completion rate dropped 12%. In `#society-testing`, Red flagged this on March 31 and Adam confirmed a fix — 3 reactions (💚🌻🎨)."
- **For channel activity summaries:** Group by topic/thread, highlight decisions and action items, note who was involved.
- **Timestamps:** Slack messages are in UTC. Convert for the audience if needed.
- **PII:** Slack messages contain real names and conversations. Ask the user about the audience before including direct quotes in outputs shared beyond the immediate team.
