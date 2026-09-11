"""Per-phase attribution and counts over retained attempt transcripts.

Pure: text and already-parsed records in, a ledger out. No filesystem, no
subprocess, no model. ``turn_ledger.py`` is imported for the Engine
transcript's stream parsing and is never modified.

Two layouts, two attribution mechanisms, one shape:

- **Baseline** (``agentclinic-session-phased`` through ``pi_session``): every
  retained ``event`` carries its own ``step_id``, and ``session-record.json``'s
  ``steps`` list is the declared phase order.
- **Engine** (the packet route through ``pi_implementer``): the transcript is
  four positional ``session`` blocks with no phase label; the chain record's
  ``phases`` list is the only authority mapping block N to phase N, so the
  count is cross-checked against it before any per-phase number is reported.

A ledger that cannot attribute a phase is ``undecidable``; a missing record is
``absent``. Neither is a zero, and neither is a per-phase number.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from satyrn_evals.turn_ledger import events_from_pi_stdout

type LedgerState = Literal["measured", "undecidable", "absent"]
type SelfTestOutcome = Literal["pass", "fail", "not_run", "unrecorded"]


@dataclass(frozen=True, slots=True)
class PhaseCounts:
    """One phase's counts.

    ``self_test_calls``/``self_test_outcome`` are ``None`` on an arm whose
    self-test evidence this cycle cannot derive in both directions; V2 owns
    that Baseline measure and V3 records it as arm-asymmetric evidence if it
    stays undecidable.
    """

    step_id: str
    turns: int
    tool_calls: int
    self_test_calls: int | None
    self_test_outcome: SelfTestOutcome | None


@dataclass(frozen=True, slots=True)
class PhaseLedger:
    """A per-phase ledger, or the named reason it is not one."""

    state: LedgerState
    reason: str | None
    cells: tuple[PhaseCounts, ...]

    @property
    def step_ids(self) -> tuple[str, ...]:
        return tuple(cell.step_id for cell in self.cells)

    def cell(self, step_id: str) -> PhaseCounts | None:
        for cell in self.cells:
            if cell.step_id == step_id:
                return cell
        return None


def _self_test_outcome(record: object) -> SelfTestOutcome:
    """The chain's independently recorded self-test verdict.

    ``not_run`` and ``unrecorded`` are distinct on purpose: "the command was
    never run" and "the record does not say what happened" are different
    findings, and neither is a pass.
    """
    if not isinstance(record, Mapping):
        return "unrecorded"
    if record.get("ran") is not True:
        return "not_run"
    exit_code = record.get("exit_code")
    if not isinstance(exit_code, int):
        return "unrecorded"
    return "pass" if exit_code == 0 else "fail"


def _engine_session_blocks(text: str) -> list[list[dict[str, object]]]:
    """The transcript's ``session``-delimited blocks, in file order.

    ``events_from_pi_stdout`` already drops ``pi_implementer``'s own
    ``adapter_marker`` lines; a real pi ``session`` event is the boundary.
    """
    blocks: list[list[dict[str, object]]] = []
    for event in events_from_pi_stdout(text):
        if event.get("type") == "session":
            blocks.append([])
            continue
        if blocks:
            blocks[-1].append(event)
    return blocks


def ledger_from_engine(
    transcript_text: str,
    chain: Mapping[str, object] | None,
) -> PhaseLedger:
    """Attribute an Engine transcript's positional blocks to the chain's
    declared phases, then count each phase."""
    if chain is None:
        return PhaseLedger("absent", "no chain record", ())
    phases = chain.get("phases")
    if not isinstance(phases, list):
        return PhaseLedger("undecidable", "chain record has no phases list", ())
    declared: list[str] = []
    outcomes: list[SelfTestOutcome] = []
    for phase in phases:
        if not isinstance(phase, Mapping) or not isinstance(phase.get("step_id"), str):
            return PhaseLedger("undecidable", "a chain phase has no step_id", ())
        declared.append(phase["step_id"])
        outcomes.append(_self_test_outcome(phase.get("self_test_outcome")))
    blocks = _engine_session_blocks(transcript_text)
    if len(blocks) != len(declared):
        return PhaseLedger(
            "undecidable",
            f"{len(blocks)} session blocks against {len(declared)} declared phases",
            (),
        )
    cells = tuple(
        PhaseCounts(
            step_id=step_id,
            turns=sum(1 for event in block if event.get("type") == "turn_start"),
            tool_calls=sum(
                1 for event in block if event.get("type") == "tool_execution_start"
            ),
            self_test_calls=sum(
                1
                for event in block
                if event.get("type") == "tool_execution_start"
                and event.get("toolName") == "run_self_test"
            ),
            self_test_outcome=outcome,
        )
        for step_id, block, outcome in zip(declared, blocks, outcomes, strict=True)
    )
    return PhaseLedger("measured", None, cells)


def ledger_from_baseline(
    transcript_text: str,
    session_record: Mapping[str, object] | None,
) -> PhaseLedger:
    """Attribute a Baseline transcript by each retained event's own
    ``step_id``, with ``session-record.json``'s step list as the declared
    order and the bounds check."""
    if session_record is None:
        return PhaseLedger("absent", "no session record", ())
    steps = session_record.get("steps")
    if not isinstance(steps, list):
        return PhaseLedger("undecidable", "session record has no steps list", ())
    declared: list[str] = []
    for step in steps:
        if not isinstance(step, Mapping) or not isinstance(step.get("step_id"), str):
            return PhaseLedger("undecidable", "a session step has no step_id", ())
        declared.append(step["step_id"])
    turns = dict.fromkeys(declared, 0)
    tool_calls = dict.fromkeys(declared, 0)
    for line in transcript_text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return PhaseLedger("undecidable", "an unparseable transcript line", ())
        if not isinstance(event, Mapping):
            return PhaseLedger("undecidable", "a non-object transcript line", ())
        if event.get("type") != "event":
            continue
        step_id = event.get("step_id")
        if not isinstance(step_id, str):
            return PhaseLedger("undecidable", "an event carried no step_id", ())
        if step_id not in turns:
            return PhaseLedger(
                "undecidable",
                f"an event's step_id {step_id!r} is outside the record's steps",
                (),
            )
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            return PhaseLedger("undecidable", "an event carried no payload", ())
        if payload.get("type") == "turn_start":
            turns[step_id] += 1
        elif payload.get("type") == "tool_execution_start":
            tool_calls[step_id] += 1
    cells = tuple(
        PhaseCounts(step_id, turns[step_id], tool_calls[step_id], None, None)
        for step_id in declared
    )
    return PhaseLedger("measured", None, cells)
