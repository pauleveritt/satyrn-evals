"""HP6 -- the chain retained and re-scorable.

Default tier throughout: the fake implementer writes files directly and
nothing spawns. The in-process seam is what every test here drives; the
``redacts``-applied half of HP6.3 needs the executable seam and is asserted
separately in `tests/integration/test_hp6_chain_record.py`, over a real
subprocess rather than the pure `declaration_ledger` function this file
exercises.
"""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from satyrn_evals.attribution import Mutation, Snapshot, attribute, snapshot
from satyrn_evals.chain_record import (
    CHAIN_RECORD_VERSION,
    AppliedState,
    ChainRecord,
    PhaseRecord,
    build_chain_record,
    chain_record_from_dict,
    chain_record_to_dict,
    check_chain,
    decisions_from_record,
    declaration_ledger,
    load_chain_record,
    run_and_record_chain,
    write_chain_record,
)
from satyrn_evals.errors import ChainRecordError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import HandoffPacket, build_packet
from satyrn_evals.route import (
    ROUTE_SCENARIO,
    BoundaryEvent,
    ImplementerResult,
    SelfTestOutcome,
    is_executable_seam,
    run_phases,
    scripted_implementer,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}
REVISION = "3e6607e533792ab0"
STEPS = list(ROUTE_SCENARIO)
GOLDEN = Path(__file__).parent / "data" / "hp6-golden-chain-record.json"


def _grade_pass(step_id: str, workspace: Path) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def _run_chain(workspace: Path, implementer, grader=_grade_pass, orchestrator=None):
    """Run one chain for real and return everything HP6 retains from it."""
    events: list[BoundaryEvent] = []
    records: list[tuple[str, str, Snapshot]] = []

    def observe(event: BoundaryEvent) -> None:
        events.append(event)
        records.append((event.step_id, event.boundary, snapshot(workspace)))
        if orchestrator is not None and event.boundary == "after_handoff":
            orchestrator(event.step_id, workspace)

    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        workspace, grader, base_revision=REVISION, observer=observe, **BUDGETS,
    )
    reported = {d.step_id: d.result.changed_files for d in decisions}
    ledger = attribute(records, reported)
    return decisions, events, ledger


def _delivered_record(workspace: Path) -> ChainRecord:
    decisions, events, ledger = _run_chain(
        workspace, scripted_implementer(ROUTE_SCENARIO, workspace)
    )
    return build_chain_record(decisions, events, ledger, executable_seam=False)


def _serialize(record: ChainRecord) -> str:
    return json.dumps(chain_record_to_dict(record), indent=2, sort_keys=True) + "\n"


# --- HP6.2: the chain record data contract ----------------------------------


def test_the_golden_chain_record_is_byte_identical(tmp_path: Path) -> None:
    assert _serialize(_delivered_record(tmp_path)) == GOLDEN.read_text()


def test_the_golden_chain_record_round_trips() -> None:
    loaded = chain_record_from_dict(json.loads(GOLDEN.read_text()))
    assert chain_record_to_dict(loaded) == json.loads(GOLDEN.read_text())


def test_a_record_written_and_reloaded_equals_the_original(
    tmp_path: Path,
) -> None:
    record = _delivered_record(tmp_path / "run")
    path = tmp_path / "chain.json"
    write_chain_record(path, record)
    assert load_chain_record(path) == record


def test_a_truncated_document_is_refused() -> None:
    data = json.loads(GOLDEN.read_text())
    del data["phases"]
    with pytest.raises(ChainRecordError, match="missing phases"):
        chain_record_from_dict(data)


def test_a_document_with_a_future_version_is_refused() -> None:
    data = json.loads(GOLDEN.read_text())
    data["version"] = CHAIN_RECORD_VERSION + 1
    with pytest.raises(ChainRecordError, match="version"):
        chain_record_from_dict(data)


def test_the_well_formed_sibling_loads() -> None:
    """The sibling of both refusals above: an untouched document loads."""
    data = json.loads(GOLDEN.read_text())
    assert chain_record_from_dict(data).version == CHAIN_RECORD_VERSION


# --- HP6.3: the declared-and-not-applied ledger ------------------------------


def _packet(step_id: str) -> HandoffPacket:
    return build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), step_id,
        base_revision=REVISION, **BUDGETS,
    )


