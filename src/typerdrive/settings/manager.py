import json
from pathlib import Path
from typing import Any, cast

from inflection import dasherize
from loguru import logger
from pydantic import BaseModel, ValidationError

from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.settings.exceptions import (
    SettingsInitError,
    SettingsResetError,
    SettingsSaveError,
    SettingsUnsetError,
    SettingsUpdateError,
)


class SettingsManager:
    settings_model: type[BaseModel]
    settings_path: Path
    invalid_warnings: dict[str, str]
    settings_instance: BaseModel

    def __init__(self, settings_model: type[BaseModel]):
        config: TyperdriveConfig = get_typerdrive_config()

        self.settings_model = settings_model
        self.settings_path = config.settings_path
        self.invalid_warnings = {}

        with SettingsInitError.handle_errors("Failed to initialize settings"):
            settings_values: dict[str, Any] = {}
            if self.settings_path.exists():
                settings_values = json.loads(self.settings_path.read_text())
            try:
                self.settings_instance = self.settings_model(**settings_values)
            except ValidationError as err:
                self.settings_instance = self.settings_model.model_construct(**settings_values)
                self.set_warnings(err)

    def set_warnings(self, err: ValidationError):
        self.invalid_warnings = {}
        for data in err.errors():
            key: str = cast(str, data["loc"][0])
            message = data["msg"]
            self.invalid_warnings[key] = message

    def update(self, **settings_values: Any):
        logger.debug(f"Updating settings with {settings_values}")

        with SettingsUpdateError.handle_errors("Failed to update settings"):
            combined_settings = {**self.settings_instance.model_dump(), **settings_values}
            try:
                self.settings_instance = self.settings_model(**combined_settings)
                self.invalid_warnings = {}
            except ValidationError as err:
                self.settings_instance = self.settings_model.model_construct(**combined_settings)
                self.set_warnings(err)

    def unset(self, *unset_keys: str):
        logger.debug(f"Unsetting keys {unset_keys}")

        with SettingsUnsetError.handle_errors("Failed to remove keys"):
            settings_values = {k: v for (k, v) in self.settings_instance.model_dump().items() if k not in unset_keys}
            try:
                self.settings_instance = self.settings_model(**settings_values)
                self.invalid_warnings = {}
            except ValidationError as err:
                self.settings_instance = self.settings_model.model_construct(**settings_values)
                self.set_warnings(err)

    def reset(self):
        logger.debug("Resetting all settings")

        with SettingsResetError.handle_errors("Failed to reset settings"):
            try:
                self.settings_instance = self.settings_model()
                self.invalid_warnings = {}
            except ValidationError as err:
                self.settings_instance = self.settings_model.model_construct()
                self.set_warnings(err)

    def validate(self):
        self.settings_model(**self.settings_instance.model_dump())

    def pretty(self, with_style: bool = True) -> str:
        (bold_, _bold) = ("[bold]", "[/bold]") if with_style else ("", "")
        (red_, _red) = ("[red]", "[/red]") if with_style else ("", "")
        lines: list[str] = []
        parts: list[tuple[str, Any]] = []
        for field_name, field_value in self.settings_instance:
            if field_name == "invalid_warning":
                continue
            field_string = str(field_value)
            if field_name in self.invalid_warnings:
                field_string = f"{red_}{field_string}{_red}"
            parts.append((dasherize(field_name), field_string))

        max_field_len = max(len(field_name) for field_name, _ in parts)
        lines.extend(f"{bold_}{k:>{max_field_len}}{_bold} -> {v}" for k, v in parts)

        if self.invalid_warnings:
            lines.append("")
            lines.append(f"{red_}Settings are invalid:{_red}")
            lines.extend(f"{bold_}{k:>{max_field_len}}{_bold} -> {v}" for k, v in self.invalid_warnings.items())

        return "\n".join(lines)

    def save(self):
        logger.debug(f"Saving settings to {self.settings_path}")

        with SettingsSaveError.handle_errors(f"Failed to save settings to {self.settings_path}"):
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(self.settings_instance.model_dump_json(indent=2))
