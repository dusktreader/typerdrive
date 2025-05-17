"""
Provide a class for managing the `typerdrive` settings feature.
"""

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
    """
    Manage settings for the `typerdrive` app.
    """

    settings_model: type[BaseModel]
    """ A `pydantic` model _type_ that defines the app's settings """

    settings_path: Path
    """ The path to the file where settings are persisted """

    invalid_warnings: dict[str, str]
    """ Tracks which fields of the settings instance are invalid """

    settings_instance: BaseModel
    """ An instance of the `settings_model` that holds the app's current settings """

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
        """
        Given a `ValidationError`, extract the field names and messages to the `invalid_warnings` dict.
        """
        self.invalid_warnings = {}
        for data in err.errors():
            key: str = cast(str, data["loc"][0])
            message = data["msg"]
            self.invalid_warnings[key] = message

    def update(self, **settings_values: Any):
        """
        Update the app settings given the provided key/value pairs.

        If validation fails, the `invalid_warngings` will be updated, but all valid fields will remain set.
        """
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
        """
        Remove all the settings corresponding to the provided keys.
        """
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
        """
        Reset the settings back to defaults.
        """
        logger.debug("Resetting all settings")

        with SettingsResetError.handle_errors("Failed to reset settings"):
            try:
                self.settings_instance = self.settings_model()
                self.invalid_warnings = {}
            except ValidationError as err:
                self.settings_instance = self.settings_model.model_construct()
                self.set_warnings(err)

    def validate(self):
        """
        Validate the current settings values.

        If invalid, `ValidationError` exceptions will be raised
        """
        self.settings_model(**self.settings_instance.model_dump())

    def pretty(self, with_style: bool = True) -> str:
        """
        Return a pretty representation of the settings.
        """
        (bold_, _bold) = ("[bold]", "[/bold]") if with_style else ("", "")
        (red_, _red) = ("[red]", "[/red]") if with_style else ("", "")
        lines: list[str] = []
        parts: list[tuple[str, Any]] = []
        for field_name in self.settings_instance.__class__.model_fields:
            if field_name == "invalid_warning":
                continue
            try:
                field_string = str(getattr(self.settings_instance, field_name))
            except AttributeError:
                field_string = "<UNSET>"
            if field_name in self.invalid_warnings:
                field_string = f"{red_}{field_string}{_red}"
            parts.append((dasherize(field_name), field_string))

        max_field_len = max(len(field_name) for field_name, _ in parts)
        lines.extend(f"{bold_}{k:>{max_field_len}}{_bold} -> {v}" for k, v in parts)

        if self.invalid_warnings:
            lines.append("")
            lines.append(f"{red_}Settings are invalid:{_red}")
            lines.extend(
                f"{bold_}{dasherize(k):>{max_field_len}}{_bold} -> {v}" for k, v in self.invalid_warnings.items()
            )

        return "\n".join(lines)

    def save(self):
        """
        Write the current settings to disk.
        """
        logger.debug(f"Saving settings to {self.settings_path}")

        with SettingsSaveError.handle_errors(f"Failed to save settings to {self.settings_path}"):
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(self.settings_instance.model_dump_json(indent=2))
