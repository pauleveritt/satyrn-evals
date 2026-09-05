#!/usr/bin/env python
"""Read the per-cell **input-token floor** out of a preserved transcript.

Why this exists, and why it is not part of ``preflight.sh``
-----------------------------------------------------------
The confirmed amendment
(``docs/superpowers/specs/2026-09-05-v11b-trim-arm-substrate-design.md`` §9)
owes a per-cell input-token floor **measured from inside a materialized
workspace**. Preflight runs *before* any workspace exists, so preflight
cannot measure it. The number can only come from a cell that actually ran —
which is what the two V5d smokes are for. This reader takes that cell's
preserved transcript and reports the figure; ``preflight.sh`` then *requires*
a recorded floor to exist before any budgeted cell, and refuses without one.

The measurement matters because it is the input to the Envelope cap decision
(proposal §2.4), and because the repo-root figures it replaces were wrong in
the direction that inflates a cap: ~93% of a repo-root ``pi`` call was
context-file discovery, not the tool's own floor
(``docs/superpowers/research/2026-09-05-pi-context-file-loading-and-arm-parity.md``).

The discipline this file is built around
----------------------------------------
**Absent is not zero.** Four silent-zero incidents are recorded in the
harvest index, and ``BRIEF.md`` rule 8 asks a detector to discriminate in
both directions. pi's usage-event shape is **not currently known to this
repository** — ``pathology.py`` parses event *types* and never reads usage —
so rather than guess a key and silently report ``0``, this reader **refuses
and names every event type and numeric-looking key it actually saw**. The
first smoke therefore *teaches* us the shape instead of fabricating a floor.

When that refusal fires, record the observed keys, add the real one to
``USAGE_KEYS``, and re-run against the same preserved transcript. Re-reading
a stored artifact costs no model time — that is `BRIEF.md` rule 3 working.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

type FloorResult = tuple[int, str]

# Spellings for "input tokens", most specific first.
#
# ``usage.input`` is OBSERVED, not guessed: the 2026-09-05 Baseline V5d smoke
# on ``agentclinic-repair-depth-2`` emitted
# ``usage: {input, output, reasoning, cacheRead, cacheWrite, totalTokens}``.
# The earlier entries are retained as hypotheses for other pi versions; they
# cost nothing and the observed key is tried first. Extend this list from an
# observed transcript, never from recall.
USAGE_KEYS: tuple[str, ...] = (
    "input",
    "input_tokens",
    "prompt_tokens",
    "promptTokens",
    "inputTokens",
)
USAGE_CONTAINERS: tuple[str, ...] = ("usage", "tokens", "metrics")


class FloorError(RuntimeError):
    """Raised instead of reporting a token floor that was never measured."""


def _events(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        if not (stripped := line.strip()):
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def _numeric_keys(event: dict) -> set[str]:
    """Every key whose value is a plain int, at depth 1 and inside containers."""
    seen = {
        k for k, v in event.items() if isinstance(v, int) and not isinstance(v, bool)
    }
    for container in USAGE_CONTAINERS:
        if isinstance(inner := event.get(container), dict):
            seen |= {
                f"{container}.{k}"
                for k, v in inner.items()
                if isinstance(v, int) and not isinstance(v, bool)
            }
    return seen


def _from_event(event: dict) -> FloorResult | None:
    for container in USAGE_CONTAINERS:
        if isinstance(inner := event.get(container), dict):
            for key in USAGE_KEYS:
                if isinstance(value := inner.get(key), int) and not isinstance(
                    value, bool
                ):
                    return value, f"{container}.{key}"
    for key in USAGE_KEYS:
        if isinstance(value := event.get(key), int) and not isinstance(value, bool):
            return value, key
    return None


def read_floor(text: str) -> FloorResult:
    """The first input-token count in the transcript, and the key it came from.

    Refuses — never returns 0 — when no usage figure is present.
    """
    if not (events := _events(text)):
        raise FloorError(
            "no JSON events in the transcript: the floor is unmeasured, not zero"
        )
    # Streaming `message_update` events carry a usage block that is not yet
    # populated, reporting 0 for every field. Observed in the 2026-09-05
    # Baseline smoke: 217 events carry usage, only 68 carry a positive input
    # count. A zero there means "not filled in yet", NOT "zero tokens" -- so
    # zeros are skipped as placeholders while an all-zero transcript is still
    # refused below rather than reported as a floor of 0.
    saw_placeholder = False
    for event in events:
        if (found := _from_event(event)) is not None:
            count, key = found
            if count <= 0:
                saw_placeholder = True
                continue
            return count, key
    if saw_placeholder:
        raise FloorError(
            "every usage block in this transcript reports 0 input tokens; that "
            "is an unpopulated stream, not a measurement. The floor is "
            "UNMEASURED, not zero."
        )
    types = sorted({str(e.get("type", "?")) for e in events})
    keys = sorted(set().union(*(_numeric_keys(e) for e in events)) or {"(none)"})
    raise FloorError(
        "no input-token usage found; the floor is UNMEASURED, not zero.\n"
        f"  event types seen: {', '.join(types)}\n"
        f"  numeric keys seen: {', '.join(keys)}\n"
        f"  keys tried: {', '.join(USAGE_KEYS)}\n"
        "Add the real key to USAGE_KEYS in scripts/token_floor.py and re-run "
        "against this same preserved transcript — no model time is needed."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", type=Path, help="a preserved transcript.txt")
    parser.add_argument("--record", type=Path, help="write the floor here as JSON")
    args = parser.parse_args(argv)

    if not args.transcript.is_file():
        print(f"token_floor: no such transcript: {args.transcript}", file=sys.stderr)
        return 2
    try:
        count, key = read_floor(
            args.transcript.read_text(encoding="utf-8", errors="replace")
        )
    except FloorError as error:
        print(f"token_floor: {error}", file=sys.stderr)
        return 1

    print(f"input-token floor: {count} (from {key})")
    if args.record is not None:
        args.record.write_text(
            json.dumps(
                {
                    "input_token_floor": count,
                    "source_key": key,
                    "transcript": str(args.transcript),
                    "measured_in": "materialized workspace (attempt cell)",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"recorded: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