def test_offline_declares_three_fields_regardless_of_observation() -> None:
    packet = _packet("phase-1-home")
    ledger = declaration_ledger(
        executable_seam=False, packet=packet, implementer_mutations=()
    )
    for name in ("turn_budget", "tool_call_budget", "base_revision"):
        assert ledger[name] is AppliedState.DECLARED_NOT_APPLIED


def test_self_test_command_is_declared_not_applied_unless_the_harness_ran_it() -> None:
    """The sibling of `redacts`'s seam-derived value: this one is driven by
    whether the harness reports it actually ran the command, not by which
    seam a chain used."""
    packet = _packet("phase-1-home")
    assert (
        declaration_ledger(
            executable_seam=False, packet=packet, implementer_mutations=()
        )["self_test_command"]
        is AppliedState.DECLARED_NOT_APPLIED
    )
    assert (
        declaration_ledger(
            executable_seam=False,
            packet=packet,
            implementer_mutations=(),
            self_test_ran=True,
        )["self_test_command"]
        is AppliedState.APPLIED
    )


def test_redacts_is_declared_not_applied_in_process_and_applied_on_the_executable_seam() -> None:
    """One field, both values, from the seam alone -- the sibling that proves
    the ledger reads the runtime and not a constant."""
    packet = _packet("phase-1-home")
    assert (
        declaration_ledger(
            executable_seam=False, packet=packet, implementer_mutations=()
        )["redacts"]
        is AppliedState.DECLARED_NOT_APPLIED
    )
    assert (
        declaration_ledger(
            executable_seam=True, packet=packet, implementer_mutations=()
        )["redacts"]
        is AppliedState.APPLIED
    )


def test_writable_paths_is_unknown_when_the_implementer_window_is_unobserved() -> None:
    packet = _packet("phase-1-home")
    ledger = declaration_ledger(
        executable_seam=False, packet=packet, implementer_mutations=None
    )
    assert ledger["writable_paths"] is AppliedState.UNKNOWN


def test_writable_paths_is_observed_compliant_when_every_mutation_admits() -> None:
    """Not `APPLIED`: compliance is not enforcement, and nothing here can
    tell "nothing tried to leave scope" apart from "something stopped it"."""
    packet = _packet("phase-1-home")
    ledger = declaration_ledger(
        executable_seam=False,
        packet=packet,
        implementer_mutations=(Mutation("app.py", "created"),),
    )
    assert ledger["writable_paths"] is AppliedState.OBSERVED_COMPLIANT


def test_writable_paths_is_declared_not_applied_when_a_mutation_is_out_of_scope() -> None:
    """The sibling that proves the ledger reads the run, not a fixture's own
    self-discipline: `scripted_implementer` happens to enforce its own scope,
    but this checks what the ledger does when an implementer does not."""
    packet = _packet("phase-1-home")
    ledger = declaration_ledger(
        executable_seam=False,
        packet=packet,
        implementer_mutations=(Mutation("static/app.css", "created"),),
    )
    assert ledger["writable_paths"] is AppliedState.DECLARED_NOT_APPLIED


def test_a_built_record_carries_the_offline_ledger_on_every_phase(
    tmp_path: Path,
) -> None:
    record = _delivered_record(tmp_path)
    for phase in record.phases:
        assert phase.declaration_ledger["redacts"] is AppliedState.DECLARED_NOT_APPLIED
        # scripted_implementer enforces its own scope, so every observed
        # mutation admits -- observed compliant, not "applied": nothing here
        # can credit the fixture's own self-discipline as route enforcement.
        assert phase.declaration_ledger["writable_paths"] is AppliedState.OBSERVED_COMPLIANT


def test_an_out_of_scope_mutation_is_a_check_chain_finding(tmp_path: Path) -> None:
    """The observation that drives `declaration_ledger` also drives a
    finding: a scope violation must not require reading the ledger by hand."""

    def sloppy(packet: HandoffPacket) -> ImplementerResult:
        (tmp_path / "static").mkdir(exist_ok=True)
        (tmp_path / "static" / "app.css").write_text("body {}")
        return ImplementerResult(
            changed_files=("static/app.css",),
            reported_outcome="delivered",
            message=None,
        )

    decisions, events, ledger = _run_chain(tmp_path, sloppy)
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    findings = check_chain(record)
    assert len(findings) == 1
    assert findings[0].step_id == STEPS[0]
    assert "outside the packet's declared writable_paths" in findings[0].reason


# --- self-test evidence: the harness runs self_test_command -----------------


