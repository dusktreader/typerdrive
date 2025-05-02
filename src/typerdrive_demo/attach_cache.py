"""
This set of demos shows the use of the `attach_cache` decorator.
"""

import json

import typer
from rich import print

from typerdrive.cache.manager import get_cache_path
from typerdrive.cache.attach import attach_cache, get_manager


def demo_1__attach_cache__storing_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to store data to the cache. The decorator gives you to access the
    `CacheManager` within a typer command. The `CacheManager` can store
    bytes, text, or JSON data in the cache. In order to use this decorator,
    your command must take a `typer.Context` object as the first argument.
    """

    cli = typer.Typer()

    @cli.command()
    @attach_cache()
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction]
        manager = get_manager(ctx)
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
        print(manager.pretty())

    cli()


def demo_2__attach_cache__loading_data():
    """
    This function demonstrates how to use the `attach_cache` decorator
    to load data from the cache. Because the demos use a temporary
    directory, the cache from the previous command is no longer
    available, so this function pre-seeds the data.
    """

    cache_path = get_cache_path("demo_2__attach_cache__loading_data")
    jawa_path = cache_path / "jawa.txt"
    jawa_path.parent.mkdir(parents=True, exist_ok=True)
    jawa_path.write_text("Utinni!")
    ewok_path = cache_path / "ewok"
    ewok_path.parent.mkdir(parents=True, exist_ok=True)
    ewok_path.write_bytes(b"Yub Nub!")
    jabba_path = cache_path / "hutt/jabba.json"
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
    @attach_cache()
    def report(ctx: typer.Context):  # pyright: ignore[reportUnusedFunction]
        manager = get_manager(ctx)
        jawa_quote = manager.load_text("jawa.txt")
        ewok_quote = manager.load_bytes("ewok").decode("utf-8")
        jabba_quote = manager.load_json("hutt/jabba.json")["quote"]
        print(f"The jawa says: '{jawa_quote}'")
        print(f"The ewok says: '{ewok_quote}'")
        print(f"Jabba the Hutt says: '{jabba_quote}'")

    cli()
