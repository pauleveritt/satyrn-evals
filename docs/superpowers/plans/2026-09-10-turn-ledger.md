# Turn ledger implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One shared, pure turn counter that reports the same thing about
model turns for both routes' transcripts — honestly, including what a
transcript's own capture policy cannot answer.

**Architecture:** A new module, `src/satyrn_evals/turn_ledger.py`. A pure
`count_turns` function over a normalized event list, plus two adapters that
turn each route's actual wire format into that normalized shape.
`pathology.py` is read for reference and never modified.

**Tech Stack:** Python 3.14 stdlib only (`json`, `dataclasses`, `typing`).
No subprocess, no network — every test in this plan is default tier.

**Spec:** [docs/superpowers/specs/2026-09-10-turn-ledger-design.md](../specs/2026-09-10-turn-ledger-design.md)

## Global Constraints

- `count_turns` never raises on malformed input; anything it cannot answer
  goes into `unresolvable`, never a guess.
- `observed_starts` and `open_at_capture_end` are `None` together, only
  together.
- `pathology.py` is not modified by any task in this plan.
- Classification reads only `message.stopReason` on a `turn_end` event;
  never infers an outcome from anything else.

---

## Task 1: `TurnOutcome`, `TurnLedger`, and `count_turns`

**Files:**
- Create: `src/satyrn_evals/turn_ledger.py`
- Test: `tests/test_turn_ledger.py`

**Interfaces:**
- Produces: `TurnOutcomeKind = Literal["normal", "error", "aborted", "unknown"]`,
  `TurnOutcome(kind, stop_reason)`, `TurnLedger(observed_starts, ended,
  open_at_capture_end, retries_observed, unresolvable)`,
  `count_turns(events: Sequence[Mapping[str, object]], *, starts_retained:
  bool = True) -> TurnLedger`. Task 2 and Task 3 both feed this function's
  `events` parameter from their own adapters.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_turn_ledger.py`:

```python
"""The turn ledger: counting model turns the same way on both routes.

Default tier throughout -- pure functions over already-parsed event
dicts, nothing spawns.
"""

from satyrn_evals.turn_ledger import TurnLedger, TurnOutcome, count_turns


def _turn_start() -> dict[str, object]:
    return {"type": "turn_start"}


def _turn_end(stop_reason: str | None, *, with_usage: bool = True) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant"}
    if stop_reason is not None:
        message["stopReason"] = stop_reason
    if with_usage:
        message["usage"] = {"input": 10, "output": 5}
    return {"type": "turn_end", "message": message, "toolResults": []}


def _message_update() -> dict[str, object]:
    return {"type": "message_update", "usage": {"input": 0, "output": 0}}


def test_a_simple_stream_reports_one_started_and_one_ended_normal_turn() -> None:
    ledger = count_turns([_turn_start(), _turn_end("stop")])
    assert ledger.observed_starts == 1
    assert ledger.open_at_capture_end == 0
    assert ledger.ended == (TurnOutcome("normal", "stop"),)


def test_one_invocation_can_hold_more_than_one_turn() -> None:
    """The thing the original 'one Pi turn per invocation' assumption got
    wrong: tool execution inside one process can trigger another
    generation, each with its own start/end pair."""
    ledger = count_turns(
        [_turn_start(), _turn_end("toolUse"), _turn_start(), _turn_end("stop")]
    )
    assert ledger.observed_starts == 2
    assert ledger.open_at_capture_end == 0
    assert [o.kind for o in ledger.ended] == ["normal", "normal"]


def test_tooluse_is_a_normal_outcome_not_an_anomaly() -> None:
    ledger = count_turns([_turn_start(), _turn_end("toolUse")])
    assert ledger.ended[0].kind == "normal"
    assert ledger.ended[0].stop_reason == "toolUse"


def test_error_and_aborted_are_their_own_distinct_outcomes() -> None:
    ledger = count_turns(
        [
            _turn_start(), _turn_end("error"),
            _turn_start(), _turn_end("aborted"),
        ]
    )
    assert [o.kind for o in ledger.ended] == ["error", "aborted"]


def test_an_unrecognized_stop_reason_defaults_to_normal_not_a_guessed_error() -> None:
    ledger = count_turns([_turn_start(), _turn_end("length")])
    assert ledger.ended[0].kind == "normal"
    assert ledger.ended[0].stop_reason == "length"