def test_a_built_record_carries_no_self_test_outcome(tmp_path: Path) -> None:
    """`build_chain_record` has no workspace to read one from -- the same
    shape `candidate_snapshot_path` already uses for the same reason."""
    record = _delivered_record(tmp_path)
    for phase in record.phases:
        assert phase.self_test_outcome is None


def test_a_phase_record_with_a_self_test_outcome_round_trips() -> None:
    outcome = SelfTestOutcome(
        command=("uv", "run", "pytest"),
        ran=True,
        exit_code=1,
        output="1 failed\n",
        reason=None,
        duration_seconds=2.0,
    )
    packet = _packet("phase-1-home")
    record = ChainRecord(
        version=CHAIN_RECORD_VERSION,
        phases=(
            PhaseRecord(
                step_id="phase-1-home",
                packet=packet,
                result=ImplementerResult(
                    changed_files=("app.py",),
                    reported_outcome="delivered",
                    message=None,
                ),
                accepted=True,
                reason="scripted pass",
                implementer_mutations=(Mutation("app.py", "created"),),
                orchestrator_mutations=(),
                declaration_ledger=declaration_ledger(
                    executable_seam=True,
                    packet=packet,
                    implementer_mutations=(Mutation("app.py", "created"),),
                    self_test_ran=True,
                ),
                self_test_outcome=outcome,
            ),
        ),
        final_decision=None,
    )
    data = chain_record_to_dict(record)
    assert data["phases"][0]["self_test_outcome"]["exit_code"] == 1
    assert chain_record_from_dict(data) == record


# --- HP6.4: cost per role, null when unmeasured ------------------------------


def test_an_offline_chain_reports_null_cost_for_both_roles(tmp_path: Path) -> None:
    record = _delivered_record(tmp_path)
    for phase in record.phases:
        assert phase.implementer_cost is None
        assert phase.orchestrator_cost is None


def test_a_chain_fed_measured_costs_reports_them_separately(tmp_path: Path) -> None:
    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path)
    )
    costs = {STEPS[0]: (1.5, 0.5), STEPS[1]: (2.0, None)}
    record = build_chain_record(
        decisions, events, ledger, executable_seam=False, costs=costs
    )
    first, second, third = record.phases
    assert first.implementer_cost == 1.5
    assert first.orchestrator_cost == 0.5
    assert second.implementer_cost == 2.0
    assert second.orchestrator_cost is None
    assert third.implementer_cost is None and third.orchestrator_cost is None
    # Never summed: nothing on `PhaseRecord` combines the two into a total,
    # so there is no field a summed value could even be read from.
    assert not hasattr(first, "total_cost") and not hasattr(first, "cost")


@pytest.mark.parametrize("costs", [{"implementer": 0}, {"orchestrator": 0}])
def test_a_zero_cost_is_refused_as_a_stand_in_for_unmeasured(
    tmp_path: Path, costs: dict[str, int]
) -> None:
    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path)
    )
    pair = (costs.get("implementer"), costs.get("orchestrator"))
    with pytest.raises(ChainRecordError, match="not a stand-in for unmeasured"):
        build_chain_record(
            decisions, events, ledger, executable_seam=False,
            costs={STEPS[0]: pair},
        )


def test_a_negative_cost_is_refused(tmp_path: Path) -> None:
    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path)
    )
    with pytest.raises(ChainRecordError, match="not a stand-in for unmeasured"):
        build_chain_record(
            decisions, events, ledger, executable_seam=False,
            costs={STEPS[0]: (-1.0, None)},
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_cost_is_refused(tmp_path: Path, value: float) -> None:
    """A NaN cost is unmeasured wearing a number: `value <= 0` alone lets it
    through, since every comparison against NaN is False."""
    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path)
    )
    with pytest.raises(ChainRecordError, match="finite"):
        build_chain_record(
            decisions, events, ledger, executable_seam=False,
            costs={STEPS[0]: (value, None)},
        )


def test_a_nan_cost_cannot_be_written_even_if_construction_is_bypassed(
    tmp_path: Path,
) -> None:
    """Defense in depth: `write_chain_record` refuses a non-finite float on
    its own, in case a future caller ever reaches a `PhaseRecord` carrying
    one some other way than `PhaseRecord.__init__` -- which is the only path
    `__post_init__` actually guards. ``object.__setattr__`` bypasses a frozen
    dataclass's own immutability the same way, to reach that state directly
    rather than assume it is unreachable."""
    record = _delivered_record(tmp_path)
    object.__setattr__(record.phases[0], "implementer_cost", float("nan"))
    with pytest.raises(ValueError, match="not JSON compliant|NaN"):
        write_chain_record(tmp_path / "chain.json", record)


