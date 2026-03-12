"""
Provide commands that can be added to a `typer` app to interact with files.
"""

import typer

from typerdrive.files.attach import attach_files
from typerdrive.files.exceptions import FilesError
from typerdrive.handle_errors import handle_errors


@handle_errors("Failed to show files", handle_exc_class=FilesError)
@attach_files(show=True)
def show(ctx: typer.Context):
    """
    Show the current files directory.
    """
    pass


def add_show(cli: typer.Typer):
    """
    Add the `show` command to the given `typer` app.
    """
    cli.command()(show)


def add_files_subcommand(cli: typer.Typer):
    """
    Add all `files` subcommands to the given app.
    """
    files_cli = typer.Typer(help="Manage files for the app", invoke_without_command=True, no_args_is_help=True)

    add_show(files_cli)

    cli.add_typer(files_cli, name="files")
