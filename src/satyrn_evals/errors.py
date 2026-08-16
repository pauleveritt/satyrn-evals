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
