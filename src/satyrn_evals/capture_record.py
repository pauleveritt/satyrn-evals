"""The capture record: the durable artifact capture writes, E3-shaped.

Like V1's receipt, the record is the authoritative result; the CLI's exit
code is coarse by design. `merge_cleanup_failure` implements E3's
precedence: a cleanup failure replaces any pending result.
"""

import contextlib
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Literal, cast

from satyrn_evals.errors import CaptureCode

type CheckName = Literal[
    "source_preflight", "base_oracle", "un_done_at_base", "winnable"
]
type CheckState = Literal["passed", "failed", "not-run"]
type CheckOutcomes = dict[CheckName, CheckState]
CHECK_NAMES: tuple[CheckName, ...] = (
    "source_preflight",
    "base_oracle",
    "un_done_at_base",
    "winnable",
)
_VALID_CHECK_STATES = frozenset({"passed", "failed", "not-run"})
_RECORD_FIELDS = frozenset(
    {
        "version",
        "outcome",
        "code",
        "message",
        "repo",
        "base_sha",
        "fix_sha",
        "task_dir",
        "oracle",
        "expected_test_ids",
        "check_outcomes",
    }
)


class CaptureOutcome(StrEnum):
    CAPTURED = "captured"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True, init=False)
class CaptureRecord:
    version: int
    outcome: CaptureOutcome
    code: CaptureCode
    message: str
    repo: str
    base_sha: str | None
    fix_sha: str | None
    task_dir: str | None
    oracle: tuple[str, ...] | None
    expected_test_ids: tuple[str, ...] | None
    check_outcomes: CheckOutcomes

    def __init__(
        self,
        version: int,
        outcome: CaptureOutcome | str,
        code: CaptureCode | str,
        message: str,
        repo: str,
        base_sha: str | None,
        fix_sha: str | None,
        task_dir: str | None,
        oracle: tuple[str, ...] | None,
        expected_test_ids: tuple[str, ...] | None,
        check_outcomes: Mapping[CheckName, CheckState],
    ) -> None:
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "outcome", CaptureOutcome(outcome))
        object.__setattr__(self, "code", CaptureCode(code))
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "repo", repo)
        object.__setattr__(self, "base_sha", base_sha)
        object.__setattr__(self, "fix_sha", fix_sha)
        object.__setattr__(self, "task_dir", task_dir)
        object.__setattr__(self, "oracle", oracle)
        object.__setattr__(self, "expected_test_ids", expected_test_ids)
        object.__setattr__(
            self, "check_outcomes", cast("CheckOutcomes", dict(check_outcomes))
        )
        _validate_record(self)


def write_capture_record(path: Path, record: CaptureRecord) -> None:
    """Atomically publish a new record without following or replacing a path."""
    _validate_record(record)
    content = json.dumps(asdict(record), indent=2) + "\n"
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        try:
            with os.fdopen(fd, "w") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary_path, path, follow_symlinks=False)
        except BaseException:
            with contextlib.suppress(OSError):
                # An asynchronous exception can arrive after link() publishes.
                # Remove the destination only when it is our temporary inode.
                if os.path.samestat(path.stat(), temporary_path.stat()):
                    path.unlink()
            raise
    finally:
        with contextlib.suppress(OSError):
            temporary_path.unlink()


def _required_string(data: dict[object, object], field: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _optional_string(data: dict[object, object], field: str) -> str | None:
    value = data[field]
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be null or a non-empty string")
    return value


def _optional_string_sequence(
    data: dict[object, object], field: str
) -> tuple[str, ...] | None:
    value = data[field]
    if value is None:
        return None
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} must be null or a list of non-empty strings")
    return tuple(value)


def _check_outcomes(value: object) -> CheckOutcomes:
    if not isinstance(value, dict):
        raise ValueError("check_outcomes must be an object")
    if set(value) != set(CHECK_NAMES) or not all(
        isinstance(state, str) and state in _VALID_CHECK_STATES
        for state in value.values()
    ):
        raise ValueError(
            "check_outcomes must name all four checks as passed/failed/not-run"
        )
    return cast("CheckOutcomes", dict(value))


