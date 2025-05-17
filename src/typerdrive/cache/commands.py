"""
Provide commands that can be added to a `typer` app to interact with the cache.
"""

from typing import Annotated

import typer

from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.handle_errors import handle_errors
from typerdrive.format import terminal_message


@handle_errors("Failed to clear cache", handle_exc_class=CacheError)
@attach_cache()
def clear(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Option(help="Clear only the entry matching this path. If not provided, clear the entire cache"),
    ] = None,
):
    """
    Remove data from the cache.

    Parameters:
        path: If provided, only remove the data at the given cache key. Otherwise, clear the entire cache.
    """
    manager: CacheManager = get_cache_manager(ctx)
    if path:
        manager.clear_path(path)
        terminal_message(f"Cleared entry at cache target {str(path)}")
    else:
        typer.confirm("Are you sure you want to clear the entire cache?", abort=True)
        count = manager.clear_all()
        terminal_message(f"Cleared all {count} files from cache")


def add_clear(cli: typer.Typer):
    """
    Add the `clear` command to the given `typer` app.
    """
    cli.command()(clear)


@handle_errors("Failed to show cache", handle_exc_class=CacheError)
@attach_cache(show=True)
def show(ctx: typer.Context):  # pyright: ignore[reportUnusedParameter]
    """
    Show the current cache directory.
    """
    pass


def add_show(cli: typer.Typer):
    """
    Add the `show` command to the given `typer` app.
    """
    cli.command()(show)


def add_cache_subcommand(cli: typer.Typer):
    """
    Add all `cache` subcommands to the given app.
    """
    cache_cli = typer.Typer(help="Manage cache for the app")

    for cmd in [add_clear, add_show]:
        cmd(cache_cli)

    cli.add_typer(cache_cli, name="cache")
