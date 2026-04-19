#!/usr/bin/env python3
"""Name normalizer for transcript-derived text.

Reads the canonical-names registry and exposes a single function:

    normalize_names(text) -> text

Used at three points in the pipeline:
  1. Before writing MI Decisions / Meeting Actions to Airtable (upstream)
  2. Before feeding decision text to Claude synthesis (harvest)
  3. In any knowledge-base write that sources from transcripts

Replacements are case-sensitive and word-boundary-matched. Full names
are replaced before first/last names so "Ashley Smith" becomes
"Ashleigh Smith" before the standalone "Ashley" → "Ashleigh" rule fires.
"""

import json
import re
from functools import lru_cache
from pathlib import Path


REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "canonical-names.json"


@lru_cache(maxsize=1)
def _load_rules():
    """Load the registry and compile ordered replacement rules.

    Rules are returned longest-first so full names match before single
    first/last names. Every rule is a (compiled_regex, replacement) pair.
    """
    data = json.loads(REGISTRY_PATH.read_text())
    rules = []

    for canonical, meta in data.get("canonicals", {}).items():
        if not meta.get("active", True):
            continue

        # Split canonical into first + last for first/last-name rules
        parts = canonical.split(maxsplit=1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else None

        # Full-name misspellings → canonical
        for misspelling in meta.get("full_name_misspellings", []):
            rules.append((misspelling, canonical))

        # First-name misspellings → canonical first name
        for misspelling in meta.get("first_name_misspellings", []):
            rules.append((misspelling, first))

        # Last-name misspellings → canonical last name
        if last:
            for misspelling in meta.get("last_name_misspellings", []):
                rules.append((misspelling, last))

    # Sort longest-first so "Ashley Smith" is replaced before "Ashley"
    rules.sort(key=lambda r: -len(r[0]))

    # Compile with word boundaries
    compiled = []
    for wrong, right in rules:
        pattern = re.compile(rf"\b{re.escape(wrong)}\b")
        compiled.append((pattern, right))

    return compiled


def normalize_names(text):
    """Apply canonical-name normalization to arbitrary text.

    Returns a new string. Safe to call on empty or None input
    (empty/None passthrough).
    """
    if not text:
        return text
    for pattern, replacement in _load_rules():
        text = pattern.sub(replacement, text)
    return text


def audit(text):
    """Return a list of (misspelling, canonical, count) for every rule
    that fired on the input. Useful for showing what got normalized.
    """
    findings = []
    if not text:
        return findings
    for pattern, replacement in _load_rules():
        matches = pattern.findall(text)
        if matches:
            findings.append((pattern.pattern, replacement, len(matches)))
    return findings


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # CLI mode: pass a string, print normalized version + audit
        text = " ".join(sys.argv[1:])
        print("NORMALIZED:")
        print(normalize_names(text))
        print("\nRULES THAT FIRED:")
        for m, c, n in audit(text):
            print(f"  {m} → {c}  ({n}×)")
    else:
        # Interactive / pipe mode
        text = sys.stdin.read()
        sys.stdout.write(normalize_names(text))
