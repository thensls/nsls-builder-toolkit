# Source-sweep subagent prompts

Launch these as read-only general-purpose subagents, one per source, IN A SINGLE MESSAGE so they run concurrently. Replace `{{SUBJECT}}`, `{{EMAIL}}`, `{{SLACK_ID}}`, and `{{ROW_LIST}}` (the current audit rows, if iterating; omit on the first pass). Each returns structured markdown: **Confirmed / New candidates / Possibly stale / Volume notes / Access notes**, every item tied to evidence.

Tell each agent explicitly: READ-ONLY. Do not create, update, delete, send, or modify anything.

## Shared preamble (prepend to each)
> You are auditing what {{SUBJECT}} ({{EMAIL}}) actually works on, using <SOURCE> as ground truth. This feeds a job-function audit spreadsheet for a leadership conversation. Be precise and evidence-based (dates, links, counts, names). READ-ONLY. Return: Confirmed (row -> evidence), New candidates (item -> evidence -> suggested row or NEW), Possibly stale (row -> why), Volume notes, Access notes. No preamble.

## Asana
> Load Asana MCP tools via ToolSearch (`+asana tasks`). Find {{SUBJECT}}'s user, then pull OPEN tasks assigned to / created by them, plus tasks completed in ~60 days. IMPORTANT: the "assigned to me" search caps ~100 results and is dominated by stale multi-year-old tasks, cross-check the LIVE project boards (the intake/request queue, active sprint boards) for current work. Group open tasks into themes and map to the row list.

## Gmail
> Load Gmail MCP tools via ToolSearch (`+gmail threads`). Search ~45 days: `from:me newer_than:45d`, recent received work mail, and topic probes tied to the row list. Distinguish what {{SUBJECT}} is DRIVING vs. merely cc'd on. If the connector returns "connection invalidated," report it in Access notes and continue, do not block.

## Slack
> Load Slack MCP tools via ToolSearch (`+slack search`). Search messages `from:<@{{SLACK_ID}}>` over ~30 days and asks directed AT them; note which channels and who routes work to them. Watch for #alerts-type channels: high message volume is often inbox/handoff notifications, not system-health alerts, verify what actually fires and where (channel vs. recurring bot DM) before characterizing it.

## Fathom
> Load Fathom MCP tools via ToolSearch (`+fathom meetings`). `list_meetings` for {{SUBJECT}} over the window with `include_action_items:true` (do NOT rely on person-name title search, a 1:1 may be titled "{{SUBJECT}} / X", not the other person's full name). Extract every action item owed by {{SUBJECT}}; list recurring meeting series (these validate the "meetings & squads" row).

## Completeness sweep (run after the first pass)
> Read the FULL action-item set (all meetings in the window) and the LIVE task boards, not just highlights. The #1 failure mode is under-elevation: the evidence contains a discrete workstream that the first synthesis buried inside a generic row. For each: is it its own row or a fold-in? Confirm anything the subject names. Only surface items with real recent evidence not already represented.
