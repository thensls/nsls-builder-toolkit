---
name: n8n
description: >-
  Manage n8n automation workflows on NSLS cloud — create, validate, test,
  update, search nodes, check executions, and deploy templates. NSLS runs
  n8n at nsls.app.n8n.cloud. Trigger phrases: n8n, workflow, automation,
  webhook, trigger, node, execution, schedule, create workflow, check
  workflow, workflow status, automation health, build automation.
  Includes safety rules and gotchas: three destructive tools require
  explicit approval, partial vs full update protocol, credential scope
  warnings, trigger type limitations.
---

# n8n Workflow Management

Manage n8n automation workflows on the NSLS cloud instance.

## NSLS n8n Cloud

- **URL:** `nsls.app.n8n.cloud`
- **MCP tools require:** `N8N_API_URL` and `N8N_API_KEY` environment variables (configured in `~/.claude.json`)
- **18 MCP tools available** for the full workflow lifecycle

## Workflow Discovery

- `mcp__n8n__n8n_list_workflows` — list all workflows (active and inactive)
- `mcp__n8n__n8n_get_workflow` — read full workflow JSON (nodes, connections, settings)
- `mcp__n8n__n8n_executions` — check execution history (success/failure/running)
- `mcp__n8n__n8n_health_check` — verify n8n cloud is healthy

## Node Search

n8n has **812 available nodes**. Use these tools to find what you need:

- `mcp__n8n__search_nodes` — search by name or category
- `mcp__n8n__get_node` — get full node documentation
- `mcp__n8n__tools_documentation` — general n8n tool docs

**Common NSLS nodes:** Webhook, HTTP Request, Code (JavaScript), AI Agent (OpenAI), Slack, Customer.io Track, Airtable, Google Sheets.

## Creating Workflows

- `mcp__n8n__n8n_create_workflow` — create from JSON definition
- `mcp__n8n__n8n_validate_workflow` — validate before activating (catches connection errors, missing credentials)
- `mcp__n8n__n8n_autofix_workflow` — auto-fix common issues

**Pattern:** Create → Validate → Fix → Test → Activate

Workflows start **inactive** by default — you must explicitly activate them.

## Updating Workflows

**ALWAYS use `mcp__n8n__n8n_update_partial_workflow`** — sends only the diff. This is the safe way to update.

**NEVER use `mcp__n8n__n8n_update_full_workflow`** without explicit user approval — it replaces the entire workflow JSON. One wrong field and you've destroyed the live workflow.

Always validate after updating.

## Testing

- `mcp__n8n__n8n_test_workflow` — test execution

**Limitation:** Only webhook, form, and chat triggers can be tested via API. Manual and schedule triggers require the n8n web UI.

Test with sample payloads that match what the trigger expects.

## Templates

- `mcp__n8n__search_templates` — find pre-built workflow templates
- `mcp__n8n__n8n_deploy_template` — deploy a template as a new workflow

Templates are a fast way to start — customize after deployment.

## SAFETY RULES (NON-NEGOTIABLE)

Three tools are **DESTRUCTIVE** and require explicit user approval every time:

1. **`n8n_delete_workflow`** — permanently deletes a workflow. Irreversible.
2. **`n8n_workflow_versions`** — has `truncate` mode that deletes ALL versions. Also has `rollback` and `delete` modes.
3. **`n8n_manage_datatable`** — has `deleteTable` and `deleteRows` actions.

**NEVER call these tools without asking the user first.** Even if the user says "clean up," confirm specifically which workflow, version, or table before proceeding.

## Gotchas & Trapdoors

- **Only webhook/form/chat triggers can be tested via API** — manual and schedule triggers require the n8n web UI.
- **`n8n_update_full_workflow` replaces the ENTIRE workflow JSON** — one wrong field and you've destroyed the live workflow. Always use partial updates.
- **Workflow versions can be truncated** (all deleted at once) — version management needs care.
- **Credentials are workspace-scoped, not workflow-scoped** — changing a credential affects every workflow that uses it.
- **Active workflows process real data** — always deactivate before making structural changes, then reactivate after verifying.
