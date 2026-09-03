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
    transcript_prefix_path: str | None = None
    feature_receipt_path: str | None = None
    preservation_receipt_path: str | None = None
    scope_violations: tuple[str, ...] = ()
    feature_verdict: str | None = None
    preservation_verdict: str | None = None
    turn_count: int = 0
    tool_count: int = 0
    context_events: int = 0


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

    Feature steps advance only when their captured record settled in
    scope and its cumulative feature selection passed; review steps
    never advance the milestone.
    """
    by_id = {step.step_id: step for step in steps}
    milestone = 0
    for spec_step in spec.steps:
        if spec_step.kind != "feature":
            continue
        record = by_id.get(spec_step.id)
        if (
            record is None
            or record.outcome != "settled"
            or record.scope_violations
            or record.feature_verdict != "pass"
        ):
            break
        milestone += 1
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
    """Write the record durably: fsync the file, then replace atomically."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(asdict(record), indent=2) + "\n")
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
            **{
                **step,
                "scope_violations": tuple(step.get("scope_violations", ())),
            }
        )
        for step in data.pop("steps", ())
    )
    data["code"] = SessionCode(data["code"])
    for name in ("adapter_command",):
        data[name] = tuple(data[name])
    return SessionRecord(**data, steps=steps)
