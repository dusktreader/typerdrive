from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class ClientError(TyperdriveError):
    exit_code: ExitCode = ExitCode.GENERAL_ERROR
