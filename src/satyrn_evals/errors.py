"""Error hierarchy carrying exit codes. Usage errors are 2; operational errors are 3."""

from enum import StrEnum


class CaptureCode(StrEnum):
    """Stable detailed outcomes stored in capture records."""

    OK = "OK"
    REPO_DIRTY = "REPO_DIRTY"
    NO_PARENT = "NO_PARENT"
    NO_SOURCE_CHANGE = "NO_SOURCE_CHANGE"
    TASK_EXISTS = "TASK_EXISTS"
    ORACLE_ENV = "ORACLE_ENV"
    NO_DISCRIMINATING_TESTS = "NO_DISCRIMINATING_TESTS"
    NOT_WINNABLE = "NOT_WINNABLE"
    GIT_FAILED = "GIT_FAILED"
    ARTIFACT_FAILED = "ARTIFACT_FAILED"
    CLEANUP_FAILED = "CLEANUP_FAILED"


class SatyrnError(Exception):
    exit_code = 3


class UsageError(SatyrnError):
    exit_code = 2


class ManifestError(UsageError):
    pass


class PatchReadError(UsageError):
    pass


class PatchParseError(UsageError):
    pass


class PatchRejected(SatyrnError):
    pass


class ApplyError(SatyrnError):
    pass


class OracleError(SatyrnError):
    pass


class HookError(SatyrnError):
    pass


class CaptureUsageError(UsageError):
    """Exit 2: the source repo or SHA admits no operation; no record is written."""


class CaptureRefused(SatyrnError):
    """Exit 3: a check or git/cleanup operation failed; a capture record names the code."""

    code: CaptureCode = CaptureCode.GIT_FAILED


class RepoDirty(CaptureRefused):
    code = CaptureCode.REPO_DIRTY


class NoParent(CaptureRefused):
    code = CaptureCode.NO_PARENT


class NoSourceChange(CaptureRefused):
    code = CaptureCode.NO_SOURCE_CHANGE


class TaskExists(CaptureRefused):
    code = CaptureCode.TASK_EXISTS


class OracleEnv(CaptureRefused):
    code = CaptureCode.ORACLE_ENV


class NoDiscriminatingTests(CaptureRefused):
    code = CaptureCode.NO_DISCRIMINATING_TESTS


class NotWinnable(CaptureRefused):
    code = CaptureCode.NOT_WINNABLE


class GitFailed(CaptureRefused):
    code = CaptureCode.GIT_FAILED


class ArtifactFailed(CaptureRefused):
    code = CaptureCode.ARTIFACT_FAILED


class CleanupFailed(CaptureRefused):
    code = CaptureCode.CLEANUP_FAILED
