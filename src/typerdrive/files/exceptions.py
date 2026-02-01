"""
Provide exceptions specific to the files feature of `typerdrive`.
"""

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class FilesError(TyperdriveError):
    """
    The base exception for files errors.
    """

    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class FilesInitError(FilesError):
    """
    Indicate that there was a problem initializing the files storage.
    """


class FilesStoreError(FilesError):
    """
    Indicate that there was a problem storing a file.
    """


class FilesClearError(FilesError):
    """
    Indicate that there was a problem deleting a file.
    """


class FilesLoadError(FilesError):
    """
    Indicate that there was a problem loading a file.
    """
