"""The attempt record: the durable artifact attempt writes, E3-shaped.

Parallel to the capture record: the exit code stays coarse; the record is
precise. It references the receipt by path and repeats the verdict at top
level.
"""

import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum, auto
from pathlib import Path

from satyrn_evals.receipt import write_json_atomically
from satyrn_evals.verdict import Verdict

_LEGACY_FIELDS = frozenset(
    {
        "version",
        "outcome",
        "code",
        "message",
        "task",
        "command",
        "command_exit",
        "patch_path",
        "transcript_path",
        "patch_digest",
        "transcript_digest",
        "verdict",
        "receipt_path",
    }
)
_V4_FIELDS = frozenset({"workspace_base_sha", "retained_path"})
_V7_FIELDS = frozenset({"attempt_dir"})
_V9_FIELDS = frozenset({"timeout"})
# V11a: rung provenance. `rung` is null when the default `contract` was
# exported; `contract_digest` names the exact text either way.
_V11_FIELDS = frozenset({"rung", "contract_digest"})


class DeadlinePhase(StrEnum):
    """The lifecycle phase that first observed a whole-attempt expiry."""

    SETUP = "setup"
    COMMAND = "command"
    PRESERVATION = "preservation"
    GRADING = "grading"
    CLEANUP = "cleanup"


@dataclass(frozen=True, slots=True)
class DeadlineProvenance:
    """A whole-attempt deadline's durable, non-verdict observation."""

    timeout: float
    phase: DeadlinePhase
    elapsed: float
    workspace_retained: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "phase", DeadlinePhase(self.phase))
        for name in ("timeout", "elapsed"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"deadline {name} must be a finite number")
            if value <= 0:
                raise ValueError(f"deadline {name} must be greater than zero")
            object.__setattr__(self, name, float(value))
        if self.elapsed < self.timeout:
            raise ValueError("deadline elapsed must be at least its timeout")
        if type(self.workspace_retained) is not bool:
            raise ValueError("deadline workspace_retained must be a boolean")


# V12 records add the configured whole-attempt timeout. A V13 record adds
# expiry provenance only when that limit actually expires.
_V12_FIELDS = frozenset({"attempt_timeout"})
_V13_FIELDS = frozenset({"deadline"})


class AttemptOutcome(StrEnum):
    ATTEMPTED = "attempted"
    REFUSED = "refused"


class AttemptCode(StrEnum):
    """Stable detailed outcomes stored in attempt records."""

    OK = "OK"
    NO_PATCH = "NO_PATCH"
    PATCH_INVALID = "PATCH_INVALID"
    TRANSCRIPT_MISSING = "TRANSCRIPT_MISSING"
    TRANSCRIPT_EMPTY = "TRANSCRIPT_EMPTY"
    WORKSPACE_FAILED = "WORKSPACE_FAILED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    REPEAT_LIMIT = "REPEAT_LIMIT"
    MODEL_ERROR = "MODEL_ERROR"
    CLEANUP_FAILED = "CLEANUP_FAILED"
    GRADE_FAILED = "GRADE_FAILED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"


class _Presence(Enum):
    REQUIRED = auto()
    FORBIDDEN = auto()
    OPTIONAL = auto()


class _ArtifactPolicy(Enum):
    ANY = auto()
    NONE = auto()
    PATCH_ONLY = auto()
    BOTH = auto()


@dataclass(frozen=True, slots=True)
class _AttemptPolicy:
    outcome: AttemptOutcome
    command_exit: _Presence
    base_sha: _Presence
    retained_path: _Presence
    artifacts: _ArtifactPolicy
    verdict: _Presence = _Presence.FORBIDDEN
    receipt: _Presence = _Presence.FORBIDDEN
    deadline: _Presence = _Presence.OPTIONAL


