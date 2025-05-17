"""
Provide exceptions specific to the settings feature of `typerdrive`.
"""

from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class SettingsError(TyperdriveError):
    """
    The base exception for settings errors.
    """
    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class SettingsInitError(SettingsError):
    """
    Indicates that there was a problem initializing the settings.
    """


class SettingsUnsetError(SettingsError):
    """
    Indicates that there was a problem unsetting a settings value.
    """


class SettingsResetError(SettingsError):
    """
    Indicates that there was a problem resetting a settings value.
    """


class SettingsUpdateError(SettingsError):
    """
    Indicates that there was a problem updating a settings value.
    """


class SettingsSaveError(SettingsError):
    """
    Indicates that there was a problem saving the settings to disk.
    """
