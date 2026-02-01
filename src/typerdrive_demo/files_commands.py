"""
This set of demos shows the use of the various files-related commands.
"""

import typer
from typerdrive import FilesManager, add_files_subcommand, set_typerdrive_config

set_typerdrive_config(app_name="files-command-demo")


def demo_1__show__basic():
    """
    This function demonstrates the use of the `show` files command.
    This command displays the files directory structure.
    """

    manager = FilesManager()
    manager.store_text("The Force will be with you.", "quotes/obi-wan.txt")
    manager.store_text("Do or do not. There is no try.", "quotes/yoda.txt")
    manager.store_json({"name": "Luke Skywalker", "occupation": "Jedi Knight"}, "characters/luke.json")

    cli = typer.Typer()
    add_files_subcommand(cli)

    cli(["files", "show"])


def demo_2__workflow__complete():
    """
    This function demonstrates a complete workflow:
    1. Store multiple files in different directories
    2. Show the files structure
    3. Store additional files
    4. Show the updated structure
    """

    manager = FilesManager()

    # Initial store
    manager.store_text("Welcome!", "messages/welcome.txt")
    manager.store_json({"version": "1.0"}, "config/app.json")

    cli = typer.Typer()
    add_files_subcommand(cli)

    print("=" * 60)
    print("Initial files:")
    print("=" * 60)
    cli(["files", "show"])

    print("\n" + "=" * 60)
    print("Adding more files...")
    print("=" * 60)

    # Add more files
    manager.store_text("Goodbye!", "messages/goodbye.txt")
    manager.store_json({"level": "debug"}, "config/logging.json")

    print("\n" + "=" * 60)
    print("Files after adding more:")
    print("=" * 60)
    cli(["files", "show"])
