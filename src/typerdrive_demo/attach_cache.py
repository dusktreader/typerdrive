"""
This set of demos shows the use of the `attach_cache` decorator.
"""

import json

import typer
from rich import print
from typerdrive import (
    CacheManager,
    TyperdriveConfig,
    attach_cache,
    get_cache_manager,
    get_typerdrive_config,
    set_typerdrive_config,
)

set_typerdrive_config(app_name="attach-cache-demo")


def demo_1__attach_cache__storing_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to store data to the cache. The decorator gives you to access the
    `CacheManager` within a typer command by adding a parameter with
    `CacheManager` type. Note that the manager argument name can be
    anything you like. The `CacheManager` can store bytes, text, or
    JSON data in the cache. In order to use this decorator, your
    command must take a `typer.Context` object as the first argument.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        manager.store_text("Utinni!", "jawa.txt")
        manager.store_bytes(b"Yub Nub!", "ewok")
        manager.store_json(
            dict(
                full_name="Jabba Desilijic Tiure",
                age=604,
                quote="beeska chata wnow kong bantha poodoo!",
            ),
            "hutt/jabba.json",
        )

    cli()


def demo_2__attach_cache__loading_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to load data from the cache. Because the demos use a temporary
    directory, the cache from the previous command is no longer
    available, so this function pre-seeds the data.
    """
    config: TyperdriveConfig = get_typerdrive_config()
    jawa_path = config.cache_dir / "jawa.txt"
    jawa_path.parent.mkdir(parents=True, exist_ok=True)
    jawa_path.write_text("Utinni!")
    ewok_path = config.cache_dir / "ewok"
    ewok_path.parent.mkdir(parents=True, exist_ok=True)
    ewok_path.write_bytes(b"Yub Nub!")
    jabba_path = config.cache_dir / "hutt/jabba.json"
    jabba_path.parent.mkdir(parents=True, exist_ok=True)
    jabba_path.write_text(
        json.dumps(
            dict(
                full_name="Jabba Desilijic Tiure",
                age=604,
                quote="beeska chata wnow kong bantha poodoo!",
            ),
        ),
    )

    cli = typer.Typer()

    @cli.command()
    @attach_cache(show=True)
    def report(ctx: typer.Context, manager: CacheManager):  # pyright: ignore[reportUnusedFunction, reportUnusedParameter]
        jawa_quote = manager.load_text("jawa.txt")
        ewok_quote = manager.load_bytes("ewok").decode("utf-8")
        jabba_quote = manager.load_json("hutt/jabba.json")["quote"]
        print(f"The jawa says: '{jawa_quote}'")
        print(f"The ewok says: '{ewok_quote}'")
        print(f"Jabba the Hutt says: '{jabba_quote}'")

    cli()


def demo_4__attach_settings__access_through_context():
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
        manager.store_text("Utinni!", "jawa.txt")
        manager.store_bytes(b"Yub Nub!", "ewok")
        manager.store_json(
            dict(
                full_name="Jabba Desilijic Tiure",
                age=604,
                quote="beeska chata wnow kong bantha poodoo!",
            ),
            "hutt/jabba.json",
        )

    cli()
