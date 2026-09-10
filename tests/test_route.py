"""HP2 slices 1-4: the implementer result, the fake, and the route.

Everything here is default tier: no model, no network, no subprocess. The
verdicts that need a real oracle live in
``tests/integration/test_hp2_route.py`` -- ``known-good`` and
``known-broken`` differ only by a timezone-naive default factory, so nothing
offline can tell them apart, and a fixture-named verdict asserted here would
be a label on a scripted result.

``ROUTE_SCENARIO`` is shared with that integration test so the in-process
seam and the executable seam cannot drift apart while both stay green.
"""

import dataclasses
import json
from pathlib import Path

import pytest

from satyrn_evals.errors import PacketError, RouteError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import HandoffPacket, build_packet
from satyrn_evals.route import (
    ROUTE_SCENARIO,
    ImplementerResult,
    implementer_result_from_dict,
    implementer_result_to_dict,
    run_phases,
    scripted_implementer,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
GOLDEN = Path(__file__).parent / "data" / "hp2-golden-result.json"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}


def _packet(step_id: str = "phase-1-home") -> HandoffPacket:
    return build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), step_id,
        base_revision="3e6607e533792ab0", **BUDGETS,
    )


# --- HP2.1 the result, and its wire form ------------------------------------


def test_a_delivered_result_with_changes_is_accepted() -> None:
    result = ImplementerResult(
        changed_files=("app.py",), reported_outcome="delivered", message=None
    )
    assert result.changed_files == ("app.py",)


def test_a_delivered_result_with_no_changes_is_refused() -> None:
    """The implementer's own claim is never the verdict. "I delivered" with
    nothing changed is malformed, not a quiet zero."""
    with pytest.raises(RouteError, match="changed_files"):
        ImplementerResult(
            changed_files=(), reported_outcome="delivered", message=None
        )


def test_a_refused_result_may_change_nothing() -> None:
    """The sibling: refusing without writing is legitimate."""
    result = ImplementerResult(
        changed_files=(), reported_outcome="refused", message="out of scope"
    )
    assert result.reported_outcome == "refused"


def test_an_unknown_outcome_is_refused() -> None:
    with pytest.raises(RouteError, match="reported_outcome"):
        ImplementerResult(
            changed_files=("app.py",), reported_outcome="maybe", message=None
        )


def test_the_golden_result_round_trips() -> None:
    data = json.loads(GOLDEN.read_text())
    assert implementer_result_to_dict(implementer_result_from_dict(data)) == data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("changed_files", "app.py"),
        ("changed_files", None),
        ("reported_outcome", ["delivered"]),
        ("message", 3),
        ("version", True),
        ("version", 2),
    ],
)
def test_a_persisted_result_of_the_wrong_shape_is_refused(
    field: str, value: object
) -> None:
    """Shape-checked before conversion, as HP1's loader is: `tuple("app.py")`
    is a well-formed result of six single-character filenames."""
    data = json.loads(GOLDEN.read_text())
    data[field] = value
    with pytest.raises(RouteError, match=field):
        implementer_result_from_dict(data)


def test_a_persisted_result_missing_a_key_fails_as_itself() -> None:
    data = json.loads(GOLDEN.read_text())
    del data["changed_files"]
    with pytest.raises(RouteError, match="missing changed_files"):
        implementer_result_from_dict(data)


# --- HP2.2 the fake implementer ---------------------------------------------


def test_the_fake_writes_the_files_its_phase_declares(tmp_path: Path) -> None:
    implementer = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    result = implementer(_packet("phase-1-home"))
    assert result.reported_outcome == "delivered"
    assert (tmp_path / "app.py").is_file()
    assert set(result.changed_files) == set(ROUTE_SCENARIO["phase-1-home"])


def test_the_fake_refuses_to_write_outside_the_declared_scope(
    tmp_path: Path,
) -> None:
    """An obliging fake would mask a route defect, which is the same failure
    shape as a test that cannot fail."""
    implementer = scripted_implementer({"phase-1-home": {"../escape.py": "x"}}, tmp_path)
    with pytest.raises(RouteError, match="outside the declared scope"):
        implementer(_packet("phase-1-home"))
    assert not (tmp_path.parent / "escape.py").exists()


def test_the_fake_writes_nothing_before_refusing(tmp_path: Path) -> None:
    """The sibling of the refusal: a partial write would leave the workspace
    in a state the route never decided on."""
    implementer = scripted_implementer(
        {"phase-1-home": {"app.py": "ok", "../escape.py": "x"}}, tmp_path
    )
    with pytest.raises(RouteError):
        implementer(_packet("phase-1-home"))
    assert not (tmp_path / "app.py").exists()


# --- HP2.3 and HP2.4 the route ----------------------------------------------


def _grader(verdicts: dict[str, str]):
    def grade(step_id: str, workspace: Path) -> tuple[str, str]:
        assert workspace.is_dir()
        return verdicts[step_id], f"scripted {verdicts[step_id]} for {step_id}"

    return grade


def _run(tmp_path: Path, verdicts: dict[str, str]):
    return run_phases(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        scripted_implementer(ROUTE_SCENARIO, tmp_path),
        tmp_path,
        _grader(verdicts),
        base_revision="3e6607e533792ab0",
        **BUDGETS,
    )


_ALL_PASS = dict.fromkeys(ROUTE_SCENARIO, "pass")


def test_three_phases_run_in_order_and_are_accepted(tmp_path: Path) -> None:
    decisions = _run(tmp_path, _ALL_PASS)
    assert [d.step_id for d in decisions] == list(ROUTE_SCENARIO)
    assert all(d.accepted for d in decisions)
    assert all(d.reason for d in decisions)


