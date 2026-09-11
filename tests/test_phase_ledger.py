"""The per-phase ledger: one shape over two retained layouts.

Default tier throughout -- synthetic transcripts built in-process, no
filesystem, no subprocess.
"""

import json

from satyrn_evals.phase_ledger import (
    ledger_from_baseline,
    ledger_from_engine,
)


def _engine_text(phases: int, *, self_tests: int = 0) -> str:
    lines: list[str] = []
    for i in range(phases):
        lines.append(json.dumps({"adapter_marker": "turn_start", "index": i}))
        lines.append(json.dumps({"type": "session", "version": 3}))
        lines.append(json.dumps({"type": "turn_start"}))
        lines.append(
            json.dumps({"type": "tool_execution_start", "toolName": "read"})
        )
        for _ in range(self_tests if i == 0 else 0):
            lines.append(
                json.dumps(
                    {"type": "tool_execution_start", "toolName": "run_self_test"}
                )
            )
    return "\n".join(lines) + "\n"


def _chain(step_ids: tuple[str, ...], outcomes: dict[str, object] | None = None):
    outcomes = outcomes or {}
    return {
        "phases": [
            {"step_id": step_id, "self_test_outcome": outcomes.get(step_id)}
            for step_id in step_ids
        ]
    }


PHASES = ("phase-1-home", "phase-2-board", "phase-3-add", "phase-4-resolve-reopen")


def test_engine_splits_positional_sessions_against_declared_phases() -> None:
    ledger = ledger_from_engine(_engine_text(4, self_tests=2), _chain(PHASES))

    assert ledger.state == "measured"
    assert ledger.step_ids == PHASES
    assert [cell.turns for cell in ledger.cells] == [1, 1, 1, 1]
    assert [cell.tool_calls for cell in ledger.cells] == [3, 1, 1, 1]
    assert ledger.cell("phase-1-home").self_test_calls == 2


def test_engine_counts_a_started_call_even_without_its_end() -> None:
    """Engine counts starts; it still does when no end event exists."""
    text = (
        json.dumps({"type": "session", "version": 3}) + "\n"
        + json.dumps({"type": "tool_execution_start", "toolName": "read"}) + "\n"
    )

    ledger = ledger_from_engine(text, _chain(("phase-1-home",)))

    assert ledger.state == "measured"
    assert ledger.cell("phase-1-home").tool_calls == 1


def test_engine_refuses_when_sessions_disagree_with_declared_phases() -> None:
    """The named refusal: a count that does not match its chain is never a
    per-phase number."""
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES[:3]))

    assert ledger.state == "undecidable"
    assert "4 session blocks against 3 declared phases" in (ledger.reason or "")
    assert ledger.cells == ()


def test_engine_is_absent_without_a_chain_record() -> None:
    ledger = ledger_from_engine(_engine_text(4), None)

    assert ledger.state == "absent"
    assert ledger.cells == ()


def test_engine_self_test_outcome_reads_the_chain_not_the_transcript() -> None:
    outcomes = {
        "phase-1-home": {"ran": True, "exit_code": 0},
        "phase-2-board": {"ran": True, "exit_code": 1},
        "phase-3-add": {"ran": False, "exit_code": None},
        "phase-4-resolve-reopen": None,
    }
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES, outcomes))

    assert [cell.self_test_outcome for cell in ledger.cells] == [
        "pass",
        "fail",
        "not_run",
        "unrecorded",
    ]


def test_engine_self_test_outcome_is_unrecorded_when_exit_code_is_missing() -> None:
    """A run without a readable exit code is unknown, never a pass."""
    outcomes = {"phase-1-home": {"ran": True}}  # no exit_code at all
    ledger = ledger_from_engine(_engine_text(4), _chain(PHASES, outcomes))

    assert ledger.cell("phase-1-home").self_test_outcome == "unrecorded"
    assert ledger.cell("phase-2-board").self_test_outcome == "unrecorded"


def test_engine_ignores_an_event_before_the_first_session() -> None:
    """A stray event outside any session block is not attributed to phase 1."""
    stray = json.dumps({"type": "tool_execution_start", "toolName": "bash"})
    text = stray + "\n" + _engine_text(4)

    ledger = ledger_from_engine(text, _chain(PHASES))

    assert ledger.state == "measured"
    assert [cell.tool_calls for cell in ledger.cells] == [1, 1, 1, 1]


