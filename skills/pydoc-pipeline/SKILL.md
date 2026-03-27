---
name: pydoc-pipeline
description: >-
  Generate documentation from Python code automatically. Extracts docstrings,
  function signatures, class hierarchies, and module structure into clean
  markdown docs. Use when the user says "generate docs", "document this code",
  "pydoc", "create API reference", "write documentation", "autodoc", or is
  working in a Python repo that needs documentation. Handles single files,
  modules, and entire packages.
---

# pydoc-pipeline

## What This Does

Generate documentation from Python source code. This skill scans a repo, identifies public APIs, writes Google-style docstrings for anything missing them, and produces a `docs/` directory with three markdown files: a module overview, a full API reference, and a usage examples page.

Target output: markdown files a developer can drop into a repo and immediately read or publish.

## When to Use

- A Python repo has no `docs/` directory.
- Modules, classes, or functions are missing docstrings.
- Someone needs an API reference for a library or internal package.
- Code is being handed off to another team and needs orientation material.
- A PR adds new public-facing functions and docs need to catch up.

Do not use this skill for one-off scripts, notebook experiments, or code with no public interface.

## Process

### 1. Scan

Use Python's `ast` module to parse every `.py` file in the repo. Build an inventory:

- All modules (files), with their module-level docstring if present.
- All top-level classes, with their class docstring.
- All methods and functions that are public (no leading underscore), with their existing docstring.
- Constructor signatures (`__init__` parameters) for each class.

Ignore: `__pycache__`, `test_*.py`, `*_test.py`, `setup.py`, `conftest.py`, `migrations/`.

### 2. Assess

Classify each item:

- **Has docstring**: include as-is in the API reference.
- **Missing docstring**: flag for generation.
- **Self-documenting** (e.g., `def get_name(self) -> str: return self.name`): skip, note as intentionally undocumented.
- **Private method with complex logic** (private name but the body has branching, external calls, or side effects): add a brief internal note.

Report the count before generating: "23 public functions found, 14 missing docstrings."

### 3. Generate Docstrings

Write Google-style docstrings for every flagged item. Rules:

- First line: one sentence, imperative mood ("Return the user record." not "Returns the user record" or "This function returns...").
- `Args` section: one line per parameter. Include type if not in the signature. Skip `self`.
- `Returns` section: what the function returns and its type. Omit if the function returns `None`.
- `Raises` section: only if the function explicitly raises or re-raises. List exception type and condition.
- `Examples` section: include when the usage is non-obvious or has gotchas.

Do not pad docstrings. If a function does one obvious thing, the one-sentence summary is enough — no need to force `Args` and `Returns` sections if the signature is self-evident from type hints.

### 4. Build Docs Structure

Create three files in `docs/`:

**`docs/README.md`** — Module overview
- What this package does in 2–3 sentences.
- Top-level module list with one-line descriptions.
- Quick install or import snippet.
- Link to `api-reference.md` and `examples.md`.

**`docs/api-reference.md`** — Full API reference
- Organized by module.
- For each module: module docstring, then each class and function in definition order.
- Each entry: signature on a code-fenced line, then the docstring rendered as prose.
- Classes: show the constructor signature. List methods as subsections under the class.
- Do not include private methods unless flagged in step 2.

**`docs/examples.md`** — Usage examples
- 3–5 realistic usage scenarios derived from the public API.
- Each example: a short title, one sentence of context, a working code block.
- Pull from existing tests or docstring `Examples` sections if they exist. Write from scratch if not.
- Keep examples runnable and self-contained where possible.

### 5. Output

Write the three files. Print a summary:

```
docs/README.md        — created
docs/api-reference.md — created (47 items documented)
docs/examples.md      — created (4 examples)

14 docstrings added to source files.
9 items were already documented.
3 items skipped (self-documenting).
```

If the user only wants docstrings added to source without generating `docs/`, do that and stop at step 3.

If the user only wants the `docs/` directory rebuilt from existing docstrings, skip step 3.

## Docstring Style Reference

Google style. Full example:

```python
def fetch_records(table_id: str, filters: dict | None = None, limit: int = 100) -> list[dict]:
    """Fetch records from an Airtable table.

    Args:
        table_id: The Airtable table ID (e.g., "tblXXXXXXXX").
        filters: Optional dict of field/value pairs to filter by.
        limit: Maximum number of records to return. Defaults to 100.

    Returns:
        List of record dicts, each with "id" and "fields" keys.

    Raises:
        AirtableError: If the table does not exist or the API key lacks access.

    Examples:
        >>> records = fetch_records("tblAbc123", filters={"status": "Active"})
        >>> for r in records:
        ...     print(r["fields"]["name"])
    """
```

Short form when type hints are present and the function is simple:

```python
def slugify(text: str) -> str:
    """Convert a string to a URL-safe slug."""
```

## What NOT to Document

Skip these:

- **Trivial one-liners** where the code is the documentation (`return self._name`).
- **Private methods** unless they contain branching logic that would confuse a future maintainer.
- **One-off scripts** with no functions or classes — not worth generating API docs for a 30-line script.
- **Test files** — tests document behavior through their assertions, not prose.
- **Generated code** — migrations, protobuf outputs, auto-generated models. Mark these with a comment at the top and skip.
- **`__dunder__` methods** other than `__init__` and `__call__` unless the behavior is non-standard.

When in doubt: if a developer fluent in Python would understand the function from its name and type signature alone, skip the docstring.

## Output Format

All output is markdown. No Sphinx, no RST, no HTML generation. Reasons:

- Markdown renders on GitHub without a build step.
- Easier to edit by hand.
- Works with most static site generators (mkdocs, Docusaurus, etc.) if the project later adds one.

If the project already uses Sphinx or mkdocs, note this to the user and ask whether to match the existing format before generating.
