---
name: braintrust-evals
description: >-
  Run LLM evaluations, compare models, build datasets, define scoring
  functions, and track experiments using the Braintrust platform. NSLS uses
  Braintrust for AI pipeline evaluation across products. Trigger phrases:
  braintrust, evaluate, model comparison, LLM eval, scoring, prompt testing,
  experiment, dataset, which model, compare models, evaluation framework,
  test prompts, model benchmark, scoring rubric, structured output testing.
  Includes gotchas: prompt-schema alignment failures, key name mismatches,
  JSON mode markdown wrapping, minItems/maxItems strict-mode issues,
  scoring function edge cases, experiment naming collisions.
---

# LLM Evaluation with Braintrust

## SAFETY: THREE-TIER PERMISSION MODEL

1. **Read-only** (viewing experiments, datasets, scores, logs) — runs without friction.
2. **Configuration** (creating experiments, datasets, scoring functions) — ask permission, explain what will be created. Note: experiment names must be unique — reusing a name overwrites the previous run.
3. **Destructive** (deleting datasets, overwriting experiments) — never proactively offered. If explicitly requested: explain what will be lost (experiment history, dataset rows), confirm they understand, then proceed.

## Purpose

This skill turns LLM evaluation from a one-shot "did it work?" into an iterative process — run an experiment, interpret the scores, diagnose what's wrong, adjust the prompt or model, and re-run until quality meets the bar. Not just how to use Braintrust, but how to think about evaluation. If Braintrust isn't set up, run `/connect` — it's an SDK, not MCP.

## Braintrust Reference

- **NSLS Braintrust project UUID:** `d55fe5d7-73f1-4a1c-9653-aa310c86754d`
- **Web UI:** `braintrust.dev` — view experiments, datasets, logs
- **Docs:** https://www.braintrust.dev/docs

## Core Concepts

| Concept | What It Is |
|---------|-----------|
| **Project** | Top-level container for all your experiments and datasets |
| **Experiment** | A named test run that evaluates model outputs against expected results |
| **Dataset** | A collection of input/expected-output pairs used as test cases |
| **Scoring function** | A metric that grades each output (built-in, LLM-as-judge, or custom) |
| **Log** | Production tracing for live AI calls (observability, not evaluation) |
| **Playground** | Interactive prompt testing in the web UI |

## Creating Datasets

Datasets are your test cases — the inputs you'll run through each model.

- Include diverse inputs that represent real usage: happy paths, edge cases, adversarial inputs
- Each row has an `input` (what the model receives) and optionally an `expected` (what the ideal output looks like)
- Build datasets from production logs, user research, or manual curation
- Braintrust SDK: `init_dataset()`, `insert()`, `summarize()`

The best datasets come from real production traffic — use Braintrust's logging to capture live inputs and curate them into test sets.

## Running Experiments

An experiment = one dataset run through one model configuration.

**Compare models:** Run the same dataset through different models (e.g., GPT-4o vs GPT-4.1 nano).

**Compare prompts:** Run the same dataset through different prompt versions.

**Compare settings:** Run the same dataset with different temperatures, reasoning levels, etc.

**Braintrust SDK:**
- `init()` — create an experiment
- `evaluated()` — log each test case with input, output, expected, and scores

**Key principle:** Change ONE variable at a time. If you change model AND prompt simultaneously, you can't attribute the quality difference.

## Scoring Functions

### Built-in Scorers

Braintrust provides ready-made scorers: factuality, relevance, toxicity, coherence.

### LLM-as-Judge

Use a model to grade another model's output. Define:
- **Criteria** — what "good" looks like
- **Rubric** — scoring scale with examples
- **Examples** — few-shot demonstrations of correct grading

### Custom Scorers

Write your own function — return a 0-1 score based on whatever logic you need. Useful for domain-specific quality checks.

### Schema Compliance Scoring

Validate that structured outputs match the expected JSON schema: correct key names, correct types, correct array lengths.

### Scoring Dimensions to Consider

For any eval, decide which of these matter most for your use case:
- Accuracy, helpfulness, tone, conciseness, schema compliance, latency, cost

## Interpreting Results

- Braintrust web UI shows side-by-side experiment comparisons
- Look at: aggregate scores, per-case breakdowns, score distributions
- Watch for high variance — a model that scores 0.9 average but swings 0.3-1.0 per case is unreliable
- Regression detection: compare new experiments against a baseline to catch quality drops

## Structured Output Validation

These patterns apply to any LLM pipeline, not just Braintrust experiments:

- **Schema-prompt alignment is critical.** If the prompt says "generate 10 items" but the schema only has room for 6, models get confused. Always ensure prompt instructions and output schema agree.
- **Key name consistency:** If your prompt uses `"description"` but your code expects `"text"`, the model may use either. Standardize across prompt, schema, and parsing code.
- **JSON mode quirk:** Some models wrap responses in markdown code blocks even in JSON mode. Strip backticks before parsing.
- **Array length:** If you need exactly N items, say so in both the prompt AND the schema. `minItems`/`maxItems` in JSON Schema can help, but some strict-mode implementations reject these — test first.
- **Always validate** LLM output against the expected schema before using it. Don't trust the model to follow the schema perfectly.

## Production Logging & Observability

- Braintrust logging wraps your production AI calls to track inputs, outputs, latency, and cost
- Use logging to build datasets from real production traffic (most representative test cases)
- Pair with PostHog for user-level analytics — Braintrust tracks the AI call, PostHog tracks what the user did with the result

## Diagnostic Loop (When Scores Are Low or Wrong)

1. **Check schema-prompt alignment.** Does the prompt ask for N items but the schema only allows M? This is the #1 cause of confused output.
2. **Check key name consistency.** Does the prompt say `"description"` but the parsing code expects `"text"`? Standardize across prompt, schema, and parser.
3. **Run a single test case manually.** Look at the raw model output before scoring. Is the JSON valid? Is it wrapped in markdown backticks? Strip backticks before parsing.
4. **Check the scoring rubric.** Vague criteria → inconsistent LLM-as-judge scores. Add concrete examples of each score level.
5. **Compare against baseline.** Is the score actually low, or did the baseline change? Always compare new experiments against a pinned baseline.
6. **Check model version.** Model updates can change behavior silently. Pin versions in production and re-run experiments after updates.
7. **Adjust ONE variable and re-run.** If you change model AND prompt simultaneously, you can't attribute the difference. Change one, measure, then change the next.

## Output Guidelines

- **For leadership:** "Model X is 15% more accurate than Model Y on our evaluation set, at 40% lower cost per call."
- **For engineering:** Per-case breakdowns, failing test cases with raw input/output, score distributions with variance.
- **For prompt iteration:** Show the specific test cases that scored lowest, with the model's actual output alongside the expected output, so the prompt author can see exactly where it went wrong.

## Gotchas & Trapdoors

- **Prompt says 10 items + schema says 6 = confused model.** Alignment is non-negotiable.
- **A model that "works" on one prompt may fail on a slight variation** — always test with diverse inputs.
- **`minItems`/`maxItems` in JSON Schema may be rejected by strict-mode implementations** — test before deploying.
- **JSON mode can still produce markdown-wrapped output** — always strip backticks before parsing.
- **Temperature 0 doesn't guarantee determinism** — it reduces but doesn't eliminate randomness.
- **Model updates can change behavior silently** — pin versions in production and re-run experiments after updates.
- **LLM-as-judge scoring is only as good as your rubric** — vague criteria produce inconsistent scores.
- **Experiment names must be unique within a project** — reusing a name overwrites the previous run.
- **Cost estimation is only as good as your token price table** — prices change when models update.