# --- HP6.5: orchestrator fallback, labelled from observation -----------------


def _silent(packet: HandoffPacket) -> ImplementerResult:
    return ImplementerResult(
        changed_files=("app.py",), reported_outcome="delivered", message=None
    )


def test_the_mixed_chain_labels_exactly_its_middle_phase(tmp_path: Path) -> None:
    """Phase 1 delivered, phase 2 under-delivers and the orchestrator
    repairs it, phase 3 delivered again -- HP5's mixed-chain fixture."""
    scripted = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    calls: list[str] = []

    def implementer(packet: HandoffPacket) -> ImplementerResult:
        calls.append("call")
        if len(calls) == 2:
            return _silent(packet)
        return scripted(packet)

    def orchestrator(step_id: str, workspace: Path) -> None:
        if step_id == STEPS[1]:
            (workspace / "models.py").write_text("# repaired by orchestrator\n")

    decisions, events, ledger = _run_chain(tmp_path, implementer, orchestrator=orchestrator)
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    first, second, third = record.phases
    assert first.fallback is False
    assert second.fallback is True
    assert third.fallback is False


def test_the_all_delivered_chain_labels_no_phase(tmp_path: Path) -> None:
    record = _delivered_record(tmp_path)
    assert all(not phase.fallback for phase in record.phases)


# --- HP6.6: the chain check ---------------------------------------------


def test_a_clean_chain_returns_no_findings(tmp_path: Path) -> None:
    assert check_chain(_delivered_record(tmp_path)) == ()


def test_a_missing_implementer_window_is_a_finding_naming_the_step(
    tmp_path: Path,
) -> None:
    record = _delivered_record(tmp_path)
    phases = list(record.phases)
    phases[1] = replace(phases[1], implementer_mutations=None)
    tampered = replace(record, phases=tuple(phases))
    findings = check_chain(tampered)
    assert len(findings) == 1
    assert findings[0].step_id == STEPS[1]
    assert "never observed" in findings[0].reason


def test_an_observed_zero_implementer_mutations_is_not_a_finding(
    tmp_path: Path,
) -> None:
    """The pair that is the whole point of the slice: absent and
    observed-zero must not land on the same verdict (the seed-221 chain)."""
    written: list[str] = []

    def orchestrator(step_id: str, workspace: Path) -> None:
        (workspace / "app.py").write_text(f"# {step_id}\n")
        written.append(step_id)

    decisions, events, ledger = _run_chain(tmp_path, _silent, orchestrator=orchestrator)
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    assert all(phase.implementer_mutations == () for phase in record.phases)
    assert check_chain(record) == ()


def test_a_disagreeing_final_decision_is_a_finding(tmp_path: Path) -> None:
    record = _delivered_record(tmp_path)
    tampered_final = replace(record.final_decision, accepted=False)
    tampered = replace(record, final_decision=tampered_final)
    findings = check_chain(tampered)
    assert len(findings) == 1
    assert findings[0].step_id == STEPS[-1]
    assert "disagrees" in findings[0].reason


# --- HP6.7: recomputation, end to end -----------------------------------


def test_recomputation_matches_a_fully_delivered_chain(tmp_path: Path) -> None:
    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path)
    )
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    assert decisions_from_record(record) == decisions


def test_recomputation_matches_a_chain_stopped_by_an_implementer_refusal(
    tmp_path: Path,
) -> None:
    def refuser(packet: HandoffPacket) -> ImplementerResult:
        return ImplementerResult(
            changed_files=(), reported_outcome="refused", message="cannot"
        )

    decisions, events, ledger = _run_chain(tmp_path, refuser)
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    assert len(decisions) == 1
    assert decisions_from_record(record) == decisions


def test_a_chain_stopped_by_an_implementer_crash_still_retains_something(
    tmp_path: Path,
) -> None:
    """The fourth exit path: nothing in the HP6 plan names a crash, and
    nothing here retains it either if `run_phases` simply unwound the stack.
    A `ChainRecord` still builds from whatever the run produced before the
    crash closed the chain."""

    def crasher(packet: HandoffPacket) -> ImplementerResult:
        raise RuntimeError("worker died")

    decisions, events, ledger = _run_chain(tmp_path, crasher)
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    assert len(record.phases) == 1
    assert record.phases[0].accepted is False
    assert "crashed" in record.phases[0].reason
    assert decisions_from_record(record) == decisions
    assert check_chain(record) == ()


