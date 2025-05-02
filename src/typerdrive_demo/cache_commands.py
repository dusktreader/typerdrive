"""
This set of demos shows the use of the various settings-related commands.
"""

import typer
from typerdrive.cache.commands import add_cache_subcommand
from typerdrive.cache.manager import CacheManager

from typerdrive_demo.helpers import fake_input


def demo_1__clear__specific_path():
    """
    This function demonstrates the use of the `clear` cache command
    targeting a specific item of cached data identified by its path.
    """

    manager = CacheManager("demo_1__clear__specific_path")
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

    cli = typer.Typer()
    add_cache_subcommand(cli)
    cli(["cache", "clear", "--path=jawa.txt"])


def demo_2__clear__full_cache():
    """
    This function demonstrates the use of the `clear` cache command
    clearing out the entire cache. Note that the command requires
    confirmation before proceeding with the deletion.
    """

    manager = CacheManager("demo_2__clear__full_cache")
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

    cli = typer.Typer()
    add_cache_subcommand(cli)

    fake_input("y")
    cli(["cache", "clear"])


def demo_3__show():
    """
    This function demonstrates the use of the `show` cache command.
    This command shows the full directory structure of the cache
    including the size of the files within it.
    """

    manager = CacheManager("demo_3__show")
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

    cli = typer.Typer()
    add_cache_subcommand(cli)

    cli(["cache", "show"])
