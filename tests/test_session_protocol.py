"""Protocol parser: round-trips and the structural refusal table."""

import json

import pytest

from satyrn_evals.errors import ProtocolError
from satyrn_evals.session_protocol import (
    CloseLine,
    EventLine,
    SessionStarted,
    StepFinished,
    parse_session_line,
    serialize_close,
    serialize_prompt,
)

STARTED = '{"version": 1, "type": "session_started", "conversation_id": "c-1"}'
EVENT = (
    '{"version": 1, "type": "event", "step_id": "add-a", '
    '"kind": "turn_end", "payload": {"k": 1}}'
)
FINISHED = (
    '{"version": 1, "type": "step_finished", "step_id": "add-a", '
    '"conversation_id": "c-1", "outcome": "settled", "message": null}'
)
CLOSE = '{"version": 1, "type": "close"}'


def test_parse_round_trips_each_type() -> None:
    assert parse_session_line(STARTED) == SessionStarted(1, "c-1")
    assert parse_session_line(EVENT) == EventLine(1, "add-a", "turn_end", {"k": 1})
    assert parse_session_line(FINISHED) == StepFinished(
        1, "add-a", "c-1", "settled", None
    )
    assert parse_session_line(CLOSE) == CloseLine(1)


def test_serialize_prompt_and_close_match_the_spec_shapes() -> None:
    assert json.loads(serialize_prompt("add-a", "Do it.")) == {
        "version": 1,
        "type": "prompt",
        "step_id": "add-a",
        "text": "Do it.",
    }
    assert serialize_prompt("add-a", "Do it.").endswith("\n")
    assert json.loads(serialize_close()) == {"version": 1, "type": "close"}


@pytest.mark.parametrize(
    ("line", "match"),
    [
        ("{not json", "malformed protocol line"),
        ('"a string"', "JSON object"),
        ('{"version": 2, "type": "close"}', "unknown protocol version"),
        ('{"version": true, "type": "close"}', "unknown protocol version"),
        ('{"version": 1, "type": "chaos"}', "unknown protocol type"),
        (STARTED.replace('"c-1"', '""'), "non-empty string"),
        (STARTED.replace('{"version": 1, "type": "session_started", "conversation_id": "c-1"}', '{"version": 1, "type": "session_started", "conversation_id": "c-1", "extra": 1}'), "exactly"),
        (EVENT.replace('"turn_end"', '"chaos"'), "unknown event kind"),
        (EVENT.replace('"payload": {"k": 1}', '"payload": 3'), "payload must be an object"),
        (EVENT.replace('"step_id": "add-a"', '"step_id": ""'), "step_id must be a non-empty"),
        (FINISHED.replace('"outcome": "settled"', '"outcome": "vibes"'), "unknown outcome"),
        (FINISHED.replace('"message": null', '"message": 3'), "string or null"),
        (FINISHED.replace('"conversation_id": "c-1"', '"conversation_id": ""'), "conversation_id must be non-empty"),
        (CLOSE.replace("}", ', "extra": 1}'), "exactly version and type"),
    ],
)
def test_parse_refusals(line: str, match: str) -> None:
    with pytest.raises(ProtocolError, match=match):
        parse_session_line(line)


def test_parse_event_kinds_the_spec_allows() -> None:
    for kind in ("turn_end", "tool_end", "context_compacted", "context_reset", "other"):
        line = EVENT.replace('"turn_end"', f'"{kind}"')
        assert parse_session_line(line).kind == kind  # type: ignore[union-attr]


def test_parse_step_finished_outcomes_the_spec_allows() -> None:
    for outcome in ("settled", "output-limit", "agent-error"):
        line = FINISHED.replace('"outcome": "settled"', f'"outcome": "{outcome}"')
        assert parse_session_line(line).outcome == outcome  # type: ignore[union-attr]