def test_recomputation_matches_a_chain_stopped_by_a_grader_rejection(
    tmp_path: Path,
) -> None:
    def grader(step_id: str, workspace: Path) -> tuple[str, str]:
        if step_id == STEPS[1]:
            return "fail", "scripted fail"
        return "pass", "scripted pass"

    decisions, events, ledger = _run_chain(
        tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path), grader
    )
    record = build_chain_record(decisions, events, ledger, executable_seam=False)
    assert len(decisions) == 2
    assert not decisions[-1].accepted
    assert decisions_from_record(record) == decisions


# --- run_and_record_chain: HP2/HP5/HP6 composed, and actually written -------


def test_run_and_record_chain_writes_the_record_before_returning(
    tmp_path: Path,
) -> None:
    """The whole point of the function: a caller that never reads the return
    value still gets a durable record, because it is on disk before this
    function's `return` executes."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"

    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
        _grade_pass, output,
        base_revision=REVISION, **BUDGETS,
    )
    assert output.is_file()
    assert load_chain_record(output) == record
    assert all(phase.accepted for phase in record.phases)


def test_run_and_record_chain_derives_the_seam_rather_than_trusting_a_flag(
    tmp_path: Path,
) -> None:
    """No `executable_seam` parameter exists to lie to: it is read off the
    implementer callable itself, the same way `is_executable_seam` proves."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    implementer = scripted_implementer(ROUTE_SCENARIO, workspace)
    assert is_executable_seam(implementer) is False

    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        workspace, _grade_pass, tmp_path / "chain.json",
        base_revision=REVISION, **BUDGETS,
    )
    for phase in record.phases:
        assert phase.declaration_ledger["redacts"] is AppliedState.DECLARED_NOT_APPLIED


def test_run_and_record_chain_retains_a_rejected_chain_too(tmp_path: Path) -> None:
    def grader(step_id: str, workspace: Path) -> tuple[str, str]:
        if step_id == STEPS[1]:
            return "fail", "scripted fail"
        return "pass", "scripted pass"

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"
    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
        grader, output,
        base_revision=REVISION, **BUDGETS,
    )
    assert len(record.phases) == 2
    assert not record.phases[-1].accepted
    assert load_chain_record(output) == record


def test_a_grader_crash_on_phase_two_still_leaves_phase_one_retained(
    tmp_path: Path,
) -> None:
    """The exact scenario Sol reproduced against the prior version: phase 1
    passes, phase 2's grader raises. Preserve-before-judging means phase 1's
    already-graded decision, and phase 2's candidate, both survive on disk
    -- not nothing, which is what a whole-chain-then-write design leaves."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"

    def grader(step_id: str, ws: Path) -> tuple[str, str]:
        if step_id == STEPS[1]:
            raise RuntimeError("grader exploded")
        return "pass", "scripted pass"

    with pytest.raises(RuntimeError, match="grader exploded"):
        run_and_record_chain(
            TASK, load_manifest(TASK), load_session_spec(TASK),
            scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
            grader, output,
            base_revision=REVISION, **BUDGETS,
        )

    assert output.is_file(), "nothing was persisted before the crash propagated"
    record = load_chain_record(output)
    assert [p.step_id for p in record.phases] == [STEPS[0], STEPS[1]]

    first, second = record.phases
    assert first.graded and first.accepted is True
    assert first.reason == "scripted pass"

    assert not second.graded
    assert second.accepted is None and second.reason is None
    assert second.result.reported_outcome == "delivered"  # the implementer DID run
    assert second.candidate_snapshot_path is not None  # candidate evidence survived

    findings = {f.step_id: f.reason for f in check_chain(record)}
    assert findings[STEPS[1]] == "phase candidate persisted but not yet graded"


def test_an_implementer_crash_on_phase_two_leaves_phase_one_graded_and_retained(
    tmp_path: Path,
) -> None:
    """The sibling failure mode: the implementer itself crashes (HP6's own
    Fix 5 in route.py). Unlike a grader crash, `run_phases` converts this
    into a refused decision and returns normally -- no exception reaches
    `run_and_record_chain` at all, so both phases end up graded."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"
    scripted = scripted_implementer(ROUTE_SCENARIO, workspace)
    calls: list[str] = []

    def implementer(packet: HandoffPacket) -> ImplementerResult:
        calls.append("call")
        if len(calls) == 2:
            raise RuntimeError("implementer died")
        return scripted(packet)

    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        workspace, _grade_pass, output,
        base_revision=REVISION, **BUDGETS,
    )
    assert [p.step_id for p in record.phases] == [STEPS[0], STEPS[1]]
    first, second = record.phases
    assert first.graded and first.accepted is True
    assert second.graded and second.accepted is False
    assert "crashed" in second.reason
    assert load_chain_record(output) == record


