"""
Provide controls for the configuration of `typerdrive` itself.

Note:
    This is _distinct_ from the functionality provided in the `settings` module.
    The `settings` feature is for configuring the app built with `typerdrive`. Usually, settings reflect behavior
    specific to the app.
    The `config` feature is for configuring `typerdrive` internal behavior.
    The `config` features should never be exposed to end-users or used to manage behavior of the app built on top of
    `typerdrive`.
"""

import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, computed_field

from typerdrive.exceptions import TyperdriveError
from typerdrive.types import FileRetentionSpec, FileRotationSpec, FileCompressionSpec


class TyperdriveConfig(BaseModel):
    """
    Define the configurable attributes of `typerdrive`.
    """

    app_name: str = sys.argv[0].split("/")[-1]
    """
    The name of the app built on `typerdrive`. Use this setting if you want to override the default behavior of using
    `sys.argv[0]`.
    """

    log_file_rotation: FileRotationSpec = "1 week"
    """
    Define the how often logs should be rotated. See the
    [`loguru` docs](https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression)
    for more information.
    """

    log_file_retention: FileRetentionSpec = "1 month"
    """
    Define the how soon logs should be deleted. See the
    [`loguru` docs](https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression)
    for more information.
    """

    log_file_compression: FileCompressionSpec = "tar.gz"
    """
    Define whether rotated logs should be compressed. See the
    [`loguru` docs](https://loguru.readthedocs.io/en/stable/overview.html#easier-file-logging-with-rotation-retention-compression)
    for more information.
    """

    log_file_name: str = "app.log"
    """ The name of the file where logs will be written. This file will be created in the `log_dir` directory. """

    console_width: int | None = None
    """ Set the width of the console for `rich.console`. Will override automatic resizing behavior. """

    console_ascii_only: bool = False
    """ If set, only use ascii characters in the console. """

    @computed_field  # type: ignore[prop-decorator]
    @property
    def log_dir(self) -> Path:
        """
        Retrieve the directory where logs will be stored.
        """
        return Path.home() / ".local/share" / self.app_name / "logs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def settings_path(self) -> Path:
        """
        Retrieve the file where settings will be stored.
        """
        return Path.home() / ".local/share" / self.app_name / "settings.json"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cache_dir(self) -> Path:
        """
        Retrieve the directory where the cache data will be stored.
        """
        return Path.home() / ".cache" / self.app_name


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
