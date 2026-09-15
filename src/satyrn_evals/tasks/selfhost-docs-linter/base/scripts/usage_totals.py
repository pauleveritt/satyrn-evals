#!/usr/bin/env python
"""Total a pi/engine transcript's usage the way that does NOT inflate output.

Why this exists
----------------
A review of the first live engine smoke
(``/Users/pauleveritt/satyrn-smokes/2026-09-08-first-smoke-123843/cell-000-engine/``
``agentclinic-repair-depth-3-20260908-123925-900511/transcript.txt``) found
that summing every ``usage`` object anywhere in the transcript inflates
output tokens **5.5x**: a naive walk-every-usage reader reports
``output=3178``, but the real number, counted correctly, is ``output=574``.

The inflation happens because a pi/engine transcript is a *streaming* record
and the same completion's usage is reported more than once:

- ``message_update`` events are incremental snapshots emitted while a
  response is still streaming in. This transcript carries 121 of them, each
  with its own partial ``usage`` block, none of which is the final count.
- ``turn_end`` repeats the *same* usage object already reported on the
  ``message_end`` for that turn (both carry ``message.usage`` with identical
  figures) -- so counting both double-counts every assistant turn.
- ``message_start`` carries a ``usage`` block too, populated with zeros
  before the response exists.

Only one event is authoritative: the terminal ``message_end`` for an
assistant response, which carries the completion's final, settled
``message.usage`` exactly once. This transcript has 24 ``message_end``
events (one per message of any role -- user, assistant, or tool result) but
only 12 carry a usage object, because only assistant responses consume
tokens. Summing those 12 gives ``output=574``, ``input=13024`` -- the figures
this module is built to reproduce, and reproduce ONLY that way.

The discipline this file is built around
-----------------------------------------
**Never fabricate a number** (the same discipline as ``scripts/token_floor.py``
and ``scripts/timing.py``). When no ``message_end`` in the transcript carries
a usage object, this module refuses rather than reporting a total of ``0`` --
that would be indistinguishable from "the transcript really used zero
tokens", which is a different fact. The refusal names every event type it
actually saw, so the reader can tell a genuinely usage-free transcript from
a shape it does not yet recognise.

**Only the terminal event counts.** ``message_update`` snapshots,
``turn_start``, and ``turn_end`` are read for event-type accounting only --
never for their usage figures, however tempting the presence of a matching
key looks. Extending the accepted key spellings (``USAGE_INPUT_KEYS`` /
``USAGE_OUTPUT_KEYS``) is safe; extending which event *type* is read is not,
without re-verifying against a real transcript that the new type is not a
duplicate of ``message_end``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

#: The one event type this module ever reads usage from. `message_end` is
#: pi/engine's terminal, settled record of one message -- observed, on the
#: reference transcript, to carry a `usage` object only for assistant
#: responses (12 of its 24 `message_end` events; the rest are the user
#: prompt and tool-result messages, which do not consume tokens).
TERMINAL_EVENT_TYPE = "message_end"

# Key spellings for "input"/"output" token counts, most specific (observed)
# first. `input`/`output` are OBSERVED: the reference transcript's
# `message.usage` block is
# `{input, output, cacheRead, cacheWrite, reasoning, totalTokens, cost}`.
# The remaining entries are retained as hypotheses for other engine/pi
# versions, the same way `token_floor.py` retains alternate spellings --
# they cost nothing and the observed key is tried first. Extend from an
# observed transcript, never from recall.
USAGE_INPUT_KEYS: tuple[str, ...] = (
    "input",
    "input_tokens",
    "prompt_tokens",
    "promptTokens",
    "inputTokens",
)
USAGE_OUTPUT_KEYS: tuple[str, ...] = (
    "output",
    "output_tokens",
    "completion_tokens",
    "completionTokens",
    "outputTokens",
)


class UsageError(RuntimeError):
    """Raised instead of reporting a usage total that was never measured."""


@dataclass(frozen=True, slots=True)
class UsageTotals:
    """Totals summed over ONLY terminal `message_end` events with usage."""

    input_total: int
    output_total: int
    counted_events: int
    input_keys_used: tuple[str, ...]
    output_keys_used: tuple[str, ...]

    def to_json_dict(self) -> dict:
        return {
            "input_total": self.input_total,
            "output_total": self.output_total,
            "counted_events": self.counted_events,
            "input_keys_used": list(self.input_keys_used),
            "output_keys_used": list(self.output_keys_used),
            "terminal_event_type": TERMINAL_EVENT_TYPE,
        }


def _events(text: str) -> list[dict]:
    """Parsed JSON-object lines. Malformed/non-JSON lines are skipped."""
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


def _usage_dict(event: dict) -> dict | None:
    """The usage object a `message_end` event carries, if any.

    Observed location is ``message.usage`` (the assistant response nested
    under the event's ``message`` key). A top-level ``usage`` is also
    accepted as a fallback for a future/other engine shape, but every
    transcript this module has been verified against uses the nested form.
    """
    message = event.get("message")
    if isinstance(message, dict) and isinstance(message.get("usage"), dict):
        return message["usage"]
    if isinstance(event.get("usage"), dict):
        return event["usage"]
    return None


def _extract_counts(usage: dict) -> tuple[int, str, int, str] | None:
    """``(input, input_key, output, output_key)`` from a usage object.

    Requires BOTH an input and an output figure to be present as plain,
    non-negative ints; otherwise returns ``None`` rather than guessing a
    missing half as zero.
    """
    input_found: tuple[int, str] | None = None
    for key in USAGE_INPUT_KEYS:
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            input_found = (value, key)
            break
    output_found: tuple[int, str] | None = None
    for key in USAGE_OUTPUT_KEYS:
        value = usage.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            output_found = (value, key)
            break
    if input_found is None or output_found is None:
        return None
    in_count, in_key = input_found
    out_count, out_key = output_found
    if in_count < 0 or out_count < 0:
        raise UsageError(
            f"a message_end usage object reported a negative count "
            f"({in_key}={in_count!r}, {out_key}={out_count!r}); refusing "
            "rather than reporting a negative total"
        )
    return in_count, in_key, out_count, out_key


def compute_usage_totals(events: list[dict]) -> UsageTotals:
    """Sum usage over ONLY terminal `message_end` events that carry it.

    Pure over a list of already-parsed event dicts -- never touches a
    filesystem or a subprocess, so the default test tier can exercise it
    directly. Refuses (:class:`UsageError`) rather than returning a total of
    ``0`` when no countable event is found, naming every event type it saw.
    """
    input_total = 0
    output_total = 0
    counted = 0
    input_keys_seen: set[str] = set()
    output_keys_seen: set[str] = set()
    types_seen: set[str] = set()

    for event in events:
        types_seen.add(str(event.get("type", "?")))
        if event.get("type") != TERMINAL_EVENT_TYPE:
            continue
        usage = _usage_dict(event)
        if usage is None:
            continue
        found = _extract_counts(usage)
        if found is None:
            continue
        in_count, in_key, out_count, out_key = found
        input_total += in_count
        output_total += out_count
        counted += 1
        input_keys_seen.add(in_key)
        output_keys_seen.add(out_key)

    if counted == 0:
        raise UsageError(
            "no message_end event carries a usage object; output is "
            "UNMEASURED, not zero.\n"
            f"  event types seen: {', '.join(sorted(types_seen)) or '(none)'}\n"
            f"  terminal event type expected: {TERMINAL_EVENT_TYPE!r}\n"
            f"  input keys tried: {', '.join(USAGE_INPUT_KEYS)}\n"
            f"  output keys tried: {', '.join(USAGE_OUTPUT_KEYS)}\n"
            "Add the real key(s) to USAGE_INPUT_KEYS/USAGE_OUTPUT_KEYS in "
            "scripts/usage_totals.py and re-run against this same preserved "
            "transcript -- no model time is needed."
        )

    return UsageTotals(
        input_total=input_total,
        output_total=output_total,
        counted_events=counted,
        input_keys_used=tuple(sorted(input_keys_seen)),
        output_keys_used=tuple(sorted(output_keys_seen)),
    )


def read_usage_totals(text: str) -> UsageTotals:
    """``compute_usage_totals`` over a raw transcript's text."""
    return compute_usage_totals(_events(text))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("transcript", type=Path, help="a preserved transcript.txt")
    parser.add_argument("--record", type=Path, help="write the totals here as JSON")
    args = parser.parse_args(argv)

    if not args.transcript.is_file():
        print(f"usage_totals: no such transcript: {args.transcript}", file=sys.stderr)
        return 2
    try:
        totals = read_usage_totals(
            args.transcript.read_text(encoding="utf-8", errors="replace")
        )
    except UsageError as error:
        print(f"usage_totals: {error}", file=sys.stderr)
        return 1

    print(
        f"output={totals.output_total} input={totals.input_total} "
        f"across {totals.counted_events} {TERMINAL_EVENT_TYPE} events "
        f"(input keys: {', '.join(totals.input_keys_used)}; "
        f"output keys: {', '.join(totals.output_keys_used)})"
    )
    if args.record is not None:
        record = totals.to_json_dict()
        record["transcript"] = str(args.transcript)
        args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"recorded: {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
