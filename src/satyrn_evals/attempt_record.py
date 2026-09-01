"""The attempt record: the durable artifact attempt writes, E3-shaped.

Parallel to the capture record: the exit code stays coarse; the record is
precise. It references the receipt by path and repeats the verdict at top
level.
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum, auto
from pathlib import Path

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
    CLEANUP_FAILED = "CLEANUP_FAILED"


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


_ATTEMPT_POLICIES: dict[AttemptCode, _AttemptPolicy] = {
    AttemptCode.OK: _AttemptPolicy(
        AttemptOutcome.ATTEMPTED,
        _Presence.REQUIRED,
        _Presence.REQUIRED,
        _Presence.FORBIDDEN,
        _ArtifactPolicy.BOTH,
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
    AttemptCode.CLEANUP_FAILED: _AttemptPolicy(
        AttemptOutcome.REFUSED,
        _Presence.OPTIONAL,
        _Presence.OPTIONAL,
        _Presence.REQUIRED,
        _ArtifactPolicy.ANY,
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
    workspace_base_sha: str | None = None
    retained_path: str | None = None
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
        for path_name, digest_name in (
            ("patch_path", "patch_digest"),
            ("transcript_path", "transcript_digest"),
        ):
            path = getattr(self, path_name)
            digest = getattr(self, digest_name)
            if (path is None) is not (digest is None):
                raise ValueError(f"attempt record {path_name} and {digest_name} must agree")
            if digest is not None and not _hex_digest(digest, 64):
                raise ValueError(f"attempt record {digest_name} must be a SHA-256 digest")
        if self.workspace_base_sha is not None and not (
            _hex_digest(self.workspace_base_sha, 40)
            or _hex_digest(self.workspace_base_sha, 64)
        ):
            raise ValueError("attempt record workspace_base_sha must be a Git object ID")
        if self.outcome is not policy.outcome:
            raise ValueError(f"{self.code} requires outcome {policy.outcome}")
        if policy.outcome is AttemptOutcome.ATTEMPTED:
            if self.verdict is None or self.receipt_path is None:
                raise ValueError("attempted record requires a verdict and receipt path")
        elif self.verdict is not None or self.receipt_path is not None:
            raise ValueError("refused record requires no verdict or receipt path")
        if self._legacy:
            if self.code not in _LEGACY_CODES:
                raise ValueError("legacy attempt record cannot contain an operational code")
            if self.workspace_base_sha is not None or self.retained_path is not None:
                raise ValueError("legacy attempt record cannot contain V4 workspace values")
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
        if policy.retained_path is _Presence.FORBIDDEN and self.retained_path is not None:
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
    if legacy:
        for name in _V4_FIELDS:
            data.pop(name)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_attempt_record(path: Path) -> AttemptRecord:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"cannot read attempt record: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("attempt record is not an object")
    fields = frozenset(data)
    current_fields = _LEGACY_FIELDS | _V4_FIELDS
    if fields not in {_LEGACY_FIELDS, current_fields}:
        if missing := _LEGACY_FIELDS - fields:
            raise ValueError(f"attempt record missing a field: {sorted(missing)}")
        if unexpected := fields - current_fields:
            raise ValueError(f"attempt record has unexpected fields: {sorted(unexpected)}")
        raise ValueError("attempt record must contain both V4 workspace fields or neither")
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
            workspace_base_sha=data.get("workspace_base_sha"),
            retained_path=data.get("retained_path"),
            _legacy=legacy,
        )
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"invalid attempt record: {e}") from e
