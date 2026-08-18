"""Error hierarchy carrying exit codes. Usage errors are 2; operational errors are 3."""


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

    code: str = "GIT_FAILED"


class RepoDirty(CaptureRefused):
    code = "REPO_DIRTY"


class NoParent(CaptureRefused):
    code = "NO_PARENT"


class NoSourceChange(CaptureRefused):
    code = "NO_SOURCE_CHANGE"


class TaskExists(CaptureRefused):
    code = "TASK_EXISTS"


class OracleEnv(CaptureRefused):
    code = "ORACLE_ENV"


class NoDiscriminatingTests(CaptureRefused):
    code = "NO_DISCRIMINATING_TESTS"


class NotWinnable(CaptureRefused):
    code = "NOT_WINNABLE"


class GitFailed(CaptureRefused):
    code = "GIT_FAILED"


class CleanupFailed(CaptureRefused):
    code = "CLEANUP_FAILED"
