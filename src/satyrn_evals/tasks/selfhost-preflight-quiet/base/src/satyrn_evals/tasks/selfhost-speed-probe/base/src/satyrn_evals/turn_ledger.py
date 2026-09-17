"""A shared turn ledger: counting model turns the same way on both routes.

**Corrected assumption, 2026-09-10.** `adapters/pi_implementer.py` was
believed to take one model turn per phase. It takes one process
invocation, which pi's own agent loop can fill with an unbounded number of
internal generations -- confirmed against a real retained transcript
(``tests/data/real-session-phased-verify-transcript.jsonl``: 20
``turn_end`` events across 3 phases, not 3). Both routes need this same
accounting; neither gets a shortcut.

Never a verdict, and never `pathology.py`'s job: that module answers "is
this transcript well-formed enough to trust" and refuses a document whose
``turn_start``/``turn_end`` counts disagree. This module answers a
different question -- "what does this stream say happened" -- for a
transcript that may itself be partial, live, or missing evidence its own
capture policy never retained. Neither module's contract changes to serve
the other's purpose.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from satyrn_evals.adapters.pi_session import _SESSION_KINDS

type TurnOutcomeKind = Literal["normal", "error", "aborted", "unknown"]

#: `stop`, `toolUse`, `error`, `aborted` are pi's own documented terminal
#: values (`docs/json.md`, `docs/rpc.md`); `pending` is mid-stream only and
#: should never reach a retained terminal event. Anything else observed is
#: still evidence the turn ended, not a reason to guess "error".
_ERROR_STOP_REASONS = frozenset({"error"})
_ABORTED_STOP_REASONS = frozenset({"aborted"})


@dataclass(frozen=True, slots=True)
class TurnOutcome:
    """One ended turn's classification, read from its own terminal
    evidence -- never inferred from anything but the turn_end event
    itself."""

    kind: TurnOutcomeKind
    stop_reason: str | None


@dataclass(frozen=True, slots=True)
class TurnLedger:
    """What a raw event stream says about model turns actually taken.

    ``observed_starts``/``open_at_capture_end`` are ``None`` together: when
    the source capture's own policy does not retain ``turn_start``, there
    is nothing to count starts from and nothing to compare ends against,
    so reporting a zero would conflate "never happened" with "never kept".
    """

    observed_starts: int | None
    ended: tuple[TurnOutcome, ...]
    open_at_capture_end: int | None
    retries_observed: int
    unresolvable: tuple[str, ...]


def _classify(event: Mapping[str, object]) -> tuple[TurnOutcome, str | None]:
    """One ``turn_end`` event to its outcome, and an unresolvable note if
    its shape could not be read."""
    message = event.get("message")
    if not isinstance(message, Mapping):
        return TurnOutcome("unknown", None), "a turn_end event carried no message"
    stop_reason = message.get("stopReason")
    if stop_reason is not None and not isinstance(stop_reason, str):
        return (
            TurnOutcome("unknown", None),
            f"a turn_end message.stopReason was not a string: {stop_reason!r}",
        )
    if stop_reason is None:
        return TurnOutcome("unknown", None), "a turn_end message carried no stopReason"
    if stop_reason in _ERROR_STOP_REASONS:
        return TurnOutcome("error", stop_reason), None
    if stop_reason in _ABORTED_STOP_REASONS:
        return TurnOutcome("aborted", stop_reason), None
    return TurnOutcome("normal", stop_reason), None


def count_turns(
    events: Sequence[Mapping[str, object]],
    *,
    starts_retained: bool = True,
) -> TurnLedger:
    """Count turns from an already-normalized event stream.

    ``starts_retained`` is supplied by the caller, never inferred from one
    transcript's own content -- an absence of ``turn_start`` lines is
    equally explained by "this policy never keeps them" and "none happened
    to open", and only the caller, who knows which adapter wrote this
    stream, can tell those apart.

    Deliberately does not classify an open turn (a ``turn_start`` with no
    matching ``turn_end``) as aborted. Whether the source process is
    genuinely gone or capture merely ended while it was still running is
    not decidable from the event stream alone; that is the caller's own
    termination evidence to apply, outside this function.
    """
    started = 0
    ended: list[TurnOutcome] = []
    unresolvable: list[str] = []
    retries = 0
    open_turns = 0
    for event in events:
        event_type = event.get("type")
        if event_type == "turn_start":
            started += 1
            open_turns += 1
        elif event_type == "turn_end":
            outcome, note = _classify(event)
            ended.append(outcome)
            if note is not None:
                unresolvable.append(note)
            if open_turns > 0:
                open_turns -= 1
        elif event_type == "auto_retry_end":
            retries += 1
    if not starts_retained:
        unresolvable.append(
            "this capture's policy does not retain turn_start; "
            "observed_starts and open_at_capture_end are unknown"
        )
        return TurnLedger(
            observed_starts=None,
            ended=tuple(ended),
            open_at_capture_end=None,
            retries_observed=retries,
            unresolvable=tuple(unresolvable),
        )
    return TurnLedger(
        observed_starts=started,
        ended=tuple(ended),
        open_at_capture_end=open_turns,
        retries_observed=retries,
        unresolvable=tuple(unresolvable),
    )


def events_from_pi_stdout(text: str) -> list[dict[str, object]]:
    """Raw pi JSONL, as `adapters/pi_implementer.py` writes it.

    Skips that adapter's own `{"adapter_marker": ..., "index": ...}`
    bookkeeping lines, interleaved in the same file ahead of each phase's
    real pi output -- resolved by the marker's own lack of a "type" key,
    not by its (name-colliding) "turn_start" value. A line that fails to
    parse as JSON, or parses without a "type" key, is skipped rather than
    raised on: both shapes are expected in this file.
    """
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict) or "type" not in parsed:
            continue
        events.append(parsed)
    return events


def events_from_session_transcript(
    text: str,
) -> tuple[list[dict[str, object]], bool]:
    """satyrn-evals' own wrapped session format
    (`adapters/pi_session.py`'s `{"type": "event", "payload": {...}}`
    lines), unwrapped to the same shape `events_from_pi_stdout` produces.

    `starts_retained` is read from `pi_session._SESSION_KINDS` at call
    time -- true only if that policy actually keeps `turn_start` -- rather
    than hard-coded, so this adapter does not silently drift from the
    writer it describes.
    """
    events: list[dict[str, object]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict) or parsed.get("type") != "event":
            continue
        payload = parsed.get("payload")
        if isinstance(payload, dict):
            events.append(payload)
    return events, "turn_start" in _SESSION_KINDS
