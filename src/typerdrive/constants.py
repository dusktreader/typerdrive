"""
Provide some constants for the project.
"""

from enum import Flag, IntEnum, StrEnum, auto


class Validation(Flag):
    """
    Defines when validation of settings should happen in the `@attach_settings` context manager.
    """

    BEFORE = auto()
    AFTER = auto()
    BOTH = BEFORE | AFTER
    NEVER = 0


class ExitCode(IntEnum):
    """
    Maps exit codes for the application.
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    CANNOT_EXECUTE = 126
    INTERNAL_ERROR = 128


class EvictionPolicy(StrEnum):
    """
    Cache eviction policies for managing cache size limits.
    """

    LEAST_RECENTLY_USED = "least-recently-used"
    LEAST_FREQUENTLY_USED = "least-frequently-used"
    NONE = "none"
