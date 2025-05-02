from typerdrive.constants import ExitCode
from typerdrive.exceptions import TyperdriveError


class SettingsError(TyperdriveError):
    exit_code: ExitCode = ExitCode.GENERAL_ERROR


class SettingsInitError(SettingsError):
    pass


class SettingsUnsetError(SettingsError):
    pass


class SettingsResetError(SettingsError):
    pass


class SettingsUpdateError(SettingsError):
    pass


class SettingsSaveError(SettingsError):
    pass
