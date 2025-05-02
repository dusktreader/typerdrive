from enum import Flag, IntEnum, auto


class Validation(Flag):
    """
    Defines whether validation should happen "before", "after", "both", or "none"
    """

    BEFORE = auto()
    AFTER = auto()
    BOTH = BEFORE | AFTER
    NONE = 0


class ExitCode(IntEnum):
    """
    Maps exit codes for the application.
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    CANNOT_EXECUTE = 126
    INTERNAL_ERROR = 128
