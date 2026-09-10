"""HP1 slice 5: the golden packet.

One packet from `phase-2-board`, byte-for-byte. Regenerating it is a visible
diff in review, which is the point: a mapping that changes silently is a
mapping nobody reviewed.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.errors import PacketError
from satyrn_evals.manifest import load_manifest
from satyrn_evals.packet import (
    HandoffPacket,
    build_packet,
    packet_from_dict,
    packet_to_dict,
)
from satyrn_evals.session_manifest import load_session_spec

REPO = Path(__file__).resolve().parent.parent
TASK = REPO / "src/satyrn_evals/tasks/agentclinic-session-phased"
GOLDEN = Path(__file__).parent / "data" / "hp1-golden-packet.json"
REVISION = "3e6607e533792ab0"


def _serialize(packet: HandoffPacket) -> str:
    return json.dumps(packet_to_dict(packet), indent=2, sort_keys=True) + "\n"


def _built() -> HandoffPacket:
    return build_packet(
        TASK,
        load_manifest(TASK),
        load_session_spec(TASK),
        "phase-2-board",
        base_revision=REVISION,
        turn_budget=40,
        tool_call_budget=60,
    )


def test_the_golden_packet_is_byte_identical() -> None:
    assert _serialize(_built()) == GOLDEN.read_text()


def test_the_golden_packet_round_trips() -> None:
    loaded = packet_from_dict(json.loads(GOLDEN.read_text()))
    assert loaded == _built()


def test_a_persisted_packet_of_an_unknown_version_is_refused() -> None:
    data = json.loads(GOLDEN.read_text())
    data["version"] = 2
    with pytest.raises(PacketError, match="version"):
        packet_from_dict(data)


def test_the_golden_packet_carries_no_hidden_selector_in_its_visible_fields() -> None:
    """The persisted file is **not** worker-safe, and this test does not claim
    it is.

    `redacts` intentionally stores the hidden selectors: that is how the gate
    knows what to look for. Only the **rendered projection** is intended for
    an implementer. This test excludes `redacts` and checks that no selector
    leaked into any other stored field. HP2 must keep that distinction
    explicit when it decides what is written where.
    """
    data = json.loads(GOLDEN.read_text())
    visible = json.dumps(
        {k: v for k, v in data.items() if k != "redacts"}
    )
    for secret in data["redacts"]:
        assert secret not in visible


def test_a_persisted_packet_missing_a_key_fails_as_itself() -> None:
    """`KeyError` would blame whichever field happened to be read first."""
    data = json.loads(GOLDEN.read_text())
    del data["facts"]
    with pytest.raises(PacketError, match="missing facts"):
        packet_from_dict(data)


# --- HP1 review: the persisted entry point re-checks shapes ------------------
#
# Every case below was reproduced by review against the first version, which
# converted before validating. A JSON string tuples into single characters and
# then satisfies every constructor rule.


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("facts", "FastAPI"),
        ("facts", None),
        ("writable_paths", "app.py"),
        ("preserve", "earlier"),
        ("redacts", "a::b"),
        ("self_test_command", "pytest"),
    ],
)
def test_a_persisted_sequence_of_the_wrong_shape_is_refused(
    field: str, value: object
) -> None:
    data = json.loads(GOLDEN.read_text())
    data[field] = value
    with pytest.raises(PacketError, match=field):
        packet_from_dict(data)


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_a_persisted_version_that_is_not_an_integer_is_refused(
    value: object,
) -> None:
    """`True == 1` and `1.0 == 1`, so an equality check alone accepts both."""
    data = json.loads(GOLDEN.read_text())
    data["version"] = value
    with pytest.raises(PacketError, match="version"):
        packet_from_dict(data)


@pytest.mark.parametrize("field", ["objective", "base_revision", "role"])
def test_a_persisted_text_field_of_the_wrong_type_is_refused(field: str) -> None:
    data = json.loads(GOLDEN.read_text())
    data[field] = ["not", "text"]
    with pytest.raises(PacketError, match=field):
        packet_from_dict(data)


@pytest.mark.parametrize("field", ["turn_budget", "tool_call_budget"])
def test_a_persisted_budget_of_the_wrong_type_is_refused(field: str) -> None:
    data = json.loads(GOLDEN.read_text())
    data[field] = True
    with pytest.raises(PacketError, match=field):
        packet_from_dict(data)


def test_an_absent_self_test_command_still_loads() -> None:
    """The sibling: `None` is a legitimate value, not a malformed one."""
    data = json.loads(GOLDEN.read_text())
    data["self_test_command"] = None
    assert packet_from_dict(data).self_test_command is None
