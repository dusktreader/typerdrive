"""
Provide exceptions specific to the logging feature of `typerdrive`.
"""

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class LoggingError(TyperdriveError):
    """
    The base exception for logging errors.
    """
    exit_code: ExitCode = ExitCode.GENERAL_ERROR
