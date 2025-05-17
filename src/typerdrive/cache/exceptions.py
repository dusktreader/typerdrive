"""
Provide exceptions specific to the cache feature of `typerdrive`.
"""

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class CacheError(TyperdriveError):
    """
    The base exception for cache errors.
    """
    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class CacheInitError(CacheError):
    """
    Indicate that there was a problem initializing the cache.
    """


class CacheStoreError(CacheError):
    """
    Indicate that there was a problem storing data in the cache.
    """


class CacheClearError(CacheError):
    """
    Indicate that there was a problem clearing data from the cache.
    """


class CacheLoadError(CacheError):
    """
    Indicate that there was a problem loading data from the cache.
    """
