from loguru import logger

from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.commands import add_cache_subcommand
from typerdrive.cache.exceptions import CacheClearError, CacheError, CacheInitError, CacheLoadError, CacheStoreError
from typerdrive.cache.manager import CacheManager
from typerdrive.cache.models import CacheStats
from typerdrive.client.attach import attach_client, get_client, get_client_manager
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.client.manager import ClientManager
from typerdrive.config import TyperdriveConfig, get_typerdrive_config, set_typerdrive_config
from typerdrive.constants import EvictionPolicy, Validation
from typerdrive.exceptions import TyperdriveError
from typerdrive.files.attach import attach_files, get_files_manager
from typerdrive.files.commands import add_files_subcommand
from typerdrive.files.exceptions import FilesClearError, FilesError, FilesInitError, FilesLoadError, FilesStoreError
from typerdrive.files.manager import FilesManager
from typerdrive.format import simple_message, strip_rich_style, terminal_message
from typerdrive.handle_errors import handle_errors
from typerdrive.logging.attach import attach_logging, get_logging_manager
from typerdrive.logging.commands import add_logs_subcommand
from typerdrive.logging.exceptions import LoggingError
from typerdrive.logging.manager import LoggingManager
from typerdrive.logging.utilities import log_error
from typerdrive.settings.attach import attach_settings, get_settings, get_settings_manager, get_settings_value
from typerdrive.settings.commands import add_settings_subcommand
from typerdrive.settings.exceptions import (
    SettingsError,
    SettingsInitError,
    SettingsResetError,
    SettingsSaveError,
    SettingsUnsetError,
    SettingsUpdateError,
)
from typerdrive.settings.manager import SettingsManager

# Disable the logger unless @attach_logging is used
logger.disable("typerdrive")


__all__ = [
    "CacheClearError",
    "CacheError",
    "CacheInitError",
    "CacheLoadError",
    "CacheManager",
    "CacheStats",
    "CacheStoreError",
    "ClientError",
    "ClientManager",
    "FilesClearError",
    "FilesError",
    "FilesInitError",
    "FilesLoadError",
    "FilesManager",
    "FilesStoreError",
    "LoggingError",
    "LoggingManager",
    "SettingsError",
    "SettingsInitError",
    "SettingsManager",
    "SettingsResetError",
    "SettingsSaveError",
    "SettingsUnsetError",
    "SettingsUpdateError",
    "TyperdriveClient",
    "TyperdriveConfig",
    "TyperdriveError",
    "EvictionPolicy",
    "Validation",
    "add_cache_subcommand",
    "add_files_subcommand",
    "add_logs_subcommand",
    "add_settings_subcommand",
    "attach_cache",
    "attach_client",
    "attach_files",
    "attach_logging",
    "attach_settings",
    "get_cache_manager",
    "get_client",
    "get_client_manager",
    "get_files_manager",
    "get_logging_manager",
    "get_settings",
    "get_settings_manager",
    "get_settings_value",
    "get_typerdrive_config",
    "handle_errors",
    "log_error",
    "set_typerdrive_config",
    "simple_message",
    "strip_rich_style",
    "terminal_message",
]
