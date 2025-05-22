"""
Provide a class for managing the `typerdrive` settings feature.
"""

import json
from pathlib import Path
from typing import Any, cast

from inflection import dasherize
from loguru import logger
from pydantic import BaseModel, ValidationError
from rich.console import Group, RenderableType
from rich.table import Table

from typerdrive.config import TyperdriveConfig, get_typerdrive_config
from typerdrive.format import pretty_field_info
from typerdrive.settings.exceptions import (
    SettingsDisplayError,
    SettingsInitError,
    SettingsResetError,
    SettingsSaveError,
    SettingsUnsetError,
    SettingsUpdateError,
)
from typerdrive.settings.utilities import construct_permissive


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

    settings_instance: BaseModel  # pyright: ignore[reportUninitializedInstanceVariable]
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
            self.construct_instance(**settings_values)

    def construct_instance(self, **settings_values: Any):
        try:
            self.settings_instance = self.settings_model(**settings_values)
            self.invalid_warnings = {}
        except ValidationError as err:
            self.settings_instance = construct_permissive(self.settings_model, **settings_values)
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
            combined_settings = {**self.settings_instance.model_dump(mode="json"), **settings_values}
            self.construct_instance(**combined_settings)

    def unset(self, *unset_keys: str):
        """
        Remove all the settings corresponding to the provided keys.
        """
        logger.debug(f"Unsetting keys {unset_keys}")

        with SettingsUnsetError.handle_errors("Failed to remove keys"):
            settings_values = {k: v for (k, v) in self.settings_instance.model_dump(mode="json").items() if k not in unset_keys}
            self.construct_instance(**settings_values)

    def reset(self):
        """
        Reset the settings back to defaults.
        """
        logger.debug("Resetting all settings")

        with SettingsResetError.handle_errors("Failed to reset settings"):
            self.construct_instance()

    def validate(self):
        """
        Validate the current settings values.

        If invalid, `ValidationError` exceptions will be raised
        """
        self.settings_model(**self.settings_instance.model_dump(mode="json"))

    def pretty(self, with_style: bool = True) -> RenderableType:
        """
        Return a pretty representation of the settings.
        """
        (bold_, _bold) = ("[bold]", "[/bold]") if with_style else ("", "")
        (italic_, _italic) = ("[italic]", "[/italic]") if with_style else ("", "")
        (underline_, _underline) = ("[underline]", "[/underline]") if with_style else ("", "")
        (red_, _red) = ("[red]", "[/red]") if with_style else ("", "")
        (blue_, _blue) = ("[blue]", "[/blue]") if with_style else ("", "")

        nested: list[str] = []

        items: list[RenderableType] = []

        values_table: Table = Table(
            title="Settings Values",
            title_style="bold underline",
            title_justify="left",
            box=None,
        )
        values_table.add_column(justify="right", style="bold", no_wrap=True)
        values_table.add_column(justify="left", style="italic", no_wrap=True)
        values_table.add_column(justify="center")
        values_table.add_column(justify="left", no_wrap=True)

        for (field_name, field_info) in self.settings_instance.__class__.model_fields.items():
            if field_name == "invalid_warning":
                continue
            try:
                field_string = str(getattr(self.settings_instance, field_name))
            except AttributeError:
                field_string = "<UNSET>"
            if field_name in self.invalid_warnings:
                field_string = f"{red_}{field_string}{_red}"
            annotation = SettingsDisplayError.enforce_defined(field_info.annotation, f"The field info annotation for {field_info} was not defined!")
            field_type: str = f"{italic_}{annotation.__name__}{_italic}"
            if issubclass(annotation, BaseModel):
                field_type = f"{blue_}{field_type}*{_blue}"
                nested.append(pretty_field_info(field_info))
            values_table.add_row(
                dasherize(field_name),
                field_type,
                "->",
                field_string
            )

        items.append(values_table)

        if self.invalid_warnings:
            items.append("")
            items.append("")
            invalid_table: Table = Table(
                title="Invalid Values",
                title_style="bold underline",
                title_justify="left",
                box=None,
            )
            invalid_table.add_column(justify="right", style="bold", no_wrap=True)
            invalid_table.add_column(justify="center")
            invalid_table.add_column(justify="left", no_wrap=True)

            for (field_name, invalid_warning) in self.invalid_warnings.items():
                invalid_table.add_row(
                    dasherize(field_name),
                    "->",
                    invalid_warning,
                )

            items.append(invalid_table)


        if nested:
            items.append("")
            items.append("")
            items.append(f"{blue_}{bold_}{underline_}{_underline}{_bold}{_blue}")
            nested_table: Table = Table(
                title="*Nested Model Types",
                title_style="blue bold underline",
                title_justify="left",
                box=None,
            )
            nested_table.add_column(style="bold")
            for model in nested:
                nested_table.add_row(model)

            items.append(nested_table)

        return Group(*items)


    def save(self):
        """
        Write the current settings to disk.
        """
        logger.debug(f"Saving settings to {self.settings_path}")

        with SettingsSaveError.handle_errors(f"Failed to save settings to {self.settings_path}"):
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings_path.write_text(self.settings_instance.model_dump_json(indent=2))