def _validate_outcome_invariants(record: CaptureRecord) -> None:
    artifact_fields = (
        record.base_sha,
        record.fix_sha,
        record.task_dir,
        record.oracle,
        record.expected_test_ids,
    )
    if record.outcome is CaptureOutcome.CAPTURED:
        if record.code is not CaptureCode.OK:
            raise ValueError("captured record code must be OK")
        if any(value is None for value in artifact_fields):
            raise ValueError("captured record must name all captured artifacts")
        if not record.oracle or not record.expected_test_ids:
            raise ValueError(
                "captured record oracle and expected_test_ids must be non-empty"
            )
        if any(state != "passed" for state in record.check_outcomes.values()):
            raise ValueError("captured record checks must all be passed")
        return
    if record.code is CaptureCode.OK:
        raise ValueError("refused record code must not be OK")
    if (record.oracle is None) != (record.expected_test_ids is None):
        raise ValueError(
            "oracle and expected_test_ids must both be null or both be present"
        )
    if record.task_dir is not None and record.code is not CaptureCode.CLEANUP_FAILED:
        raise ValueError("only CLEANUP_FAILED refusal may name a written task_dir")
    if record.task_dir is not None and (
        not record.oracle or not record.expected_test_ids
    ):
        raise ValueError("refusal with task_dir must name oracle and expected_test_ids")


def _validate_record(record: CaptureRecord) -> None:
    if type(record.version) is not int or record.version != 1:
        raise ValueError("version must be integer 1")
    for field, value in (("message", record.message), ("repo", record.repo)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field} must be a non-empty string")
    for field, value in (
        ("base_sha", record.base_sha),
        ("fix_sha", record.fix_sha),
        ("task_dir", record.task_dir),
    ):
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{field} must be null or a non-empty string")
    for field, value in (
        ("oracle", record.oracle),
        ("expected_test_ids", record.expected_test_ids),
    ):
        if value is not None and (
            not isinstance(value, tuple)
            or not all(isinstance(item, str) and item for item in value)
        ):
            raise ValueError(f"{field} must be null or a tuple of non-empty strings")
    _check_outcomes(record.check_outcomes)
    _validate_outcome_invariants(record)


def load_capture_record(path: Path) -> CaptureRecord:
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read capture record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("capture record is not an object")
    missing = _RECORD_FIELDS - set(data)
    if missing:
        raise ValueError(f"capture record missing a field: {sorted(missing)[0]}")
    extra = set(data) - _RECORD_FIELDS
    if extra:
        raise ValueError(f"capture record has unexpected field: {sorted(extra)[0]}")
    if type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("version must be integer 1")
    try:
        outcome = CaptureOutcome(data["outcome"])
    except (TypeError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    try:
        code = CaptureCode(data["code"])
    except (TypeError, ValueError) as e:
        raise ValueError(f"bad code: {e}") from e
    record = CaptureRecord(
        version=data["version"],
        outcome=outcome,
        code=code,
        message=_required_string(data, "message"),
        repo=_required_string(data, "repo"),
        base_sha=_optional_string(data, "base_sha"),
        fix_sha=_optional_string(data, "fix_sha"),
        task_dir=_optional_string(data, "task_dir"),
        oracle=_optional_string_sequence(data, "oracle"),
        expected_test_ids=_optional_string_sequence(data, "expected_test_ids"),
        check_outcomes=_check_outcomes(data["check_outcomes"]),
    )
    return record


def merge_cleanup_failure(
    pending: CaptureRecord, cleanup_message: str
) -> CaptureRecord:
    """CLEANUP_FAILED replaces any pending result (E3 precedence).

    The outcome becomes REFUSED even when the pending record was captured:
    a retained worktree means the operation did not fully complete.
    """
    return replace(
        pending,
        outcome=CaptureOutcome.REFUSED,
        code=CaptureCode.CLEANUP_FAILED,
        message=f"{cleanup_message}; displaced {pending.code}: {pending.message}",
    )
