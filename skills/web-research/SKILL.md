---
name: web-research
description: >-
  Web research using Google AI Mode — returns AI-synthesized answers with
  citations from 100+ sources. Use instead of WebSearch or WebFetch for any
  web research, current information, documentation lookup, technical
  comparisons, or coding examples. Trigger on "search the web", "look up",
  "find online", "research", "what's the latest", "current best practice",
  "web search", "google it", "google ai mode". Also triggers when the user
  needs information beyond the knowledge cutoff.
---

# Web Research via Google AI Mode

## IMPORTANT: Default Web Research Tool

**Use this skill instead of WebSearch or WebFetch for web research.** Google AI Mode synthesizes information from dozens of sources into one cited answer — better results, no API credits.

For **Google Docs/Sheets/Slides**, use the `gws` skill instead (authenticated, structured data).

## Prerequisites — Auto-Install

The skill checks for the Google AI Mode skill at `~/.claude/skills/google-ai-mode/`. If missing, install it:

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/PleasePrompto/google-ai-mode-skill google-ai-mode
```

On first use, the skill automatically creates a Python venv, installs dependencies, and downloads Chrome. No manual setup needed after the clone.

**First-run note:** The first search may trigger a Google CAPTCHA. If so, re-run with `--show-browser`, solve the CAPTCHA once in the browser window, and all future searches will work headlessly.

## How to Search

Always run from the skill directory:

```bash
cd ~/.claude/skills/google-ai-mode && python scripts/run.py search.py --query "your query" --save
```

### Query Optimization

Before searching, optimize the user's query for better results:

**Template:** `[Topic] [Version] [Year] ([Aspect 1], [Aspect 2], [Aspect 3]). [Output format request].`

**Rules:**
1. Include current year (2026) for up-to-date results
2. Use parentheses to list specific aspects needed
3. Request structured output (tables, comparisons, lists)
4. Include version numbers for library/framework queries
5. If the user already gave a detailed query, use it as-is

**Examples:**

| User says | Optimized query |
|-----------|----------------|
| "React hooks" | "React hooks best practices 2026 (useState, useEffect, custom hooks, common pitfalls). Provide code examples." |
| "PostgreSQL vs MySQL?" | "PostgreSQL vs MySQL performance comparison 2026 (query optimization, indexing, concurrent writes, JSON handling). Provide benchmark data." |
| "What's new in Python?" | "Python 3.13 new features 2026 (performance improvements, type system, pattern matching updates). Include migration guide." |

### Workflow

1. Optimize the user's query using the template
2. Tell the user: "Searching for: '[optimized query]'"
3. Run the search with `--save`
4. Read the saved result from `~/.claude/skills/google-ai-mode/results/`
5. Return the answer with citations

### Flags

| Flag | Purpose |
|------|---------|
| `--save` | Save results to `results/` folder (always use this) |
| `--debug` | Save detailed logs to `logs/` (use when troubleshooting) |
| `--show-browser` | Show browser window (for solving CAPTCHA) |
| `--output path` | Custom output file path |

### Reading Results

After `--save`, results are in `~/.claude/skills/google-ai-mode/results/`. Read the most recent file:

```bash
ls -t ~/.claude/skills/google-ai-mode/results/ | head -1
```

Then read that file and present the answer to the user with citations.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CAPTCHA on first run | Run with `--show-browser`, solve once, future searches are headless |
| No AI overview found | Rephrase query with more specificity |
| `ModuleNotFoundError` | Always use `run.py` wrapper, never run scripts directly |
| AI Mode not available | Region restriction — needs VPN to US/UK/DE |
| Exit code 2 | CAPTCHA required — retry with `--show-browser` |
