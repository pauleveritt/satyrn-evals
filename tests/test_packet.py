"""HP1 slice 1: the handoff packet type.

Every refusal here lands with the sibling success that proves it can pass
(``BRIEF.md`` invariant 5). The type is a data contract only — no I/O, no
builder, no rendering. Those are slices 3 and 4.

``facts`` emptiness is deliberately **not** refused at this layer. The spec
states that rule once, on the builder, so the two cannot drift apart.
"""

import dataclasses

import pytest

from satyrn_evals.errors import PacketError, UsageError
from satyrn_evals.packet import PACKET_VERSION, HandoffPacket

_FIELDS: dict[str, object] = {
    "objective": "Create app.py with the FastAPI application instance.",
    "facts": ("The web framework is FastAPI.",),
    "base_revision": "3e6607e533792ab0",
    "writable_paths": ("app.py", "templates/*"),
    "preserve": ("Phase 1 served the home page.",),
    "self_test_command": ("uv", "run", "python", "-m", "pytest", "tests"),
    "redacts": ("grader_tests/test_phase1_home.py::test_home_has_html5_doctype",),
    "turn_budget": 40,
    "tool_call_budget": 60,
}


def _packet(**overrides: object) -> HandoffPacket:
    return HandoffPacket(**{**_FIELDS, **overrides})  # type: ignore[arg-type]


def test_a_well_formed_packet_is_accepted() -> None:
    """The sibling success for every refusal below."""
    packet = _packet()
    assert packet.version == PACKET_VERSION
    assert packet.role == "implement"
    assert packet.objective.startswith("Create app.py")


def test_the_packet_is_frozen_and_slotted() -> None:
    packet = _packet()
    with pytest.raises(dataclasses.FrozenInstanceError):
        packet.objective = "rewritten"  # type: ignore[misc]
    assert not hasattr(packet, "__dict__")


def test_a_packet_error_is_a_usage_error_with_exit_two() -> None:
    """Malformed input is the caller's fault, like a bad session spec."""
    assert issubclass(PacketError, UsageError)
    assert PacketError.exit_code == 2


def test_an_empty_objective_is_refused() -> None:
    with pytest.raises(PacketError, match="objective"):
        _packet(objective="   ")


def test_an_unknown_version_is_refused() -> None:
    with pytest.raises(PacketError, match="version"):
        _packet(version=2)


def test_version_one_is_accepted() -> None:
    assert _packet(version=1).version == 1


def test_a_command_given_as_a_bare_string_is_refused() -> None:
    """A string would split into characters wherever argv is expected."""
    with pytest.raises(PacketError, match="self_test_command"):
        _packet(self_test_command="uv run python -m pytest tests")


def test_a_command_of_no_tokens_is_refused() -> None:
    """`()` is a command that runs nothing; absence is spelled `None`."""
    with pytest.raises(PacketError, match="self_test_command"):
        _packet(self_test_command=())


def test_an_absent_command_is_accepted_as_none() -> None:
    assert _packet(self_test_command=None).self_test_command is None


@pytest.mark.parametrize("bad", [0, -1, True, 2.0, "40"])
def test_a_budget_that_is_not_a_positive_integer_is_refused(bad: object) -> None:
    """`True` is an `int` in Python and would pass a naive check as 1."""
    with pytest.raises(PacketError, match="turn_budget"):
        _packet(turn_budget=bad)


def test_a_positive_budget_is_accepted() -> None:
    assert _packet(turn_budget=1).turn_budget == 1


def test_an_unknown_role_is_refused() -> None:
    with pytest.raises(PacketError, match="role"):
        _packet(role="orchestrate")


_SEQUENCE_FIELDS = ("facts", "preserve", "writable_paths", "redacts")


@pytest.mark.parametrize("field", _SEQUENCE_FIELDS)
def test_a_string_sequence_field_refuses_a_bare_string(field: str) -> None:
    """`facts="x"` would silently become a sequence of characters."""
    with pytest.raises(PacketError, match=field):
        _packet(**{field: "a bare string"})


@pytest.mark.parametrize("field", _SEQUENCE_FIELDS)
def test_a_string_sequence_field_accepts_a_tuple(field: str) -> None:
    assert getattr(_packet(**{field: ("one",)}), field) == ("one",)


def test_a_blank_entry_in_a_string_sequence_is_refused() -> None:
    with pytest.raises(PacketError, match="facts"):
        _packet(facts=("The web framework is FastAPI.", "  "))


def test_empty_facts_are_accepted_by_the_type() -> None:
    """The requirement belongs to the builder (slice 3), stated once."""
    assert _packet(facts=()).facts == ()


def test_an_empty_base_revision_is_refused() -> None:
    with pytest.raises(PacketError, match="base_revision"):
        _packet(base_revision="")


def test_the_packet_carries_no_parent_validation_command() -> None:
    """Sourcing one from `manifest.oracle` would put the hidden oracle hook
    into a document the implementer reads; the spec removed the field rather
    than carrying it empty."""
    names = {f.name for f in dataclasses.fields(HandoffPacket)}
    assert "validation_command" not in names
    assert names == {
        "objective",
        "facts",
        "base_revision",
        "writable_paths",
        "preserve",
        "self_test_command",
        "redacts",
        "turn_budget",
        "tool_call_budget",
        "role",
        "version",
    }
