"""
This set of demos shows the use of the various settings-related commands.
"""

import json
from pathlib import Path

import typer
from pydantic import BaseModel
from typerdrive.settings.commands import add_settings_subcommand
from typerdrive_demo.helpers import fake_input


def demo_1__bind__basic():
    """
    This function demonstrates the use of the `bind` settings command.
    This command allows you to set the settings values for your app as
    defined in the settings model. It will allow you to override
    defaults. After updating the settings model, the updated values are
    written to disk where they can be retrieved for future commands.
    After the `bind` command is complete, it shows the updated settings.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--name=jawa", "--planet=tatooine"])


def demo_2__bind__invalid_settings():
    """
    This function demonstrates how the `bind` settings command
    requires all settings that do not have a default to be provided
    a value through the command line. If any of these required values
    are not included, the CLI app will show an error message.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--name=jawa"])


def demo_3__bind__help():
    """
    This function demonstrates the help text that's provided with
    the `bind` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "bind", "--help"])


def demo_4__update():
    """
    This function demonstrates the use of the `update` settings command.
    This command allows you to set _some_ of the settings values for your
    app as defined in the settings model. Unlike the `bind` command,
    `update` allows the settings to have missing values that result in an
    invalid state. Any settings options that are not provided are ignored.
    After the `update` command is complete, it shows the updated settings
    including any settings values that are still invalid.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "update", "--planet=tatooine"])


def demo_5__update__help():
    """
    This function demonstrates the help text that's provided with
    the `update` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "update", "--help"])


def demo_6__unset():
    """
    This function demonstrates the use of the `unset` settings command.
    This command allows you to return settings values to their defaults.
    If a selected settings value does not have a default, it will just
    be removed from the settings. The `unset` command allows the final
    settings to be in an invalid state. After the `unset` command is
    complete, it shows the updated settings including any settings
    values that are still invalid.

    Note:
        To demonstrate this working, we need to hack the settings file
        before the command is invoked.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    settings_path = Path.home() / ".local/share/demo_6__unset/settings.json"
    settings_path.write_text(
        json.dumps(
            dict(
                name="hutt",
                planet="nal hutta",
                is_humanoid=False,
                alignment="evil",
            ),
        ),
    )

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "unset", "--name", "--alignment"])


def demo_7__unset__help():
    """
    This function demonstrates the help text that's provided with
    the `unset` command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "unset", "--help"])


def demo_8__show():
    """
    This function demonstrates the `show` command. It simply shows
    the current settings.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)
    cli(["settings", "show"])


def demo_9__reset():
    """
    This function demonstrates the `reset` command. It clears all the
    settings. All settings values with defaults are reset to their
    defaults. All settings values without defaults are just removed.
    After the `reset` command is complete, it shows the updated settings
    including any settings values that are now invalid.

    Note:
        To demonstrate this working, we need to hack the settings file
        before the command is invoked. We also need to add a forced
        confirmation because this command requires you to confirm before
        it proceeds.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str
        is_humanoid: bool = True
        alignment: str = "neutral"

    settings_path = Path.home() / ".local/share/demo_9__reset/settings.json"
    settings_path.write_text(
        json.dumps(
            dict(
                name="hutt",
                planet="nal hutta",
                is_humanoid=False,
                alignment="evil",
            ),
        ),
    )

    cli = typer.Typer()
    add_settings_subcommand(cli, ExampleSettings)

    fake_input("y")
    cli(["settings", "reset"])
