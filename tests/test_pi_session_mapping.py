"""The Pi adapter's mapping: kinds, payload retention, argv space form."""

import json

import pytest

from satyrn_evals.adapters.pi_session import build_pi_argv, map_rpc_event

EVENTS = {
    "turn_end": {"type": "turn_end", "message": {"role": "assistant"}},
    "tool_execution_end": {"type": "tool_execution_end", "toolCallId": "t1"},
    "compaction_start": {"type": "compaction_start"},
    "compaction_end": {"type": "compaction_end", "entries": 7},
}


def test_mapped_kinds_and_payload_retention() -> None:
    for event in EVENTS.values():
        line = map_rpc_event(event, step_id="add-a", conversation_id="c-1")
        assert line is not None
        obj = json.loads(line)
        assert obj["type"] == "event"
        assert obj["step_id"] == "add-a"
        assert obj["payload"] == event  # the original event, unmodified
    assert json.loads(map_rpc_event(EVENTS["compaction_end"], step_id="add-a", conversation_id="c-1"))["kind"] == "context_compacted"


def test_agent_settled_maps_to_the_terminal() -> None:
    line = map_rpc_event(
        {"type": "agent_settled"}, step_id="add-a", conversation_id="c-1"
    )
    obj = json.loads(line)  # type: ignore[arg-type]
    assert obj == {
        "version": 1,
        "type": "step_finished",
        "step_id": "add-a",
        "conversation_id": "c-1",
        "outcome": "settled",
        "message": None,
    }


def test_unmapped_events_and_responses_are_skipped() -> None:
    assert map_rpc_event({"type": "message_update"}, step_id="s", conversation_id="c") is None
    assert map_rpc_event({"type": "response", "success": True}, step_id="s", conversation_id="c") is None


def test_pi_argv_uses_space_form_only() -> None:
    argv = build_pi_argv("anthropic", "claude-x", pi_bin="/custom/pi")
    assert argv[:4] == ["/custom/pi", "--mode", "rpc", "--no-session"]
    assert "--provider" in argv and "anthropic" in argv
    assert "--model" in argv and "claude-x" in argv
    assert not any(token.startswith("--model=") for token in argv)


def test_missing_model_is_refused() -> None:
    with pytest.raises(Exception, match="--model is required"):
        from satyrn_evals.adapters.pi_session import main

        main(["--provider", "anthropic", "--help" if False else "--pi-bin", "pi"])
