from loguru import logger

from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.commands import add_cache_subcommand
from typerdrive.cache.exceptions import CacheClearError, CacheError, CacheInitError, CacheLoadError, CacheStoreError
from typerdrive.cache.manager import CacheManager
from typerdrive.client.attach import attach_client, get_client, get_client_manager
from typerdrive.client.base import TyperdriveClient
from typerdrive.client.exceptions import ClientError
from typerdrive.client.manager import ClientManager
from typerdrive.config import TyperdriveConfig, get_typerdrive_config, set_typerdrive_config
from typerdrive.constants import Validation
from typerdrive.exceptions import TyperdriveError, handle_errors
from typerdrive.format import simple_message, strip_rich_style, terminal_message
from typerdrive.logging.attach import attach_logging, get_logging_manager
from typerdrive.logging.commands import add_logs_subcommand
from typerdrive.logging.exceptions import LoggingError
from typerdrive.logging.manager import LoggingManager
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
    "CacheStoreError",
    "ClientError",
    "ClientManager",
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
    "Validation",
    "add_cache_subcommand",
    "add_logs_subcommand",
    "add_settings_subcommand",
    "attach_cache",
    "attach_client",
    "attach_logging",
    "attach_settings",
    "get_cache_manager",
    "get_client",
    "get_client_manager",
    "get_logging_manager",
    "get_settings",
    "get_settings_manager",
    "get_settings_value",
    "get_typerdrive_config",
    "handle_errors",
    "set_typerdrive_config",
    "simple_message",
    "strip_rich_style",
    "terminal_message",
]
