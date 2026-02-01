"""
Provide commands that can be added to a `typer` app to interact with the cache.
"""

from typing import Annotated

import typer

from typerdrive.cache.attach import attach_cache, get_cache_manager
from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.format import terminal_message
from typerdrive.handle_errors import handle_errors


@handle_errors("Failed to clear cache", handle_exc_class=CacheError)
@attach_cache()
def clear(
    ctx: typer.Context,
    group: Annotated[
        str | None,
        typer.Option(help="Clear only entries with this group. If not provided, clear entire cache"),
    ] = None,
):
    """
    Remove multiple entries from the cache.

    Parameters:
        group: If provided, only remove entries with this group. Otherwise, clear entire cache.
    """
    manager: CacheManager = get_cache_manager(ctx)

    if group:
        count = manager.clear(group=group)
        terminal_message(f"Cleared {count} entries with group '{group}'")
    else:
        typer.confirm("Are you sure you want to clear the entire cache?", abort=True)
        count = manager.clear()
        terminal_message(f"Cleared {count} entries from cache")


def add_clear(cli: typer.Typer):
    """
    Add the `clear` command to the given `typer` app.
    """
    cli.command()(clear)


@handle_errors("Failed to show cache", handle_exc_class=CacheError)
@attach_cache()
def show(
    ctx: typer.Context,
    group: Annotated[
        str | None,
        typer.Option(help="Filter entries by group"),
    ] = None,
    stats: Annotated[
        bool,
        typer.Option(help="Show cache statistics instead of entries"),
    ] = False,
):
    """
    Show cache contents or statistics.

    Parameters:
        group: Optional group to filter entries
        stats: If True, show statistics instead of entries
    """
    manager: CacheManager = get_cache_manager(ctx)
    manager.show(group=group, show_stats=stats)


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
