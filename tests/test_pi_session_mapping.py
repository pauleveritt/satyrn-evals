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


def test_terminal_outcome_from_agent_end_stop_reasons() -> None:
    """Pi declares the terminal via stopReason (rpc.md:1469); the adapter
    must not blanket-map every settle to "settled" (review finding 3)."""
    from satyrn_evals.adapters.pi_session import terminal_outcome_from_agent_end

    derive = terminal_outcome_from_agent_end
    assert derive({"type": "agent_end", "messages": [{"stopReason": "stop"}]}) == "settled"
    assert derive({"type": "agent_end", "messages": [{"stopReason": "toolUse"}]}) == "settled"
    assert derive({"type": "agent_end", "messages": [{"stopReason": "length"}]}) == "output-limit"
    assert derive({"type": "agent_end", "messages": [{"stopReason": "error"}]}) == "agent-error"
    assert derive({"type": "agent_end", "messages": [{"stopReason": "aborted"}]}) == "agent-error"
    # willRetry: an automatic retry follows — not terminal
    assert derive({"type": "agent_end", "willRetry": True, "messages": [{"stopReason": "error"}]}) is None
    # no messages / no stopReason: settles normally
    assert derive({"type": "agent_end", "messages": []}) == "settled"
    assert derive({"type": "agent_end"}) == "settled"


def test_agent_end_and_retry_end_are_retained_as_events() -> None:
    end = {"type": "agent_end", "messages": [{"stopReason": "length"}]}
    line = map_rpc_event(end, step_id="add-a", conversation_id="c-1")
    obj = json.loads(line)  # type: ignore[arg-type]
    assert obj["kind"] == "other" and obj["payload"] == end
    retry = {"type": "auto_retry_end", "success": False, "finalError": "x"}
    obj = json.loads(map_rpc_event(retry, step_id="s", conversation_id="c"))  # type: ignore[arg-type]
    assert obj["kind"] == "other" and obj["payload"] == retry


def test_message_update_is_retained_as_model_stream_evidence() -> None:
    """The smoke's positive evidence: Pi's streaming event reaches the
    transcript with its payload unmodified (review finding 2)."""
    event = {"type": "message_update", "delta": {"type": "text", "text": "he"}}
    line = map_rpc_event(event, step_id="add-a", conversation_id="c-1")
    assert line is not None
    obj = json.loads(line)
    assert obj["type"] == "event"
    assert obj["kind"] == "other"
    assert obj["payload"] == event  # pristine


def test_unmapped_events_and_responses_are_skipped() -> None:
    assert map_rpc_event({"type": "message_start"}, step_id="s", conversation_id="c") is None
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


def test_unknown_adapter_argument_is_refused() -> None:
    from satyrn_evals.adapters.pi_session import main

    with pytest.raises(Exception, match="unknown adapter argument"):
        main(["--chaos"])
