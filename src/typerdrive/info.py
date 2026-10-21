"""
Provide app information commands for a `typer` app.
"""

from typing import Annotated

import typer
from rich import box
from rich.table import Table

from typerdrive.config import get_typerdrive_config
from typerdrive.format import terminal_message


def show_info(
    full: Annotated[bool, typer.Option("--full", help="Show the full Typerdrive configuration.")] = False,
):
    """Show app metadata and, optionally, the full Typerdrive configuration."""
    config = get_typerdrive_config()

    if full:
        config_info = Table(box=box.SIMPLE_HEAD)
        config_info.add_column("Setting", style="bold", no_wrap=True)
        config_info.add_column("Value")
        for key, value in config.model_dump().items():
            config_info.add_row(key, str(value))
        terminal_message(config_info, subject="Typerdrive Config")
        return

    version = config.version or "unknown"
    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold", no_wrap=True)
    info.add_column()
    info.add_row("Name", config.app_name)
    info.add_row("Version", version)
    if config.description:
        info.add_row("Description", config.description)
    terminal_message(info, subject="App Information")


def show_version(
    terse: Annotated[bool, typer.Option("--terse", help="Print only the unformatted version string.")] = False,
):
    """Show the app version."""
    config = get_typerdrive_config()

    if terse:
        message = config.version or "unknown"
    elif not config.version:
        message = f"{config.app_name} (version unknown)"
    else:
        message = f"{config.app_name} v{config.version}"

    typer.echo(message)


def add_info_subcommand(cli: typer.Typer):
    """Add the `info` and `version` commands to the given `typer` app."""
    cli.command(name="version")(show_version)
    cli.command(name="info")(show_info)
