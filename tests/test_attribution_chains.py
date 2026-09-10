"""HP5.4 -- three chains, run for real against the route.

Nothing here is scripted at the ledger level: each chain runs through
``run_phases`` with an observer snapshotting a real temporary directory, and
the ledger is computed from what the observer saw. Default tier -- files are
written directly and nothing spawns.

The mixed chain is the one that matters. A report that always names the
implementer satisfies the delivered chain, and one that always names the
orchestrator satisfies the seed-221 chain; only the third separates a working
detector from a coin-flip (``BRIEF.md`` invariant 5).
"""

from pathlib import Path

from satyrn_evals.attribution import Snapshot, attribute, snapshot
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import HandoffPacket
from satyrn_evals.route import (
    ROUTE_SCENARIO,
    BoundaryEvent,
    ImplementerResult,
    run_phases,
    scripted_implementer,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}
STEPS = list(ROUTE_SCENARIO)


def _grade_pass(step_id: str, workspace: Path) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def _observer(workspace: Path, records: list[tuple[str, str, Snapshot]]):
    def observe(event: BoundaryEvent) -> None:
        records.append((event.step_id, event.boundary, snapshot(workspace)))

    return observe


def _run(workspace: Path, implementer, orchestrator=None):
    """Run the chain, letting an optional orchestrator act between phases.

    The orchestrator's writes land after a phase's ``after_handoff`` and
    before the next ``before_handoff``, which is exactly the window the
    ledger attributes to it -- so the fixture does not get to choose the
    answer, the ordering does.
    """
    records: list[tuple[str, str, Snapshot]] = []
    observe = _observer(workspace, records)

    def watched(event: BoundaryEvent) -> None:
        observe(event)
        if orchestrator is not None and event.boundary == "after_handoff":
            orchestrator(event.step_id, workspace)
            # The orchestrator acted after its window opened; the window
            # closes at the next boundary, which the route emits.

    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        workspace, _grade_pass, base_revision="3e6607e533792ab0",
        observer=watched, **BUDGETS,
    )
    reported = {d.step_id: d.result.changed_files for d in decisions}
    return decisions, attribute(records, reported)


def _silent(packet: HandoffPacket) -> ImplementerResult:
    """The seed-221 implementer: reports a refusal-free delivery of nothing.

    It cannot report ``delivered`` with no changed files -- ``ImplementerResult``
    refuses that -- so it names the file the orchestrator will write, which is
    the more dangerous shape anyway: a claim with no work behind it.
    """
    return ImplementerResult(
        changed_files=("app.py",), reported_outcome="delivered", message=None
    )


def test_a_delivered_chain_attributes_every_mutation_to_the_implementer(
    tmp_path: Path,
) -> None:
    _, ledger = _run(tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path))
    assert ledger.unobserved_phases == ()
    assert ledger.orchestrator_mutations == 0
    assert ledger.implementer_mutations > 0
    for phase in ledger.phases:
        assert phase.orchestrator == ()
        assert phase.implementer


def test_a_seed_221_chain_reports_zero_implementer_mutations(
    tmp_path: Path,
) -> None:
    """The incident, detected rather than passed over: three phases accepted,
    and not one of them changed a file inside its own window."""
    written: list[str] = []

    def orchestrator(step_id: str, workspace: Path) -> None:
        (workspace / "app.py").write_text(f"# {step_id}\n")
        written.append(step_id)

    decisions, ledger = _run(tmp_path, _silent, orchestrator)
    assert all(d.accepted for d in decisions)  # the chain passes, as it did
    assert written == STEPS
    assert ledger.unobserved_phases == ()
    assert ledger.implementer_mutations == 0
    assert ledger.orchestrator_mutations > 0


def test_a_mixed_chain_splits_per_phase(tmp_path: Path) -> None:
    """Phase 1 is delivered; phase 2's implementer under-delivers and the
    orchestrator repairs it; phase 3 is delivered again."""
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

    _, ledger = _run(tmp_path, implementer, orchestrator)
    first, second, third = ledger.phases
    assert first.implementer and first.orchestrator == ()
    assert second.implementer == ()
    assert [m.path for m in second.orchestrator] == ["models.py"]
    assert third.implementer and third.orchestrator == ()


def test_the_scripted_implementer_is_not_consumed_by_the_silent_phase(
    tmp_path: Path,
) -> None:
    """The mixed fixture skips one scripted phase, so phase 3 writes phase
    2's files. Recorded rather than hidden: the split is what is under test,
    and the file contents are not."""
    scripted = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    calls: list[str] = []

    def implementer(packet: HandoffPacket) -> ImplementerResult:
        calls.append("call")
        if len(calls) == 2:
            return _silent(packet)
        return scripted(packet)

    _run(tmp_path, implementer, lambda step_id, ws: None)
    assert len(calls) == 3
