"""HP1 slice 3: building a packet from one session step.

Asserted against the **real** phased task rather than a synthetic fixture,
because the mappings are what the cycle exists to get right.
"""

import dataclasses
from pathlib import Path

import pytest

from satyrn_evals.engine_contract import admits
from satyrn_evals.errors import PacketError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import HandoffPacket, build_packet
from satyrn_evals.patch import within_source
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
REVISION = "3e6607e533792ab0"


BUDGETS: dict[str, int] = {"turn_budget": 40, "tool_call_budget": 60}


def _build(step_id: str = "phase-2-board", **kw: object) -> HandoffPacket:
    return build_packet(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        step_id,
        base_revision=REVISION,
        **{**BUDGETS, **kw},  # type: ignore[arg-type]
    )


def test_the_builder_is_deterministic() -> None:
    """The golden packet in slice 5 depends on this: no clock, no randomness,
    no environment read."""
    assert _build() == _build()


def test_the_objective_is_the_step_prompt() -> None:
    spec = load_session_spec(TASK)
    step = next(s for s in spec.steps if s.id == "phase-2-board")
    assert _build().objective == step.prompt


def test_the_facts_are_the_steps_pinned_decisions() -> None:
    spec = load_session_spec(TASK)
    step = next(s for s in spec.steps if s.id == "phase-2-board")
    assert _build().facts == step.facts


def test_a_step_without_facts_is_refused() -> None:
    """Optional in the loader, required by the builder -- the rule lives here
    and only here."""
    spec = load_session_spec(TASK)
    stripped = dataclasses.replace(
        spec,
        steps=tuple(dataclasses.replace(s, facts=()) for s in spec.steps),
    )
    with pytest.raises(PacketError, match="facts"):
        build_packet(
            TASK, load_manifest(TASK), stripped, "phase-2-board",
            base_revision=REVISION, **BUDGETS,
        )


def test_preserve_carries_earlier_objectives_as_prose() -> None:
    spec = load_session_spec(TASK)
    first = next(s for s in spec.steps if s.id == "phase-1-home")
    assert first.prompt in _build().preserve


def test_the_first_phase_preserves_nothing() -> None:
    """The sibling: `preserve` grows, so an always-full value would pass the
    test above while being wrong."""
    assert _build("phase-1-home").preserve == ()


def _preserve_is_selector_free(packet: HandoffPacket) -> bool:
    return all("::" not in entry for entry in packet.preserve)


def test_preserve_names_no_grader_selector() -> None:
    packet = _build("phase-3-add")
    assert packet.preserve, "an empty preserve would satisfy this vacuously"
    assert _preserve_is_selector_free(packet)


def test_the_selector_check_fails_on_a_planted_selector() -> None:
    """The sibling runs the same predicate, rather than asserting a fact
    about a string that the predicate never sees."""
    packet = _build("phase-3-add")
    planted = dataclasses.replace(
        packet, preserve=packet.preserve + (packet.redacts[0],)
    )
    assert not _preserve_is_selector_free(planted)


def test_redacts_holds_every_hidden_selector_and_the_overlay_name() -> None:
    packet = _build()
    spec = load_session_spec(TASK)
    for step in spec.steps:
        for selector in step.new_feature_selectors:
            assert selector in packet.redacts
    assert any("grader" in entry for entry in packet.redacts)


def test_the_self_test_command_comes_from_the_session_spec() -> None:
    assert _build().self_test_command == ("uv", "run", "python", "-m", "pytest", "tests")


def test_the_writable_paths_are_the_contract_renderers() -> None:
    """The builder calls the renderer rather than copying `source_paths`.

    Distinguishable since HP4: this task declares `templates` and `tests`
    directories, so the renderer returns `templates/*` and `tests/*` and a
    builder that copied `source_paths` would now fail here.
    """
    from satyrn_evals.engine_contract import writable_paths

    manifest = load_manifest(TASK)
    built = _build().writable_paths
    assert built == writable_paths(TASK, manifest.source_paths, manifest.source_dirs)
    assert built != manifest.source_paths


def test_the_declared_scope_no_longer_hides_a_creation_target() -> None:
    """The gap this test used to record, closed by HP4.

    It read: `writable_paths` leaves a path absent from `base/` as an exact
    filename, while the session route matches by prefix, so the two disagree
    about a file the task expects the model to create. The manifest now
    declares its directories and the disagreement is gone for that file.
    The remaining one-directional invariant, and the bare-directory
    asymmetry left open on purpose, live in
    `tests/test_declared_scope_against_enforced.py`.
    """
    manifest = load_manifest(TASK)
    declared = _build().writable_paths
    assert "templates/*" in declared
    assert "templates" not in declared
    assert admits(declared, "templates/base.html")
    assert within_source("templates/base.html", manifest.source_paths)


def test_an_unknown_step_is_refused() -> None:
    with pytest.raises(PacketError, match="phase-9"):
        _build("phase-9-nonexistent")


def test_an_empty_base_revision_is_refused() -> None:
    with pytest.raises(PacketError, match="base_revision"):
        build_packet(
            TASK, load_manifest(TASK), load_session_spec(TASK), "phase-2-board",
            base_revision="", **BUDGETS,
        )


def test_budgets_are_required_arguments() -> None:
    """No default: two unexplained numbers frozen into a golden file is a
    decision nobody made. The caller states them."""
    with pytest.raises(TypeError, match="turn_budget"):
        build_packet(
            TASK, load_manifest(TASK), load_session_spec(TASK), "phase-2-board",
            base_revision=REVISION,
        )
    assert _build(turn_budget=7).turn_budget == 7


def test_a_self_test_command_naming_the_oracle_hook_never_reaches_a_packet() -> None:
    """Defence in depth for the review's finding 1. The authoring check fires
    first, but only for a caller that runs it; this is the boundary that
    actually hands the string to an implementer."""
    spec = load_session_spec(TASK)
    leaky = dataclasses.replace(
        spec,
        self_test_command=("python", "-m", "pytest", "-p", "satyrn_evals.oracle_hook"),
    )
    with pytest.raises(PacketError, match="oracle_hook"):
        build_packet(
            TASK, load_manifest(TASK), leaky, "phase-2-board",
            base_revision=REVISION, **BUDGETS,
        )


def test_the_real_self_test_command_reaches_the_packet() -> None:
    """The success sibling, through the same boundary."""
    assert _build().self_test_command == ("uv", "run", "python", "-m", "pytest", "tests")
