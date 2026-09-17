"""MODEL_ERROR through the real attempt path.

The classifier has unit tests; this pins the *wiring* -- where it sits
relative to `decide_refusal` and the patch. That placement is the part
that went wrong in review: an earlier draft consulted the substrate
before looking at the patch, so a cell that had edited files and then hit
a GPU fault was refused ungraded, unrecoverably.

Integration-tier: a real subprocess through the seam. No model runs.
"""

import json
import sys
from pathlib import Path

import pytest

from satyrn_evals.attempt import attempt
from satyrn_evals.attempt_record import AttemptCode, AttemptOutcome
from satyrn_evals.manifest import DEFAULT_TASKS_ROOT

pytestmark = pytest.mark.integration

FAKE = Path(__file__).parent / "fake_attempt.py"
KNOWN_GOOD = DEFAULT_TASKS_ROOT / "format_number" / "fixtures" / "known-good.patch"
TASK = "format_number"


def _errored(error: str) -> str:
    return "\n".join([
        '{"type": "session", "version": 3, "cwd": "/w"}',
        '{"type": "agent_start"}',
        '{"type": "turn_start"}',
        json.dumps({"type": "turn_end", "message": {
            "role": "assistant", "content": [], "model": "m",
            "usage": {"totalTokens": 0}, "stopReason": "error",
            "errorMessage": error,
        }}),
        '{"type": "agent_end"}',
    ])


_OOM = "[METAL] Command buffer execution failed: Insufficient Memory (OutOfMemory)."
_CONTEXT = '400: {"message":"Prompt too long: 80036 tokens exceeds max context window"}'


def _run(tmp_path: Path, *args: str):
    return attempt(
        task=TASK, tasks_root=DEFAULT_TASKS_ROOT, output=tmp_path / "attempts",
        command=[sys.executable, str(FAKE), *args], timeout=60,
    )


def test_no_patch_plus_a_runtime_fault_is_model_error(tmp_path: Path) -> None:
    """The cell the slice exists for: nothing delivered, and the
    transcript says the substrate failed underneath it."""
    record = _run(tmp_path, "--no-patch", "--transcript", _errored(_OOM))
    assert record.code is AttemptCode.MODEL_ERROR
    assert record.outcome is AttemptOutcome.REFUSED
    assert "Insufficient Memory" in record.message


def test_no_patch_plus_context_exhaustion_stays_no_patch(tmp_path: Path) -> None:
    """The success sibling: the server answered about its own input
    limit, so the model was reached. Genuine pathology, and it stays in
    the denominator."""
    record = _run(tmp_path, "--no-patch", "--transcript", _errored(_CONTEXT))
    assert record.code is AttemptCode.NO_PATCH


def test_a_delivered_patch_is_graded_even_when_the_turn_errored(
    tmp_path: Path,
) -> None:
    """The regression this pins, found in review: a model that edited
    files and then hit a GPU fault has still produced a gradeable patch.
    MODEL_ERROR replaces the NO_PATCH the cell would otherwise get; it
    never displaces a patch, because refusing one ungraded destroys
    evidence that cannot be recovered offline."""
    record = _run(
        tmp_path, "--patch", str(KNOWN_GOOD), "--transcript", _errored(_OOM)
    )
    assert record.code is not AttemptCode.MODEL_ERROR
    assert record.code is AttemptCode.OK
    assert record.verdict is not None  # it was actually graded