def test_a_turn_end_with_no_message_is_unknown_not_dropped() -> None:
    ledger = count_turns([_turn_start(), {"type": "turn_end"}])
    assert ledger.ended[0].kind == "unknown"
    assert ledger.ended[0].stop_reason is None
    assert ledger.unresolvable


def test_an_unmatched_start_is_open_not_ended_and_not_aborted() -> None:
    """Proves the function stays pure over the event stream: an open turn
    is retained as open, never silently reclassified as terminal."""
    ledger = count_turns([_turn_start(), _turn_start()])
    assert ledger.open_at_capture_end == 1
    assert ledger.ended == ()
    assert ledger.observed_starts == 2


def test_duplicate_message_updates_never_inflate_the_turn_count() -> None:
    """The same class of bug usage_totals.py had to guard token totals
    against, now proven for turn counting."""
    events = [_turn_start()] + [_message_update()] * 50 + [_turn_end("stop")]
    ledger = count_turns(events)
    assert ledger.observed_starts == 1
    assert len(ledger.ended) == 1


def test_a_turn_end_with_no_usage_still_counts_and_classifies() -> None:
    ledger = count_turns([_turn_start(), _turn_end("stop", with_usage=False)])
    assert ledger.ended[0].kind == "normal"


def test_starts_not_retained_reports_none_never_a_fabricated_zero() -> None:
    ledger = count_turns([_turn_end("stop")], starts_retained=False)
    assert ledger.observed_starts is None
    assert ledger.open_at_capture_end is None
    assert ledger.unresolvable
    # The ended-turn count is still answerable even when starts are not:
    assert len(ledger.ended) == 1


def test_retries_are_counted_but_never_change_the_turn_count() -> None:
    events = [
        _turn_start(),
        {"type": "auto_retry_start", "attempt": 1},
        {"type": "auto_retry_end", "success": True, "attempt": 2},
        _turn_end("stop"),
    ]
    ledger = count_turns(events)
    assert ledger.observed_starts == 1
    assert len(ledger.ended) == 1
    assert ledger.retries_observed == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_turn_ledger.py`
Expected: collection error (`satyrn_evals.turn_ledger` does not exist yet).

- [ ] **Step 3: Implement `turn_ledger.py`**

Create `src/satyrn_evals/turn_ledger.py`:

```python
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

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_turn_ledger.py`
Expected: PASS, all 11 tests.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/satyrn_evals/turn_ledger.py tests/test_turn_ledger.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/turn_ledger.py tests/test_turn_ledger.py
git commit -m "turn_ledger: count model turns the same way on both routes"
```

---

## Task 2: `events_from_pi_stdout`

**Files:**
- Modify: `src/satyrn_evals/turn_ledger.py`
- Modify: `tests/test_turn_ledger.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `events_from_pi_stdout(text: str) -> list[dict[str, object]]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_turn_ledger.py`:

```python
import json

from satyrn_evals.turn_ledger import events_from_pi_stdout


def test_events_from_pi_stdout_parses_real_pi_event_lines() -> None:
    text = (
        json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "turn_end", "message": {"stopReason": "stop"}}) + "\n"
    )
    events = events_from_pi_stdout(text)
    assert [e["type"] for e in events] == ["turn_start", "turn_end"]


def test_events_from_pi_stdout_skips_the_adapters_own_marker_lines() -> None:
    """pi_implementer.py writes {"adapter_marker": "turn_start", "index": N}
    into the same file ahead of each phase's real pi output -- an
    unfortunate name collision with pi's genuine turn_start event, resolved
    because the marker carries no "type" key at all."""
    text = (
        json.dumps({"adapter_marker": "turn_start", "index": 0}) + "\n"
        + json.dumps({"type": "turn_start"}) + "\n"
        + json.dumps({"type": "turn_end", "message": {"stopReason": "stop"}}) + "\n"
    )
    events = events_from_pi_stdout(text)
    assert len(events) == 2
    assert all("type" in e for e in events)


def test_events_from_pi_stdout_skips_unparseable_lines() -> None:
    text = "not json\n" + json.dumps({"type": "turn_start"}) + "\n"
    events = events_from_pi_stdout(text)
    assert len(events) == 1


