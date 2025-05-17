"""
Provide exceptions specific to the client feature of `typerdrive`.
"""

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class ClientError(TyperdriveError):
    """
    The base exception for client errors.
    """
    exit_code: ExitCode = ExitCode.GENERAL_ERROR
