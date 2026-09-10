"""HP5.2 -- the boundary observer on the route.

The load-bearing test here is the first one: with no observer the route makes
the same decisions it made before HP5, so this slice cannot have altered a
verdict.
"""

from pathlib import Path

import pytest

from satyrn_evals.errors import RouteError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import HandoffPacket
from satyrn_evals.route import (
    ROUTE_SCENARIO,
    Boundary,
    ImplementerResult,
    run_phases,
    scripted_implementer,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}
STEPS = list(ROUTE_SCENARIO)


def _grader(verdicts: dict[str, str]):
    def grade(step_id: str, workspace: Path) -> tuple[str, str]:
        return verdicts[step_id], f"scripted {verdicts[step_id]} for {step_id}"

    return grade


_ALL_PASS = dict.fromkeys(ROUTE_SCENARIO, "pass")


def _run(tmp_path: Path, verdicts, observer=None, implementer=None):
    return run_phases(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        implementer or scripted_implementer(ROUTE_SCENARIO, tmp_path),
        tmp_path,
        _grader(verdicts),
        base_revision="3e6607e533792ab0",
        observer=observer,
        **BUDGETS,
    )


def _recorder() -> tuple[list[tuple[str, str]], object]:
    seen: list[tuple[str, str]] = []

    def observe(step_id: str, boundary: Boundary) -> None:
        seen.append((step_id, boundary))

    return seen, observe


def test_without_an_observer_the_route_is_unchanged(tmp_path: Path) -> None:
    """The whole point of the seam: attribution observes, it never gates."""
    plain = _run(tmp_path / "a", _ALL_PASS)
    seen, observe = _recorder()
    watched = _run(tmp_path / "b", _ALL_PASS, observe)
    assert [(d.step_id, d.accepted, d.reason) for d in plain] == [
        (d.step_id, d.accepted, d.reason) for d in watched
    ]
    assert seen  # and the observer did fire, so the comparison means something


def test_a_full_chain_emits_every_boundary_in_order(tmp_path: Path) -> None:
    seen, observe = _recorder()
    _run(tmp_path, _ALL_PASS, observe)
    expected = [(s, b) for s in STEPS for b in ("before_handoff", "after_handoff")]
    expected.append((STEPS[-1], "chain_end"))
    assert seen == expected


def test_a_rejected_phase_still_closes_its_window_and_ends_the_chain(
    tmp_path: Path,
) -> None:
    """A chain that stops early is when attribution matters most."""
    seen, observe = _recorder()
    _run(tmp_path, {**_ALL_PASS, "phase-2-board": "fail"}, observe)
    assert seen == [
        (STEPS[0], "before_handoff"),
        (STEPS[0], "after_handoff"),
        (STEPS[1], "before_handoff"),
        (STEPS[1], "after_handoff"),
        (STEPS[1], "chain_end"),
    ]


def test_a_refusing_implementer_still_closes_its_window(tmp_path: Path) -> None:
    def refuser(packet: HandoffPacket) -> ImplementerResult:
        return ImplementerResult(
            changed_files=(), reported_outcome="refused", message="cannot"
        )

    seen, observe = _recorder()
    _run(tmp_path, _ALL_PASS, observe, implementer=refuser)
    assert seen == [
        (STEPS[0], "before_handoff"),
        (STEPS[0], "after_handoff"),
        (STEPS[0], "chain_end"),
    ]


def test_after_handoff_fires_before_grading(tmp_path: Path) -> None:
    """The implementer's window must close before the grader can touch the
    workspace, or a grader that writes would be attributed to the worker."""
    order: list[str] = []

    def observe(step_id: str, boundary: Boundary) -> None:
        order.append(f"{boundary}:{step_id}")

    def grade(step_id: str, workspace: Path) -> tuple[str, str]:
        order.append(f"grade:{step_id}")
        return "pass", "ok"

    run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, tmp_path), tmp_path, grade,
        base_revision="3e6607e533792ab0", observer=observe, **BUDGETS,
    )
    first = order.index("after_handoff:phase-1-home")
    assert first < order.index("grade:phase-1-home")


def test_an_observer_that_raises_is_not_swallowed(tmp_path: Path) -> None:
    """A broken observer must fail loudly. A silently dropped boundary would
    surface later as an unobserved window, which reads like a finding about
    the run rather than a bug in the harness."""

    def observe(step_id: str, boundary: Boundary) -> None:
        raise RouteError("observer is broken")

    with pytest.raises(RouteError, match="observer is broken"):
        _run(tmp_path, _ALL_PASS, observe)