def test_events_from_pi_stdout_skips_blank_lines() -> None:
    text = "\n" + json.dumps({"type": "turn_start"}) + "\n\n"
    events = events_from_pi_stdout(text)
    assert len(events) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_turn_ledger.py -k pi_stdout`
Expected: collection error (`events_from_pi_stdout` does not exist yet).

- [ ] **Step 3: Implement**

Add to `src/satyrn_evals/turn_ledger.py` (imports gain `import json` at the
top):

```python
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
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_turn_ledger.py`
Expected: PASS, all tests including Task 1's.

- [ ] **Step 5: Lint**

Run: `uv run ruff check src/satyrn_evals/turn_ledger.py tests/test_turn_ledger.py`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add src/satyrn_evals/turn_ledger.py tests/test_turn_ledger.py
git commit -m "turn_ledger: parse raw pi stdout, skipping the adapter's own markers"
```

---

## Task 3: `events_from_session_transcript`, and the real-transcript proof

**Files:**
- Modify: `src/satyrn_evals/turn_ledger.py`
- Modify: `tests/test_turn_ledger.py`
- Create: `tests/data/real-session-phased-verify-transcript.jsonl` (already
  copied to this path from
  `~/satyrn-smokes/2026-09-09-session-phased-verify-114708/agentclinic-session-phased-session-20260909-154709-056037/transcript.jsonl`
  during planning; verify it is present before starting this task —
  `wc -l tests/data/real-session-phased-verify-transcript.jsonl` should
  report `304`)

**Interfaces:**
- Consumes: `count_turns` (Task 1).
- Produces: `events_from_session_transcript(text: str) -> tuple[list[dict[str, object]], bool]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_turn_ledger.py`:

```python
from pathlib import Path

from satyrn_evals.adapters.pi_session import _SESSION_KINDS
from satyrn_evals.turn_ledger import events_from_session_transcript

REAL_TRANSCRIPT = (
    Path(__file__).parent / "data" / "real-session-phased-verify-transcript.jsonl"
)


def test_events_from_session_transcript_unwraps_the_payload() -> None:
    text = (
        json.dumps({"type": "session_started", "conversation_id": "x"}) + "\n"
        + json.dumps(
            {
                "type": "event",
                "step_id": "phase-1-home",
                "kind": "turn_end",
                "payload": {"type": "turn_end", "message": {"stopReason": "stop"}},
            }
        )
        + "\n"
    )
    events, starts_retained = events_from_session_transcript(text)
    assert events == [{"type": "turn_end", "message": {"stopReason": "stop"}}]


def test_starts_retained_reflects_the_real_session_kinds_policy() -> None:
    """Not hand-copied: read from pi_session's own dict, so this stays
    correct if that policy ever changes."""
    _, starts_retained = events_from_session_transcript("")
    assert starts_retained == ("turn_start" in _SESSION_KINDS)


def test_the_real_transcript_reports_twenty_normal_turns_with_starts_unknown() -> None:
    """Acceptance criteria 1 and 8 together: the real transcript this
    design was verified against, read through this module rather than a
    one-off script."""
    events, starts_retained = events_from_session_transcript(
        REAL_TRANSCRIPT.read_text()
    )
    assert starts_retained is False
    ledger = count_turns(events, starts_retained=starts_retained)
    assert ledger.observed_starts is None
    assert ledger.open_at_capture_end is None
    assert ledger.unresolvable
    assert len(ledger.ended) == 20
    assert all(o.kind == "normal" for o in ledger.ended)
    tool_use = sum(1 for o in ledger.ended if o.stop_reason == "toolUse")
    stop = sum(1 for o in ledger.ended if o.stop_reason == "stop")
    assert (tool_use, stop) == (17, 3)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_turn_ledger.py -k session_transcript`
Expected: collection error (`events_from_session_transcript` does not
exist yet).

- [ ] **Step 3: Implement**

Add to `src/satyrn_evals/turn_ledger.py`:

```python
from satyrn_evals.adapters.pi_session import _SESSION_KINDS


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
```

Move the `import json` already added in Task 2 stays at the top; add the
new `from satyrn_evals.adapters.pi_session import _SESSION_KINDS` import
alongside it.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -q tests/test_turn_ledger.py`
Expected: PASS, all tests across all three tasks.

- [ ] **Step 5: Run the full default-tier suite for regressions**

Run: `uv run pytest -q`
Expected: PASS.

- [ ] **Step 6: Lint and the full gate**

Run: `just gates`
Expected: clean (pytest, ruff, lint-docs, strict Sphinx build all pass).

- [ ] **Step 7: Commit**

```bash
git add src/satyrn_evals/turn_ledger.py tests/test_turn_ledger.py \
  tests/data/real-session-phased-verify-transcript.jsonl
git commit -m "turn_ledger: parse session transcripts, verified against a real one"
```
