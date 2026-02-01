"""
This set of demos shows the use of the `attach_cache` decorator.
"""

from datetime import timedelta

import typer
from rich import print
from typerdrive import (
    CacheManager,
    attach_cache,
    get_cache_manager,
    set_typerdrive_config,
)

set_typerdrive_config(app_name="attach-cache-demo")


def demo_1__attach_cache__storing_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to store data to the cache. The decorator gives you access to the
    `CacheManager` within a typer command by adding a parameter with
    `CacheManager` type. Note that the manager argument name can be
    anything you like. The `CacheManager` can store any picklable Python
    object including bytes, strings, dicts, lists, and Pydantic models.
    In order to use this decorator, your command must take a
    `typer.Context` object as the first argument.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedFunction]
        # Store simple string
        manager.set("jawa", "Utinni!")

        # Store bytes
        manager.set("ewok", b"Yub Nub!")

        # Store dict with group
        manager.set(
            "hutt/jabba",
            dict(
                full_name="Jabba Desilijic Tiure",
                age=604,
                quote="beeska chata wnow kong bantha poodoo!",
            ),
            group="characters",
        )

    cli()


def demo_2__attach_cache__loading_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to load data from the cache. First we pre-populate the cache with
    some data, then load it back.
    """

    # Pre-populate the cache
    manager = CacheManager()
    manager.set("jawa", "Utinni!")
    manager.set("ewok", b"Yub Nub!")
    manager.set(
        "hutt/jabba",
        dict(
            full_name="Jabba Desilijic Tiure",
            age=604,
            quote="beeska chata wnow kong bantha poodoo!",
        ),
    )

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedFunction]
        jawa_quote = manager.get("jawa")
        ewok_quote = manager.get("ewok")
        if isinstance(ewok_quote, bytes):
            ewok_quote = ewok_quote.decode("utf-8")
        jabba_data = manager.get("hutt/jabba")
        jabba_quote = jabba_data["quote"] if jabba_data else "unknown"

        print(f"The jawa says: '{jawa_quote}'")
        print(f"The ewok says: '{ewok_quote}'")
        print(f"Jabba the Hutt says: '{jabba_quote}'")

    cli()


def demo_3__attach_cache__expiration_and_groups():
    """
    This function demonstrates the use of expiration times and groups
    for organizing cache entries.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedFunction]
        # Store with 1 hour expiration
        manager.set(
            "session_token",
            "secret-token-12345",
            expire=timedelta(hours=1),
        )

        # Store multiple entries with the same group
        manager.set("user:1", {"name": "Luke"}, group="users")
        manager.set("user:2", {"name": "Leia"}, group="users")
        manager.set("user:3", {"name": "Han"}, group="users")

        print("Stored session token and user data")

    cli()


def demo_4__attach_cache__access_through_context():
    """
    This function demonstrates how the cache manager can also be accessed
    through the Typer context if you do not want to use a `CacheManager`
    parameter. To access the manager with the context, use the
    `get_cache_manager()` helper function
    """

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction]
        manager = get_cache_manager(ctx)

        # Store data using context-retrieved manager
        manager.set("jawa", "Utinni!")
        manager.set("ewok", b"Yub Nub!")
        manager.set(
            "hutt/jabba",
            dict(
                full_name="Jabba Desilijic Tiure",
                age=604,
                quote="beeska chata wnow kong bantha poodoo!",
            ),
        )

    cli()