_ATTEMPT_POLICIES: dict[AttemptCode, _AttemptPolicy] = {
    AttemptCode.OK: _AttemptPolicy(
        AttemptOutcome.ATTEMPTED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        # Cleanup is deliberately later than grading.  If its safety cannot
        # be confirmed, keep the hook-derived outcome and receipt, and name
        # the retained workspace as independent recovery provenance.
        _Presence.OPTIONAL,
        _ArtifactPolicy.BOTH,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
    ),
    AttemptCode.NO_PATCH: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.PATCH_INVALID: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.TRANSCRIPT_MISSING: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.PATCH_ONLY,
    ),
    AttemptCode.TRANSCRIPT_EMPTY: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.BOTH,
    ),
    AttemptCode.WORKSPACE_FAILED: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.FORBIDDEN,
        _Presence.OPTIONAL,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.NONE,
    ),
    AttemptCode.COMMAND_TIMEOUT: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.FORBIDDEN,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.REPEAT_LIMIT: _AttemptPolicy(
        # Stopped by the repeated-call spending rule, exactly as a timeout
        # stops a cell: no exit code, artifacts harvested if the adapter
        # wrote any. Its own code rather than NO_PATCH because a cell we
        # stopped is not the same event as one that refused on its own,
        # and pooling the two is the maintainer's call, not this table's.
        AttemptOutcome.REFUSED,
        _Presence.FORBIDDEN,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.MODEL_ERROR: _AttemptPolicy(
        # The inference substrate failed underneath a well-formed request,
        # so the cell measured nothing. The command itself ran and exited,
        # unlike a timeout, hence a required exit code. Its own code
        # rather than NO_PATCH because an infrastructure failure counted
        # as a refusal understates the arm -- the defect that voided the
        # first V11c mini-probe. n stays intact; excluding it from a
        # success count is the maintainer's call, not this table's.
        AttemptOutcome.REFUSED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.CLEANUP_FAILED: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.OPTIONAL,
        _Presence.OPTIONAL,
        _Presence.REQUIRED,
        _ArtifactPolicy.ANY,
    ),
    AttemptCode.GRADE_FAILED: _AttemptPolicy(
        AttemptOutcome.ATTEMPTED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.OPTIONAL,
        _ArtifactPolicy.BOTH,
    ),
    AttemptCode.DEADLINE_EXCEEDED: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.OPTIONAL,
        _Presence.OPTIONAL,
        _Presence.OPTIONAL,
        _ArtifactPolicy.ANY,
        deadline=_Presence.REQUIRED,
    ),
}

