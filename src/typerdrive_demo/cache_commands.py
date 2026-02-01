"""
This set of demos shows the use of the various cache-related commands.
"""


import typer
from typerdrive import CacheManager, add_cache_subcommand, set_typerdrive_config

from typerdrive_demo.helpers import fake_input

set_typerdrive_config(app_name="cache-command-demo")


def demo_1__show__basic():
    """
    This function demonstrates the use of the `show` cache command.
    This command displays cache contents in a table format.
    """

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
        group="characters",
    )

    cli = typer.Typer()
    add_cache_subcommand(cli)

    cli(["cache", "show"])


def demo_2__show__with_filters():
    """
    This function demonstrates the use of the `show` cache command
    with group filters.
    """

    manager = CacheManager()
    manager.set("user:1", {"name": "Luke"}, group="users")
    manager.set("user:2", {"name": "Leia"}, group="users")
    manager.set("user:3", {"name": "Han"}, group="users")
    manager.set("session:abc", "token-12345", group="sessions")
    manager.set("config", {"theme": "dark"})

    cli = typer.Typer()
    add_cache_subcommand(cli)

    print("=" * 60)
    print("Showing all entries with 'users' group:")
    print("=" * 60)
    cli(["cache", "show", "--group=users"])


def demo_3__show__stats():
    """
    This function demonstrates the use of the `show` cache command
    with the --stats flag to display cache statistics only.
    """

    manager = CacheManager()
    manager.set("key1", "value1")
    manager.set("key2", "value2")
    manager.set("key3", "value3")

    # Trigger some hits and misses
    manager.get("key1")
    manager.get("key2")
    manager.get("nonexistent")

    cli = typer.Typer()
    add_cache_subcommand(cli)

    print("=" * 60)
    print("First, showing cache entries (with stats at bottom):")
    print("=" * 60)
    try:
        cli(["cache", "show"], standalone_mode=False)
    except SystemExit:
        pass

    print("\n" + "=" * 60)
    print("Now, showing only cache statistics with --stats flag:")
    print("=" * 60)
    try:
        cli(["cache", "show", "--stats"], standalone_mode=False)
    except SystemExit:
        pass


def demo_4__clear__by_group():
    """
    This function demonstrates the use of the `clear` cache command
    to remove all entries with a specific group.
    """

    manager = CacheManager()
    manager.set("user:1", {"name": "Luke"}, group="users")
    manager.set("user:2", {"name": "Leia"}, group="users")
    manager.set("user:3", {"name": "Han"}, group="users")
    manager.set("session", "token-12345", group="sessions")

    cli = typer.Typer()
    add_cache_subcommand(cli)
    cli(["cache", "clear", "--group=users"])


def demo_5__clear__full_cache():
    """
    This function demonstrates the use of the `clear` cache command
    to clear out the entire cache. Note that the command requires
    confirmation before proceeding with the deletion.
    """

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
    add_cache_subcommand(cli)

    fake_input("y")
    cli(["cache", "clear"])
