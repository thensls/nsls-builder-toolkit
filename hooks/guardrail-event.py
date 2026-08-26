#!/usr/bin/env python3
"""
Record a guardrail event that only Claude can see happened.

The hard gates report themselves -- guardrail-gate.py is deterministic, it sees
every Bash/Write/Edit call, and it emits `guardrail_blocked` from inside the
block. Everything else about the guardrails is conversational: Claude notices a
build has grown past Tier 1, suggests a reviewer, offers to draft the note to
Kevin, watches a build move off a personal repo. No hook can observe any of
that, so if Claude does not report it, it did not happen as far as the org is
concerned -- and the guardrail page shows only the rare hard block, which reads
as "this thing does nothing".

    guardrail-event.py <label> "<what happened>" [--automation NAME]

<label> takes the bare word: flagged, registered, mentor, migrated, proceeded,
blocked, authorized, disputed. See CLAUDE.md for which moment each one marks.

The description is read by a human on Signal's guardrail page, so it should say
what happened in one plain clause -- "suggested Kevin review the member digest
before it ships", not "guardrail raised". Never put anything in it the builder
would be unhappy to see attributed to them; this is a record of the build's
history, not of their reluctance.

Exits 0 whatever happens, prints one line saying what it did. Reporting must
never be the reason a session stumbles.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

USAGE = __doc__.strip()


def main():
    args = [a for a in sys.argv[1:]]
    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return

    try:
        import guardrail_emit
    except Exception:
        # Nothing to fall back to, and nothing worth interrupting for.
        print("Guardrail reporting is unavailable in this checkout.")
        return

    if args[0] in ("--list", "labels"):
        for label, meaning in guardrail_emit.LABELS.items():
            print(f"  {label[len('guardrail_'):]:<12} {meaning}")
        return

    def opt(name, default=""):
        if name in args:
            i = args.index(name)
            if i + 1 < len(args):
                return args[i + 1]
        return default

    label = args[0]
    # Everything positional after the label is the description, so an unquoted
    # sentence still records something useful instead of one stray word.
    positional = [
        a for i, a in enumerate(args[1:], start=1)
        if not a.startswith("--")
        and not (i > 1 and args[i - 1].startswith("--"))
    ]
    description = " ".join(positional).strip()

    if not description:
        print("Nothing recorded: a guardrail event needs a description of what "
              "happened, in the builder's terms.")
        return

    print(guardrail_emit.emit(
        label,
        description,
        automation=opt("--automation") or opt("--build"),
        cwd=opt("--cwd") or os.getcwd(),
        dedupe="--no-dedupe" not in args,
        # Splits the dedupe slot so two different declines on one build stay two
        # rows. Passed through by emit_detached; the CLI is the detached path.
        variant=opt("--variant"),
    ))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # never break a session over a report
    sys.exit(0)
