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

Run LLM evaluations, compare models, build datasets, define scoring functions, and track experiments using the Braintrust platform.

## Braintrust Setup

Braintrust is an LLM evaluation and observability platform for running experiments, tracking quality, and comparing models.

- **NSLS Braintrust project UUID:** `d55fe5d7-73f1-4a1c-9653-aa310c86754d`
- **API key:** Store in env var `BRAINTRUST_API_KEY`
- **SDK:** `braintrust` npm package (Node.js) or `braintrust` pip package (Python)
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