# --- P1#2: candidate content, offline regrading, missing-evidence findings --


def test_candidate_snapshot_holds_the_actual_file_content(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"
    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
        _grade_pass, output,
        base_revision=REVISION, **BUDGETS,
    )
    first = record.phases[0]
    assert first.candidate_snapshot_path is not None
    content = json.loads(Path(first.candidate_snapshot_path).read_text())
    assert content["app.py"] == ROUTE_SCENARIO[STEPS[0]]["app.py"]
    # digest actually matches the file on disk -- not a placeholder
    digest = hashlib.sha256(
        Path(first.candidate_snapshot_path).read_bytes()
    ).hexdigest()
    assert digest == first.candidate_snapshot_digest


def test_a_missing_candidate_snapshot_is_a_check_chain_finding_when_the_record_retains_them(
    tmp_path: Path,
) -> None:
    """The "missing worker evidence" rejection: a record that demonstrably
    captures candidate snapshots elsewhere, tampered so one phase lost
    its own, is flagged -- the retention gap is not silently accepted."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"
    record = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
        _grade_pass, output,
        base_revision=REVISION, **BUDGETS,
    )
    phases = list(record.phases)
    phases[1] = replace(
        phases[1], candidate_snapshot_path=None, candidate_snapshot_digest=None
    )
    tampered = replace(record, phases=tuple(phases))
    findings = {f.step_id: f.reason for f in check_chain(tampered)}
    assert findings[STEPS[1]] == "phase has retained mutations but no candidate snapshot"


def test_build_chain_record_alone_is_not_held_to_the_candidate_standard(
    tmp_path: Path,
) -> None:
    """The sibling in the other direction: `build_chain_record` never
    captures snapshots (it has no workspace to read from), and a record
    built only through it is not penalized for a standard it never claimed."""
    record = _delivered_record(tmp_path)
    assert all(p.candidate_snapshot_path is None for p in record.phases)
    assert check_chain(record) == ()


def test_offline_regrading_from_only_the_retained_candidate_snapshots(
    tmp_path: Path,
) -> None:
    """Reuses the same `PhaseGrader` shape the original run used, but calls
    it against a workspace rebuilt from nothing but the persisted record's
    `candidate_snapshot_path` files -- no access to the original workspace,
    no implementer, no re-run. If retention were insufficient, this would
    have nothing correct to reconstruct from."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    output = tmp_path / "chain.json"

    # A grader that inspects real file content, not a scripted verdict --
    # otherwise "regrading" would trivially agree with itself.
    def content_grader(step_id: str, ws: Path) -> tuple[str, str]:
        app_py = (ws / "app.py").read_text() if (ws / "app.py").is_file() else ""
        phase_index = STEPS.index(step_id)
        expected_marker = f"# phase-{phase_index + 1}"
        if expected_marker in app_py:
            return "pass", f"{expected_marker} present"
        return "fail", f"{expected_marker} missing"

    original = run_and_record_chain(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, workspace), workspace,
        content_grader, output,
        base_revision=REVISION, **BUDGETS,
    )
    assert all(p.accepted for p in original.phases)

    # "Offline": a fresh load, a fresh directory, no relation to `workspace`.
    reloaded = load_chain_record(output)
    for phase in reloaded.phases:
        assert phase.candidate_snapshot_path is not None
        reconstructed = tmp_path / f"regrade-{phase.step_id}"
        reconstructed.mkdir()
        content = json.loads(Path(phase.candidate_snapshot_path).read_text())
        for name, text in content.items():
            path = reconstructed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        verdict, reason = content_grader(phase.step_id, reconstructed)
        assert (verdict == "pass") == phase.accepted, (
            f"offline regrade disagreed with the retained decision for "
            f"{phase.step_id}: {reason!r}"
        )