_LEGACY_CODES = frozenset(
    {
        AttemptCode.OK,
        AttemptCode.NO_PATCH,
        AttemptCode.PATCH_INVALID,
        AttemptCode.TRANSCRIPT_MISSING,
        AttemptCode.TRANSCRIPT_EMPTY,
    }
)


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    version: int
    outcome: AttemptOutcome
    code: AttemptCode
    message: str
    task: str
    command: tuple[str, ...]
    command_exit: int | None
    patch_path: str | None
    transcript_path: str | None
    patch_digest: str | None
    transcript_digest: str | None
    verdict: Verdict | None
    receipt_path: str | None
    timeout: float | None = None
    rung: str | None = None
    contract_digest: str | None = None
    workspace_base_sha: str | None = None
    retained_path: str | None = None
    attempt_dir: str | None = None
    deadline: DeadlineProvenance | None = None
    attempt_timeout: float | None = None
    _legacy: bool = field(default=False, repr=False, compare=False, kw_only=True)

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", AttemptOutcome(self.outcome))
        object.__setattr__(self, "code", AttemptCode(self.code))
        policy = _ATTEMPT_POLICIES[self.code]
        if self.verdict is not None:
            object.__setattr__(self, "verdict", Verdict(self.verdict))
        if type(self.version) is not int or self.version != 1:
            raise ValueError("attempt record version must be 1")
        if not _nonempty_text(self.message) or not _nonempty_text(self.task):
            raise ValueError("attempt record text and command must be non-empty")
        if (
            not isinstance(self.command, tuple)
            or not self.command
            or any(not _nonempty_text(value) for value in self.command)
        ):
            raise ValueError(
                "attempt record text and command must be non-empty strings"
            )
        if self.command_exit is not None and type(self.command_exit) is not int:
            raise ValueError("attempt record command_exit must be an integer or null")
        for name in (
            "patch_path",
            "transcript_path",
            "receipt_path",
            "retained_path",
        ):
            value = getattr(self, name)
            if value is not None and not _nonempty_text(value):
                raise ValueError(f"attempt record {name} must be non-empty or null")
        if self.deadline is not None and not isinstance(
            self.deadline, DeadlineProvenance
        ):
            raise ValueError(
                "attempt record deadline must be DeadlineProvenance or null"
            )
        for path_name, digest_name in (
            ("patch_path", "patch_digest"),
            ("transcript_path", "transcript_digest"),
        ):
            path = getattr(self, path_name)
            digest = getattr(self, digest_name)
            if path is None and digest is not None:
                raise ValueError(
                    f"attempt record {path_name} and {digest_name} must agree"
                )
            allows_unhashed_artifact = (
                self.deadline is not None
                and self.deadline.phase
                in (DeadlinePhase.COMMAND, DeadlinePhase.PRESERVATION)
            )
            if path is not None and digest is None and not allows_unhashed_artifact:
                raise ValueError(
                    f"attempt record {path_name} and {digest_name} must agree"
                )
            if digest is not None and not _hex_digest(digest, 64):
                raise ValueError(
                    f"attempt record {digest_name} must be a SHA-256 digest"
                )
        if self.workspace_base_sha is not None and not (
            _hex_digest(self.workspace_base_sha, 40)
            or _hex_digest(self.workspace_base_sha, 64)
        ):
            raise ValueError(
                "attempt record workspace_base_sha must be a Git object ID"
            )
        if self.timeout is not None and type(self.timeout) not in (int, float):
            raise ValueError("attempt record timeout must be a positive finite number")
        if self.timeout is not None:
            if not math.isfinite(self.timeout) or self.timeout <= 0:
                raise ValueError(
                    "attempt record timeout must be a positive finite number"
                )
            if type(self.timeout) is not float:
                object.__setattr__(self, "timeout", float(self.timeout))
        if self.attempt_timeout is not None and type(self.attempt_timeout) not in (
            int,
            float,
        ):
            raise ValueError(
                "attempt record attempt_timeout must be a positive finite number"
            )
        if self.attempt_timeout is not None:
            if not math.isfinite(self.attempt_timeout) or self.attempt_timeout <= 0:
                raise ValueError(
                    "attempt record attempt_timeout must be a positive finite number"
                )
            if type(self.attempt_timeout) is not float:
                object.__setattr__(self, "attempt_timeout", float(self.attempt_timeout))
        if self.rung is not None and not _nonempty_text(self.rung):
            raise ValueError("attempt record rung must be non-empty or null")
        if self.contract_digest is not None and not _hex_digest(
            self.contract_digest, 64
        ):
            raise ValueError("attempt record contract_digest must be a SHA-256 digest")
        if self.rung is not None and self.contract_digest is None:
            raise ValueError("attempt record rung requires a contract_digest")
        if self.attempt_timeout is not None and (
            self.timeout is None
            or self.contract_digest is None
            or self.attempt_dir is None
        ):
            raise ValueError(
                "attempt timeout requires a current timeout, contract digest, and attempt directory"
            )
        if self.deadline is not None:
            if self.attempt_timeout is None:
                raise ValueError("deadline provenance requires an attempt timeout")
            if self.deadline.timeout != self.attempt_timeout:
                raise ValueError("deadline timeout must match attempt_timeout")
        if self.outcome is not policy.outcome:
            raise ValueError(f"{self.code} requires outcome {policy.outcome}")
        if policy.verdict is _Presence.REQUIRED and self.verdict is None:
            raise ValueError(f"{self.code} requires a verdict")
        if policy.verdict is _Presence.FORBIDDEN and self.verdict is not None:
            raise ValueError(f"{self.code} requires no verdict")
        if policy.receipt is _Presence.REQUIRED and self.receipt_path is None:
            raise ValueError(f"{self.code} requires a receipt path")
        if policy.receipt is _Presence.FORBIDDEN and self.receipt_path is not None:
            raise ValueError(f"{self.code} requires no receipt path")
        if policy.deadline is _Presence.REQUIRED and self.deadline is None:
            raise ValueError(f"{self.code} requires deadline provenance")
        if self.deadline is not None:
            allowed_phases = {
                # Whole deadline is controlling if it fires before another
                # command outcome is observed.
                AttemptCode.DEADLINE_EXCEEDED: frozenset(
                    {
                        DeadlinePhase.SETUP,
                        DeadlinePhase.COMMAND,
                        DeadlinePhase.PRESERVATION,
                        DeadlinePhase.CLEANUP,
                    }
                ),
                # A prior command stop remains the execution outcome if the
                # whole budget only expires while preserving available files.
                AttemptCode.COMMAND_TIMEOUT: frozenset(
                    {DeadlinePhase.PRESERVATION, DeadlinePhase.CLEANUP}
                ),
                AttemptCode.REPEAT_LIMIT: frozenset(
                    {DeadlinePhase.PRESERVATION, DeadlinePhase.CLEANUP}
                ),
                # A record written before cleanup keeps its independent
                # execution/verdict outcome if the budget expires there.
                AttemptCode.OK: frozenset(
                    {DeadlinePhase.GRADING, DeadlinePhase.CLEANUP}
                ),
                AttemptCode.GRADE_FAILED: frozenset(
                    {DeadlinePhase.GRADING, DeadlinePhase.CLEANUP}
                ),
                AttemptCode.NO_PATCH: frozenset({DeadlinePhase.CLEANUP}),
                AttemptCode.PATCH_INVALID: frozenset({DeadlinePhase.CLEANUP}),
                AttemptCode.TRANSCRIPT_MISSING: frozenset({DeadlinePhase.CLEANUP}),
                AttemptCode.TRANSCRIPT_EMPTY: frozenset({DeadlinePhase.CLEANUP}),
                AttemptCode.WORKSPACE_FAILED: frozenset(
                    {DeadlinePhase.PRESERVATION, DeadlinePhase.CLEANUP}
                ),
                AttemptCode.MODEL_ERROR: frozenset({DeadlinePhase.CLEANUP}),
                AttemptCode.CLEANUP_FAILED: frozenset(
                    {DeadlinePhase.PRESERVATION, DeadlinePhase.CLEANUP}
                ),
            }
            if self.deadline.phase not in allowed_phases.get(self.code, frozenset()):
                raise ValueError(
                    f"{self.code} cannot carry deadline phase {self.deadline.phase}"
                )
            if self.code is AttemptCode.DEADLINE_EXCEEDED:
                match self.deadline.phase:
                    case DeadlinePhase.SETUP:
                        if (
                            self.command_exit is not None
                            or self.workspace_base_sha is not None
                            or self.patch_path is not None
                            or self.transcript_path is not None
                        ):
                            raise ValueError(
                                "setup deadline cannot contain command, workspace, or artifact evidence"
                            )
                    case DeadlinePhase.COMMAND:
                        if (
                            self.command_exit is not None
                            or self.workspace_base_sha is None
                        ):
                            raise ValueError(
                                "command deadline requires base SHA and no command exit"
                            )
                    case DeadlinePhase.PRESERVATION:
                        if self.command_exit is None or self.workspace_base_sha is None:
                            raise ValueError(
                                "preservation deadline requires base SHA and command exit"
                            )
            workspace_retained = self.retained_path is not None
            if self.deadline.workspace_retained is not workspace_retained:
                raise ValueError(
                    "deadline workspace_retained and retained_path must agree"
                )
        if self.attempt_dir is not None and not _nonempty_text(self.attempt_dir):
            raise ValueError("attempt record attempt_dir must be non-empty or null")
        if self._legacy:
            if self.code not in _LEGACY_CODES:
                raise ValueError(
                    "legacy attempt record cannot contain an operational code"
                )
            if self.workspace_base_sha is not None or self.retained_path is not None:
                raise ValueError(
                    "legacy attempt record cannot contain V4 workspace values"
                )
            if self.attempt_dir is not None:
                raise ValueError(
                    "legacy attempt record cannot contain an attempt directory"
                )
        if policy.command_exit is _Presence.REQUIRED and self.command_exit is None:
            raise ValueError(f"{self.code} requires command_exit")
        if policy.command_exit is _Presence.FORBIDDEN and self.command_exit is not None:
            raise ValueError(f"{self.code} requires null command_exit")
        if (
            not self._legacy
            and policy.base_sha is _Presence.REQUIRED
            and self.workspace_base_sha is None
        ):
            raise ValueError(f"{self.code} requires workspace_base_sha")
        if policy.retained_path is _Presence.REQUIRED and self.retained_path is None:
            raise ValueError(f"{self.code} requires retained_path")
        deadline_retention = (
            self.deadline is not None and self.deadline.workspace_retained
        )
        if (
            policy.retained_path is _Presence.FORBIDDEN
            and self.retained_path is not None
            and not deadline_retention
        ):
            raise ValueError("only CLEANUP_FAILED may retain a path")
        if policy.artifacts is _ArtifactPolicy.BOTH and (
            self.patch_path is None or self.transcript_path is None
        ):
            raise ValueError(f"{self.code} requires patch and transcript")
        if policy.artifacts is _ArtifactPolicy.PATCH_ONLY and (
            self.patch_path is None or self.transcript_path is not None
        ):
            raise ValueError(f"{self.code} requires a patch and no transcript")
        if policy.artifacts is _ArtifactPolicy.NONE and (
            self.patch_path is not None or self.transcript_path is not None
        ):
            raise ValueError(f"{self.code} cannot contain delivered artifacts")


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _hex_digest(value: object, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def write_attempt_record(path: Path, record: AttemptRecord) -> None:
    data = asdict(record)
    legacy = data.pop("_legacy")
    if data.get("attempt_dir") is None:
        data.pop("attempt_dir", None)
    if data.get("timeout") is None:
        data.pop("timeout", None)
    if data.get("attempt_timeout") is None:
        data.pop("attempt_timeout", None)
    if data.get("deadline") is None:
        data.pop("deadline", None)
    if data.get("contract_digest") is None:
        # The timeout precedent: an older-generation record writes the older
        # field set exactly. A null rung with a digest still writes both.
        for name in _V11_FIELDS:
            data.pop(name, None)
    if legacy:
        for name in _V4_FIELDS:
            data.pop(name)
    write_json_atomically(path, data)


def load_attempt_record(path: Path) -> AttemptRecord:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read attempt record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("attempt record is not an object")
    fields = frozenset(data)
    legacy_fields = _LEGACY_FIELDS
    v4_fields = _LEGACY_FIELDS | _V4_FIELDS
    v7_fields = v4_fields | _V7_FIELDS
    v9_fields = v7_fields | _V9_FIELDS
    current_fields = v9_fields | _V11_FIELDS
    v12_fields = current_fields | _V12_FIELDS
    v13_fields = v12_fields | _V13_FIELDS
    if fields not in {
        legacy_fields,
        v4_fields,
        v7_fields,
        v9_fields,
        current_fields,
        v12_fields,
        v13_fields,
    }:
        if missing := _LEGACY_FIELDS - fields:
            raise ValueError(f"attempt record missing a field: {sorted(missing)}")
        if unexpected := fields - v13_fields:
            raise ValueError(
                f"attempt record has unexpected fields: {sorted(unexpected)}"
            )
        raise ValueError(
            "attempt record must contain both V4 workspace fields or neither"
        )
    if "timeout" in fields and data.get("timeout") is None:
        raise ValueError("current attempt record requires a timeout")
    if "attempt_timeout" in fields and data.get("attempt_timeout") is None:
        raise ValueError("current attempt record requires an attempt_timeout")
    if "contract_digest" in fields and data.get("contract_digest") is None:
        raise ValueError("current attempt record requires a contract_digest")
    deadline = None
    if "deadline" in fields:
        deadline = data["deadline"]
        if not isinstance(deadline, dict):
            raise ValueError("attempt record deadline is not an object")
        try:
            deadline = DeadlineProvenance(**deadline)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid attempt record deadline: {exc}") from exc
    legacy = fields == _LEGACY_FIELDS
    command = data["command"]
    if not isinstance(command, list):
        raise ValueError("attempt record command is not an array")
    try:
        outcome = AttemptOutcome(data["outcome"])
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad outcome: {e}") from e
    try:
        verdict = Verdict(data["verdict"]) if data.get("verdict") is not None else None
    except (KeyError, ValueError) as e:
        raise ValueError(f"bad verdict: {e}") from e
    try:
        return AttemptRecord(
            version=data["version"],
            outcome=outcome,
            code=AttemptCode(data["code"]),
            message=data["message"],
            task=data["task"],
            command=tuple(command),
            command_exit=data["command_exit"],
            patch_path=data.get("patch_path"),
            transcript_path=data.get("transcript_path"),
            patch_digest=data.get("patch_digest"),
            transcript_digest=data.get("transcript_digest"),
            verdict=verdict,
            receipt_path=data.get("receipt_path"),
            timeout=data.get("timeout"),
            rung=data.get("rung"),
            contract_digest=data.get("contract_digest"),
            workspace_base_sha=data.get("workspace_base_sha"),
            retained_path=data.get("retained_path"),
            attempt_dir=data.get("attempt_dir"),
            deadline=deadline,
            attempt_timeout=data.get("attempt_timeout"),
            _legacy=legacy,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"invalid attempt record: {e}") from e
