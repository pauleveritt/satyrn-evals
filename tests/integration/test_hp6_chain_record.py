"""HP6's integration half: the redacts-applied claim, through a real process.

`chain_record.declaration_ledger`'s `redacts` field is `applied` only on the
executable seam, because `assert_projection_is_clean` runs inside
`command_implementer` and nowhere else. `test_chain_record.py` proves the
*function* returns that value for `executable_seam=True`; it does not prove a
record built from a real subprocess run actually carries it. This does.

`executable_seam` is derived with `route.is_executable_seam(implementer)`
here, not hand-asserted -- the exact gap an earlier version of this file had:
it passed `executable_seam=True` itself, so it could never have caught a
caller that lied about which seam ran. Deriving it from the same
`command_implementer` object the run actually used is what a real driver
must do too (see `chain_record.run_and_record_chain`).
"""

import dataclasses
import sys
from pathlib import Path

import pytest

from satyrn_evals.attribution import Snapshot, attribute, snapshot
from satyrn_evals.chain_record import (
    AppliedState,
    build_chain_record,
    check_chain,
    run_and_record_chain,
)
from satyrn_evals.manifest import load_manifest
from satyrn_evals.route import (
    BoundaryEvent,
    command_implementer,
    is_executable_seam,
    run_phases,
)
from satyrn_evals.session_manifest import load_session_spec

pytestmark = pytest.mark.integration

TASK = Path(__file__).parent.parent.parent / "src/satyrn_evals/tasks/agentclinic-session-phased"
FAKE = Path(__file__).parent / "fake_implementer.py"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}


def _grade_pass(step_id: str, workspace: Path) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def test_a_record_built_over_the_real_executable_seam_reports_redacts_applied(
    tmp_path: Path,
) -> None:
    events: list[BoundaryEvent] = []
    records: list[tuple[str, str, Snapshot]] = []

    def observe(event: BoundaryEvent) -> None:
        events.append(event)
        records.append((event.step_id, event.boundary, snapshot(tmp_path)))

    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        tmp_path, _grade_pass, base_revision="3e6607e533792ab0",
        observer=observe, **BUDGETS,
    )
    reported = {d.step_id: d.result.changed_files for d in decisions}
    ledger = attribute(records, reported)
    assert is_executable_seam(implementer) is True
    record = build_chain_record(
        decisions, events, ledger, executable_seam=is_executable_seam(implementer)
    )

    assert all(d.accepted for d in decisions)
    for phase in record.phases:
        assert phase.declaration_ledger["redacts"] is AppliedState.APPLIED
        # Observed compliant, not applied: the fake executable enforces
        # scope against itself, but nothing here can take credit for a
        # fixture's own self-discipline as route enforcement.
        assert (
            phase.declaration_ledger["writable_paths"]
            is AppliedState.OBSERVED_COMPLIANT
        )
    assert check_chain(record) == ()


def test_the_same_run_in_process_reports_redacts_declared_not_applied(
    tmp_path: Path,
) -> None:
    """The sibling in the same file: one task, both values, from the seam
    alone -- proven end to end, not only on the pure `declaration_ledger`
    function `test_chain_record.py` already covers."""
    from satyrn_evals.route import ROUTE_SCENARIO, scripted_implementer

    events: list[BoundaryEvent] = []
    records: list[tuple[str, str, Snapshot]] = []

    def observe(event: BoundaryEvent) -> None:
        events.append(event)
        records.append((event.step_id, event.boundary, snapshot(tmp_path)))

    implementer = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        tmp_path, _grade_pass, base_revision="3e6607e533792ab0",
        observer=observe, **BUDGETS,
    )
    reported = {d.step_id: d.result.changed_files for d in decisions}
    ledger = attribute(records, reported)
    assert is_executable_seam(implementer) is False
    record = build_chain_record(
        decisions, events, ledger, executable_seam=is_executable_seam(implementer)
    )

    for phase in record.phases:
        assert phase.declaration_ledger["redacts"] is AppliedState.DECLARED_NOT_APPLIED


# --- self-test evidence: the harness runs self_test_command -----------------


def test_a_run_and_recorded_chain_retains_a_passing_self_test(
    tmp_path: Path,
) -> None:
    """`run_and_record_chain` is the only place that reads
    `.satyrn-self-test-result.json` back off the workspace --
    `build_chain_record` has no workspace to read one from. Controls
    `self_test_command` directly rather than trusting the real task's own
    (`uv run python -m pytest tests`, not deterministic against an empty
    fixture workspace)."""
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("true",)
    )
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    record = run_and_record_chain(
        TASK, load_manifest(TASK), spec, implementer, tmp_path, _grade_pass,
        tmp_path / "chain.json", base_revision="3e6607e533792ab0", **BUDGETS,
    )
    for phase in record.phases:
        assert phase.self_test_outcome is not None
        assert phase.self_test_outcome.ran is True
        assert phase.self_test_outcome.exit_code == 0
        assert phase.declaration_ledger["self_test_command"] is AppliedState.APPLIED


def test_a_run_and_recorded_chain_retains_a_failing_self_test_without_gating(
    tmp_path: Path,
) -> None:
    """The never-gates proof, end to end: a failing self-test on every
    phase does not stop the chain or flip the grader's own accept
    decision."""
    spec = dataclasses.replace(
        load_session_spec(TASK), self_test_command=("false",)
    )
    implementer = command_implementer([sys.executable, str(FAKE)], tmp_path)
    record = run_and_record_chain(
        TASK, load_manifest(TASK), spec, implementer, tmp_path, _grade_pass,
        tmp_path / "chain.json", base_revision="3e6607e533792ab0", **BUDGETS,
    )
    for phase in record.phases:
        assert phase.self_test_outcome.ran is True
        assert phase.self_test_outcome.exit_code != 0
        assert phase.accepted is True
        assert phase.declaration_ledger["self_test_command"] is AppliedState.APPLIED
