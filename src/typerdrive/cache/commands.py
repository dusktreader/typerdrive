from typing import Annotated

import typer

from typerdrive.cache.attach import get_manager, attach_cache
from typerdrive.cache.exceptions import CacheError
from typerdrive.cache.manager import CacheManager
from typerdrive.exceptions import handle_errors
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
    manager: CacheManager = get_manager(ctx)
    if path:
        manager.clear_path(path)
        terminal_message(f"Cleared entry at cache target {str(path)}")
    else:
        typer.confirm("Are you sure you want to clear the entire cache?", abort=True)
        count = manager.clear_all()
        terminal_message(f"Cleared all {count} files from cache")


def add_clear(cli: typer.Typer):
    cli.command()(clear)


@handle_errors("Failed to show cache", handle_exc_class=CacheError)
@attach_cache(show=True)
def show(ctx: typer.Context):  # pyright: ignore[reportUnusedParameter]
    pass


def add_show(cli: typer.Typer):
    cli.command()(show)


def add_cache_subcommand(cli: typer.Typer):
    cache_cli = typer.Typer(help="Manage cache for the app")

    for cmd in [add_clear, add_show]:
        cmd(cache_cli)

    cli.add_typer(cache_cli, name="cache")
