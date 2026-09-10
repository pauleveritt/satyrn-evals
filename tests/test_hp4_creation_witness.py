"""HP4.4 -- legitimate file creation, end to end on the offline route.

D4's acceptance, verbatim: phase 1 creates ``app.py``,
``templates/base.html`` and ``tests/test_app.py`` with zero scope
violations, and a write outside the declared scope is still refused, from
the same fixture.

Default tier throughout. The fake writes files; nothing spawns a process.
"""

from pathlib import Path

import pytest

from satyrn_evals.engine_contract import admits
from satyrn_evals.errors import RouteError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import build_packet
from satyrn_evals.route import ROUTE_SCENARIO, run_phases, scripted_implementer
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
BUDGETS = {"turn_budget": 40, "tool_call_budget": 60}
CREATED = ("app.py", "templates/base.html", "tests/test_app.py")


def _grade_all_pass(step_id: str, workspace: Path) -> tuple[str, str]:
    return "pass", f"scripted pass for {step_id}"


def _run(tmp_path: Path, scenario=ROUTE_SCENARIO):
    return run_phases(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        scripted_implementer(scenario, tmp_path),
        tmp_path,
        _grade_all_pass,
        base_revision="3e6607e533792ab0",
        **BUDGETS,
    )


def test_phase_one_creates_all_three_targets_with_no_scope_violation(
    tmp_path: Path,
) -> None:
    """The fake refuses anything its packet does not admit, so reaching the
    end of phase 1 is itself the zero-violation claim."""
    decisions = _run(tmp_path)
    assert decisions[0].step_id == "phase-1-home"
    assert decisions[0].accepted
    for target in CREATED:
        assert (tmp_path / target).is_file(), target


def test_each_created_target_is_admitted_by_its_own_packet(tmp_path: Path) -> None:
    """Stated against the packet the implementer actually receives, not
    against the manifest, because the packet is all the implementer reads."""
    packet = build_packet(
        TASK, load_manifest(TASK), load_session_spec(TASK), "phase-1-home",
        base_revision="3e6607e533792ab0", **BUDGETS,
    )
    for target in CREATED:
        assert admits(packet.writable_paths, target), target


def test_a_write_outside_the_declared_scope_is_still_refused(
    tmp_path: Path,
) -> None:
    """The sibling of the success above, from the same fixture: one file
    swapped for a path no entry admits."""
    scenario = {
        **ROUTE_SCENARIO,
        "phase-1-home": {**ROUTE_SCENARIO["phase-1-home"], "static/app.css": "x"},
    }
    with pytest.raises(RouteError, match="'static/app.css' is outside"):
        _run(tmp_path, scenario)


def test_a_refused_write_leaves_no_half_delivered_workspace(
    tmp_path: Path,
) -> None:
    """Scope is checked for every file before any is written, so the
    refusal above cannot have created the in-scope files first."""
    scenario = {
        **ROUTE_SCENARIO,
        "phase-1-home": {**ROUTE_SCENARIO["phase-1-home"], "static/app.css": "x"},
    }
    with pytest.raises(RouteError):
        _run(tmp_path, scenario)
    for target in CREATED:
        assert not (tmp_path / target).exists(), target


def test_the_undeclared_manifest_would_have_refused_a_target(tmp_path: Path) -> None:
    """The defect HP4 closed, reconstructed so the witness can fail: under
    the probe, ``templates`` renders exact and the fake refuses phase 1's
    own ``templates/base.html``."""
    from satyrn_evals.engine_contract import writable_paths

    manifest = load_manifest(TASK)
    probed = writable_paths(TASK, manifest.source_paths, None)
    assert not admits(probed, "templates/base.html")
    assert admits(
        writable_paths(TASK, manifest.source_paths, manifest.source_dirs),
        "templates/base.html",
    )
