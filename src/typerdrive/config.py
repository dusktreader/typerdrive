import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, computed_field

from typerdrive.exceptions import TyperdriveError
from typerdrive.types import FileRetentionSpec, FileRotationSpec, FileCompressionSpec


class TyperdriveConfig(BaseModel):
    app_name: str = sys.argv[0].split("/")[-1]
    log_file_rotation: FileRotationSpec = "1 week"
    log_file_retention: FileRetentionSpec = "1 month"
    log_file_compression: FileCompressionSpec = "tar.gz"
    log_file_name: str = "app.log"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def log_dir(self) -> Path:
        return Path.home() / ".local/share" / self.app_name / "logs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def settings_path(self) -> Path:
        return Path.home() / ".local/share" / self.app_name / "settings.json"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cache_dir(self) -> Path:
        return Path.home() / ".cache" / self.app_name


_typerdrive_config: TyperdriveConfig = TyperdriveConfig.model_construct()


def set_typerdrive_config(**kwargs: Any):
    global _typerdrive_config
    combined_config = {**_typerdrive_config.model_dump(), **kwargs}

    # TyperdriveConfigError?
    with TyperdriveError.handle_errors("Invalid typerdrive config provided"):
        _typerdrive_config = TyperdriveConfig(**combined_config)


def get_typerdrive_config() -> TyperdriveConfig:
    return _typerdrive_config.model_copy()
