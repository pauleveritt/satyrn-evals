"""HP5.5 -- what the implementer claimed against what its window shows.

Both are retained and the difference is stated. Nothing here decides what a
discrepancy *means*: classifying it would be a pathology detector, which HP5
excludes.
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


def _run(workspace: Path, implementer, orchestrator=None):
    records: list[tuple[str, str, Snapshot]] = []

    def observe(event: BoundaryEvent) -> None:
        records.append((event.step_id, event.boundary, snapshot(workspace)))
        if orchestrator is not None and event.boundary == "after_handoff":
            orchestrator(event.step_id, workspace)

    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), implementer,
        workspace, lambda step_id, ws: ("pass", "ok"),
        base_revision="3e6607e533792ab0", observer=observe, **BUDGETS,
    )
    return attribute(records, {d.step_id: d.result.changed_files for d in decisions})


def test_a_file_claimed_but_not_written_is_recorded_as_claimed_not_made(
    tmp_path: Path,
) -> None:
    def liar(packet: HandoffPacket) -> ImplementerResult:
        return ImplementerResult(
            changed_files=("app.py",), reported_outcome="delivered", message=None
        )

    ledger = _run(tmp_path, liar, lambda step_id, ws: (ws / "app.py").write_text(step_id))
    first = ledger.phases[0]
    assert first.reported == ("app.py",)
    assert first.implementer == ()
    assert first.claimed_not_made == ("app.py",)


def test_a_truthful_implementer_records_no_discrepancy(tmp_path: Path) -> None:
    """The sibling. Without it, a `claimed_not_made` that always returned the
    reported list would pass the test above."""
    ledger = _run(tmp_path, scripted_implementer(ROUTE_SCENARIO, tmp_path))
    for phase in ledger.phases:
        assert phase.claimed_not_made == ()
        assert phase.made_not_claimed == ()


def test_a_file_written_but_not_claimed_is_recorded_too(tmp_path: Path) -> None:
    """The other direction: work the implementer did and did not report."""
    scripted = scripted_implementer(ROUTE_SCENARIO, tmp_path)

    def understater(packet: HandoffPacket) -> ImplementerResult:
        result = scripted(packet)
        return ImplementerResult(
            changed_files=result.changed_files[:1],
            reported_outcome="delivered",
            message=None,
        )

    ledger = _run(tmp_path, understater)
    first = ledger.phases[0]
    assert len(first.reported) == 1
    assert set(first.made_not_claimed) == {
        m.path for m in first.implementer
    } - set(first.reported)
    assert first.made_not_claimed


def test_an_unobserved_window_reports_no_discrepancy_either_way() -> None:
    """With nothing observed there is nothing to compare, and inventing a
    discrepancy from an absent window would be the zero-versus-unobserved
    confusion in a second place."""
    ledger = attribute(
        [("p1", "before_handoff", {})], {"p1": ("app.py",)}
    )
    (phase,) = ledger.phases
    assert phase.implementer is None
    assert phase.claimed_not_made == ()
    assert phase.made_not_claimed == ()
