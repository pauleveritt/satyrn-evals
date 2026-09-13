"""HP1 slice 4: rendering, and the gates over it.

Every gate here is tested in both directions, and each is also shown to fail
on a stub renderer that returns nothing. A gate that passes because there was
nothing to check is the failure mode this whole slice exists to prevent.
"""

import dataclasses
import shlex
from pathlib import Path

import pytest

from satyrn_evals.contamination import scan_texts
from satyrn_evals.errors import PacketError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.packet import (
    RENDERED_FIELDS,
    HandoffPacket,
    assert_overlay_absent_from_packet,
    assert_redactions_absent,
    build_packet,
    render_packet,
    render_projection,
    worker_projection,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"


def _packet(step_id: str = "phase-2-board", **over: object) -> HandoffPacket:
    packet = build_packet(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        step_id,
        base_revision="3e6607e533792ab0",
        turn_budget=40,
        tool_call_budget=60,
    )
    return dataclasses.replace(packet, **over)  # type: ignore[arg-type]


# --- the rendered surface ---------------------------------------------------


def test_the_rendered_fields_are_the_documented_five() -> None:
    assert RENDERED_FIELDS == (
        "objective",
        "facts",
        "preserve",
        "writable_paths",
        "self_test_command",
    )


@pytest.mark.parametrize("field", RENDERED_FIELDS)
def test_every_rendered_field_actually_appears(field: str) -> None:
    """Without this, every gate below passes on a renderer that drops fields.

    The check is on the rendered **section**, not bare substring containment.
    Review found the earlier version could not fail for `writable_paths` or
    `self_test_command`: every one of their tokens (`app.py`, `tests`, `uv`,
    `pytest`) already appears inside the objective prompt, so a renderer that
    skipped those two fields still passed.
    """
    packet = _packet("phase-3-add")
    text = render_packet(packet)
    assert f"## {field}\n" in text, field
    value = getattr(packet, field)
    match value:
        case str() as body:
            assert body in text
        case tuple() as argv if field == "self_test_command":
            assert shlex.join(argv) in text
        case tuple() as entries:
            assert entries
            for entry in entries:
                assert f"- {entry}" in text, entry


def test_redacts_is_never_rendered() -> None:
    """A packet that printed its own forbidden strings would refuse itself."""
    packet = _packet()
    text = render_packet(packet)
    for secret in packet.redacts:
        assert secret not in text


# --- the redaction gate -----------------------------------------------------


def test_a_clean_packet_passes_the_redaction_gate() -> None:
    assert_redactions_absent(_packet())


@pytest.mark.parametrize("field", RENDERED_FIELDS)
def test_a_selector_planted_in_any_rendered_field_is_refused(field: str) -> None:
    """Parametrized over every rendered field: planting only into one would
    let a renderer that omits the others pass."""
    packet = _packet("phase-3-add")
    secret = packet.redacts[0]
    value = getattr(packet, field)
    planted = f"{value} {secret}" if isinstance(value, str) else (
        tuple(value or ()) + (secret,)
    )
    with pytest.raises(PacketError, match="redacted"):
        assert_redactions_absent(_packet("phase-3-add", **{field: planted}))


def test_the_planted_string_is_really_in_the_fixture() -> None:
    """The gate cannot pass by finding nothing that was never there."""
    packet = _packet("phase-3-add")
    secret = packet.redacts[0]
    contaminated = _packet("phase-3-add", preserve=packet.preserve + (secret,))
    assert secret in render_packet(contaminated)


def test_the_self_test_command_renders_as_one_runnable_command() -> None:
    """One argv token per bullet is not a command. Review caught this as a
    real defect, not a style point."""
    text = render_packet(_packet())
    assert "uv run python -m pytest tests" in text
    assert "- uv\n" not in text


def test_an_empty_render_is_refused_rather_than_passing() -> None:
    """A renderer returning nothing satisfies "no secret appears". That is an
    absence of signal reported as a pass, so the gate refuses it instead."""
    with pytest.raises(PacketError, match="nothing to check"):
        assert_redactions_absent(_packet(), rendered="")


# --- the overlay gate -------------------------------------------------------


def test_the_overlay_gate_is_clean_on_the_real_packet() -> None:
    manifest = load_manifest(TASK)
    assert_overlay_absent_from_packet(_packet(), load_overlay(TASK, manifest))


def test_the_overlay_gate_fires_on_a_planted_overlay_path() -> None:
    manifest = load_manifest(TASK)
    spec = load_overlay(TASK, manifest)
    planted = _packet(preserve=(f"see {spec.rel_paths[0]}",))
    with pytest.raises(PacketError, match="overlay"):
        assert_overlay_absent_from_packet(planted, spec)


def test_scan_texts_reports_unmeasured_when_handed_no_text() -> None:
    """The gate refuses that outcome. Driven directly rather than through an
    API parameter that exists only for a test: `render_packet` never returns
    absent text, so no production path reaches it.
    """
    spec = load_overlay(TASK, load_manifest(TASK))
    assert scan_texts([("packet", None)], spec).outcome == "unmeasured"


def test_a_stub_renderer_fails_a_gate() -> None:
    """The done-when condition for this slice, asserted rather than claimed:
    a renderer returning nothing is refused rather than reported clean."""
    with pytest.raises(PacketError, match="nothing to check"):
        assert_redactions_absent(_packet("phase-3-add"), rendered="")


def test_an_absent_command_renders_no_section() -> None:
    """`None` means the task offers none, so the heading is omitted rather
    than rendered empty."""
    text = render_packet(_packet(self_test_command=None))
    assert "self_test_command" not in text
    assert "objective" in text


def test_an_empty_sequence_renders_no_section() -> None:
    """Phase 1 preserves nothing, so the section is absent rather than a
    heading with no items under it."""
    packet = _packet("phase-1-home")
    assert packet.preserve == ()
    text = render_packet(packet)
    assert "## preserve" not in text
    assert "## objective" in text


# --- review: what the worker can actually read ------------------------------


def test_the_worker_projection_carries_only_the_rendered_fields() -> None:
    from satyrn_evals.packet import worker_projection

    assert set(worker_projection(_packet())) == set(RENDERED_FIELDS)


def test_the_worker_projection_carries_no_redacted_selector() -> None:
    """The defect review reproduced: the first executable seam wrote the whole
    packet into the worker's workspace, all 14 selectors included."""
    import json as _json

    from satyrn_evals.packet import worker_projection

    packet = _packet()
    serialized = _json.dumps(worker_projection(packet))
    assert packet.redacts
    for secret in packet.redacts:
        assert secret not in serialized


def test_a_contaminated_projection_is_refused() -> None:
    from satyrn_evals.packet import assert_projection_is_clean, worker_projection

    packet = _packet()
    projection = worker_projection(packet)
    projection["preserve"] = [packet.redacts[0]]
    with pytest.raises(PacketError, match="redacted"):
        assert_projection_is_clean(packet, projection)


def test_a_clean_projection_is_accepted() -> None:
    from satyrn_evals.packet import assert_projection_is_clean, worker_projection

    packet = _packet()
    assert_projection_is_clean(packet, worker_projection(packet))


def test_an_empty_projection_is_refused_rather_than_passing() -> None:
    from satyrn_evals.packet import assert_projection_is_clean

    with pytest.raises(PacketError, match="nothing to check"):
        assert_projection_is_clean(_packet(), {})


# --- HP7: rendering the projection, which is what a real adapter reads -----


def test_render_projection_matches_render_packet_over_the_real_projection() -> None:
    """The provable claim `render_packet`'s own docstring makes -- "the text
    an implementer receives" -- is only true if a worker's actual JSON
    projection renders identically to the pre-projection object."""
    packet = _packet("phase-3-add")
    assert render_projection(worker_projection(packet)) == render_packet(packet)


def test_render_projection_refuses_a_non_mapping() -> None:
    with pytest.raises(PacketError, match="JSON object"):
        render_projection(["not", "a", "mapping"])  # type: ignore[arg-type]


def test_render_projection_refuses_an_empty_projection() -> None:
    with pytest.raises(PacketError, match="nothing to render"):
        render_projection({})


def test_render_projection_omits_an_absent_self_test_command() -> None:
    packet = _packet(self_test_command=None)
    text = render_projection(worker_projection(packet))
    assert "self_test_command" not in text
    assert "objective" in text


@pytest.mark.parametrize(
    "projection",
    [
        {"facts": ["FastAPI"]},  # missing entirely
        {"objective": None, "facts": ["FastAPI"]},
        {"objective": "   ", "facts": ["FastAPI"]},
        {"objective": 5, "facts": ["FastAPI"]},
    ],
)
def test_render_projection_refuses_a_missing_or_blank_objective(
    projection: dict[str, object],
) -> None:
    """A projection missing `objective` must not silently render whatever
    fields it does have and launch an implementer on nothing -- the same
    rule `HandoffPacket.__post_init__` already enforces for the packet
    itself (`_check_text`)."""
    with pytest.raises(PacketError, match="objective"):
        render_projection(projection)


def test_render_projection_accepts_the_real_objective() -> None:
    """The sibling: a real projection's `objective` passes."""
    packet = _packet()
    assert "objective" in render_projection(worker_projection(packet))
