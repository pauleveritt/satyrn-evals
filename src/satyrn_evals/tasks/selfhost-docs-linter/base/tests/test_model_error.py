"""Classify an infrastructure failure apart from a model-side one.

Both shapes end a cell with `stopReason: "error"` and `totalTokens: 0`,
so neither field can be the rule -- three screens were tried on 2026-09-05
and two over-fired, one hitting a genuine 285-turn context exhaustion and
one matching all twelve cells including four passes. The `errorMessage`
is the only field carrying the cause.

Every fixture here is the shape of a real terminal turn from a retained
transcript, cited in its test.
"""

import json

from satyrn_evals.model_error import infrastructure_failure


def _doc(*, stop: str, error: str | None, tokens: int = 0) -> str:
    message = {
        "role": "assistant", "content": [], "model": "gemma-4-12B-it-MLX-8bit",
        "usage": {"totalTokens": tokens}, "stopReason": stop,
    }
    if error is not None:
        message["errorMessage"] = error
    return "\n".join([
        '{"type": "session", "version": 3, "cwd": "/w"}',
        '{"type": "agent_start"}',
        '{"type": "turn_start"}',
        json.dumps({"type": "turn_end", "message": message}),
        '{"type": "agent_end"}',
    ])


_OOM = (
    "[METAL] Command buffer execution failed: Insufficient Memory "
    "(00000008:kIOGPUCommandBufferCallbackErrorOutOfMemory)."
)
_CONTEXT = (
    '400: {"message":"Prompt too long: 80036 tokens exceeds max context '
    'window of 80000 tokens","type":"invalid_request_error"}'
)


def test_a_runtime_fault_is_an_infrastructure_failure() -> None:
    """The known-bad: GPU out-of-memory mid-stream. Voided the first V11c
    mini-probe when it scored as NO_PATCH
    (`miniprobe/plausible-wrong-fix/…-200818-705745`)."""
    assert infrastructure_failure(_doc(stop="error", error=_OOM)) is not None


def test_context_exhaustion_is_not_an_infrastructure_failure() -> None:
    """The known-good, and the one that defeated two earlier screens: the
    server answered with a status code about its own input limit, so the
    model was reached. Genuine pathology; stays in the denominator
    (`miniprobe-2/misleading-locus/…-203854-827825`, 285 turns)."""
    assert infrastructure_failure(_doc(stop="error", error=_CONTEXT)) is None


def test_a_healthy_terminal_turn_is_not_a_failure() -> None:
    """The success sibling: a cell that simply finished."""
    assert infrastructure_failure(_doc(stop="stop", error=None, tokens=4325)) is None


def test_an_output_limit_is_not_an_infrastructure_failure() -> None:
    """`length` is the model hitting its own output cap -- a model-side
    outcome pi declares distinctly (`pi_session.py`), not a fault."""
    assert infrastructure_failure(_doc(stop="length", error=None, tokens=23592)) is None


def test_an_error_stop_without_a_message_is_a_failure() -> None:
    """Conservative on purpose: an error with no cause given is reported
    rather than counted as a refusal. Under report-never-drop an over-call
    is visible for the maintainer; the current behaviour -- infrastructure
    silently counted as NO_PATCH -- is the invisible one."""
    assert infrastructure_failure(_doc(stop="error", error=None)) is not None


def test_a_5xx_is_an_infrastructure_failure() -> None:
    """Corrected 2026-09-06 after review. An earlier draft called *any*
    status-coded error model-side, which put a 503 -- the server blaming
    itself -- in the denominator as a refusal. pi's own retry layer treats
    500/502/503/504 and "overloaded" as transient provider errors and
    retries them, so a 5xx that reaches the terminal turn is a substrate
    failure that survived those retries."""
    assert infrastructure_failure(
        _doc(stop="error", error='503: {"message":"model overloaded"}')
    ) is not None


def test_a_4xx_is_model_side_however_it_is_rendered() -> None:
    """pi emits `"<status>: <body>"` only when the provider returns a
    structured error object, and `"<status> <message>"` otherwise. The
    status is the signal; the separator is not. A server returning a bare
    string must not turn a context overflow into an infrastructure
    failure."""
    assert infrastructure_failure(
        _doc(stop="error", error='400 "Prompt too long"')
    ) is None


def test_a_provider_stop_reason_is_model_side() -> None:
    """pi renders model-side stop reasons with no status at all
    (`Provider finish_reason: content_filter`). Those are outcomes, not
    faults, and must not be swept up by the no-status branch."""
    assert infrastructure_failure(
        _doc(stop="error", error="Provider finish_reason: content_filter")
    ) is None


def test_an_unparseable_transcript_is_not_a_failure() -> None:
    """Absent evidence is not a finding. A transcript that cannot be read
    says nothing about infrastructure, so it must not manufacture a
    MODEL_ERROR -- V10's `unmeasured, never zero` discipline."""
    assert infrastructure_failure("not json at all\n") is None
    assert infrastructure_failure("") is None


def test_a_transcript_with_no_terminal_turn_is_not_a_failure() -> None:
    """Sibling of the pin above: no terminal turn, no claim."""
    assert infrastructure_failure(
        '{"type": "session", "version": 3, "cwd": "/w"}\n'
    ) is None