def test_a_later_phase_starts_from_the_accepted_predecessors_state(
    tmp_path: Path,
) -> None:
    _run(tmp_path, _ALL_PASS)
    assert (tmp_path / "app.py").is_file()
    assert (tmp_path / "models.py").is_file()
    assert "phase-3" in (tmp_path / "app.py").read_text()
    assert "phase-1" in (tmp_path / "templates" / "base.html").read_text()


def test_a_rejected_phase_stops_the_route(tmp_path: Path) -> None:
    """No partial chain: the rule `WorktreeTransaction` implements properly in
    HP3, held here so the two cycles cannot disagree."""
    decisions = _run(tmp_path, {**_ALL_PASS, "phase-2-board": "fail"})
    assert [d.step_id for d in decisions] == ["phase-1-home", "phase-2-board"]
    assert decisions[-1].accepted is False
    assert "scripted fail" in decisions[-1].reason


def test_the_route_records_a_reason_on_every_decision(tmp_path: Path) -> None:
    for decision in _run(tmp_path, {**_ALL_PASS, "phase-3-add": "fail"}):
        assert decision.reason.strip()


def test_an_implementer_that_refuses_stops_the_route(tmp_path: Path) -> None:
    def refuser(packet: HandoffPacket) -> ImplementerResult:
        return ImplementerResult(
            changed_files=(), reported_outcome="refused", message="cannot"
        )

    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), refuser, tmp_path,
        _grader(_ALL_PASS), base_revision="3e6607e533792ab0", **BUDGETS,
    )
    assert len(decisions) == 1
    assert decisions[0].accepted is False
    assert "refused" in decisions[0].reason


def test_an_implementer_that_crashes_stops_the_route_without_propagating(
    tmp_path: Path,
) -> None:
    """HP6: the live seam's most likely first failure. A crash closes the
    chain the way a refusal does, so the caller still has something to
    retain, rather than losing every decision the run had already made."""

    def crasher(packet: HandoffPacket) -> ImplementerResult:
        raise RuntimeError("subprocess died")

    decisions = run_phases(
        TASK, load_manifest(TASK), load_session_spec(TASK), crasher, tmp_path,
        _grader(_ALL_PASS), base_revision="3e6607e533792ab0", **BUDGETS,
    )
    assert len(decisions) == 1
    assert decisions[0].accepted is False
    assert "crashed" in decisions[0].reason
    assert "subprocess died" in decisions[0].reason
    assert decisions[0].result.reported_outcome == "refused"


def test_a_route_contract_violation_still_propagates_rather_than_being_retained(
    tmp_path: Path,
) -> None:
    """The sibling of the crash test: a broken implementer -- one that
    violates HP2's own contract -- is a bug to surface loudly, not a run
    outcome to fold into a retained decision."""

    def broken(packet: HandoffPacket) -> ImplementerResult:
        raise RouteError("this implementer double is malformed")

    with pytest.raises(RouteError, match="malformed"):
        run_phases(
            TASK, load_manifest(TASK), load_session_spec(TASK), broken, tmp_path,
            _grader(_ALL_PASS), base_revision="3e6607e533792ab0", **BUDGETS,
        )


def test_the_route_grades_rather_than_trusting_the_implementer(
    tmp_path: Path,
) -> None:
    """A delivered result with a failing verdict is a rejection. The claim is
    not the verdict (`BRIEF.md` invariant 2, one layer out)."""
    decisions = _run(tmp_path, {**_ALL_PASS, "phase-1-home": "fail"})
    assert decisions[0].accepted is False


def test_a_packet_that_cannot_be_built_stops_the_route(tmp_path: Path) -> None:
    spec = load_session_spec(TASK)
    stripped = dataclasses.replace(
        spec, steps=tuple(dataclasses.replace(s, facts=()) for s in spec.steps)
    )
    with pytest.raises(PacketError, match="facts"):
        run_phases(
            TASK, load_manifest(TASK), stripped,
            scripted_implementer(ROUTE_SCENARIO, tmp_path), tmp_path,
            _grader(_ALL_PASS), base_revision="3e6607e533792ab0", **BUDGETS,
        )


def test_the_fake_delivers_a_different_phase_on_each_call(tmp_path: Path) -> None:
    """Regression for a defect the route tests caught: the first fake matched
    the phase by looking for its step id in the packet's objective, which the
    prompts never contain, so all three phases wrote phase 1's files."""
    implementer = scripted_implementer(ROUTE_SCENARIO, tmp_path)
    delivered = [
        set(implementer(_packet(step)).changed_files)
        for step in ROUTE_SCENARIO
    ]
    assert delivered[0] != delivered[1] != delivered[2]
    assert delivered == [set(v) for v in ROUTE_SCENARIO.values()]


def test_the_fake_refuses_a_call_beyond_its_scripted_phases(
    tmp_path: Path,
) -> None:
    """The sibling: exhaustion is refused rather than silently repeating the
    last phase, which is how the original defect stayed invisible."""
    implementer = scripted_implementer({"only": {"app.py": "x"}}, tmp_path)
    implementer(_packet())
    with pytest.raises(RouteError, match="more times than it has phases"):
        implementer(_packet())


@pytest.mark.parametrize("bad", [["app.py"], ("app.py", ""), ("app.py", 3)])
def test_changed_files_must_be_a_tuple_of_non_blank_strings(bad: object) -> None:
    """A list would pass an `isinstance(str)` loop and then compare unequal to
    every persisted tuple, which is a difference that shows up much later."""
    with pytest.raises(RouteError, match="changed_files"):
        ImplementerResult(
            changed_files=bad,  # type: ignore[arg-type]
            reported_outcome="delivered",
            message=None,
        )
