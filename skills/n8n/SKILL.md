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

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (list workflows, get workflow, check executions, health check, search nodes/templates, validate) — runs without friction.
2. **Configuration** (create workflow, partial update, activate/deactivate, deploy template, autofix) — ask permission, explain what will change and whether it affects a live workflow. Deactivating a workflow stops it from processing real data — confirm first.
3. **Destructive** (delete workflow, truncate versions, delete datatable/rows, full workflow update) — never proactively offered. If explicitly requested: explain exactly what will be permanently deleted or overwritten, confirm which specific workflow/table, confirm they understand it cannot be undone, then proceed.

## Purpose

This skill makes n8n workflows queryable and manageable through conversation — not just listing workflows, but understanding what they do in the NSLS context, diagnosing why an execution failed, and knowing the safe way to make changes without breaking live automations. If n8n tools aren't available, run `/connect` first.

## NSLS n8n Landscape

NSLS runs automation workflows for: Society Feedback River (chat → PII scrub → Slack), auth alerts, exception notifications, member lifecycle events, and more. The n8n instance at `nsls.app.n8n.cloud` is the automation backbone — changes here affect real users and real notifications.

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

## Diagnostic Loop (When Workflows Fail)

1. **Check execution history:** `n8n_executions` → find the failed run → read the error output.
2. **Identify the failing node:** The execution error usually names the specific node that failed.
3. **Check node configuration:** `n8n_get_workflow` → find the failing node → check its config against `get_node` documentation.
4. **Validate:** `n8n_validate_workflow` → catches connection errors, missing credentials, type mismatches.
5. **Try autofix:** `n8n_autofix_workflow` for common structural issues.
6. **Fix and re-validate:** Apply the fix with `n8n_update_partial_workflow` (never full update) → validate again → test.
7. **If testing fails:** Only webhook/form/chat triggers can be tested via API. Manual and schedule triggers require the n8n web UI.

## Output Guidelines

- **For the person debugging:** Include the failing node name, the error message, and what you changed.
- **For status updates:** "The Society Feedback River workflow failed 3 times today — the Slack node lost its credential. Reattached and verified."
- **For workflow documentation:** List nodes in execution order with what each one does.

## Gotchas & Trapdoors

- **Only webhook/form/chat triggers can be tested via API** — manual and schedule triggers require the n8n web UI.
- **`n8n_update_full_workflow` replaces the ENTIRE workflow JSON** — one wrong field and you've destroyed the live workflow. Always use partial updates.
- **Workflow versions can be truncated** (all deleted at once) — version management needs care.
- **Credentials are workspace-scoped, not workflow-scoped** — changing a credential affects every workflow that uses it.
- **Active workflows process real data** — always deactivate before making structural changes, then reactivate after verifying.
