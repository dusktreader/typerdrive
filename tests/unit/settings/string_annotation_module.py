# This module intentionally uses `from __future__ import annotations` so that
# all annotations are stored as strings rather than evaluated types.  This
# replicates the annotation-evaluation behaviour introduced in Python 3.14
# (PEP 649) and lets us test `attach_settings` against string annotations on
# any supported Python version.
from __future__ import annotations

import typer
from typerdrive.settings.attach import attach_settings, get_settings
from typerdrive.settings.manager import SettingsManager

from tests.unit.settings.models import DefaultSettingsModel


def make_string_annotated_cli() -> typer.Typer:
    """
    Return a Typer app whose command functions have string annotations.

    Because this module uses `from __future__ import annotations`, every type
    annotation in every function defined here is stored as a plain string in
    `__annotations__`.  Passing such a function to `attach_settings` previously
    caused a `NameError` because the decorator compared raw annotation strings
    against type objects using `is`.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_settings(DefaultSettingsModel)
    def noop(ctx: typer.Context, stuff: DefaultSettingsModel) -> None:
        settings = get_settings(ctx, DefaultSettingsModel)
        assert settings.name == "jawa"
        print("Passed!")

    return cli


def make_string_annotated_manager_cli() -> typer.Typer:
    """
    Return a Typer app whose command uses a `SettingsManager` parameter with string annotations.
    """
    cli = typer.Typer()

    @cli.command()
    @attach_settings(DefaultSettingsModel)
    def noop(ctx: typer.Context, mgr: SettingsManager) -> None:
        assert isinstance(mgr, SettingsManager)
        print("Passed!")

    return cli
