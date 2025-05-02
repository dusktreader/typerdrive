"""
This set of demos shows the use of the `attach_settings` decorator.
"""

import typer
from pydantic import BaseModel
from typerdrive.constants import Validation
from typerdrive.settings.attach import attach_settings, get_settings


def demo_1__attach_settings__basic():
    """
    This function demonstrates the use of the `attach_settings` decorator.
    This decorator allows you to attach a Pydantic model to a typer command.
    In order to use this decorator, your command must take a `typer.Context`
    object as the first argument.
    """

    class ExampleSettings(BaseModel):
        name: str = "jawa"
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction]
        settings: ExampleSettings = get_settings(ctx, ExampleSettings)
        print(f"Look at this {settings.name} from {settings.planet}. It's soooo {settings.alignment}!")

    cli()


def demo_2__attach_settings__enforce_validation():
    """
    This function demonstrates how the `attach_settings` decorator will,
    by default, require the settings to be valid before they can be
    attached to the app's context.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings)
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        print("We will never got to this line")

    cli()


def demo_3__attach_settings__allow_invalid():
    """
    This function demonstrates how the `validation` argument passed to the
    `attach_settings` decorator works. By default this flag is set to
    `Validation.BEFORE`, meaning the settings must be valid before it is
    attached to the app's context. If you set it to `Validation.NONE`, the
    settings will be bound even if there are invalid settings. This is
    important because your settings may have non-default settings that need
    to be set _through_ a command.
    """

    class ExampleSettings(BaseModel):
        name: str
        planet: str = "tatooine"
        alignment: str = "neutral"

    cli = typer.Typer()

    @cli.command()
    @attach_settings(ExampleSettings, validation=Validation.NONE)
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction]
        settings: ExampleSettings = get_settings(ctx, ExampleSettings)
        print(f"Here are the settings that are missing a required field: {settings}")

    cli()
