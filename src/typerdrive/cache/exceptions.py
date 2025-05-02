from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class CacheError(TyperdriveError):
    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class CacheInitError(CacheError):
    pass


class CacheStoreError(CacheError):
    pass


class CacheClearError(CacheError):
    pass


class CacheLoadError(CacheError):
    pass