def test_engine_refuses_a_chain_phase_without_a_step_id() -> None:
    chain = {"phases": [{"step_id": "phase-1-home"}, {"no_step": True}]}

    ledger = ledger_from_engine(_engine_text(2), chain)

    assert ledger.state == "undecidable"
    assert "no step_id" in (ledger.reason or "")


def _baseline_text(steps: tuple[str, ...], *, omit_step: str | None = None) -> str:
    lines = [json.dumps({"version": 1, "type": "session_started"})]
    for step_id in steps:
        line = {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "kind": "other",
            "payload": {"type": "turn_start"},
        }
        if step_id == omit_step:
            line.pop("step_id")
        lines.append(json.dumps(line))
        lines.append(
            json.dumps(
                {
                    "version": 1,
                    "type": "event",
                    "step_id": step_id,
                    "kind": "tool_start",
                    "payload": {"type": "tool_execution_start"},
                }
            )
        )
    return "\n".join(lines) + "\n"


def _session_record(step_ids: tuple[str, ...]) -> dict[str, object]:
    return {"steps": [{"step_id": step_id} for step_id in step_ids]}


def test_baseline_attributes_by_each_events_own_step_id() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), _session_record(PHASES))

    assert ledger.state == "measured"
    assert [cell.turns for cell in ledger.cells] == [1, 1, 1, 1]
    assert [cell.tool_calls for cell in ledger.cells] == [1, 1, 1, 1]
    assert all(cell.self_test_calls is None for cell in ledger.cells)


def test_baseline_counts_a_started_call_even_without_its_end() -> None:
    """A tool call is a start on both arms: no end event is required."""
    text = "\n".join(
        json.dumps(line)
        for line in (
            {"version": 1, "type": "session_started"},
            {
                "version": 1,
                "type": "event",
                "step_id": "phase-1-home",
                "kind": "tool_start",
                "payload": {"type": "tool_execution_start"},
            },
        )
    ) + "\n"

    ledger = ledger_from_baseline(text, _session_record(("phase-1-home",)))

    assert ledger.state == "measured"
    assert ledger.cell("phase-1-home").tool_calls == 1


def test_baseline_refuses_an_event_missing_its_step_id() -> None:
    """The design's named refusal: a transcript that cannot be attributed is
    undecidable, never a per-phase number."""
    text = _baseline_text(PHASES, omit_step="phase-2-board")

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "step_id" in (ledger.reason or "")
    assert ledger.cells == ()


def test_baseline_refuses_an_event_outside_the_records_steps() -> None:
    text = _baseline_text(PHASES)
    text += json.dumps(
        {
            "version": 1,
            "type": "event",
            "step_id": "phase-9-ghost",
            "payload": {"type": "turn_start"},
        }
    )

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "phase-9-ghost" in (ledger.reason or "")


def test_baseline_refuses_an_unparseable_line() -> None:
    text = _baseline_text(PHASES) + "not json\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "unparseable" in (ledger.reason or "")


def test_baseline_is_absent_without_a_session_record() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), None)

    assert ledger.state == "absent"
    assert ledger.cells == ()


def test_baseline_refuses_a_record_without_steps() -> None:
    ledger = ledger_from_baseline(_baseline_text(PHASES), {"nope": True})

    assert ledger.state == "undecidable"
    assert "steps" in (ledger.reason or "")


def test_baseline_refuses_a_record_step_without_a_step_id() -> None:
    ledger = ledger_from_baseline(
        _baseline_text(PHASES), {"steps": [{"not_step_id": 1}]}
    )

    assert ledger.state == "undecidable"
    assert "no step_id" in (ledger.reason or "")


def test_baseline_refuses_a_non_object_line() -> None:
    text = _baseline_text(PHASES) + "[1, 2]\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "non-object" in (ledger.reason or "")


def test_baseline_refuses_an_event_without_a_payload() -> None:
    text = _baseline_text(PHASES).rstrip("\n") + "\n" + json.dumps(
        {"version": 1, "type": "event", "step_id": "phase-1-home"}
    ) + "\n"

    ledger = ledger_from_baseline(text, _session_record(PHASES))

    assert ledger.state == "undecidable"
    assert "payload" in (ledger.reason or "")
