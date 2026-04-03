---
name: airtable-guide
description: >-
  Navigate the NSLS Airtable landscape — find the right base, understand table
  structures, query records, and manage data. NSLS has 24+ Airtable bases
  across every department. Trigger phrases: airtable, which base, base ID,
  find table, airtable query, list records, NSLS bases, where is the data,
  which airtable, base directory. Includes gotchas: Automation Tracker
  access limitations, schema change blast radius, delete permanence,
  detail level efficiency.
---

# NSLS Airtable Navigation

Find the right base, understand table structures, query records, and manage data across the NSLS Airtable landscape.

## NSLS Base Directory

NSLS has 24+ Airtable bases across every department. Here's the current inventory:

### Product
| Base ID | Name |
|---------|------|
| `appZ2KFx8LmY6VV2e` | Society Product OS |
| `appr7mgxEHTuvXD7V` | ProductCentral |
| `appzPdpN2yj06wb34` | ProductCentral (Copy) |
| `appVhrz5nF4exJBId` | User Testing |

### People (HR)
| Base ID | Name |
|---------|------|
| `appnXPTu01esWWbrK` | NSLS People Ops |
| `appllq45ZuLxLWBtz` | Ignite CRM |
| `appmJR4ahPE1avxIx` | Ignite CRM (In Progress) |

### Leadership (SLT)
| Base ID | Name |
|---------|------|
| `appHDEHQA4bvlWwQq` | SLT Meeting Intelligence |
| `appItVHRP0Q9ruV7q` | SLT Meeting Agenda (2024-2025) |

### Marketing
| Base ID | Name |
|---------|------|
| `appX4VDGHChrKYl61` | Bulk Email |
| `app5rj9bOGQNFoIoD` | Campus Discovery CRM |
| `appwJ28B0Cs3twIC6` | Speaker Broadcast Catalog |

### Operations
| Base ID | Name |
|---------|------|
| `appwbKaXw2K0xoJk6` | Operations |
| `appWa5knjfvKEDDi0` | Funnel Project Tracker |
| `appttpAgmJ5RqqZb7` | Directory Information Requests |

### Research & Analysis
| Base ID | Name |
|---------|------|
| `appFB05BB9cI97B4L` | BI Squad |
| `appsaBXPKsWsA7gWx` | Jobs to be Done (ODI) — Survey-data Analysis Template |
| `appmwYIZnwICgYEMv` | Idea / Feedback Analysis |

### Cross-functional
| Base ID | Name |
|---------|------|
| `appGBXrSRcufR7r9Z` | Achievement Agent Sandbox |
| `appwLG4aNGK3DYFdR` | Achievement Agent Sandbox |
| `appt15WVDjDlYj2Gk` | SNT Matcher 2025 MVP |
| `appwJ447EBj5Jt0bX` | Summit Public Directory |

## Finding What You Need

1. **Start broad:** `mcp__airtable__list_bases` → scan names for your topic
2. **Get table names (fast):** `mcp__airtable__list_tables` with `detailLevel: "tableIdentifiersOnly"` — returns just table names and IDs, minimal context usage
3. **Drill into a table:** `mcp__airtable__describe_table` with `detailLevel: "full"` on the specific table you need

**Efficiency tip:** Always start with `tableIdentifiersOnly` — requesting `full` detail on a large base can be overwhelming and burn through context.

## Querying Records

- `mcp__airtable__list_records` — list records with optional filters
- `mcp__airtable__search_records` — text search across records

### filterByFormula Examples

```
# Exact match
{Status} = "Active"

# Contains text
FIND("keyword", {Description}) > 0

# Date range
IS_AFTER({Created}, "2026-01-01")

# Multiple conditions
AND({Status} = "Active", {Department} = "Product")
```

### Sorting and Limiting

- `sort` parameter: `[{"field": "Created", "direction": "desc"}]`
- `maxRecords` to limit results

## Writing Data

- `mcp__airtable__create_record` — create a single record
- `mcp__airtable__update_records` — update one or more records (pass an array)
- `mcp__airtable__delete_records` — delete by record ID

**Always confirm before deleting.** Airtable API deletes are not easily reversible.

## The Automation Tracker (Special)

The Automation Tracker base (`appd5oK1wLVPYZeia`) tracks all NSLS automations and the builder pipeline. Most builders won't have direct Airtable access to this base.

**Use the Railway proxy instead:** `https://web-production-6281e.up.railway.app`

- For registration: use the `register-automation` skill
- For queries: `GET /automations`, `POST /find`
- The proxy is unauthenticated — works for anyone with the URL

## Schema Management

- `mcp__airtable__create_table` — create a new table
- `mcp__airtable__create_field` / `update_field` — add or modify columns
- `mcp__airtable__list_comments` / `create_comment` — comments on records
- `mcp__airtable__upload_attachment` — attach files to records

**Caution:** Schema changes affect everyone using the base. Always confirm before creating or modifying tables and fields.

## Gotchas & Trapdoors

- **`delete_records` is permanent** — no recycle bin in the API (the Airtable web UI has one, but the API does not).
- **`list_tables` with `detailLevel: "full"` on a large base can blow up context** — start with `tableIdentifiersOnly`.
- **`filterByFormula` syntax is Airtable-specific, not SQL** — different operators, different quoting rules.
- **Schema changes (`create_field`, `update_field`, `create_table`) affect ALL users of the base instantly.**
- **Linked record fields return record IDs, not display values** — you need a second query to resolve them.
- **The Automation Tracker base (`appd5oK1wLVPYZeia`) is not accessible to most builders** — always use the Railway proxy for tracker operations.
