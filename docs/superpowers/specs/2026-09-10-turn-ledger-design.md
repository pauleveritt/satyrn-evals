# Turn ledger design: counting model turns the same way on both routes

Written 2026-09-10. A TE1 prerequisite, not a numbered HP cycle. Design
only: **it authorizes no inference and no comparison spending.** Read with
[the TE plan](../../current/engine-turn-efficiency-plan.md), whose TE1 "fix
the contrast and the unit of effort" this answers one piece of, and with
`BRIEF.md`'s invariants on denominators and missingness.

## The correction this exists for

TE1's own draft assumed `adapters/pi_implementer.py` — described in its own
prior module docstring as "one Pi turn per phase" — took exactly one model
turn per phase, making Engine-side turn counting trivial and Baseline-side
counting the only hard problem. **That assumption is wrong, corrected
2026-09-10** (`adapters/pi_implementer.py`'s module docstring carries the
same correction). `pi --print --mode json` runs a complete multi-generation
agent interaction inside one process invocation; tool execution can trigger
another generation, repeatedly, each with its own `turn_start`/`turn_end`
pair (pi's own `docs/json.md`, "Turn lifecycle"). Nothing on the packet
route bounds this — `turn_budget`/`tool_call_budget` are declared and never
applied (`chain_record.declaration_ledger`) — and the invocation runs with
`--no-extensions --no-skills`, so none of Engine's own guards are loaded
either. **Both routes need the same model-turn accounting**, because both
can loop internally, unmitigated, inside what looks like one bounded step.

Verified against a real retained transcript rather than assumed:
`~/satyrn-smokes/2026-09-09-session-phased-verify-114708/agentclinic-session-phased-session-20260909-154709-056037/transcript.jsonl`
carries 20 `turn_end` events across 3 phases (6-7 per phase, not 1), 17 with
`stopReason: "toolUse"` and 3 with `stopReason: "stop"` — the tool-use turns
matching its 17 `tool_execution_end` events exactly.

**A second finding from the same transcript, load-bearing for this design:**
`turn_start` never appears in it at all (`grep -c turn_start` on the file:
`0`). `adapters/pi_session.py`'s own event filter
(`_SESSION_KINDS`, `pi_session.py:46-58`) has no entry for `turn_start`,
`message_start`, or `tool_execution_start` — `map_rpc_event`
(`pi_session.py:132-156`) returns `None` for any event type absent from
that dict, which the driver then never writes. Only `turn_end`,
`tool_execution_end`, `compaction_start`/`_end`, `message_update`,
`agent_end` and `auto_retry_end` survive. **Baseline session transcripts,
as currently captured, cannot answer "how many turns started" or "was one
left open" at all** — that evidence was never retained. `adapters/pi_implementer.py`
carries no such filter (it pipes `pi`'s raw stdout straight to a file), so
Engine-side phase transcripts, once real ones exist, will have the full
event set.

**Retries do not inflate starts.** `auto_retry_start`/`auto_retry_end`
(pi's `docs/rpc.md`, "auto_retry_start / auto_retry_end") retry the *same*
turn after a transient provider error (rate limit, 5xx) — no new
`turn_start` is emitted for a retry. A turn's retry history is otherwise
invisible unless tracked separately from the start/end count.

## What this closes, and what it does not

This closes TE1's turn-accounting gap only: a way to count what a raw event
stream actually says about model turns, honestly, for either route's
transcript shape. It does not decide the turn ceiling, does not compute
per-role or per-phase totals (that is TE1's own remaining recompute work,
built on top of this), does not classify a pathology, and does not change
`pathology.py`'s existing document-validity contract — that module answers
"is this transcript well-formed enough to trust," a different, narrower
question this one does not touch or relax.

## The module

`src/satyrn_evals/turn_ledger.py`, new file.

```python
type TurnOutcomeKind = Literal["normal", "error", "aborted", "unknown"]

@dataclass(frozen=True, slots=True)
class TurnOutcome:
    """One ended turn's classification, read from its own terminal
    evidence -- never inferred from anything but the turn_end event
    itself."""
    kind: TurnOutcomeKind
    stop_reason: str | None  # the raw observed value; None if absent

@dataclass(frozen=True, slots=True)
class TurnLedger:
    """What a raw event stream says about model turns actually taken.
    Never a verdict: a large open-turn count or many errors is retained
    evidence, not a pathology classification -- pathology.py's job, not
    this one's."""
    observed_starts: int | None
    ended: tuple[TurnOutcome, ...]
    open_at_capture_end: int | None
    retries_observed: int
    unresolvable: tuple[str, ...]
```

`observed_starts` and `open_at_capture_end` are `None` together, and only
together: when the source capture's own policy does not retain
`turn_start`, there is nothing to count starts from and nothing to compare
ends against, so reporting `open_at_capture_end: 0` would be exactly the
absence-as-zero conflation this repository's own HP5/HP6 rules exist to
prevent for mutations. `unresolvable` names the reason in that case rather
than leaving the reader to guess from two `None`s why.

### `count_turns`

```python
def count_turns(
    events: Sequence[Mapping[str, object]],
    *,
    starts_retained: bool = True,
) -> TurnLedger: ...
```

Pure: `events` is an already-normalized sequence of raw pi event dicts
(after either adapter below has unwrapped its own wire format).
`starts_retained` is supplied by the caller, never inferred from one
transcript's own content — it is a property of *which capture wrote this*,
which no single document can honestly determine about itself (an absence
of `turn_start` lines is equally explained by "this policy never keeps
them" and "none happened to open," and only the caller, who knows the
writer, can tell those apart).

**Deliberately does not classify an open turn as `aborted`.** A `turn_start`
with no matching `turn_end` by the end of `events` is retained only in
`open_at_capture_end`'s count. Whether that means the process is genuinely
gone (and the turn will never close) or capture merely ended while the
process was still running is not decidable from the event stream alone —
the caller's own termination evidence (a subprocess exit code, a timeout
signal, a confirmed process-still-running check) decides that, outside
this function. Keeping this function pure and event-stream-only is what
makes it independently testable without needing to fabricate termination
evidence for every case.

**Classification, from each `turn_end`'s `message.stopReason`:**

| `stopReason` observed | `TurnOutcome.kind` |
|---|---|
| `"stop"`, `"toolUse"`, or any other value not below | `normal` |
| `"error"` | `error` |
| `"aborted"` | `aborted` |
| absent, or `message` itself absent | `unknown` |

`toolUse` is deliberately `normal`: it is the ordinary "generation stopped
to call a tool, and will continue" shape, confirmed as 17 of the 20 real
`turn_end`s above — the common case, not an anomaly. New stop-reason
strings default to `normal` too, matching pi's own documented set (`stop`,
`toolUse`, `error`, `aborted`, and `pending` — which only appears mid-stream
and should never reach a retained terminal event); an unrecognized value is
still evidence the turn ended, just not a reason to guess "error".

`retries_observed` counts `auto_retry_end` events verbatim — diagnostic,
never subtracted from or added to any other count, since a turn that
needed three retries is still exactly one turn.

`unresolvable` accumulates human-readable notes for anything the stream
could not answer: `starts_retained=False` (names the reason above), any
event with `type == "turn_end"` whose `message` is missing or malformed.

### Two adapters, because the two routes write different wire shapes

```python
def events_from_pi_stdout(text: str) -> list[dict[str, object]]: ...
```

Parses raw pi JSONL — `adapters/pi_implementer.py`'s transcript format.
**Must skip that adapter's own bookkeeping lines**: `pi_implementer.py`
writes `{"adapter_marker": "turn_start", "index": N}` markers into the same
file, ahead of each phase's own `pi` invocation output
(`pi_implementer.py`, `_marker`/`main`) — an unfortunate name collision
with pi's real `"type": "turn_start"` event, distinguished cleanly because
the marker has no `"type"` key at all. A line that fails to parse as JSON,
or parses but carries no `"type"` key, is skipped as non-pi bookkeeping,
not raised as an error — this file is expected to carry exactly that.

```python
def events_from_session_transcript(
    text: str,
) -> tuple[list[dict[str, object]], bool]:
```

Parses `adapters/pi_session.py`'s wrapped format
(`{"type": "event", "payload": {...}, ...}` lines, plus one leading
`{"type": "session_started", ...}` line to skip) and returns
`(unwrapped_payloads, starts_retained)`. `starts_retained` is computed as
`"turn_start" in pi_session._SESSION_KINDS` — read from the actual
retention policy at call time, not hand-copied, so this stays correct if
that dict ever changes without needing a matching edit here.

## Acceptance

1. Against the real transcript named above: `observed_starts is None`,
   `open_at_capture_end is None`, `unresolvable` names the missing-starts
   reason, `len(ended) == 20`, with 17 `normal` (`toolUse`) and 3 `normal`
   (`stop`) — all 20 are `normal`; none of this transcript's real turns
   ended in error or abort.
2. A synthetic multi-generation stream (`turn_start`, `turn_end`
   `toolUse`, `turn_start`, `turn_end` `stop`, all with `starts_retained=True`)
   reports `observed_starts == 2`, `open_at_capture_end == 0`, two `normal`
   outcomes — proving one invocation can be correctly counted as more than
   one turn, the thing the original "one Pi turn" assumption got wrong.
3. A synthetic stream with an `error` and an `aborted` `stopReason` each
   produce their own distinct `TurnOutcome.kind`.
4. A synthetic stream ending on an unmatched `turn_start` (no closing
   `turn_end`) reports `open_at_capture_end == 1`, and that turn does not
   appear in `ended` — proving an open turn is retained as open, not
   silently dropped and not silently classified as anything terminal.
5. A stream padded with many duplicate `message_update` events between a
   real `turn_start`/`turn_end` pair still reports exactly one ended turn —
   proving the counter is immune to the same class of inflation
   `usage_totals.py` had to guard token totals against.
6. A `turn_end` whose `message` carries no `usage` key still counts and
   classifies normally — turn counting must not depend on usage presence.
7. `events_from_pi_stdout` on a transcript containing `pi_implementer.py`
   marker lines interleaved with real pi events extracts only the real
   events, in order, markers skipped.
8. `events_from_session_transcript` run against the real transcript named
   above returns `starts_retained is False`, matching `_SESSION_KINDS`'s
   actual current shape, verified by importing the real dict rather than a
   copy.

## Out of scope

- **Per-phase, per-role or whole-attempt recompute.** This module answers
  "what does one event stream say about turns"; folding that across phases
  and roles into TE1's frozen totals is separate, later work built on it.
- **A turn ceiling, or any pass/fail judgment.** Purely descriptive.
- **Reclassifying `pathology.py`'s malformed-document refusal.** That
  function's contract (`turn_start` count must equal `turn_end` count, or
  refuse the whole document) is untouched. This module answers a different
  question for a different purpose and does not relax that one.
- ~~**Fixing `pi_session.py`'s capture filter** to retain `turn_start`.~~
  **Done 2026-09-10** — `turn_start`, `message_start` and
  `tool_execution_start` now map to kind `"other"`, the same bucket
  `message_update`/`agent_end`/`auto_retry_end` already use, so no
  protocol schema change was needed. Does not help any already-retained
  transcript, including this design's own real fixture — see
  `tests/test_turn_ledger.py::test_the_real_transcript_now_reads_starts_retained_true_despite_predating_the_fix`
  for the resulting honesty caveat: reading an archived transcript
  through `events_from_session_transcript`'s *live* `starts_retained`
  check can now silently misreport zero starts for a file the fix
  predates. A caller analyzing archived evidence must track each file's
  own capture-date policy, not trust the live check for anything not
  captured just now.
- **Termination-evidence interpretation.** `count_turns` reports
  `open_at_capture_end` as a bare fact; deciding whether an open turn is
  "aborted" from an independent exit code or timeout is the caller's job,
  named but not implemented here.
