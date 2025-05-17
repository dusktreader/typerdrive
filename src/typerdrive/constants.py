"""
Provide some constants for the project.
"""

from enum import Flag, IntEnum, auto


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
