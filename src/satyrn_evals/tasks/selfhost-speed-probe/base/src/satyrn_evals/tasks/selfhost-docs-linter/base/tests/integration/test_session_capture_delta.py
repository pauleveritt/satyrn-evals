"""Per-checkpoint transcript-delta capture edges (V7 F4 fix, coverage pins).

The three defensive branches of the delta scan — the prior-cursor guard, the
mid-line partial-drop, and the transcript-absent path — are exercised here
by calling ``_capture_checkpoint`` directly against a real prepared session
workspace with crafted transcript states. They are unreachable through the
normal run flow (the cursor is always a whole-line boundary and the file
only grows), which is exactly why they need direct tests to hold the 100%
branch-coverage gate.
"""

import json
from pathlib import Path

import pytest

from satyrn_evals.manifest import DEFAULT_TASKS_ROOT, load_manifest
from satyrn_evals.overlay import load_overlay
from satyrn_evals.session import _capture_checkpoint
from satyrn_evals.session_manifest import SessionStep
from satyrn_evals.session_record import StepRecord
from satyrn_evals.workspace import (
    prepare_session_workspace,
    release_session_workspace,
)

pytestmark = pytest.mark.integration

TASK_DIR = DEFAULT_TASKS_ROOT / "agentclinic-repair-misleading-locus"
# A grader-only rel path that must never surface in executor-visible payloads.
_OVERLAY_REL = "test_acceptance.py"

def _overlay():
    return load_overlay(TASK_DIR, load_manifest(TASK_DIR))

def _event(step_id: str, kind: str, payload: dict) -> str:
    return json.dumps(
        {
            "version": 1,
            "type": "event",
            "step_id": step_id,
            "conversation_id": "c",
            "kind": kind,
            "payload": payload,
        }
    )

def _transcript(*lines: str) -> bytes:
    return "".join(line + "\n" for line in lines).encode()

def _capture(
    tmp_path: Path,
    transcript_bytes: bytes | None,
    transcript_prior_len: int,
) -> StepRecord:
    manifest = load_manifest(TASK_DIR)
    spec = load_overlay(TASK_DIR, manifest)
    session_dir = tmp_path / "session"
    session_dir.mkdir()
    transcript_path = session_dir / "transcript.jsonl"
    if transcript_bytes is not None:
        transcript_path.write_bytes(transcript_bytes)
    workspace = prepare_session_workspace(
        base=TASK_DIR / "base", protected_paths=(TASK_DIR, tmp_path)
    )
    try:
        step = SessionStep(
            id="s1", kind="feature", prompt="add slugify", new_feature_selectors=()
        )
        return _capture_checkpoint(
            workspace,
            session_dir,
            step,
            transcript_path,
            index=1,
            outcome="settled",
            prompt_digest="d",
            turn_count=1,
            tool_count=0,
            context_events=0,
            source_paths=manifest.source_paths,
            overlay=spec,
            visibility="hidden",
            transcript_prior_len=transcript_prior_len,
        )
    finally:
        release_session_workspace(workspace)

def _c_outcome(record: StepRecord) -> str | None:
    if record.contamination is None:
        return None
    for check in record.contamination["checks"]:
        if check["check"] == "grader_name_in_payload":
            return check["outcome"]
    return None

def test_capture_scans_only_the_transcript_delta(tmp_path: Path) -> None:
    """A leak in an earlier step's events is not re-scanned under this step.

    The prior step's mention of the overlay path must not surface in the
    current checkpoint's payload scan: the cursor excludes everything the
    previous capture already consumed.
    """
    earlier_leak = _event("s0", "turn_end", {"text": f"opened {_OVERLAY_REL}"})
    clean = _event("s1", "turn_end", {"text": "implemented slugify"})
    data = _transcript(earlier_leak, clean)
    prior = len(earlier_leak) + 1  # whole-line boundary after the earlier event

    record = _capture(tmp_path, data, prior)
    assert _c_outcome(record) == "clean"

def test_capture_with_prior_zero_sees_the_whole_transcript(tmp_path: Path) -> None:
    """The first checkpoint (cursor 0) scans from byte 0 and flags the leak."""
    earlier_leak = _event("s0", "turn_end", {"text": f"opened {_OVERLAY_REL}"})
    record = _capture(tmp_path, _transcript(earlier_leak), 0)
    assert _c_outcome(record) == "flagged"

def test_capture_rejects_prior_cursor_beyond_transcript(tmp_path: Path) -> None:
    """A cursor past the file end is a programming error, never silent."""
    data = _transcript(_event("s1", "turn_end", {"text": "ok"}))
    with pytest.raises(AssertionError, match="prior cursor"):
        _capture(tmp_path, data, transcript_prior_len=len(data) + 50)

def test_capture_drops_a_partial_leading_line(tmp_path: Path) -> None:
    """A mid-line cursor never parses a fragment under the current step.

    The remaining full line is scanned; the capture completes normally.
    """
    first = _event("s1", "turn_end", {"text": f"opened {_OVERLAY_REL}"})
    second = _event("s1", "tool_end", {"text": "wrote the code"})
    data = _transcript(first, second)
    mid_line = len(first) // 2  # inside the first line, not at a boundary

    record = _capture(tmp_path, data, mid_line)
    # the partial first-line fragment is dropped; only `second` is scanned
    assert _c_outcome(record) == "clean"

def test_capture_payload_scan_unmeasured_without_transcript(
    tmp_path: Path,
) -> None:
    """No retained transcript means check (c) is unmeasured, never clean."""
    record = _capture(tmp_path, transcript_bytes=None, transcript_prior_len=0)
    assert _c_outcome(record) == "unmeasured"
