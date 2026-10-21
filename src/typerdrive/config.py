"""
Provide controls for the configuration of `typerdrive` itself.

Note:
    This is _distinct_ from the functionality provided in the `settings` module.

    The `settings` feature is for configuring the app built with `typerdrive`. Usually, settings reflect behavior
    specific to the app.

    The `config` feature is for configuring `typerdrive` behavior and app metadata that `typerdrive` uses, such as the
    app name, version, and description. It should not be used to manage the app's own behavior.
"""

import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, computed_field
from xdg_base_dirs import xdg_state_home, xdg_cache_home

from typerdrive.exceptions import TyperdriveError
from typerdrive.types import FileRetentionSpec, FileRotationSpec, FileCompressionSpec


class TyperdriveConfig(BaseModel):
    """
    Define the configurable attributes of `typerdrive`.

    This class uses the XDG Base Directory specification for storing application data:
    - Logs and settings use XDG_STATE_HOME (defaults to ~/.local/state)
    - Cache data uses XDG_CACHE_HOME (defaults to ~/.cache)
    """

    app_name: str = sys.argv[0].split("/")[-1]
    """
    The name of the app built on `typerdrive`. Use this setting if you want to override the default behavior of using
    `sys.argv[0]`.
    """

    version: str | None = None
    """
    The version of the app built on `typerdrive`.
    """

    description: str | None = None
    """
    A short description of the app built on `typerdrive`.
    """

    log_file_rotation: FileRotationSpec = "1 week"
    """
    Define the how often logs should be rotated. See the [`loguru` docs](
        https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression
    ) for more information.
    """

    log_file_retention: FileRetentionSpec = "1 month"
    """
    Define the how soon logs should be deleted. See the [`loguru` docs](
        https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression
    ) for more information.
    """

    log_file_compression: FileCompressionSpec = "tar.gz"
    """
    Define whether rotated logs should be compressed. See the [`loguru` docs](
        https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression
    ) for more information.
    """

    log_file_name: str = "app.log"
    """
    The name of the file where logs will be written. This file will be created in the `log_dir` directory.
    """

    console_width: int | None = None
    """
    Set the width of the console for `rich.console`. Will override automatic resizing behavior.
    """

    console_ascii_only: bool = False
    """
    If set, only use ascii characters in the console.
    """

    state_home: Path = Field(default_factory=xdg_state_home)
    """
    Base directory for state data, defaulting to XDG_STATE_HOME.
    """

    cache_home: Path = Field(default_factory=xdg_cache_home)
    """
    Base directory for cache data, defaulting to XDG_CACHE_HOME.
    """

    @computed_field
    @property
    def log_dir(self) -> Path:
        """
        Retrieve the directory where logs will be stored.
        """
        return self.state_home / self.app_name / "logs"

    @computed_field
    @property
    def settings_path(self) -> Path:
        """
        Retrieve the file where settings will be stored.
        """
        return self.state_home / self.app_name / "settings.json"

    @computed_field
    @property
    def cache_dir(self) -> Path:
        """
        Retrieve the directory where the cache data will be stored.
        """
        return self.cache_home / self.app_name

    @computed_field
    @property
    def files_dir(self) -> Path:
        """
        Retrieve the directory where files will be stored.
        """
        return self.state_home / self.app_name / "files"

    @computed_field
    @property
    def database_path(self) -> Path:
        """
        Retrieve the file where the application database will be stored.
        """
        return self.state_home / self.app_name / "db.sqlite"


_typerdrive_config: TyperdriveConfig = TyperdriveConfig.model_construct()


def set_typerdrive_config(**kwargs: Any):
    """
    Update the `TyperdriveConfig` with the provided key/values.
    """
    global _typerdrive_config
    combined_config = {**_typerdrive_config.model_dump(), **kwargs}

    # TyperdriveConfigError?
    with TyperdriveError.handle_errors("Invalid typerdrive config provided"):
        _typerdrive_config = TyperdriveConfig(**combined_config)


def get_typerdrive_config() -> TyperdriveConfig:
    """
    Retrieve the current `TyperdriveConfig`.
    """
    return _typerdrive_config.model_copy()
