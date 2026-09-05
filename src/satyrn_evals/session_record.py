"""Session records: codes, per-step entries, and the durable session record.

Derived counts come from retained events only; the terminal message
supplies no totals (2026-09-01 spec, Artifacts and record). The session
record is written for every session that starts — adapter-error and
timeout terminations included — so the smoke and any regrade read one
artifact (V6 delta spec, layer (b) reading rules).
"""

import json
import os
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path

from satyrn_evals.session_manifest import SessionSpec

type Outcome = str
"""Adapter terminal outcome for one step: settled | output-limit | agent-error."""


class SessionCode(StrEnum):
    """Stable detailed outcomes stored in session records."""

    COMPLETE = "COMPLETE"
    STEP_TIMEOUT = "STEP_TIMEOUT"
    OUTPUT_LIMIT = "OUTPUT_LIMIT"
    ADAPTER_ERROR = "ADAPTER_ERROR"
    PROTOCOL_ERROR = "PROTOCOL_ERROR"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    GRADE_UNAVAILABLE = "GRADE_UNAVAILABLE"
    WORKSPACE_FAILED = "WORKSPACE_FAILED"
    CLEANUP_FAILED = "CLEANUP_FAILED"


_NOT_CAPTURED = frozenset(
    {SessionCode.WORKSPACE_FAILED, SessionCode.CLEANUP_FAILED}
)


@dataclass(frozen=True, slots=True)
class StepRecord:
    """One captured checkpoint: prompt, terminal, artifacts, verdicts."""

    step_id: str
    prompt_digest: str
    outcome: Outcome
    patch_path: str | None = None
    patch_digest: str | None = None
    patch_bytes: int | None = None
    snapshot_path: str | None = None
    snapshot_digest: str | None = None
    transcript_prefix_path: str | None = None
    transcript_prefix_digest: str | None = None
    transcript_prefix_bytes: int | None = None
    feature_receipt_path: str | None = None
    preservation_receipt_path: str | None = None
    scope_violations: tuple[str, ...] = ()
    feature_verdict: str | None = None
    preservation_verdict: str | None = None
    turn_count: int = 0
    tool_count: int = 0
    context_events: int = 0
    contamination: dict | None = None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """The durable record of one session attempt."""

    version: int
    task: str
    adapter_command: tuple[str, ...]
    base_commit: str
    code: SessionCode
    conversation_id: str | None = None
    terminal_step: str | None = None
    message: str | None = None
    provenance: dict[str, str] = field(default_factory=dict)
    retained_path: str | None = None
    steps: tuple[StepRecord, ...] = ()

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ValueError("session record version must be 1")
        if not isinstance(self.code, SessionCode):
            raise ValueError("session record code must be a SessionCode")


def deepest_feature_milestone(
    spec: SessionSpec, steps: Sequence[StepRecord]
) -> int:
    """The deepest passing feature milestone, zero if none passed.

    A feature milestone is the deepest checkpoint whose cumulative
    selection passed: every feature step's record is scanned, because a
    LATER checkpoint passing its cumulative union means the model
    repaired work an EARLIER checkpoint had not yet finished — stopping
    at the first failure would score a repaired session as zero. A step
    counts only when its captured record settled in scope and its
    cumulative feature selection passed; review steps never advance the
    milestone.
    """
    by_id = {step.step_id: step for step in steps}
    milestone = 0
    for index, spec_step in enumerate(spec.steps):
        if spec_step.kind != "feature":
            continue
        record = by_id.get(spec_step.id)
        if (
            record is not None
            and record.outcome == "settled"
            and not record.scope_violations
            and record.feature_verdict == "pass"
        ):
            milestone = index + 1
    return milestone


def session_outcomes(
    record: SessionRecord, spec: SessionSpec
) -> dict[str, bool | int | str | None]:
    """Derive the top-level outcomes without conflating them."""
    settled = all(step.outcome == "settled" for step in record.steps)
    return {
        "all_prompts_settled": settled
        and len(record.steps) == len(spec.steps),
        "deepest_milestone": deepest_feature_milestone(spec, record.steps),
        "retained_nonempty_patch": any(
            (step.patch_bytes or 0) > 0 for step in record.steps
        ),
        "all_scope_valid": all(
            not step.scope_violations for step in record.steps
        ),
        "last_preservation_verdict": (
            record.steps[-1].preservation_verdict if record.steps else None
        ),
        "grading_available": (
            record.code not in _NOT_CAPTURED
            and record.code != SessionCode.GRADE_UNAVAILABLE
            and bool(record.steps)
        ),
    }


def write_session_record(path: Path, record: SessionRecord) -> None:
    """Write the record durably: fsync the file, then replace atomically.

    Mirror write_receipt's shape rule: the per-step ``contamination`` key
    is omitted when a step carries no finding (pre-V7 records and
    non-hidden sessions), and loaded as None either way.
    """
    data = asdict(record)
    for step in data["steps"]:
        if step.get("contamination") is None:
            del step["contamination"]
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, indent=2) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_session_record(path: Path) -> SessionRecord:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("session record is not an object")
    if data.get("version") != 1:
        raise ValueError("session record version must be 1")
    steps = tuple(
        StepRecord(
            step_id=str(step["step_id"]),
            prompt_digest=str(step["prompt_digest"]),
            outcome=str(step["outcome"]),
            patch_path=step.get("patch_path"),
            patch_digest=step.get("patch_digest"),
            patch_bytes=step.get("patch_bytes"),
            snapshot_path=step.get("snapshot_path"),
            snapshot_digest=step.get("snapshot_digest"),
            transcript_prefix_path=step.get("transcript_prefix_path"),
            transcript_prefix_digest=step.get("transcript_prefix_digest"),
            transcript_prefix_bytes=step.get("transcript_prefix_bytes"),
            feature_receipt_path=step.get("feature_receipt_path"),
            preservation_receipt_path=step.get("preservation_receipt_path"),
            scope_violations=tuple(step.get("scope_violations", ())),
            feature_verdict=step.get("feature_verdict"),
            preservation_verdict=step.get("preservation_verdict"),
            turn_count=step.get("turn_count", 0),
            tool_count=step.get("tool_count", 0),
            context_events=step.get("context_events", 0),
            contamination=step.get("contamination"),
        )
        for step in data.pop("steps", ())
    )
    data["code"] = SessionCode(data["code"])
    for name in ("adapter_command",):
        data[name] = tuple(data[name])
    return SessionRecord(**data, steps=steps)
